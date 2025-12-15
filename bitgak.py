"""
빗각투자 지표 모듈 (Bitgak Indicators)

빗각투자란?
- 유튜버 인범의 기술적 분석 방법
- 매수자들의 평균단가(매물대)를 분석
- 주가가 평단가에 근접할 때 발생하는 매수 행동 패턴 활용

핵심 지표:
- VWAP: 거래량 가중 평균가 (군중 평균단가)
- CSI: 군중 스트레스 지수 (현재가 vs VWAP)
- HVN: 고거래량 가격대 (매물대)
- 빗각 라인: 고점-저점 연결선
"""

import pandas as pd
import numpy as np


def calculate_bitgak_vwap(df, period=None):
    """
    VWAP (Volume Weighted Average Price) 계산
    = 군중의 평균 매수가

    Args:
        df: OHLCV 데이터프레임
        period: 계산 기간 (None이면 전체 기간)
    """
    if period:
        df_calc = df.tail(period).copy()
    else:
        df_calc = df.copy()

    # 전형적인 가격 (TP) = (고가 + 저가 + 종가) / 3
    typical_price = (df_calc['High'] + df_calc['Low'] + df_calc['Close']) / 3

    # VWAP = Σ(TP × 거래량) / Σ(거래량)
    df['VWAP'] = (typical_price * df_calc['Volume']).cumsum() / df_calc['Volume'].cumsum()

    # 20일 롤링 VWAP (최근 추세 반영)
    tp = (df['High'] + df['Low'] + df['Close']) / 3
    df['VWAP_20'] = (tp * df['Volume']).rolling(20).sum() / df['Volume'].rolling(20).sum()

    return df


def calculate_bitgak_csi(df):
    """
    CSI (Crowd Stress Index) - 군중 스트레스 지수
    = (현재가 - VWAP) / VWAP × 100

    해석:
    - CSI < -10%: 군중 대부분 손실 → 공포/존버 구간
    - CSI > +10%: 군중 대부분 수익 → 차익실현 압력
    - CSI ≈ 0%: 본전 심리 구간 → 매수/탈출 심리 충돌
    """
    if 'VWAP_20' not in df.columns:
        df = calculate_bitgak_vwap(df)

    # 20일 VWAP 기준 CSI (최근 매수자 기준)
    df['CSI'] = (df['Close'] - df['VWAP_20']) / df['VWAP_20'] * 100

    return df


def calculate_bitgak_hvn(df, lookback=60):
    """
    HVN (High Volume Node) - 매물대 계산
    거래량이 집중된 가격대 = 많은 사람이 매수한 가격 = 지지/저항

    Args:
        df: OHLCV 데이터프레임
        lookback: 분석 기간

    Returns:
        HVN 가격대, 근접도 추가된 df
    """
    recent = df.tail(lookback).copy()

    # 거래량 기준 상위 20% 거래일의 평균 가격 = 핵심 매물대
    vol_threshold = recent['Volume'].quantile(0.8)
    high_vol_days = recent[recent['Volume'] >= vol_threshold]

    if len(high_vol_days) > 0:
        # 고거래량일의 가중평균 가격
        hvn_price = (high_vol_days['Close'] * high_vol_days['Volume']).sum() / high_vol_days['Volume'].sum()
    else:
        hvn_price = recent['Close'].mean()

    df['HVN_Price'] = hvn_price

    # 매물대 근접도 (%)
    df['HVN_Proximity'] = abs(df['Close'] - hvn_price) / df['Close'] * 100

    return df, hvn_price


def find_bitgak_lines(df, lookback=60):
    """
    빗각 라인 자동 생성
    - 로컬 고점/저점 중 거래량이 실린 변곡점 찾기
    - 고점-저점 연결하여 빗각 라인 생성

    Returns:
        list of bitgak lines (slope, intercept, type)
    """
    recent = df.tail(lookback).copy()
    vol_avg = recent['Volume'].mean()

    # 로컬 고점 찾기 (5일 기준)
    recent['Local_High'] = recent['High'].rolling(5, center=True).max()
    recent['Local_Low'] = recent['Low'].rolling(5, center=True).min()

    # 거래량이 평균 이상인 변곡점만
    significant_highs = recent[
        (recent['High'] == recent['Local_High']) &
        (recent['Volume'] > vol_avg * 1.3)
    ]
    significant_lows = recent[
        (recent['Low'] == recent['Local_Low']) &
        (recent['Volume'] > vol_avg * 1.3)
    ]

    bitgak_lines = []

    # 하락 빗각: 고점 → 저점 연결
    if len(significant_highs) > 0 and len(significant_lows) > 0:
        # 가장 최근 고점과 저점
        last_high = significant_highs.iloc[-1] if len(significant_highs) > 0 else None
        last_low = significant_lows.iloc[-1] if len(significant_lows) > 0 else None

        if last_high is not None and last_low is not None:
            high_idx = recent.index.get_loc(last_high.name)
            low_idx = recent.index.get_loc(last_low.name)

            if high_idx != low_idx:
                # 기울기 계산
                slope = (last_low['Low'] - last_high['High']) / (low_idx - high_idx)
                intercept = last_high['High'] - slope * high_idx

                bitgak_lines.append({
                    'type': 'falling' if slope < 0 else 'rising',
                    'slope': slope,
                    'intercept': intercept,
                    'high_price': last_high['High'],
                    'low_price': last_low['Low']
                })

    return bitgak_lines


def detect_bitgak_touch(current_price, bitgak_lines, current_idx, tolerance=0.02):
    """
    현재가가 빗각 라인에 터치했는지 감지

    Args:
        current_price: 현재 가격
        bitgak_lines: 빗각 라인 리스트
        current_idx: 현재 인덱스
        tolerance: 허용 오차 (2%)
    """
    for line in bitgak_lines:
        line_price = line['slope'] * current_idx + line['intercept']
        distance = abs(current_price - line_price) / current_price

        if distance < tolerance:
            return True, line['type'], round(line_price, 2)

    return False, None, None


def analyze_bitgak_signal(df, lookback=60):
    """
    빗각 투자 종합 신호 분석

    Returns:
        dict: 빗각 분석 결과
        - score: 빗각 신호 점수 (0~3)
        - signals: 신호 목록
        - csi: 군중 스트레스 지수
        - hvn_proximity: 매물대 근접도
    """
    if len(df) < lookback:
        return {"score": 0, "signals": [], "error": "데이터 부족"}

    # 지표 계산
    df = calculate_bitgak_vwap(df)
    df = calculate_bitgak_csi(df)
    df, hvn_price = calculate_bitgak_hvn(df, lookback)

    latest = df.iloc[-1]
    score = 0
    signals = []

    # 1. VWAP 근접 여부 (CSI -5% ~ +2% = 본전 심리 구간)
    csi = latest.get('CSI', 0)
    if pd.notna(csi):
        if -5 <= csi <= 2:
            score += 1
            signals.append(f"✨ VWAP 근접 (CSI: {csi:.1f}%) - 본전/매수 심리 구간")
        elif csi < -10:
            signals.append(f"😰 CSI {csi:.1f}% - 군중 손실 구간 (공포)")
            score += 0.5  # 역발상 매수 기회
        elif csi > 10:
            signals.append(f"🤑 CSI {csi:.1f}% - 군중 수익 구간 (차익실현 압력)")
            score -= 0.5

    # 2. 매물대(HVN) 근접 여부 (2% 이내)
    hvn_proximity = latest.get('HVN_Proximity', 100)
    if pd.notna(hvn_proximity):
        if hvn_proximity < 2:
            score += 1
            signals.append(f"📍 매물대 터치 ({hvn_proximity:.1f}%) - 반등 기대")
        elif hvn_proximity < 5:
            score += 0.5
            signals.append(f"📍 매물대 근접 ({hvn_proximity:.1f}%)")

    # 3. 빗각 라인 터치
    bitgak_lines = find_bitgak_lines(df, lookback)
    if bitgak_lines:
        touched, line_type, line_price = detect_bitgak_touch(
            latest['Close'],
            bitgak_lines,
            len(df) - 1
        )
        if touched:
            score += 1
            if line_type == 'falling':
                signals.append(f"📐 하락 빗각 터치 (${line_price}) - 반등 포인트")
            else:
                signals.append(f"📐 상승 빗각 터치 (${line_price}) - 지지 확인")

    # 4. RSI 과매도 보조 조건 (기존 RSI 활용)
    rsi = latest.get('RSI', 50)
    if pd.notna(rsi) and rsi < 35:
        score += 0.5
        signals.append(f"🔻 RSI {rsi:.1f} 과매도 (빗각 신호 보강)")

    # 빗각 신호 등급
    if score >= 2.5:
        signal_grade = "STRONG_BITGAK"
        signals.insert(0, "🎯🎯 강한 빗각 매수 신호!")
    elif score >= 1.5:
        signal_grade = "BITGAK"
        signals.insert(0, "🎯 빗각 매수 신호")
    else:
        signal_grade = "NONE"

    return {
        "score": round(score, 1),
        "grade": signal_grade,
        "signals": signals,
        "csi": round(csi, 2) if pd.notna(csi) else None,
        "vwap_20": round(latest.get('VWAP_20', 0), 2),
        "hvn_price": round(hvn_price, 2),
        "hvn_proximity": round(hvn_proximity, 2) if pd.notna(hvn_proximity) else None,
        "bitgak_lines": len(bitgak_lines)
    }


def calculate_all_bitgak(df, lookback=60):
    """빗각 지표 한번에 계산"""
    df = calculate_bitgak_vwap(df)
    df = calculate_bitgak_csi(df)
    df, hvn_price = calculate_bitgak_hvn(df, lookback)
    return df, hvn_price

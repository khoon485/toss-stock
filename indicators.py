"""
기술적 지표 계산 모듈
- 이동평균선 (SMA, EMA)
- 일목균형표 (Ichimoku Cloud)
- RSI (상대강도지수)
- MACD (이동평균수렴확산)
- 볼린저밴드
- ATR (변동성)
- 거래량 분석
"""

import pandas as pd
import numpy as np


def calculate_ma(df, windows=[5, 20, 60]):
    """이동평균선 계산"""
    for w in windows:
        df[f'MA{w}'] = df['Close'].rolling(window=w).mean()
    return df


def calculate_ichimoku(df):
    """일목균형표 계산"""
    # 전환선 (9일)
    high_9 = df['High'].rolling(window=9).max()
    low_9 = df['Low'].rolling(window=9).min()
    df['Tenkan'] = (high_9 + low_9) / 2

    # 기준선 (26일)
    high_26 = df['High'].rolling(window=26).max()
    low_26 = df['Low'].rolling(window=26).min()
    df['Kijun'] = (high_26 + low_26) / 2

    # 선행스팬 A (전환선 + 기준선) / 2, 26일 앞으로
    df['SpanA'] = ((df['Tenkan'] + df['Kijun']) / 2).shift(26)

    # 선행스팬 B (52일 고가 + 저가) / 2, 26일 앞으로
    high_52 = df['High'].rolling(window=52).max()
    low_52 = df['Low'].rolling(window=52).min()
    df['SpanB'] = ((high_52 + low_52) / 2).shift(26)

    # 후행스팬 (현재 종가, 26일 뒤로)
    df['Chikou'] = df['Close'].shift(-26)

    return df


def calculate_rsi(df, period=14):
    """RSI (상대강도지수) 계산"""
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    return df


def calculate_macd(df, fast=12, slow=26, signal=9):
    """MACD 계산"""
    df['EMA12'] = df['Close'].ewm(span=fast, adjust=False).mean()
    df['EMA26'] = df['Close'].ewm(span=slow, adjust=False).mean()
    df['MACD'] = df['EMA12'] - df['EMA26']
    df['MACD_Signal'] = df['MACD'].ewm(span=signal, adjust=False).mean()
    df['MACD_Hist'] = df['MACD'] - df['MACD_Signal']
    return df


def calculate_bollinger(df, period=20, std=2):
    """볼린저밴드 계산"""
    df['BB_Middle'] = df['Close'].rolling(window=period).mean()
    rolling_std = df['Close'].rolling(window=period).std()
    df['BB_Upper'] = df['BB_Middle'] + (rolling_std * std)
    df['BB_Lower'] = df['BB_Middle'] - (rolling_std * std)
    df['BB_Width'] = (df['BB_Upper'] - df['BB_Lower']) / df['BB_Middle'] * 100
    return df


def calculate_atr(df, period=14):
    """ATR (Average True Range) 변동성 지표"""
    high = df['High']
    low = df['Low']
    close = df['Close']

    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())

    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df['ATR'] = tr.rolling(window=period).mean()
    df['ATR_pct'] = df['ATR'] / df['Close'] * 100  # ATR을 %로

    return df


def calculate_volume_analysis(df):
    """거래량 분석"""
    df['Volume_MA20'] = df['Volume'].rolling(window=20).mean()
    df['Volume_Ratio'] = df['Volume'] / df['Volume_MA20']
    return df


def calculate_momentum(df):
    """모멘텀 (수익률) 계산"""
    if df is None or len(df) < 5:
        return {}

    current = df['Close'].iloc[-1]

    momentum = {}

    # 1주 수익률
    if len(df) >= 5:
        momentum["return_1w"] = round((current / df['Close'].iloc[-5] - 1) * 100, 2)

    # 1개월 수익률
    if len(df) >= 21:
        momentum["return_1m"] = round((current / df['Close'].iloc[-21] - 1) * 100, 2)

    # 3개월 수익률
    if len(df) >= 63:
        momentum["return_3m"] = round((current / df['Close'].iloc[-63] - 1) * 100, 2)

    # 6개월 수익률
    if len(df) >= 126:
        momentum["return_6m"] = round((current / df['Close'].iloc[-126] - 1) * 100, 2)

    # 1년 수익률
    if len(df) >= 252:
        momentum["return_1y"] = round((current / df['Close'].iloc[-252] - 1) * 100, 2)

    return momentum


def calculate_support_resistance(df, window=20):
    """지지/저항선 계산"""
    if len(df) < window:
        return {}

    recent = df.tail(window)

    # 최근 고점/저점
    resistance = recent['High'].max()
    support = recent['Low'].min()

    # 피봇 포인트
    pivot = (recent['High'].iloc[-1] + recent['Low'].iloc[-1] + recent['Close'].iloc[-1]) / 3
    r1 = 2 * pivot - recent['Low'].iloc[-1]
    s1 = 2 * pivot - recent['High'].iloc[-1]

    return {
        "resistance": round(resistance, 2),
        "support": round(support, 2),
        "pivot": round(pivot, 2),
        "r1": round(r1, 2),
        "s1": round(s1, 2),
        "distance_to_resistance": round((resistance / df['Close'].iloc[-1] - 1) * 100, 2),
        "distance_to_support": round((support / df['Close'].iloc[-1] - 1) * 100, 2),
    }


def detect_candle_patterns(df):
    """캔들 패턴 감지"""
    patterns = []

    if len(df) < 3:
        return patterns

    curr = df.iloc[-1]
    prev = df.iloc[-2]
    prev2 = df.iloc[-3]

    open_p, high, low, close = curr['Open'], curr['High'], curr['Low'], curr['Close']
    body = abs(close - open_p)
    upper_shadow = high - max(open_p, close)
    lower_shadow = min(open_p, close) - low
    total_range = high - low

    if total_range == 0:
        return patterns

    # 도지 (Doji) - 시가 = 종가
    if body / total_range < 0.1:
        patterns.append("✳️ 도지 (Doji) - 추세 전환 가능")

    # 망치형 (Hammer) - 하락 추세에서 긴 아래꼬리
    if lower_shadow > body * 2 and upper_shadow < body * 0.5 and close < prev['Close']:
        patterns.append("🔨 망치형 (Hammer) - 반등 신호")

    # 역망치형 (Inverted Hammer)
    if upper_shadow > body * 2 and lower_shadow < body * 0.5 and close < prev['Close']:
        patterns.append("🔨 역망치형 - 반등 가능")

    # 교수형 (Hanging Man) - 상승 추세에서 긴 아래꼬리
    if lower_shadow > body * 2 and upper_shadow < body * 0.5 and close > prev['Close']:
        patterns.append("☠️ 교수형 (Hanging Man) - 하락 전환 주의")

    # 장악형 (Engulfing)
    prev_body = abs(prev['Close'] - prev['Open'])
    if body > prev_body * 1.5:
        if close > open_p and prev['Close'] < prev['Open']:  # 상승 장악형
            patterns.append("📈 상승 장악형 (Bullish Engulfing) - 매수 신호")
        elif close < open_p and prev['Close'] > prev['Open']:  # 하락 장악형
            patterns.append("📉 하락 장악형 (Bearish Engulfing) - 매도 신호")

    # 샛별형 (Morning Star) / 저녁별형 (Evening Star)
    if len(df) >= 3:
        # 3일 패턴 체크
        day1_body = abs(prev2['Close'] - prev2['Open'])
        day2_body = abs(prev['Close'] - prev['Open'])
        day3_body = body

        # 샛별형: 큰 음봉 → 작은 봉 → 큰 양봉
        if (prev2['Close'] < prev2['Open'] and  # 1일차 음봉
            day2_body < day1_body * 0.3 and     # 2일차 작은 봉
            close > open_p and                   # 3일차 양봉
            day3_body > day1_body * 0.5):
            patterns.append("⭐ 샛별형 (Morning Star) - 강한 반등 신호")

    return patterns


def calculate_all_indicators(df):
    """모든 기술적 지표 한번에 계산"""
    df = calculate_ma(df)
    df = calculate_ichimoku(df)
    df = calculate_rsi(df)
    df = calculate_macd(df)
    df = calculate_bollinger(df)
    df = calculate_volume_analysis(df)
    df = calculate_atr(df)
    return df

"""
기술적 분석 모듈
- 이동평균선 (SMA, EMA)
- 일목균형표 (Ichimoku Cloud)
- RSI (상대강도지수)
- MACD (이동평균수렴확산)
- 볼린저밴드
- 52주 고점/저점
- 거래량 분석
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

# 레버리지 ETF → 원본 매핑
LEVERAGE_MAP = {
    # 3x 레버리지
    "SOXL": "SOXX",   # 반도체 3x → 반도체 ETF
    "SOXS": "SOXX",   # 반도체 -3x
    "TQQQ": "QQQ",    # 나스닥 3x
    "SQQQ": "QQQ",    # 나스닥 -3x
    "UPRO": "SPY",    # S&P500 3x
    "SPXU": "SPY",    # S&P500 -3x
    "LABU": "XBI",    # 바이오 3x
    "LABD": "XBI",    # 바이오 -3x
    "FAS": "XLF",     # 금융 3x
    "FAZ": "XLF",     # 금융 -3x
    "TECL": "XLK",    # 기술 3x
    "TECS": "XLK",    # 기술 -3x

    # 2x 레버리지 (개별주)
    "MSTX": "MSTR",   # 마이크로스트래티지 2x
    "MSTZ": "MSTR",   # 마이크로스트래티지 -2x
    "NVDL": "NVDA",   # 엔비디아 2x
    "NVDD": "NVDA",   # 엔비디아 -2x
    "TSLL": "TSLA",   # 테슬라 2x
    "TSLS": "TSLA",   # 테슬라 -2x
    "AAPU": "AAPL",   # 애플 2x
    "AAPD": "AAPL",   # 애플 -2x
    "GOOGL2": "GOOGL", # 구글 2x (가상)
    "AMZN2": "AMZN",  # 아마존 2x (가상)
    "CONL": "COIN",   # 코인베이스 2x
    "CONY": "COIN",   # 코인베이스 -2x

    # 코인 관련
    "BITX": "BTC-USD",  # 비트코인 2x
    "BITU": "BTC-USD",
    "ETHU": "ETH-USD",  # 이더리움 2x
}

def get_underlying(symbol):
    """레버리지 ETF면 원본 심볼 반환"""
    return LEVERAGE_MAP.get(symbol.upper(), symbol)


def get_fundamentals(symbol):
    """펀더멘털 데이터 가져오기"""
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info

        return {
            "market_cap": info.get("marketCap"),
            "pe_ratio": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
            "pb_ratio": info.get("priceToBook"),
            "ps_ratio": info.get("priceToSalesTrailing12Months"),
            "peg_ratio": info.get("pegRatio"),
            "eps": info.get("trailingEps"),
            "revenue_growth": info.get("revenueGrowth"),
            "earnings_growth": info.get("earningsGrowth"),
            "profit_margin": info.get("profitMargins"),
            "roe": info.get("returnOnEquity"),
            "roa": info.get("returnOnAssets"),
            "debt_to_equity": info.get("debtToEquity"),
            "current_ratio": info.get("currentRatio"),
            "dividend_yield": info.get("dividendYield"),
            "beta": info.get("beta"),
            "52w_high": info.get("fiftyTwoWeekHigh"),
            "52w_low": info.get("fiftyTwoWeekLow"),
            "avg_volume": info.get("averageVolume"),
            "short_ratio": info.get("shortRatio"),
            "target_price": info.get("targetMeanPrice"),
            "recommendation": info.get("recommendationKey"),
            "sector": info.get("sector"),
            "industry": info.get("industry"),
        }
    except Exception as e:
        print(f"  펀더멘털 데이터 실패: {e}")
        return {}


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


def get_market_indicators():
    """시장 전체 지표 (VIX, 금리, 섹터 등)"""
    indicators = {}

    try:
        # VIX (공포지수)
        vix = yf.Ticker("^VIX")
        vix_data = vix.history(period="5d")
        if len(vix_data) > 0:
            indicators["vix"] = round(vix_data['Close'].iloc[-1], 2)
            indicators["vix_change"] = round(vix_data['Close'].pct_change().iloc[-1] * 100, 2)

        # S&P 500
        spy = yf.Ticker("SPY")
        spy_data = spy.history(period="5d")
        if len(spy_data) > 0:
            indicators["spy"] = round(spy_data['Close'].iloc[-1], 2)
            indicators["spy_change"] = round(spy_data['Close'].pct_change().iloc[-1] * 100, 2)

        # 나스닥
        qqq = yf.Ticker("QQQ")
        qqq_data = qqq.history(period="5d")
        if len(qqq_data) > 0:
            indicators["qqq"] = round(qqq_data['Close'].iloc[-1], 2)
            indicators["qqq_change"] = round(qqq_data['Close'].pct_change().iloc[-1] * 100, 2)

        # 10년물 국채 금리
        tlt = yf.Ticker("^TNX")
        tlt_data = tlt.history(period="5d")
        if len(tlt_data) > 0:
            indicators["us10y"] = round(tlt_data['Close'].iloc[-1], 2)

        # 달러 인덱스
        dxy = yf.Ticker("DX-Y.NYB")
        dxy_data = dxy.history(period="5d")
        if len(dxy_data) > 0:
            indicators["dxy"] = round(dxy_data['Close'].iloc[-1], 2)

    except Exception as e:
        print(f"  시장 지표 가져오기 실패: {e}")

    # VIX 해석
    if indicators.get("vix"):
        vix_val = indicators["vix"]
        if vix_val < 15:
            indicators["market_sentiment"] = "EXTREME_GREED"
            indicators["sentiment_desc"] = "극도의 탐욕 (시장 과열)"
        elif vix_val < 20:
            indicators["market_sentiment"] = "GREED"
            indicators["sentiment_desc"] = "탐욕 (안정적 상승)"
        elif vix_val < 25:
            indicators["market_sentiment"] = "NEUTRAL"
            indicators["sentiment_desc"] = "중립"
        elif vix_val < 30:
            indicators["market_sentiment"] = "FEAR"
            indicators["sentiment_desc"] = "공포 (변동성 증가)"
        else:
            indicators["market_sentiment"] = "EXTREME_FEAR"
            indicators["sentiment_desc"] = "극도의 공포 (매수 기회?)"

    return indicators


def generate_trading_strategy(analysis, market_indicators):
    """매매 전략 생성 (분할매수/매도, 손절선, 목표가)"""
    strategy = {
        "action": "HOLD",
        "confidence": "MEDIUM",
        "entry_strategy": [],
        "exit_strategy": [],
        "stop_loss": None,
        "take_profit": [],
        "position_size": "0%",
        "reasoning": []
    }

    current_price = analysis.get("current_price", 0)
    recommendation = analysis.get("recommendation", "HOLD")
    fundamentals = analysis.get("fundamentals", {})
    sr = analysis.get("support_resistance", {})
    momentum = analysis.get("momentum", {})
    score = analysis.get("score", 0)

    if current_price == 0:
        return strategy

    # 목표가 (애널리스트)
    target_price = fundamentals.get("target_price")
    upside = ((target_price / current_price) - 1) * 100 if target_price else None

    # 지지선/저항선
    support = sr.get("support", current_price * 0.9)
    resistance = sr.get("resistance", current_price * 1.1)

    # VIX 기반 시장 상황
    vix = market_indicators.get("vix", 20)
    market_sentiment = market_indicators.get("market_sentiment", "NEUTRAL")

    # === 전략 결정 ===

    # STRONG_BUY / BUY
    if recommendation in ["STRONG_BUY", "BUY"]:
        strategy["action"] = "BUY"

        # 분할매수 전략
        if score >= 5:
            strategy["confidence"] = "HIGH"
            strategy["position_size"] = "30%"
            strategy["entry_strategy"] = [
                f"1차 매수: 현재가 ${current_price:.2f}에서 포지션의 50%",
                f"2차 매수: ${current_price * 0.97:.2f} (-3%)에서 30%",
                f"3차 매수: ${current_price * 0.95:.2f} (-5%)에서 20%",
            ]
            strategy["reasoning"].append("강한 매수 신호 - 적극적 분할매수 권장")
        else:
            strategy["confidence"] = "MEDIUM"
            strategy["position_size"] = "20%"
            strategy["entry_strategy"] = [
                f"1차 매수: 현재가 ${current_price:.2f}에서 포지션의 40%",
                f"2차 매수: ${current_price * 0.95:.2f} (-5%)에서 30%",
                f"3차 매수: ${current_price * 0.90:.2f} (-10%)에서 30%",
            ]
            strategy["reasoning"].append("매수 신호 - 보수적 분할매수 권장")

        # 손절선
        strategy["stop_loss"] = {
            "price": round(support * 0.97, 2),
            "percentage": round((support * 0.97 / current_price - 1) * 100, 1),
            "desc": f"지지선 ${support:.2f} 하회 시 손절"
        }

        # 목표가 (익절)
        if target_price and upside > 10:
            strategy["take_profit"] = [
                {"price": round(current_price * 1.10, 2), "percentage": 10, "sell_ratio": "30%", "desc": "+10%에서 1차 익절"},
                {"price": round(current_price * 1.20, 2), "percentage": 20, "sell_ratio": "30%", "desc": "+20%에서 2차 익절"},
                {"price": round(target_price, 2), "percentage": round(upside, 1), "sell_ratio": "40%", "desc": f"목표가 도달 시 전량 익절"},
            ]
        else:
            strategy["take_profit"] = [
                {"price": round(resistance, 2), "percentage": round((resistance/current_price-1)*100, 1), "sell_ratio": "50%", "desc": "저항선 도달 시 절반 익절"},
                {"price": round(resistance * 1.05, 2), "percentage": round((resistance*1.05/current_price-1)*100, 1), "sell_ratio": "50%", "desc": "저항선 돌파 시 나머지 익절"},
            ]

    # STRONG_SELL / SELL
    elif recommendation in ["STRONG_SELL", "SELL"]:
        strategy["action"] = "SELL"
        strategy["confidence"] = "HIGH" if score <= -5 else "MEDIUM"
        strategy["position_size"] = "0%"

        strategy["exit_strategy"] = [
            f"즉시 매도: 포지션의 50% 현재가 ${current_price:.2f}에서",
            f"잔여 매도: 반등 시 ${current_price * 1.03:.2f} (+3%)에서 나머지",
        ]

        strategy["reasoning"].append("매도 신호 발생 - 포지션 축소 권장")

        if momentum.get("return_1m", 0) < -15:
            strategy["reasoning"].append("1개월 -15% 이상 급락 - 손실 확대 방지")

    # HOLD
    else:
        strategy["action"] = "HOLD"
        strategy["confidence"] = "MEDIUM"
        strategy["position_size"] = "현재 유지"

        strategy["reasoning"].append("명확한 방향성 없음 - 관망")

        # 추가 매수/매도 조건
        strategy["entry_strategy"] = [
            f"추가 매수 조건: ${support:.2f} 지지 확인 시",
            f"또는: RSI 30 이하 과매도 시",
        ]
        strategy["exit_strategy"] = [
            f"매도 조건: ${resistance:.2f} 저항 돌파 실패 시",
            f"또는: RSI 70 이상 + 거래량 감소 시",
        ]

    # 시장 상황 반영
    if market_sentiment == "EXTREME_FEAR" and strategy["action"] == "BUY":
        strategy["reasoning"].append(f"VIX {vix} 극도의 공포 - 역발상 매수 기회")
        strategy["confidence"] = "HIGH"
    elif market_sentiment == "EXTREME_GREED" and strategy["action"] == "BUY":
        strategy["reasoning"].append(f"VIX {vix} 극도의 탐욕 - 추격매수 주의")
        strategy["confidence"] = "LOW"
        strategy["position_size"] = "10%"

    return strategy


def get_stock_data(symbol, period="3mo"):
    """야후 파이낸스에서 주가 데이터 가져오기"""
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period)
        return df
    except Exception as e:
        print(f"[{symbol}] 데이터 가져오기 실패: {e}")
        return None


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


def calculate_volume_analysis(df):
    """거래량 분석"""
    df['Volume_MA20'] = df['Volume'].rolling(window=20).mean()
    df['Volume_Ratio'] = df['Volume'] / df['Volume_MA20']
    return df


def analyze_signals(df, symbol, underlying=None):
    """매수/매도 신호 분석"""
    if df is None or len(df) < 60:
        return {"symbol": symbol, "error": "데이터 부족"}

    # 모든 지표 계산
    df = calculate_ma(df)
    df = calculate_ichimoku(df)
    df = calculate_rsi(df)
    df = calculate_macd(df)
    df = calculate_bollinger(df)
    df = calculate_volume_analysis(df)
    df = calculate_atr(df)

    latest = df.iloc[-1]
    prev = df.iloc[-2]

    # 52주 고점/저점
    high_52w = df['High'].tail(252).max() if len(df) >= 252 else df['High'].max()
    low_52w = df['Low'].tail(252).min() if len(df) >= 252 else df['Low'].min()

    signals = {
        "symbol": symbol,
        "underlying": underlying,
        "current_price": round(latest['Close'], 2),
        "date": str(df.index[-1].date()),
        "high_52w": round(high_52w, 2),
        "low_52w": round(low_52w, 2),
        "from_high_52w": round((latest['Close'] - high_52w) / high_52w * 100, 1),
        "from_low_52w": round((latest['Close'] - low_52w) / low_52w * 100, 1),
        "indicators": {},
        "signals": [],
        "recommendation": "HOLD"
    }

    score = 0  # 통합 점수 (양수=매수, 음수=매도)
    volume_multiplier = 1.0  # 거래량에 따른 신호 강도 배수
    signal_flags = {}  # 복합 조건 체크용

    # === 거래량 멀티플라이어 먼저 계산 ===
    if pd.notna(latest['Volume_Ratio']):
        vol_ratio = round(latest['Volume_Ratio'], 2)
        signals["indicators"]["Volume_Ratio"] = vol_ratio

        if vol_ratio >= 2.0:
            signals["signals"].append(f"📊 거래량 급증 ({vol_ratio}배) - 신호 강도 1.3배")
            volume_multiplier = 1.3
            signal_flags["volume_surge"] = True
        elif vol_ratio >= 1.5:
            signals["signals"].append(f"📊 거래량 증가 ({vol_ratio}배)")
            volume_multiplier = 1.15
        elif vol_ratio <= 0.5:
            signals["signals"].append(f"📊 거래량 감소 ({vol_ratio}배) - 신호 약화")
            volume_multiplier = 0.7

    # 1. 이평선 분석
    if pd.notna(latest['MA5']) and pd.notna(latest['MA20']):
        signals["indicators"]["MA5"] = round(latest['MA5'], 2)
        signals["indicators"]["MA20"] = round(latest['MA20'], 2)
        if pd.notna(latest.get('MA60')):
            signals["indicators"]["MA60"] = round(latest['MA60'], 2)

        # 골든크로스 / 데드크로스 (강한 신호)
        if prev['MA5'] <= prev['MA20'] and latest['MA5'] > latest['MA20']:
            signals["signals"].append("📈 골든크로스 (MA5 > MA20) - 강한 매수 신호")
            score += 2 * volume_multiplier
            signal_flags["golden_cross"] = True
        elif prev['MA5'] >= prev['MA20'] and latest['MA5'] < latest['MA20']:
            signals["signals"].append("📉 데드크로스 (MA5 < MA20) - 강한 매도 신호")
            score -= 2 * volume_multiplier
            signal_flags["death_cross"] = True

        # 가격 vs 이평선 (확인 신호)
        if latest['Close'] > latest['MA20']:
            signals["signals"].append("✅ 가격이 20일선 위 - 상승 추세")
            score += 0.5
            signal_flags["above_ma20"] = True
        else:
            signals["signals"].append("⚠️ 가격이 20일선 아래 - 하락 추세")
            score -= 0.5
            signal_flags["below_ma20"] = True

    # 2. 일목균형표 분석
    if pd.notna(latest['Tenkan']) and pd.notna(latest['Kijun']):
        signals["indicators"]["Tenkan"] = round(latest['Tenkan'], 2)
        signals["indicators"]["Kijun"] = round(latest['Kijun'], 2)

        # 전환선 vs 기준선 크로스
        if prev['Tenkan'] <= prev['Kijun'] and latest['Tenkan'] > latest['Kijun']:
            signals["signals"].append("📈 일목 골든크로스 (전환선 > 기준선) - 매수 신호")
            score += 1.5 * volume_multiplier
        elif prev['Tenkan'] >= prev['Kijun'] and latest['Tenkan'] < latest['Kijun']:
            signals["signals"].append("📉 일목 데드크로스 (전환선 < 기준선) - 매도 신호")
            score -= 1.5 * volume_multiplier

        # 구름대 분석
        if pd.notna(latest['SpanA']) and pd.notna(latest['SpanB']):
            cloud_top = max(latest['SpanA'], latest['SpanB'])
            cloud_bottom = min(latest['SpanA'], latest['SpanB'])

            if latest['Close'] > cloud_top:
                signals["signals"].append("✅ 가격이 구름대 위 - 강세")
                score += 0.5
                signal_flags["above_cloud"] = True
            elif latest['Close'] < cloud_bottom:
                signals["signals"].append("⚠️ 가격이 구름대 아래 - 약세")
                score -= 0.5
                signal_flags["below_cloud"] = True
            else:
                signals["signals"].append("➖ 가격이 구름대 안 - 횡보/불확실")

    # 3. RSI 분석 - 극단값은 단독 트리거!
    rsi_override = None  # RSI 극단값 시 다른 신호 무시용
    if pd.notna(latest['RSI']):
        rsi = round(latest['RSI'], 1)
        signals["indicators"]["RSI"] = rsi

        if rsi >= 80:
            signals["signals"].append(f"🔴🔴 RSI {rsi} - 극단적 과매수 ⚠️ 단독 SELL 트리거")
            rsi_override = "SELL"
            signal_flags["rsi_extreme_overbought"] = True
        elif rsi >= 70:
            signals["signals"].append(f"🔴 RSI {rsi} - 과매수 구간 (매도 고려)")
            score -= 2
            signal_flags["rsi_overbought"] = True
        elif rsi <= 20:
            signals["signals"].append(f"🟢🟢 RSI {rsi} - 극단적 과매도 (강한 매수 신호 +5점, 단 낙폭 주의)")
            score += 5  # 강제 BUY 대신 높은 점수만
            signal_flags["rsi_extreme_oversold"] = True
        elif rsi <= 30:
            signals["signals"].append(f"🟢 RSI {rsi} - 과매도 구간 (매수 고려)")
            score += 2
            signal_flags["rsi_oversold"] = True
        elif rsi >= 60:
            signals["signals"].append(f"📈 RSI {rsi} - 강세")
            score += 0.5
        elif rsi <= 40:
            signals["signals"].append(f"📉 RSI {rsi} - 약세")
            score -= 0.5
        else:
            signals["signals"].append(f"➖ RSI {rsi} - 중립")

    # 4. MACD 분석
    if pd.notna(latest['MACD']) and pd.notna(latest['MACD_Signal']):
        signals["indicators"]["MACD"] = round(latest['MACD'], 3)
        signals["indicators"]["MACD_Signal"] = round(latest['MACD_Signal'], 3)

        # MACD 크로스
        if prev['MACD'] <= prev['MACD_Signal'] and latest['MACD'] > latest['MACD_Signal']:
            signals["signals"].append("📈 MACD 골든크로스 - 매수 신호")
            score += 1.5 * volume_multiplier
            signal_flags["macd_golden"] = True
        elif prev['MACD'] >= prev['MACD_Signal'] and latest['MACD'] < latest['MACD_Signal']:
            signals["signals"].append("📉 MACD 데드크로스 - 매도 신호")
            score -= 1.5 * volume_multiplier
            signal_flags["macd_death"] = True

        # MACD 양수/음수
        if latest['MACD'] > 0:
            signal_flags["macd_positive"] = True
        else:
            signal_flags["macd_negative"] = True

        # MACD 히스토그램 방향 (참고용)
        if pd.notna(latest['MACD_Hist']) and pd.notna(prev['MACD_Hist']):
            if latest['MACD_Hist'] > prev['MACD_Hist']:
                signals["signals"].append("📈 MACD 히스토그램 상승 중")
            else:
                signals["signals"].append("📉 MACD 히스토그램 하락 중")

    # 5. 볼린저밴드 분석
    if pd.notna(latest['BB_Upper']) and pd.notna(latest['BB_Lower']):
        signals["indicators"]["BB_Upper"] = round(latest['BB_Upper'], 2)
        signals["indicators"]["BB_Lower"] = round(latest['BB_Lower'], 2)

        if latest['Close'] >= latest['BB_Upper']:
            signals["signals"].append("🔴 볼린저 상단 돌파 - 과매수/조정 가능")
            score -= 1
            signal_flags["bb_upper"] = True
        elif latest['Close'] <= latest['BB_Lower']:
            signals["signals"].append("🟢 볼린저 하단 이탈 - 과매도/반등 가능")
            score += 1
            signal_flags["bb_lower"] = True

    # 6. 52주 고점/저점 분석
    if signals["from_high_52w"] >= -5:
        signals["signals"].append(f"🔝 52주 고점 근처 ({signals['from_high_52w']}%) - 추격매수 주의")
        score -= 1
        signal_flags["near_high"] = True
    elif signals["from_low_52w"] <= 10:
        signals["signals"].append(f"🔻 52주 저점 근처 ({signals['from_low_52w']}%) - 반등 기대")
        score += 0.5
        signal_flags["near_low"] = True

    # 7. 지지/저항선 근접 체크
    sr = calculate_support_resistance(df)
    signals["support_resistance"] = sr
    if sr:
        dist_to_support = sr.get("distance_to_support", -100)
        dist_to_resistance = sr.get("distance_to_resistance", 100)
        if dist_to_support >= -3:  # 지지선 근처 (3% 이내)
            signal_flags["near_support"] = True
        if dist_to_resistance <= 3:  # 저항선 근처 (3% 이내)
            signal_flags["near_resistance"] = True

    # 8. 모멘텀 (수익률)
    momentum = calculate_momentum(df)
    signals["momentum"] = momentum

    if momentum:
        return_1m = momentum.get("return_1m", 0)
        if return_1m > 20:
            signals["signals"].append(f"🚀 1개월 +{return_1m}% 급등 - 과열 주의")
            score -= 1
        elif return_1m > 10:
            signals["signals"].append(f"🚀 1개월 +{return_1m}% - 강한 상승")
        elif return_1m < -15:
            signals["signals"].append(f"💥 1개월 {return_1m}% 급락 - 낙폭과대")
            score -= 2
        elif return_1m < -10:
            signals["signals"].append(f"💥 1개월 {return_1m}% - 하락세")
            score -= 1

    # 9. ATR (변동성)
    if pd.notna(latest.get('ATR_pct')):
        atr_pct = round(latest['ATR_pct'], 2)
        signals["indicators"]["ATR_pct"] = atr_pct
        if atr_pct > 5:
            signals["signals"].append(f"⚡ 변동성 높음 (ATR {atr_pct}%) - 리스크 주의")

    # 10. 캔들 패턴
    candle_patterns = detect_candle_patterns(df)
    signals["candle_patterns"] = candle_patterns
    for pattern in candle_patterns:
        signals["signals"].append(pattern)
        if "매수" in pattern or "반등" in pattern:
            score += 1
            signal_flags["bullish_candle"] = True
        elif "매도" in pattern or "하락" in pattern:
            score -= 1
            signal_flags["bearish_candle"] = True

    # === 복합 조건 보너스 ===
    combo_bonus = 0

    # 바닥 신호 콤보: RSI 과매도 + 지지선 근처 + 거래량 증가
    if (signal_flags.get("rsi_oversold") and
        signal_flags.get("near_support") and
        signal_flags.get("volume_surge")):
        signals["signals"].append("🎯 바닥 신호 콤보! (RSI 과매도 + 지지선 + 거래량) +2점")
        combo_bonus += 2

    # 천장 신호 콤보: RSI 과매수 + 저항선 근처
    if (signal_flags.get("rsi_overbought") and
        signal_flags.get("near_resistance")):
        signals["signals"].append("🎯 천장 신호 콤보! (RSI 과매수 + 저항선) -2점")
        combo_bonus -= 2

    # 추세 확인 콤보: 골든크로스 + 구름대 위 + MACD 양수
    if (signal_flags.get("golden_cross") and
        signal_flags.get("above_cloud") and
        signal_flags.get("macd_positive")):
        signals["signals"].append("🎯 추세 확인 콤보! (골든크로스 + 구름대 위 + MACD+) +1.5점")
        combo_bonus += 1.5

    # 하락 확인 콤보: 데드크로스 + 구름대 아래 + MACD 음수
    if (signal_flags.get("death_cross") and
        signal_flags.get("below_cloud") and
        signal_flags.get("macd_negative")):
        signals["signals"].append("🎯 하락 확인 콤보! (데드크로스 + 구름대 아래 + MACD-) -1.5점")
        combo_bonus -= 1.5

    score += combo_bonus

    # === 확신도 필터 (70% 룰) ===
    buy_signals = sum(1 for s in signals["signals"] if "📈" in s or "🟢" in s or "✅" in s)
    sell_signals = sum(1 for s in signals["signals"] if "📉" in s or "🔴" in s or "⚠️" in s)
    total_signals = buy_signals + sell_signals

    signals["buy_signals"] = buy_signals
    signals["sell_signals"] = sell_signals

    confidence = "LOW"
    if total_signals >= 3:
        if buy_signals / total_signals >= 0.7:
            confidence = "HIGH"
        elif sell_signals / total_signals >= 0.7:
            confidence = "HIGH"
        elif buy_signals / total_signals >= 0.5 or sell_signals / total_signals >= 0.5:
            confidence = "MEDIUM"

    signals["confidence"] = confidence

    # === 최종 추천 결정 ===
    score = round(score, 1)

    # RSI 80+ 극단적 과매수는 강제 SELL (떨어지는 칼날 RSI 20-는 점수만 반영)
    if rsi_override == "SELL":
        signals["recommendation"] = "SELL"
        signals["signals"].append("⚠️ RSI 80+ 단독 트리거로 SELL 결정 (다른 신호 무시)")
    else:
        # 매수/매도 신호 비율도 고려 (신호가 한쪽으로 몰려있으면 신뢰)
        buy_ratio = buy_signals / total_signals if total_signals > 0 else 0
        sell_ratio = sell_signals / total_signals if total_signals > 0 else 0

        # 점수 기반 + 신호 비율 보정
        if score >= 4 or (score >= 2 and buy_ratio >= 0.8):
            signals["recommendation"] = "STRONG_BUY"
        elif score >= 1.5 and buy_ratio >= 0.7:
            # 점수 1.5 이상 + 매수신호 70% 이상이면 BUY
            signals["recommendation"] = "BUY"
        elif score >= 2:
            signals["recommendation"] = "BUY"
        elif score <= -4 or (score <= -2 and sell_ratio >= 0.8):
            signals["recommendation"] = "STRONG_SELL"
        elif score <= -1.5 and sell_ratio >= 0.7:
            signals["recommendation"] = "SELL"
        elif score <= -2:
            signals["recommendation"] = "SELL"
        else:
            signals["recommendation"] = "HOLD"

    signals["score"] = score
    signals["combo_bonus"] = combo_bonus

    return signals


def load_portfolio():
    """포트폴리오 파일 로드"""
    filepath = os.path.join(DATA_DIR, "portfolio.json")
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def analyze_portfolio():
    """포트폴리오 전체 분석"""
    portfolio = load_portfolio()
    if not portfolio:
        print("portfolio.json 파일이 없습니다.")
        return None

    # 시장 전체 지표 먼저 가져오기
    print("시장 지표 분석 중...")
    market_indicators = get_market_indicators()
    print(f"  VIX: {market_indicators.get('vix', 'N/A')} ({market_indicators.get('sentiment_desc', '')})")

    results = {
        "analyzed_at": datetime.now().isoformat(),
        "market": market_indicators,
        "holdings": []
    }

    # 새 구조 (us/kr 분리) 또는 기존 구조 지원
    holdings_data = portfolio.get("holdings", [])

    if isinstance(holdings_data, dict):
        # 새 구조: {"us": [...], "kr": [...]}
        all_holdings = []
        for market_type, holdings_list in holdings_data.items():
            for h in holdings_list:
                h["market"] = market_type  # us 또는 kr
                all_holdings.append(h)
    else:
        # 기존 구조: [...]
        all_holdings = holdings_data
        for h in all_holdings:
            h["market"] = "us"

    for holding in all_holdings:
        symbol = holding["symbol"]
        market = holding.get("market", "us")
        underlying = get_underlying(symbol)
        is_leveraged = underlying != symbol

        market_label = "🇺🇸" if market == "us" else "🇰🇷"

        if is_leveraged:
            print(f"{market_label} [{symbol}] → 원본 [{underlying}] 분석 중...")
        else:
            print(f"{market_label} [{symbol}] 분석 중...")

        # 원본 종목 데이터로 분석
        df = get_stock_data(underlying, period="1y")
        analysis = analyze_signals(df, symbol, underlying if is_leveraged else None)
        analysis["name"] = holding.get("name", "")
        analysis["quantity"] = holding.get("quantity", 0)
        analysis["is_leveraged"] = is_leveraged
        analysis["market"] = market

        if is_leveraged:
            # 레버리지 ETF 자체 가격도 추가
            lev_df = get_stock_data(symbol, period="5d")
            if lev_df is not None and len(lev_df) > 0:
                analysis["leveraged_price"] = round(lev_df['Close'].iloc[-1], 2)

        # 펀더멘털 데이터 추가
        print(f"  펀더멘털 데이터 가져오는 중...")
        fundamentals = get_fundamentals(underlying)
        analysis["fundamentals"] = fundamentals

        # 매매 전략 생성
        print(f"  매매 전략 생성 중...")
        strategy = generate_trading_strategy(analysis, market_indicators)
        analysis["strategy"] = strategy

        results["holdings"].append(analysis)
        rec = analysis.get('recommendation', 'N/A')
        score = analysis.get('score', 'N/A')
        action = strategy.get('action', 'N/A')
        print(f"  → {rec} (점수: {score}) | 전략: {action}")

    return results


def save_report(results):
    """분석 결과 저장 (년/월/일 폴더 구조)"""
    now = datetime.now()
    report_dir = os.path.join(DATA_DIR, "reports", str(now.year), f"{now.month:02d}", f"{now.day:02d}")
    os.makedirs(report_dir, exist_ok=True)

    timestamp = now.strftime("%H%M%S")

    # JSON 저장
    json_path = os.path.join(report_dir, f"report_{timestamp}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # 텍스트 리포트 저장
    txt_path = os.path.join(report_dir, f"report_{timestamp}.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(f"{'='*60}\n")
        f.write(f"       포트폴리오 분석 리포트\n")
        f.write(f"{'='*60}\n")
        f.write(f"분석 시각: {results['analyzed_at']}\n\n")

        # 시장 전체 현황
        market = results.get("market", {})
        if market:
            f.write(f"{'─'*60}\n")
            f.write(f"📊 시장 현황\n")
            f.write(f"{'─'*60}\n")
            if market.get("vix"):
                sentiment_emoji = {"EXTREME_GREED": "🟢🟢", "GREED": "🟢", "NEUTRAL": "⚪", "FEAR": "🔴", "EXTREME_FEAR": "🔴🔴"}.get(market.get("market_sentiment", ""), "")
                f.write(f"  VIX (공포지수): {market['vix']} {sentiment_emoji}\n")
                f.write(f"  시장 심리: {market.get('sentiment_desc', '')}\n")
            if market.get("spy"):
                f.write(f"  S&P 500 (SPY): ${market['spy']} ({market.get('spy_change', 0):+.1f}%)\n")
            if market.get("qqq"):
                f.write(f"  나스닥 (QQQ): ${market['qqq']} ({market.get('qqq_change', 0):+.1f}%)\n")
            if market.get("us10y"):
                f.write(f"  미국 10년물 금리: {market['us10y']}%\n")
            f.write(f"\n")

        for h in results["holdings"]:
            f.write(f"{'─'*60}\n")

            # 종목 정보
            if h.get("is_leveraged") and h.get("underlying"):
                f.write(f"종목: {h.get('name', '')} ({h['symbol']})\n")
                f.write(f"  └─ 원본: {h['underlying']} 기준 분석\n")
            else:
                f.write(f"종목: {h.get('name', '')} ({h['symbol']})\n")

            # 가격 정보
            market = h.get("market", "us")
            currency = "₩" if market == "kr" else "$"

            if h.get("leveraged_price"):
                f.write(f"현재가: {currency}{h.get('leveraged_price'):,.0f} (레버리지)\n")
                f.write(f"원본가: {currency}{h.get('current_price', 0):,.0f} ({h.get('underlying')})\n")
            else:
                price = h.get('current_price', 0)
                if market == "kr":
                    f.write(f"현재가: {currency}{price:,.0f}\n")
                else:
                    f.write(f"현재가: {currency}{price:,.2f}\n")

            # 52주 정보
            if h.get("high_52w"):
                if market == "kr":
                    f.write(f"52주: {currency}{h.get('low_52w'):,.0f} ~ {currency}{h.get('high_52w'):,.0f}\n")
                else:
                    f.write(f"52주: {currency}{h.get('low_52w'):,.2f} ~ {currency}{h.get('high_52w'):,.2f}\n")
                f.write(f"  └─ 고점 대비: {h.get('from_high_52w')}%\n")

            # 추천
            rec = h.get('recommendation', 'N/A')
            rec_emoji = {"STRONG_BUY": "🟢🟢", "BUY": "🟢", "HOLD": "⚪", "SELL": "🔴", "STRONG_SELL": "🔴🔴"}.get(rec, "")
            f.write(f"\n추천: {rec_emoji} {rec}\n")
            f.write(f"점수: {h.get('score', 'N/A')} (매수신호: {h.get('buy_signals', 0)} / 매도신호: {h.get('sell_signals', 0)})\n")

            # 주요 지표
            indicators = h.get("indicators", {})
            if indicators:
                f.write(f"\n주요 지표:\n")
                if "RSI" in indicators:
                    f.write(f"  RSI: {indicators['RSI']}\n")
                if "MACD" in indicators:
                    f.write(f"  MACD: {indicators['MACD']} (Signal: {indicators.get('MACD_Signal', 'N/A')})\n")
                if "MA20" in indicators:
                    f.write(f"  이평선: MA5={indicators.get('MA5')} / MA20={indicators['MA20']}\n")
                if "ATR_pct" in indicators:
                    f.write(f"  변동성(ATR): {indicators['ATR_pct']}%\n")

            # 모멘텀 (수익률)
            momentum = h.get("momentum", {})
            if momentum:
                f.write(f"\n모멘텀 (수익률):\n")
                if "return_1w" in momentum:
                    f.write(f"  1주: {momentum['return_1w']:+.1f}%\n")
                if "return_1m" in momentum:
                    f.write(f"  1개월: {momentum['return_1m']:+.1f}%\n")
                if "return_3m" in momentum:
                    f.write(f"  3개월: {momentum['return_3m']:+.1f}%\n")

            # 지지/저항선
            sr = h.get("support_resistance", {})
            if sr:
                f.write(f"\n지지/저항:\n")
                if market == "kr":
                    f.write(f"  저항선: {currency}{sr.get('resistance'):,.0f} ({sr.get('distance_to_resistance'):+.1f}%)\n")
                    f.write(f"  지지선: {currency}{sr.get('support'):,.0f} ({sr.get('distance_to_support'):+.1f}%)\n")
                else:
                    f.write(f"  저항선: {currency}{sr.get('resistance'):,.2f} ({sr.get('distance_to_resistance'):+.1f}%)\n")
                    f.write(f"  지지선: {currency}{sr.get('support'):,.2f} ({sr.get('distance_to_support'):+.1f}%)\n")

            # 펀더멘털
            fund = h.get("fundamentals", {})
            if fund and fund.get("pe_ratio"):
                f.write(f"\n펀더멘털:\n")
                if fund.get("pe_ratio"):
                    f.write(f"  PER: {fund['pe_ratio']:.1f}\n")
                if fund.get("pb_ratio"):
                    f.write(f"  PBR: {fund['pb_ratio']:.1f}\n")
                if fund.get("revenue_growth"):
                    f.write(f"  매출성장률: {fund['revenue_growth']*100:.1f}%\n")
                if fund.get("profit_margin"):
                    f.write(f"  이익률: {fund['profit_margin']*100:.1f}%\n")
                if fund.get("target_price"):
                    f.write(f"  애널리스트 목표가: ${fund['target_price']}\n")
                if fund.get("recommendation"):
                    f.write(f"  애널리스트 의견: {fund['recommendation']}\n")

            # 신호
            f.write(f"\n신호 분석:\n")
            for sig in h.get("signals", []):
                f.write(f"  {sig}\n")

            # 매매 전략
            strategy = h.get("strategy", {})
            if strategy:
                action = strategy.get("action", "HOLD")
                action_emoji = {"BUY": "🟢", "SELL": "🔴", "HOLD": "⚪"}.get(action, "")
                confidence = strategy.get("confidence", "MEDIUM")

                f.write(f"\n{'─'*40}\n")
                f.write(f"💰 매매 전략: {action_emoji} {action} (신뢰도: {confidence})\n")
                f.write(f"권장 비중: {strategy.get('position_size', 'N/A')}\n")

                # 이유
                for reason in strategy.get("reasoning", []):
                    f.write(f"  • {reason}\n")

                # 진입 전략
                if strategy.get("entry_strategy"):
                    f.write(f"\n📥 진입 전략:\n")
                    for entry in strategy["entry_strategy"]:
                        f.write(f"  {entry}\n")

                # 청산 전략
                if strategy.get("exit_strategy"):
                    f.write(f"\n📤 청산 전략:\n")
                    for exit in strategy["exit_strategy"]:
                        f.write(f"  {exit}\n")

                # 손절선
                sl = strategy.get("stop_loss")
                if sl:
                    if market == "kr":
                        f.write(f"\n🛑 손절선: {currency}{sl['price']:,.0f} ({sl['percentage']}%)\n")
                    else:
                        f.write(f"\n🛑 손절선: {currency}{sl['price']:,.2f} ({sl['percentage']}%)\n")
                    f.write(f"  {sl['desc']}\n")

                # 익절 목표
                if strategy.get("take_profit"):
                    f.write(f"\n🎯 익절 목표:\n")
                    for tp in strategy["take_profit"]:
                        if market == "kr":
                            f.write(f"  {currency}{tp['price']:,.0f} (+{tp['percentage']}%) → {tp['sell_ratio']} 매도\n")
                        else:
                            f.write(f"  {currency}{tp['price']:,.2f} (+{tp['percentage']}%) → {tp['sell_ratio']} 매도\n")
                        f.write(f"    {tp['desc']}\n")

            f.write(f"\n")

        f.write(f"{'='*60}\n")
        f.write(f"분석 완료\n")

    print(f"\n리포트 저장 완료:")
    print(f"  - {json_path}")
    print(f"  - {txt_path}")

    return json_path, txt_path


if __name__ == "__main__":
    print("포트폴리오 분석 시작...\n")
    results = analyze_portfolio()
    if results:
        save_report(results)
        print("\n완료!")

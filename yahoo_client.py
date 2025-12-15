"""
야후 파이낸스 클라이언트 모듈
- 주가 데이터 조회
- 펀더멘털 데이터 조회
- 시장 지표 조회
- 레버리지 ETF 매핑
"""

import yfinance as yf

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


def is_leveraged(symbol):
    """레버리지 ETF인지 확인"""
    return symbol.upper() in LEVERAGE_MAP


def get_stock_data(symbol, period="3mo"):
    """야후 파이낸스에서 주가 데이터 가져오기"""
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period)
        return df
    except Exception as e:
        print(f"[{symbol}] 데이터 가져오기 실패: {e}")
        return None


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


def get_ticker_info(symbol):
    """종목 기본 정보 가져오기"""
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        return {
            "name": info.get("longName") or info.get("shortName"),
            "symbol": symbol,
            "exchange": info.get("exchange"),
            "currency": info.get("currency"),
            "sector": info.get("sector"),
            "industry": info.get("industry"),
        }
    except Exception as e:
        print(f"[{symbol}] 종목 정보 실패: {e}")
        return {"symbol": symbol}


def get_exchange_rate(base="USD", target="KRW"):
    """환율 가져오기"""
    try:
        symbol = f"{base}{target}=X"
        ticker = yf.Ticker(symbol)
        data = ticker.history(period="1d")
        if len(data) > 0:
            return round(data['Close'].iloc[-1], 2)
    except Exception as e:
        print(f"환율 가져오기 실패: {e}")
    return None


def get_current_price(symbol):
    """현재가 가져오기"""
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(period="1d")
        if len(data) > 0:
            return round(data['Close'].iloc[-1], 2)
    except Exception as e:
        print(f"[{symbol}] 현재가 실패: {e}")
    return None

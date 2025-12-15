"""
토스증권 자동 분석 시스템 - 메인 분석기

모듈 구조:
├── yahoo_client.py  # 야후 파이낸스 API
├── indicators.py    # 기술적 지표 (MA, RSI, MACD, 볼린저, 일목균형표)
├── bitgak.py        # 빗각투자 지표 (VWAP, CSI, HVN)
├── strategy.py      # 매매 전략 생성
└── portfolio.py     # 포트폴리오 관리, 리포트 저장
"""

import pandas as pd
from datetime import datetime

# 모듈 import
from yahoo_client import (
    get_stock_data, get_fundamentals, get_market_indicators,
    get_underlying, is_leveraged, LEVERAGE_MAP,
    get_exchange_rate, get_current_price
)
from indicators import (
    calculate_all_indicators, calculate_momentum,
    calculate_support_resistance, detect_candle_patterns
)
from bitgak import (
    calculate_bitgak_vwap, calculate_bitgak_csi,
    calculate_bitgak_hvn, analyze_bitgak_signal
)
from strategy import generate_trading_strategy
from portfolio import (
    load_portfolio, save_report, get_all_holdings
)


def analyze_signals(df, symbol, underlying=None):
    """매수/매도 신호 분석"""
    if df is None or len(df) < 60:
        return {"symbol": symbol, "error": "데이터 부족"}

    # 모든 지표 계산
    df = calculate_all_indicators(df)
    df = calculate_bitgak_vwap(df)
    df = calculate_bitgak_csi(df)
    df, hvn_price = calculate_bitgak_hvn(df)

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

    score = 0
    volume_multiplier = 1.0
    signal_flags = {}

    # === 거래량 멀티플라이어 ===
    if pd.notna(latest['Volume_Ratio']):
        vol_ratio = round(latest['Volume_Ratio'], 2)
        signals["indicators"]["Volume_Ratio"] = vol_ratio
        if vol_ratio >= 2.0:
            signals["signals"].append(f"📊 거래량 급증 ({vol_ratio}배)")
            volume_multiplier = 1.3
            signal_flags["volume_surge"] = True
        elif vol_ratio >= 1.5:
            signals["signals"].append(f"📊 거래량 증가 ({vol_ratio}배)")
            volume_multiplier = 1.15
        elif vol_ratio <= 0.5:
            signals["signals"].append(f"📊 거래량 감소 ({vol_ratio}배)")
            volume_multiplier = 0.7

    # === 1. 이평선 분석 ===
    if pd.notna(latest['MA5']) and pd.notna(latest['MA20']):
        signals["indicators"]["MA5"] = round(latest['MA5'], 2)
        signals["indicators"]["MA20"] = round(latest['MA20'], 2)
        if pd.notna(latest.get('MA60')):
            signals["indicators"]["MA60"] = round(latest['MA60'], 2)

        if prev['MA5'] <= prev['MA20'] and latest['MA5'] > latest['MA20']:
            signals["signals"].append("📈 골든크로스 (MA5 > MA20)")
            score += 2 * volume_multiplier
            signal_flags["golden_cross"] = True
        elif prev['MA5'] >= prev['MA20'] and latest['MA5'] < latest['MA20']:
            signals["signals"].append("📉 데드크로스 (MA5 < MA20)")
            score -= 2 * volume_multiplier
            signal_flags["death_cross"] = True

        if latest['Close'] > latest['MA20']:
            signals["signals"].append("✅ 가격이 20일선 위")
            score += 0.5
            signal_flags["above_ma20"] = True
        else:
            signals["signals"].append("⚠️ 가격이 20일선 아래")
            score -= 0.5
            signal_flags["below_ma20"] = True

    # === 2. 일목균형표 분석 ===
    if pd.notna(latest['Tenkan']) and pd.notna(latest['Kijun']):
        signals["indicators"]["Tenkan"] = round(latest['Tenkan'], 2)
        signals["indicators"]["Kijun"] = round(latest['Kijun'], 2)

        if prev['Tenkan'] <= prev['Kijun'] and latest['Tenkan'] > latest['Kijun']:
            signals["signals"].append("📈 일목 골든크로스")
            score += 1.5 * volume_multiplier
        elif prev['Tenkan'] >= prev['Kijun'] and latest['Tenkan'] < latest['Kijun']:
            signals["signals"].append("📉 일목 데드크로스")
            score -= 1.5 * volume_multiplier

        if pd.notna(latest['SpanA']) and pd.notna(latest['SpanB']):
            cloud_top = max(latest['SpanA'], latest['SpanB'])
            cloud_bottom = min(latest['SpanA'], latest['SpanB'])
            if latest['Close'] > cloud_top:
                signals["signals"].append("✅ 가격이 구름대 위")
                score += 0.5
                signal_flags["above_cloud"] = True
            elif latest['Close'] < cloud_bottom:
                signals["signals"].append("⚠️ 가격이 구름대 아래")
                score -= 0.5
                signal_flags["below_cloud"] = True

    # === 3. RSI 분석 ===
    rsi_override = None
    if pd.notna(latest['RSI']):
        rsi = round(latest['RSI'], 1)
        signals["indicators"]["RSI"] = rsi

        if rsi >= 80:
            signals["signals"].append(f"🔴🔴 RSI {rsi} - 극단적 과매수")
            rsi_override = "SELL"
        elif rsi >= 70:
            signals["signals"].append(f"🔴 RSI {rsi} - 과매수")
            score -= 2
            signal_flags["rsi_overbought"] = True
        elif rsi <= 20:
            signals["signals"].append(f"🟢🟢 RSI {rsi} - 극단적 과매도")
            score += 5
        elif rsi <= 30:
            signals["signals"].append(f"🟢 RSI {rsi} - 과매도")
            score += 2
            signal_flags["rsi_oversold"] = True
        elif rsi >= 60:
            signals["signals"].append(f"📈 RSI {rsi} - 강세")
            score += 0.5
        elif rsi <= 40:
            signals["signals"].append(f"📉 RSI {rsi} - 약세")
            score -= 0.5

    # === 4. MACD 분석 ===
    if pd.notna(latest['MACD']) and pd.notna(latest['MACD_Signal']):
        signals["indicators"]["MACD"] = round(latest['MACD'], 3)
        signals["indicators"]["MACD_Signal"] = round(latest['MACD_Signal'], 3)

        if prev['MACD'] <= prev['MACD_Signal'] and latest['MACD'] > latest['MACD_Signal']:
            signals["signals"].append("📈 MACD 골든크로스")
            score += 1.5 * volume_multiplier
            signal_flags["macd_golden"] = True
        elif prev['MACD'] >= prev['MACD_Signal'] and latest['MACD'] < latest['MACD_Signal']:
            signals["signals"].append("📉 MACD 데드크로스")
            score -= 1.5 * volume_multiplier

        signal_flags["macd_positive"] = latest['MACD'] > 0
        signal_flags["macd_negative"] = latest['MACD'] <= 0

    # === 5. 볼린저밴드 분석 ===
    if pd.notna(latest['BB_Upper']) and pd.notna(latest['BB_Lower']):
        signals["indicators"]["BB_Upper"] = round(latest['BB_Upper'], 2)
        signals["indicators"]["BB_Lower"] = round(latest['BB_Lower'], 2)

        if latest['Close'] >= latest['BB_Upper']:
            signals["signals"].append("🔴 볼린저 상단 돌파")
            score -= 1
        elif latest['Close'] <= latest['BB_Lower']:
            signals["signals"].append("🟢 볼린저 하단 이탈")
            score += 1

    # === 6. 52주 분석 ===
    if signals["from_high_52w"] >= -5:
        signals["signals"].append(f"🔝 52주 고점 근처 ({signals['from_high_52w']}%)")
        score -= 1
    elif signals["from_low_52w"] <= 10:
        signals["signals"].append(f"🔻 52주 저점 근처 ({signals['from_low_52w']}%)")
        score += 0.5

    # === 7. 지지/저항선 ===
    sr = calculate_support_resistance(df)
    signals["support_resistance"] = sr
    if sr:
        if sr.get("distance_to_support", -100) >= -3:
            signal_flags["near_support"] = True
        if sr.get("distance_to_resistance", 100) <= 3:
            signal_flags["near_resistance"] = True

    # === 8. 모멘텀 ===
    momentum = calculate_momentum(df)
    signals["momentum"] = momentum
    if momentum:
        return_1m = momentum.get("return_1m", 0)
        if return_1m > 20:
            signals["signals"].append(f"🚀 1개월 +{return_1m}% 급등")
            score -= 1
        elif return_1m < -15:
            signals["signals"].append(f"💥 1개월 {return_1m}% 급락")
            score -= 2

    # === 9. ATR ===
    if pd.notna(latest.get('ATR_pct')):
        atr_pct = round(latest['ATR_pct'], 2)
        signals["indicators"]["ATR_pct"] = atr_pct
        if atr_pct > 5:
            signals["signals"].append(f"⚡ 변동성 높음 (ATR {atr_pct}%)")

    # === 10. 캔들 패턴 ===
    candle_patterns = detect_candle_patterns(df)
    signals["candle_patterns"] = candle_patterns
    for pattern in candle_patterns:
        signals["signals"].append(pattern)
        if "매수" in pattern or "반등" in pattern:
            score += 1
        elif "매도" in pattern or "하락" in pattern:
            score -= 1

    # === 11. 빗각 분석 ===
    bitgak_result = analyze_bitgak_signal(df)
    signals["bitgak"] = bitgak_result

    if bitgak_result.get("csi") is not None:
        signals["indicators"]["CSI"] = bitgak_result["csi"]
        signals["indicators"]["VWAP_20"] = bitgak_result.get("vwap_20")
        signals["indicators"]["HVN_Price"] = bitgak_result.get("hvn_price")
        signals["indicators"]["HVN_Proximity"] = bitgak_result.get("hvn_proximity")

    for bitgak_sig in bitgak_result.get("signals", []):
        signals["signals"].append(bitgak_sig)

    # 빗각 가중치 (혼합 모드)
    bitgak_score = bitgak_result.get("score", 0)
    csi = bitgak_result.get("csi", 0)
    hvn_proximity = bitgak_result.get("hvn_proximity", 100)

    # CSI 구간별 가중치
    # -5% ~ +2%: 본전 심리 구간 (최적)
    # -10% ~ -5% 또는 +2% ~ +5%: 보통
    # 그 외: 추격매수 주의
    csi_in_optimal = -5 <= csi <= 2 if csi is not None else False
    csi_in_ok = -10 <= csi <= 5 if csi is not None else False
    hvn_near = hvn_proximity <= 3 if hvn_proximity is not None else False

    # 빗각 조건 충족 여부
    bitgak_ready = csi_in_optimal and hvn_near
    bitgak_ok = csi_in_ok and hvn_proximity <= 5 if hvn_proximity else False

    if bitgak_ready:
        # 최적 빗각 조건: 강한 보너스
        score += 3
        signal_flags["strong_bitgak"] = True
        signals["signals"].append("🎯🎯 빗각 최적 진입 구간!")
    elif bitgak_ok and bitgak_score >= 1:
        # 괜찮은 빗각 조건
        score += bitgak_score * 1.2
        signal_flags["bitgak_signal"] = True
    elif bitgak_score >= 1:
        # 빗각 신호는 있지만 조건 미충족
        score += bitgak_score * 0.5
        signal_flags["bitgak_weak"] = True

    # 빗각 미충족 플래그 (나중에 경고용)
    signal_flags["bitgak_ready"] = bitgak_ready
    signal_flags["bitgak_ok"] = bitgak_ok

    # === 복합 조건 보너스 ===
    combo_bonus = 0

    if signal_flags.get("rsi_oversold") and signal_flags.get("near_support") and signal_flags.get("volume_surge"):
        signals["signals"].append("🎯 바닥 신호 콤보! +2점")
        combo_bonus += 2

    if signal_flags.get("rsi_overbought") and signal_flags.get("near_resistance"):
        signals["signals"].append("🎯 천장 신호 콤보! -2점")
        combo_bonus -= 2

    if signal_flags.get("golden_cross") and signal_flags.get("above_cloud") and signal_flags.get("macd_positive"):
        signals["signals"].append("🎯 추세 확인 콤보! +1.5점")
        combo_bonus += 1.5

    if signal_flags.get("strong_bitgak") and signal_flags.get("rsi_oversold"):
        signals["signals"].append("🎯 빗각 콤보! +2점")
        combo_bonus += 2

    if signal_flags.get("bitgak_signal") and signal_flags.get("near_support"):
        signals["signals"].append("🎯 빗각+지지선 콤보! +1.5점")
        combo_bonus += 1.5

    score += combo_bonus

    # === 확신도 필터 ===
    buy_signals = sum(1 for s in signals["signals"] if "📈" in s or "🟢" in s or "✅" in s)
    sell_signals = sum(1 for s in signals["signals"] if "📉" in s or "🔴" in s or "⚠️" in s)
    total_signals = buy_signals + sell_signals

    signals["buy_signals"] = buy_signals
    signals["sell_signals"] = sell_signals

    confidence = "LOW"
    if total_signals >= 3:
        ratio = buy_signals / total_signals if total_signals > 0 else 0
        if ratio >= 0.7 or (1 - ratio) >= 0.7:
            confidence = "HIGH"
        elif ratio >= 0.5:
            confidence = "MEDIUM"
    signals["confidence"] = confidence

    # === 최종 추천 ===
    score = round(score, 1)

    if rsi_override == "SELL":
        signals["recommendation"] = "SELL"
    else:
        buy_ratio = buy_signals / total_signals if total_signals > 0 else 0
        sell_ratio = sell_signals / total_signals if total_signals > 0 else 0

        if score >= 4 or (score >= 2 and buy_ratio >= 0.8):
            signals["recommendation"] = "STRONG_BUY"
        elif score >= 2 or (score >= 1.5 and buy_ratio >= 0.7):
            signals["recommendation"] = "BUY"
        elif score <= -4 or (score <= -2 and sell_ratio >= 0.8):
            signals["recommendation"] = "STRONG_SELL"
        elif score <= -2 or (score <= -1.5 and sell_ratio >= 0.7):
            signals["recommendation"] = "SELL"
        else:
            signals["recommendation"] = "HOLD"

    # === 빗각 미충족 경고 (혼합 모드) ===
    # BUY 신호인데 빗각 조건 안 맞으면 경고 + 신뢰도 하락
    bitgak_warning = None
    if signals["recommendation"] in ["STRONG_BUY", "BUY"]:
        if signal_flags.get("bitgak_ready"):
            # 빗각 최적: 신뢰도 상승
            if confidence == "MEDIUM":
                confidence = "HIGH"
            signals["signals"].append("✅ 빗각 조건 충족 - 진입 적기")
        elif signal_flags.get("bitgak_ok"):
            # 빗각 OK: 유지
            signals["signals"].append("⚡ 빗각 조건 부분 충족")
        else:
            # 빗각 미충족: 경고 + 신뢰도 하락
            csi_val = signals.get("indicators", {}).get("CSI", 0)
            hvn_dist = signals.get("indicators", {}).get("HVN_Proximity", 100)

            if csi_val is not None and csi_val > 5:
                bitgak_warning = f"⚠️ 추격매수 주의! CSI {csi_val:.1f}% (군중 수익 중)"
            elif csi_val is not None and csi_val < -10:
                bitgak_warning = f"⚠️ 낙폭과대 구간! CSI {csi_val:.1f}% (공포 구간)"
            elif hvn_dist is not None and hvn_dist > 5:
                bitgak_warning = f"⚠️ 매물대 원거리 ({hvn_dist:.1f}%) - 분할매수 권장"
            else:
                bitgak_warning = "⚠️ 빗각 조건 미충족 - 추격매수 주의"

            signals["signals"].append(bitgak_warning)
            confidence = "LOW"

    signals["confidence"] = confidence
    signals["bitgak_warning"] = bitgak_warning
    signals["score"] = score
    signals["combo_bonus"] = combo_bonus

    return signals


def sort_holdings(holdings):
    """
    보유 종목 정렬:
    1. 보유 중 (quantity > 0) 먼저
    2. STRONG_BUY → STRONG_SELL → BUY → SELL → HOLD 순
    """
    rec_order = {
        "STRONG_BUY": 0,
        "STRONG_SELL": 1,
        "BUY": 2,
        "SELL": 3,
        "HOLD": 4,
    }

    def sort_key(h):
        has_quantity = 1 if h.get("quantity", 0) > 0 else 0
        rec = h.get("recommendation", "HOLD")
        rec_priority = rec_order.get(rec, 5)
        return (-has_quantity, rec_priority)  # 보유 먼저, 그 다음 추천순

    return sorted(holdings, key=sort_key)


def analyze_portfolio():
    """포트폴리오 전체 분석"""
    portfolio = load_portfolio()
    if not portfolio:
        print("portfolio.json 파일이 없습니다.")
        return None

    print("시장 지표 분석 중...")
    market_indicators = get_market_indicators()
    print(f"  VIX: {market_indicators.get('vix', 'N/A')} ({market_indicators.get('sentiment_desc', '')})")

    results = {
        "analyzed_at": datetime.now().isoformat(),
        "market": market_indicators,
        "holdings": []
    }

    all_holdings = get_all_holdings(portfolio)

    for holding in all_holdings:
        symbol = holding["symbol"]
        market = holding.get("market", "us")
        underlying = get_underlying(symbol)
        is_lev = is_leveraged(symbol)

        market_label = "[US]" if market == "us" else "[KR]" if market == "kr" else "[CRYPTO]"

        if is_lev:
            print(f"{market_label} [{symbol}] → [{underlying}] 분석 중...")
        else:
            print(f"{market_label} [{symbol}] 분석 중...")

        df = get_stock_data(underlying, period="1y")
        analysis = analyze_signals(df, symbol, underlying if is_lev else None)
        analysis["name"] = holding.get("name", "")
        analysis["quantity"] = holding.get("quantity", 0)
        analysis["is_leveraged"] = is_lev
        analysis["market"] = market

        if is_lev:
            lev_df = get_stock_data(symbol, period="5d")
            if lev_df is not None and len(lev_df) > 0:
                analysis["leveraged_price"] = round(lev_df['Close'].iloc[-1], 2)

        print(f"  펀더멘털 데이터 가져오는 중...")
        analysis["fundamentals"] = get_fundamentals(underlying)

        print(f"  매매 전략 생성 중...")
        analysis["strategy"] = generate_trading_strategy(analysis, market_indicators)

        results["holdings"].append(analysis)

        rec = analysis.get('recommendation', 'N/A')
        score = analysis.get('score', 'N/A')
        action = analysis.get('strategy', {}).get('action', 'N/A')
        bitgak = analysis.get('bitgak', {}).get('grade', 'NONE')
        print(f"  → {rec} (점수: {score}) | 전략: {action} | 빗각: {bitgak}")

    # 정렬: 보유 종목 먼저, 그 다음 추천순
    results["holdings"] = sort_holdings(results["holdings"])

    # === 포트폴리오 요약 계산 ===
    print("\n포트폴리오 요약 계산 중...")

    # 현금 잔고
    cash = portfolio.get("cash", {"usd": 0, "krw": 0})
    cash_usd = cash.get("usd", 0)
    cash_krw = cash.get("krw", 0)

    # 환율 가져오기
    exchange_rate = get_exchange_rate("USD", "KRW") or 1420  # 기본값
    print(f"  환율: $1 = {exchange_rate:,.0f}원")

    # 투자 자산 계산
    total_usd = 0  # USD 투자 (미국주식 + 코인)
    total_krw = 0  # KRW 투자 (한국주식)

    holdings_summary = []

    for h in results["holdings"]:
        qty = h.get("quantity", 0)
        if qty <= 0:
            continue

        market = h.get("market", "us")
        symbol = h["symbol"]

        # 현재가 가져오기 (레버리지면 레버리지 가격, 아니면 current_price)
        if h.get("leveraged_price"):
            current_price = h["leveraged_price"]
        else:
            current_price = h.get("current_price", 0)

        # 평균 매수가
        avg_price = 0
        for mkt_holdings in portfolio.get("holdings", {}).values():
            for ph in mkt_holdings:
                if ph.get("symbol", "").upper() == symbol.upper():
                    avg_price = ph.get("avg_price", 0)
                    break

        current_value = qty * current_price
        cost_basis = qty * avg_price
        profit_loss = current_value - cost_basis if avg_price > 0 else 0
        profit_pct = ((current_price / avg_price) - 1) * 100 if avg_price > 0 else 0

        if market == "kr":
            total_krw += current_value
        else:  # us 또는 crypto
            total_usd += current_value

        holdings_summary.append({
            "symbol": symbol,
            "name": h.get("name", ""),
            "market": market,
            "quantity": qty,
            "avg_price": avg_price,
            "current_price": current_price,
            "current_value": current_value,
            "profit_loss": profit_loss,
            "profit_pct": round(profit_pct, 2)
        })

    # 총합 계산
    total_usd_in_krw = total_usd * exchange_rate
    total_cash_in_krw = (cash_usd * exchange_rate) + cash_krw
    grand_total_krw = total_usd_in_krw + total_krw + total_cash_in_krw

    results["summary"] = {
        "exchange_rate": exchange_rate,
        "investments": {
            "usd": round(total_usd, 2),  # USD 투자총액 (미국+코인)
            "usd_in_krw": round(total_usd_in_krw, 0),
            "krw": round(total_krw, 0),  # KRW 투자총액 (한국)
        },
        "cash": {
            "usd": cash_usd,
            "krw": cash_krw,
            "total_in_krw": round(total_cash_in_krw, 0),
        },
        "total_krw": round(grand_total_krw, 0),
        "holdings_detail": holdings_summary
    }

    print(f"  USD 투자: ${total_usd:,.2f} ({total_usd_in_krw:,.0f}원)")
    print(f"  KRW 투자: {total_krw:,.0f}원")
    print(f"  현금: ${cash_usd:,.2f} + {cash_krw:,.0f}원")
    print(f"  총 자산: {grand_total_krw:,.0f}원")

    return results


if __name__ == "__main__":
    print("포트폴리오 분석 시작...\n")
    results = analyze_portfolio()
    if results:
        save_report(results)
        print("\n완료!")

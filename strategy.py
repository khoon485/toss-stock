"""
매매 전략 생성 모듈
- 분할매수/매도 전략
- 손절선/익절 목표
- 시장 상황 반영
"""


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
    bitgak = analysis.get("bitgak", {})

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

    # 빗각 신호 확인
    bitgak_grade = bitgak.get("grade", "NONE")
    bitgak_score = bitgak.get("score", 0)

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

        # 빗각 신호가 있으면 전략 보강
        if bitgak_grade in ["STRONG_BITGAK", "BITGAK"]:
            hvn_price = bitgak.get("hvn_price", current_price * 0.95)
            strategy["entry_strategy"].append(f"빗각 매수: 매물대 ${hvn_price:.2f} 근처에서 추가 매수 고려")
            strategy["reasoning"].append(f"빗각 신호 ({bitgak_grade}) - 매물대/VWAP 기반 진입")

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

        # 빗각 신호가 있으면 매수 조건에 추가
        if bitgak_grade != "NONE":
            hvn_price = bitgak.get("hvn_price", current_price * 0.95)
            strategy["entry_strategy"] = [
                f"빗각 매수 대기: 매물대 ${hvn_price:.2f} 도달 시 매수 검토",
                f"CSI 확인: {bitgak.get('csi', 'N/A')}% (본전 구간 -5%~+2%)",
            ]
            strategy["reasoning"].append(f"빗각 신호 감지 - 매물대 근처 진입 대기")
        else:
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

    # 빗각 경고 반영
    bitgak_warning = analysis.get("bitgak_warning")
    if bitgak_warning and strategy["action"] == "BUY":
        strategy["reasoning"].append(bitgak_warning)
        # 빗각 미충족 시 비중 축소
        if "추격매수" in bitgak_warning or "원거리" in bitgak_warning:
            strategy["confidence"] = "LOW"
            if strategy["position_size"] == "30%":
                strategy["position_size"] = "15%"
            elif strategy["position_size"] == "20%":
                strategy["position_size"] = "10%"
            strategy["reasoning"].append("빗각 미충족 - 비중 50% 축소")

    return strategy

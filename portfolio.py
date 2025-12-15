"""
포트폴리오 관리 모듈
- 포트폴리오 로드/저장
- 분석 리포트 생성
"""

import json
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")


def load_portfolio():
    """포트폴리오 파일 로드"""
    filepath = os.path.join(DATA_DIR, "portfolio.json")
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def save_portfolio(portfolio):
    """포트폴리오 파일 저장"""
    filepath = os.path.join(DATA_DIR, "portfolio.json")
    portfolio["updated_at"] = datetime.now().isoformat()
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(portfolio, f, ensure_ascii=False, indent=2)
    return filepath


def add_holding(symbol, name, quantity=0, market="us"):
    """종목 추가"""
    portfolio = load_portfolio() or {"holdings": {"us": [], "kr": [], "crypto": []}}

    holdings = portfolio.get("holdings", {})
    if isinstance(holdings, list):
        # 기존 구조 변환
        holdings = {"us": holdings, "kr": [], "crypto": []}
        portfolio["holdings"] = holdings

    if market not in holdings:
        holdings[market] = []

    # 중복 체크
    for h in holdings[market]:
        if h["symbol"].upper() == symbol.upper():
            print(f"[{symbol}] 이미 존재합니다.")
            return False

    holdings[market].append({
        "symbol": symbol.upper(),
        "name": name,
        "quantity": quantity
    })

    save_portfolio(portfolio)
    print(f"[{symbol}] 추가 완료")
    return True


def remove_holding(symbol, market="us"):
    """종목 제거"""
    portfolio = load_portfolio()
    if not portfolio:
        return False

    holdings = portfolio.get("holdings", {})
    if market not in holdings:
        return False

    original_len = len(holdings[market])
    holdings[market] = [h for h in holdings[market] if h["symbol"].upper() != symbol.upper()]

    if len(holdings[market]) < original_len:
        save_portfolio(portfolio)
        print(f"[{symbol}] 제거 완료")
        return True

    print(f"[{symbol}] 찾을 수 없습니다.")
    return False


def get_all_holdings(portfolio=None):
    """모든 종목 리스트 반환 (market 정보 포함)"""
    if portfolio is None:
        portfolio = load_portfolio()

    if not portfolio:
        return []

    holdings_data = portfolio.get("holdings", [])

    if isinstance(holdings_data, dict):
        # 새 구조: {"us": [...], "kr": [...], "crypto": [...]}
        all_holdings = []
        for market_type, holdings_list in holdings_data.items():
            for h in holdings_list:
                h["market"] = market_type
                all_holdings.append(h)
        return all_holdings
    else:
        # 기존 구조: [...]
        for h in holdings_data:
            h["market"] = "us"
        return holdings_data


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
        _write_text_report(f, results)

    print(f"\n리포트 저장 완료:")
    print(f"  - {json_path}")
    print(f"  - {txt_path}")

    return json_path, txt_path


def _write_text_report(f, results):
    """텍스트 리포트 작성"""
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
        _write_holding_report(f, h)

    # 포트폴리오 요약 섹션
    summary = results.get("summary", {})
    if summary:
        _write_portfolio_summary(f, summary)

    f.write(f"{'='*60}\n")
    f.write(f"분석 완료\n")


def _write_holding_report(f, h):
    """개별 종목 리포트 작성"""
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

    # 빗각 분석 (Bitgak)
    bitgak = h.get("bitgak", {})
    if bitgak and bitgak.get("csi") is not None:
        f.write(f"\n📐 빗각 분석:\n")
        bitgak_grade = bitgak.get("grade", "NONE")
        grade_emoji = {"STRONG_BITGAK": "🎯🎯", "BITGAK": "🎯", "NONE": "➖"}.get(bitgak_grade, "")
        f.write(f"  빗각 신호: {grade_emoji} {bitgak_grade} (점수: {bitgak.get('score', 0)})\n")
        f.write(f"  CSI (군중스트레스): {bitgak.get('csi', 'N/A')}%\n")
        if market == "kr":
            f.write(f"  VWAP (평균단가): {currency}{bitgak.get('vwap_20', 0):,.0f}\n")
            f.write(f"  매물대 (HVN): {currency}{bitgak.get('hvn_price', 0):,.0f}\n")
        else:
            f.write(f"  VWAP (평균단가): {currency}{bitgak.get('vwap_20', 0):,.2f}\n")
            f.write(f"  매물대 (HVN): {currency}{bitgak.get('hvn_price', 0):,.2f}\n")
        f.write(f"  매물대 근접도: {bitgak.get('hvn_proximity', 'N/A')}%\n")

        # CSI 해석
        csi_val = bitgak.get('csi', 0)
        if csi_val is not None:
            if csi_val < -10:
                f.write(f"  └─ 군중 대부분 손실 중 (공포/존버 구간)\n")
            elif csi_val > 10:
                f.write(f"  └─ 군중 대부분 수익 중 (차익실현 압력)\n")
            elif -5 <= csi_val <= 2:
                f.write(f"  └─ 본전 심리 구간 (매수 기회!)\n")

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
            for exit_s in strategy["exit_strategy"]:
                f.write(f"  {exit_s}\n")

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


def _write_portfolio_summary(f, summary):
    """포트폴리오 요약 섹션 작성"""
    f.write(f"{'='*60}\n")
    f.write(f"💼 포트폴리오 요약\n")
    f.write(f"{'='*60}\n\n")

    exchange_rate = summary.get("exchange_rate", 1420)
    investments = summary.get("investments", {})
    cash = summary.get("cash", {})

    # 보유 종목 현황
    holdings_detail = summary.get("holdings_detail", [])
    if holdings_detail:
        f.write(f"📈 보유 종목 현황:\n")
        f.write(f"{'─'*60}\n")
        f.write(f"  {'종목':<15} {'수량':>10} {'평단가':>12} {'현재가':>12} {'수익률':>10}\n")
        f.write(f"{'─'*60}\n")

        for h in holdings_detail:
            symbol = h.get("symbol", "")
            qty = h.get("quantity", 0)
            avg_price = h.get("avg_price", 0)
            current_price = h.get("current_price", 0)
            profit_pct = h.get("profit_pct", 0)
            market = h.get("market", "us")

            currency = "₩" if market == "kr" else "$"

            if market == "kr":
                avg_str = f"{currency}{avg_price:,.0f}"
                cur_str = f"{currency}{current_price:,.0f}"
            else:
                avg_str = f"{currency}{avg_price:,.2f}"
                cur_str = f"{currency}{current_price:,.2f}"

            pct_str = f"{profit_pct:+.1f}%" if avg_price > 0 else "N/A"
            emoji = "🟢" if profit_pct > 0 else "🔴" if profit_pct < 0 else "⚪"

            f.write(f"  {symbol:<15} {qty:>10.4f} {avg_str:>12} {cur_str:>12} {emoji}{pct_str:>8}\n")

        f.write(f"{'─'*60}\n\n")

    # 투자 자산
    f.write(f"💰 자산 현황:\n")
    f.write(f"{'─'*60}\n")

    usd_total = investments.get("usd", 0)
    usd_in_krw = investments.get("usd_in_krw", 0)
    krw_total = investments.get("krw", 0)
    cash_usd = cash.get("usd", 0)
    cash_krw = cash.get("krw", 0)
    cash_total_krw = cash.get("total_in_krw", 0)
    grand_total = summary.get("total_krw", 0)

    f.write(f"  USD 투자 (미국주식+코인): ${usd_total:>12,.2f}  (₩{usd_in_krw:>15,.0f})\n")
    f.write(f"  KRW 투자 (한국주식):                        ₩{krw_total:>15,.0f}\n")
    f.write(f"{'─'*60}\n")
    f.write(f"  투자 합계:                                  ₩{(usd_in_krw + krw_total):>15,.0f}\n")
    f.write(f"\n")
    f.write(f"  현금 (USD): ${cash_usd:>12,.2f}  (₩{(cash_usd * exchange_rate):>15,.0f})\n")
    f.write(f"  현금 (KRW):                                 ₩{cash_krw:>15,.0f}\n")
    f.write(f"{'─'*60}\n")
    f.write(f"  현금 합계:                                  ₩{cash_total_krw:>15,.0f}\n")
    f.write(f"\n")

    f.write(f"{'='*60}\n")
    f.write(f"  📊 오늘 환율: $1 = ₩{exchange_rate:,.2f}\n")
    f.write(f"{'='*60}\n")
    f.write(f"  🏦 총 자산:                                 ₩{grand_total:>15,.0f}\n")
    f.write(f"{'='*60}\n\n")


def get_latest_report():
    """가장 최근 리포트 경로 반환"""
    reports_dir = os.path.join(DATA_DIR, "reports")
    if not os.path.exists(reports_dir):
        return None

    # 가장 최근 년/월/일 폴더 찾기
    latest = None
    for year in sorted(os.listdir(reports_dir), reverse=True):
        year_dir = os.path.join(reports_dir, year)
        if not os.path.isdir(year_dir):
            continue
        for month in sorted(os.listdir(year_dir), reverse=True):
            month_dir = os.path.join(year_dir, month)
            if not os.path.isdir(month_dir):
                continue
            for day in sorted(os.listdir(month_dir), reverse=True):
                day_dir = os.path.join(month_dir, day)
                if not os.path.isdir(day_dir):
                    continue
                # 가장 최근 파일
                files = sorted([f for f in os.listdir(day_dir) if f.endswith('.json')], reverse=True)
                if files:
                    return os.path.join(day_dir, files[0])
    return None


def load_latest_report():
    """가장 최근 리포트 로드"""
    path = get_latest_report()
    if path and os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

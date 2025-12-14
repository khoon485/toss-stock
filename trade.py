"""
매매일지 관리
- 매수/매도 기록
- 수익률 계산
- 거래 내역 조회
"""

import json
import os
import sys
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
TRADES_FILE = os.path.join(DATA_DIR, "trades.json")


def load_trades():
    """매매일지 로드"""
    if os.path.exists(TRADES_FILE):
        with open(TRADES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"trades": []}


def save_trades(data):
    """매매일지 저장"""
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(TRADES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def add_trade(trade_type, symbol, quantity, price, memo=""):
    """매매 기록 추가"""
    data = load_trades()

    trade = {
        "id": len(data["trades"]) + 1,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "time": datetime.now().strftime("%H:%M:%S"),
        "type": trade_type,  # buy / sell
        "symbol": symbol.upper(),
        "quantity": float(quantity),
        "price": float(price),
        "total": round(float(quantity) * float(price), 2),
        "memo": memo
    }

    data["trades"].append(trade)
    save_trades(data)

    emoji = "🟢" if trade_type == "buy" else "🔴"
    action = "매수" if trade_type == "buy" else "매도"
    print(f"{emoji} {action} 기록 추가됨:")
    print(f"  종목: {trade['symbol']}")
    print(f"  수량: {trade['quantity']}")
    print(f"  가격: ${trade['price']}")
    print(f"  총액: ${trade['total']}")
    if memo:
        print(f"  메모: {memo}")

    return trade


def list_trades(symbol=None, limit=10):
    """매매 내역 조회"""
    data = load_trades()
    trades = data["trades"]

    if symbol:
        trades = [t for t in trades if t["symbol"] == symbol.upper()]

    trades = trades[-limit:]  # 최근 N개

    if not trades:
        print("매매 기록이 없습니다.")
        return

    print(f"\n{'='*60}")
    print(f"  매매일지 (최근 {len(trades)}건)")
    print(f"{'='*60}")

    for t in trades:
        emoji = "🟢" if t["type"] == "buy" else "🔴"
        action = "매수" if t["type"] == "buy" else "매도"
        print(f"\n{emoji} [{t['date']}] {t['symbol']} {action}")
        print(f"   수량: {t['quantity']} | 가격: ${t['price']} | 총액: ${t['total']}")
        if t.get("memo"):
            print(f"   메모: {t['memo']}")

    print(f"\n{'='*60}")


def get_holdings_summary():
    """보유 현황 요약 (매매일지 기반)"""
    data = load_trades()
    trades = data["trades"]

    holdings = {}

    for t in trades:
        symbol = t["symbol"]
        if symbol not in holdings:
            holdings[symbol] = {
                "quantity": 0,
                "total_cost": 0,
                "trades": []
            }

        if t["type"] == "buy":
            holdings[symbol]["quantity"] += t["quantity"]
            holdings[symbol]["total_cost"] += t["total"]
        else:  # sell
            holdings[symbol]["quantity"] -= t["quantity"]
            holdings[symbol]["total_cost"] -= t["total"]

        holdings[symbol]["trades"].append(t)

    print(f"\n{'='*60}")
    print(f"  보유 현황 (매매일지 기준)")
    print(f"{'='*60}")

    for symbol, data in holdings.items():
        if data["quantity"] > 0:
            avg_price = data["total_cost"] / data["quantity"] if data["quantity"] > 0 else 0
            print(f"\n{symbol}")
            print(f"  보유 수량: {data['quantity']}")
            print(f"  평균 단가: ${avg_price:.2f}")
            print(f"  총 투자금: ${data['total_cost']:.2f}")

    print(f"\n{'='*60}")


def delete_trade(trade_id):
    """매매 기록 삭제"""
    data = load_trades()

    original_len = len(data["trades"])
    data["trades"] = [t for t in data["trades"] if t["id"] != trade_id]

    if len(data["trades"]) < original_len:
        save_trades(data)
        print(f"✅ ID {trade_id} 기록 삭제됨")
    else:
        print(f"❌ ID {trade_id} 기록을 찾을 수 없음")


def print_help():
    """도움말"""
    print("""
매매일지 사용법:

  매수 기록:
    python trade.py buy <종목> <수량> <가격> [메모]
    예: python trade.py buy GOOGL 4 192.50 "분할매수 1차"

  매도 기록:
    python trade.py sell <종목> <수량> <가격> [메모]
    예: python trade.py sell GOOGL 2 200.00 "익절"

  전체 내역:
    python trade.py list
    python trade.py list GOOGL  (특정 종목만)

  보유 현황:
    python trade.py holdings

  기록 삭제:
    python trade.py delete <ID>
    예: python trade.py delete 3
""")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print_help()
        sys.exit(0)

    cmd = sys.argv[1].lower()

    if cmd == "buy":
        if len(sys.argv) < 5:
            print("사용법: python trade.py buy <종목> <수량> <가격> [메모]")
            sys.exit(1)
        symbol = sys.argv[2]
        quantity = sys.argv[3]
        price = sys.argv[4]
        memo = sys.argv[5] if len(sys.argv) > 5 else ""
        add_trade("buy", symbol, quantity, price, memo)

    elif cmd == "sell":
        if len(sys.argv) < 5:
            print("사용법: python trade.py sell <종목> <수량> <가격> [메모]")
            sys.exit(1)
        symbol = sys.argv[2]
        quantity = sys.argv[3]
        price = sys.argv[4]
        memo = sys.argv[5] if len(sys.argv) > 5 else ""
        add_trade("sell", symbol, quantity, price, memo)

    elif cmd == "list":
        symbol = sys.argv[2] if len(sys.argv) > 2 else None
        list_trades(symbol)

    elif cmd == "holdings":
        get_holdings_summary()

    elif cmd == "delete":
        if len(sys.argv) < 3:
            print("사용법: python trade.py delete <ID>")
            sys.exit(1)
        trade_id = int(sys.argv[2])
        delete_trade(trade_id)

    else:
        print_help()

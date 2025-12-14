"""
통합 실행 스크립트
1. 토스증권 스크린샷
2. 포트폴리오 분석
3. 리포트 저장
"""

import os
import sys
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from crawler import get_driver, take_screenshot
from analyzer import analyze_portfolio, save_report


def run_full_analysis():
    """전체 분석 실행"""
    print("=" * 60)
    print(f"분석 시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 1. 토스증권 스크린샷
    print("\n[1/2] 토스증권 스크린샷...")
    try:
        driver = get_driver()
        screenshot_path = take_screenshot(driver, f"toss_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        print(f"  ✓ 저장: {screenshot_path}")
    except Exception as e:
        print(f"  ✗ 스크린샷 실패: {e}")
        print("  (Chrome 디버그 모드가 실행 중이어야 합니다)")

    # 2. 포트폴리오 분석
    print("\n[2/2] 포트폴리오 기술적 분석...")
    results = analyze_portfolio()

    if results:
        json_path, txt_path = save_report(results)

        # 요약 출력
        print("\n" + "=" * 60)
        print("분석 요약")
        print("=" * 60)
        for h in results["holdings"]:
            rec = h.get("recommendation", "N/A")
            emoji = {"STRONG_BUY": "🟢🟢", "BUY": "🟢", "HOLD": "⚪", "SELL": "🔴", "STRONG_SELL": "🔴🔴"}.get(rec, "")
            print(f"{emoji} {h['symbol']:6} | ${h.get('current_price', 'N/A'):>8} | {rec}")

    print("\n" + "=" * 60)
    print(f"완료: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)


if __name__ == "__main__":
    run_full_analysis()

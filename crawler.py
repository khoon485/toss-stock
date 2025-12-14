"""
토스증권 크롤러
- 스크린샷 캡처
- 포트폴리오 데이터 추출
- 매수/매도 자동화 (추후)
"""

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json
import os
from datetime import datetime

# 경로 설정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCREENSHOT_DIR = os.path.join(BASE_DIR, "screenshots")
DATA_DIR = os.path.join(BASE_DIR, "data")

# 폴더 생성
os.makedirs(SCREENSHOT_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

def get_driver():
    """Chrome 드라이버 반환 (이미 열린 브라우저에 붙기)"""
    options = uc.ChromeOptions()
    options.add_argument("--remote-debugging-port=9222")
    options.debugger_address = "127.0.0.1:9222"

    driver = uc.Chrome(options=options)
    return driver

def take_screenshot(driver, name=None):
    """스크린샷 저장"""
    if name is None:
        name = datetime.now().strftime("%Y%m%d_%H%M%S")

    filepath = os.path.join(SCREENSHOT_DIR, f"{name}.png")
    driver.save_screenshot(filepath)
    print(f"스크린샷 저장: {filepath}")
    return filepath

def get_portfolio(driver):
    """보유 종목 정보 추출 (토스증권 구조에 맞게 수정 필요)"""
    # TODO: 토스증권 DOM 구조 분석 후 구현
    portfolio = {
        "timestamp": datetime.now().isoformat(),
        "holdings": []
    }

    # 예시: 종목 리스트 찾기 (셀렉터는 실제 DOM 보고 수정해야 함)
    # items = driver.find_elements(By.CSS_SELECTOR, ".stock-item")
    # for item in items:
    #     portfolio["holdings"].append({
    #         "name": item.find_element(By.CSS_SELECTOR, ".name").text,
    #         "quantity": item.find_element(By.CSS_SELECTOR, ".qty").text,
    #         "price": item.find_element(By.CSS_SELECTOR, ".price").text,
    #     })

    return portfolio

def save_portfolio(portfolio):
    """포트폴리오 JSON 저장"""
    filepath = os.path.join(DATA_DIR, "portfolio.json")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(portfolio, f, ensure_ascii=False, indent=2)
    print(f"포트폴리오 저장: {filepath}")

def goto_toss(driver):
    """토스증권으로 이동"""
    toss_url = "https://www.tossinvest.com"
    driver.get(toss_url)
    import time
    time.sleep(3)  # 페이지 로딩 대기

def main():
    print("토스증권 크롤러 시작...")
    print("Chrome 디버그 모드 연결 시도 중...")

    try:
        print("드라이버 생성 중...")
        driver = get_driver()
        print("연결 성공!")
        print(f"현재 페이지: {driver.current_url}")

        # 토스증권으로 이동
        if "tossinvest" not in driver.current_url:
            print("토스증권으로 이동 중...")
            goto_toss(driver)
            print(f"이동 완료: {driver.current_url}")

        # 스크린샷
        screenshot_path = take_screenshot(driver)

        # 포트폴리오 (추후 구현)
        # portfolio = get_portfolio(driver)
        # save_portfolio(portfolio)

        print("-" * 50)
        print("완료!")

    except Exception as e:
        print(f"에러: {e}")
        print("\n디버그 모드 Chrome 실행 방법:")
        print('1. 모든 Chrome 창 닫기')
        print('2. 실행: chrome.exe --remote-debugging-port=9222')
        print('3. 토스증권 로그인')
        print('4. 이 스크립트 다시 실행')

if __name__ == "__main__":
    main()

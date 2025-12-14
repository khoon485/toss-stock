# 토스증권 자동 분석 시스템

## 프로젝트 개요
토스증권 포트폴리오를 자동으로 분석하고 매수/매도 신호를 제공하는 시스템.

**주요 기능:**
- 기술적 분석 (이평선, 일목균형표, RSI, MACD, 볼린저밴드)
- 펀더멘털 분석 (PER, PBR, 매출성장률, 애널리스트 목표가)
- 시장 전체 분석 (VIX, SPY, QQQ, 금리)
- 캔들 패턴 감지 (도지, 망치형, 장악형 등)
- 구체적 매매 전략 (분할매수 가격대, 손절선, 익절 목표)
- 레버리지 ETF → 원본 종목 자동 매핑

## 폴더 구조
```
toss-stock/
├── crawler.py        # 토스증권 스크린샷 (Selenium)
├── analyzer.py       # 기술적 분석 (이평선, 일목균형표)
├── run_analysis.py   # 통합 실행
├── auto_run.bat      # 배치 실행
├── venv/             # Python 가상환경
├── data/
│   ├── portfolio.json       # 보유 종목 리스트
│   ├── analysis_report.json # 분석 결과 (JSON)
│   └── analysis_report.txt  # 분석 결과 (텍스트)
└── screenshots/      # 토스증권 캡처 이미지
```

## 주요 명령어

### 분석 실행
```powershell
cd C:\Users\SRPOST\Projects\toss-stock
.\venv\Scripts\python.exe analyzer.py
```

### 토스증권 스크린샷 (Chrome 디버그 모드 필요)
```powershell
# 1. Chrome 디버그 모드 실행
& "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\temp\chrome-debug"

# 2. 토스증권 로그인 후 크롤러 실행
.\venv\Scripts\python.exe crawler.py
```

### 통합 실행 (스크린샷 + 분석)
```powershell
.\venv\Scripts\python.exe run_analysis.py
```

## 사용자 요청 예시

- "분석 결과 봐줘" → `data/analysis_report.txt` 읽기
- "토스 스크린샷 찍어줘" → `crawler.py` 실행
- "NVDA 추가해줘" → `portfolio.json`에 종목 추가
- "포트폴리오 분석해줘" → `analyzer.py` 실행

## 기술적 분석 기준

### 이동평균선
- 골든크로스 (MA5 > MA20): 매수 신호
- 데드크로스 (MA5 < MA20): 매도 신호
- 가격 > 20일선: 상승 추세
- 가격 < 20일선: 하락 추세

### 일목균형표
- 전환선 > 기준선: 매수 신호
- 전환선 < 기준선: 매도 신호
- 가격 > 구름대: 강세
- 가격 < 구름대: 약세

### 추천 점수
- STRONG_BUY: 점수 >= 3
- BUY: 점수 >= 1
- HOLD: 점수 0
- SELL: 점수 <= -1
- STRONG_SELL: 점수 <= -3

## 종목 추가/수정
`data/portfolio.json` 파일 수정:
```json
{
  "holdings": [
    {"symbol": "AAPL", "name": "Apple Inc", "quantity": 10}
  ]
}
```

## 토스증권 URL
https://www.tossinvest.com/

## 사용자 요청 예시 (확장)
- "분석 돌려줘" → analyzer.py 실행
- "AAPL 분석해줘" → portfolio.json에 추가 후 분석
- "리포트 봐줘" → analysis_report.txt 읽기
- "시장 상황 어때?" → VIX, SPY 등 시장 지표 확인
- "NVDA 팔아야해?" → 해당 종목 전략 확인

## 레버리지 ETF 매핑
레버리지 ETF 분석 시 자동으로 원본 종목 차트를 분석함:
- SOXL/SOXS → SOXX (반도체)
- TQQQ/SQQQ → QQQ (나스닥)
- MSTX → MSTR (마이크로스트래티지)
- NVDL → NVDA (엔비디아)
- TSLL → TSLA (테슬라)
- CONL → COIN (코인베이스)

## 참고사항
- 가상환경 경로: `venv\Scripts\python.exe`
- yfinance로 야후 파이낸스 데이터 사용
- Chrome 디버그 포트: 9222
- 분석은 미국 시장 마감 후 데이터 기준

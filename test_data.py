import FinanceDataReader as fdr
import pandas as pd
from datetime import datetime

print("✅ FinanceDataReader 테스트 시작!")
print(f"버전: {fdr.__version__}")

# 오늘 날짜
today = datetime.today().strftime("%Y-%m-%d")
print(f"오늘 날짜: {today}")

# 1. 코스피 종목 리스트 가져오기
print("\n📊 코스피 종목 리스트 불러오는 중...")
kospi_stocks = fdr.StockListing('KOSPI')

print("\n📋 실제 컬럼명:")
print(kospi_stocks.columns.tolist())

# 컬럼이 어떻게 되어 있는지 확인하면서 안전하게 처리
print("\n📊 상위 10종목 (시가총액 기준)")

# 가능한 컬럼명으로 처리
if 'Marcap' in kospi_stocks.columns:
    sort_col = 'Marcap'
elif 'MarketCap' in kospi_stocks.columns:
    sort_col = 'MarketCap'
else:
    sort_col = 'Close'  # 마지노선

top10 = kospi_stocks.head(10).copy()

# 시가총액 단위 변환 (억 원)
if sort_col in top10.columns:
    top10[sort_col] = top10[sort_col] / 100000000

print(top10[['Code', 'Name', sort_col, 'Close', 'Volume']])

# 2. 코스피 지수
print("\n📈 코스피 지수 (최근 5거래일)")
kospi_index = fdr.DataReader('KS11', start='2026-05-01')
print(kospi_index.tail(5))

print("\n🎉 테스트 완료!")
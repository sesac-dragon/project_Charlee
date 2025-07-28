import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

def insert_backtest_result_to_db(df):
    conn = pymysql.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        port=int(os.getenv("DB_PORT")),
        database=os.getenv("DB_NAME"),
        charset='utf8mb4'
    )
    cursor = conn.cursor()

    insert_sql = """
    INSERT INTO backtest_result (
        time, market, open, high, close, `signal`, trade_amount,
        avg_price, gap_pct, total_buy_amount, realized_pnl,
        cash, trade_fee, total_fee, portfolio_value
    ) VALUES (
        %s, %s, %s, %s, %s, %s, %s,
        %s, %s, %s, %s,
        %s, %s, %s, %s
    )
    """

    for _, row in df.iterrows():
        cursor.execute(insert_sql, (
            row["시간"], row["마켓"], row["시가"], row["고가"], row["종가"], row["신호"], row["매매금액"],
            row["현재 평단가"], row["현재 종가와 평단가의 gap(%)"], row["누적 매수금"], row["실현 손익"],
            row["보유 현금"], row["거래시 수수료"], row["총 누적 수수료"], row["총 포트폴리오 가치"]
        ))

    conn.commit()
    cursor.close()
    conn.close()
    print("✅ 백테스트 결과가 DB에 저장되었습니다.")

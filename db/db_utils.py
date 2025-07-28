import pymysql
from db.db_config import DB_CONFIG

def insert_order(order_data: dict, table_name: str):
    """체결 완료된 주문 정보를 DB에 저장합니다."""
    
    # DB에 이미 존재하는 컬럼만 필터링
    # 이 코드는 나중에 테이블 구조가 변경되어도 유연하게 대처할 수 있게 합니다.
    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute(f"SHOW COLUMNS FROM {table_name}")
    db_columns = [column[0] for column in cursor.fetchall()]
    
    # order_data에서 DB에 있는 컬럼만 필터링
    filtered_data = {key: value for key, value in order_data.items() if key in db_columns}
    
    # SQL INSERT 쿼리 생성
    columns = ", ".join(filtered_data.keys())
    placeholders = ", ".join(["%s"] * len(filtered_data))
    query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
    
    try:
        cursor.execute(query, list(filtered_data.values()))
        conn.commit()
        print(f"✅ [DB] {order_data.get('market')} {table_name}에 저장 완료")
    except Exception as e:
        print(f"❌ [DB] 데이터 저장 실패: {e}")
        conn.rollback()
    finally:
        conn.close()
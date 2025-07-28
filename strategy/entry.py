# 이 파일의 로직은 core/main.py로 이전되었으며, 현재는 사용되지 않습니다.
# import time
# 
# from strategy.buy_entry import run_buy_entry_flow
# from strategy.sell_entry import run_sell_entry_flow
# 
# import time
# 
# def run_casino_entry():
#     print("[entry.py] ▶ 카지노 매매 시스템 시작")
# 
#     while True:
#         try:
#             # 1. 매수 전략 실행
#             print("\n[entry.py] ▶ 매수 전략 실행")
#             run_buy_entry_flow()
# 
#             # 2. 매도 전략 실행
#             print("\n[entry.py] ▶ 매도 전략 실행")
#             run_sell_entry_flow()
# 
#         except Exception as e:
#             print(f"\n[entry.py] ⚠️ 예외 발생: {e}")
# 
#         # 딜레이 (예: 5초)
#         time.sleep(5)
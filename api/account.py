# api/account.py

import requests
import copy
from api.auth import generate_jwt_token
from core import config

def get_accounts():
    print("[account.py] get_accounts() 실행됨")

    headers = {
        'Authorization': generate_jwt_token(copy.deepcopy({}))
    }

    try:
        response = requests.get(f"{config.SERVER_URL}/v1/accounts", headers=headers)

        if response.status_code == 200:
            accounts = response.json()
            print("[account.py] 계좌 조회 성공")
            print("[DEBUG] 현재 계좌 정보:", accounts)
            return accounts
        else:
            print("[account.py] 계좌 조회 실패")
            raise Exception(f"[Upbit API] 계좌 조회 실패: {response.status_code} - {response.text}")

    except Exception as e:
        print(f"[account.py] 예외 발생: {e}")
        raise

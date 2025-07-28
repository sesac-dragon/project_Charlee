import requests
import time
import copy
from core import config
from api.auth import generate_jwt_token


def send_order(market: str, side: str, ord_type: str,
               volume: float = None, unit_price: float = None, amount_krw: float = None) -> dict:
    url = f"{config.SERVER_URL}/v1/orders"
    body = {
        "market": market,
        "side": side,
        "ord_type": ord_type,
    }

    if ord_type == "limit":
        body.update({
            "price": str(unit_price),
            "volume": str(volume)
        })
    elif ord_type == "price":
        body["price"] = str(amount_krw)
    elif ord_type == "market":
        body["volume"] = str(volume)

    headers = {
        "Authorization": generate_jwt_token(body)  # ✅ query 포함
    }

    response = requests.post(url, json=body, headers=headers)

    if response.status_code == 201:
        return response.json()
    else:
        raise Exception(f"❌ 주문 실패: {response.status_code} - {response.text}")


def cancel_order(uuid: str) -> dict:
    url = f"{config.SERVER_URL}/v1/order"
    query = {"uuid": uuid}
    headers = {"Authorization": generate_jwt_token(copy.deepcopy(query))}

    response = requests.delete(url, params=query, headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"❌ 주문 취소 실패: {response.status_code} - {response.text}")


def cancel_and_new_order(prev_order_uuid: str, market: str, price: float, amount: float) -> dict:
    try:
        cancel_response = cancel_order(prev_order_uuid)
        if not cancel_response.get("uuid"):
            raise ValueError("기존 주문 취소 실패 (uuid 없음)")
    except Exception as e:
        raise RuntimeError(f"기존 주문 취소 실패: {e}")

    time.sleep(0.3)

    try:
        new_response = send_order(
            market=market,
            side="bid" if "KRW" in market else "ask",
            ord_type="limit",
            unit_price=price,
            volume=round(amount, 8)
        )
        return {"new_order_uuid": new_response.get("uuid")}
    except Exception as e:
        raise RuntimeError(f"신규 주문 실패: {e}")


def get_order_results_by_uuids_safe(uuids, batch_size=20):
    results = []

    for i in range(0, len(uuids), batch_size):
        batch = uuids[i:i + batch_size]
        for uuid in batch:
            query = {"uuid": uuid}
            headers = {"Authorization": generate_jwt_token(query)}
            response = requests.get(f"{config.SERVER_URL}/v1/order", params=query, headers=headers)

            if response.status_code == 200:
                results.append(response.json())
            else:
                pass  # ✅ 로그 생략 (사용자 요청)

    return results


def cancel_orders_by_uuids(uuid_list):
    url = f"{config.SERVER_URL}/v1/orders/cancel/batch"
    data = {"uuids": uuid_list}
    headers = {"Authorization": generate_jwt_token(copy.deepcopy(data))}

    try:
        response = requests.delete(url, headers=headers, json=data)
        if response.status_code == 200:
            return response.json()
        else:
            return {}  # ✅ 로그 생략
    except Exception:
        return {}  # ✅ 로그 생략

import pandas as pd

def generate_buy_orders(setting_df: pd.DataFrame, buy_log_df: pd.DataFrame, current_prices: dict) -> pd.DataFrame:
    """
    # --- [전략의 핵심 ①: 매수 전략] ---
    # "하락 추종 분할 매수" 전략에 따라 매수 주문을 생성하거나, 기존 주문을 조정합니다.
    # 이 함수는 시스템의 두뇌 역할을 하며, 모든 매수 관련 의사결정을 담당합니다.
    """
    print("[casino_strategy.py] generate_buy_orders() 호출됨")

    new_logs = []

    # 설정 파일(setting.csv)에 정의된 모든 코인에 대해 개별적으로 전략을 적용합니다.
    for _, setting in setting_df.iterrows():
        market = setting["market"]
        unit_size = setting["unit_size"]
        small_pct = setting["small_flow_pct"]
        small_units = setting["small_flow_units"]
        large_pct = setting["large_flow_pct"]
        large_units = setting["large_flow_units"]

        current_price = current_prices.get(market)
        if current_price is None:
            print(f"❌ 현재 가격 없음 → {market}")
            continue

        # --- [상황 판단] --- #
        # 현재 해당 코인의 거래 기록이 있는지 확인하여, 어떤 상태인지 판단합니다.
        coin_logs = buy_log_df[buy_log_df["market"] == market]
        initial_logs = coin_logs[coin_logs["buy_type"] == "initial"]
        flow_logs = coin_logs[coin_logs["buy_type"].isin(["small_flow", "large_flow"])]

        # ✅ [상황 1: 신규 진입] - 해당 코인을 보유하고 있지 않을 때
        if coin_logs.empty:
            # 이 코인에 대한 첫 거래이므로, 3가지 종류의 주문을 한 번에 계획합니다.
            print(f"📌 {market} → 상황1: 최초 주문 생성")

            # 1. 현재가 매수 (Initial Buy): 리스크 관리를 위해 소액으로 즉시 시장에 진입합니다.
            new_logs.append({
                "time": pd.Timestamp.now(),
                "market": market,
                "target_price": current_price,
                "buy_amount": unit_size,
                "buy_units": 1,
                "buy_type": "initial",
                "buy_uuid": None,
                "filled": "update"  # "update" 상태는 이 주문을 거래소로 전송해야 함을 의미합니다.
            })

            # 2. 1차 하락 매수 (Small Flow): 첫 매수 가격보다 일정 비율 하락 시, 추가 매수할 주문을 미리 계획합니다.
            small_price = round(current_price * (1 - small_pct))
            new_logs.append({
                "time": pd.Timestamp.now(),
                "market": market,
                "target_price": small_price,
                "buy_amount": unit_size * small_units,
                "buy_units": small_units,
                "buy_type": "small_flow",
                "buy_uuid": None,
                "filled": "update"
            })

            # 3. 2차 하락 매수 (Large Flow): 더 큰 하락에 대비한, 더 많은 수량의 추가 매수 주문을 계획합니다.
            large_price = round(current_price * (1 - large_pct))
            new_logs.append({
                "time": pd.Timestamp.now(),
                "market": market,
                "target_price": large_price,
                "buy_amount": unit_size * large_units,
                "buy_units": large_units,
                "buy_type": "large_flow",
                "buy_uuid": None,
                "filled": "update"
            })

        # ✅ [상황 2: 보유 중] - 이미 첫 매수(initial)가 체결되었을 때
        elif not initial_logs.empty and any(initial_logs["filled"] == "done"):
            print(f"📌 {market} → 수정된 상황2: flow 주문 개별 처리 시작")

            # 미리 계획해둔 하락 매수 주문(flow)들의 상태를 하나씩 점검합니다.
            for _, row in flow_logs.iterrows():
                buy_type = row["buy_type"]
                target_price = row["target_price"]
                raw_filled = row["filled"]
                filled = "" if pd.isna(raw_filled) else str(raw_filled).strip()
                row_index = row.name

                if pd.isna(target_price) or pd.isna(row["buy_amount"]) or pd.isna(row["buy_units"]):
                    raise ValueError(f"[❌ 에러] {market} - {buy_type} 주문에 누락된 값이 있습니다. 행: {row.to_dict()}")

                target_price = float(target_price)
                unit_pct = small_pct if buy_type == "small_flow" else large_pct

                # Case 1: (미체결 상태) 가격이 올라서 매수 기회를 놓칠 것 같을 때
                if filled == "wait":
                    # "이러다 물 주기 전에 나무가 다 크겠어. 물뿌리개 위치를 살짝 위로 옮기자!"
                    # 현재 가격에 맞춰 예약 매수 가격을 약간 상향 조정하여, 체결 가능성을 높입니다.
                    threshold = target_price * (unit_pct / 2)
                    if current_price - target_price > threshold:
                        new_price = round((target_price + threshold) * (1 - unit_pct))
                        print(f"↗ {market} {buy_type} 가격 재조정: {target_price} → {new_price}")
                        buy_log_df.loc[row_index, "target_price"] = new_price
                        buy_log_df.loc[row_index, "filled"] = "update"

                # Case 2: (체결 완료) 추가 매수에 성공했을 때
                elif filled == "done":
                    # "좋았어, 땅이 촉촉해졌군! 그럼 이제 더 깊은 곳에 새 물뿌리개를 또 설치하자!"
                    # 현재 체결된 가격을 기준으로, 동일한 하락 비율을 적용하여 더 낮은 가격에 새로운 추가 매수 주문을 생성합니다.
                    # 이것이 바로 "하락을 따라가며 계속 매수"하는 이 전략의 핵심입니다.
                    buy_log_df.at[row_index, "buy_uuid"] = None

                    new_price = round(target_price * (1 - unit_pct))
                    print(f"🔁 {market} {buy_type} 연속 주문: {target_price} → {new_price}")
                    buy_log_df.loc[row_index, "target_price"] = new_price
                    buy_log_df.loc[row_index, "filled"] = "update"

                # Case 3: (신규 또는 수동 입력) 로그는 있지만 아직 거래소에 전송되지 않았을 때
                elif pd.isna(filled) or filled == "":
                    # "흠, 이건 내가 직접 설치한 물뿌리개로군. 고장 나진 않았는지 점검만 해봐야겠다!"
                    # 주문에 필요한 모든 정보가 올바르게 있는지 확인하고, "update" 상태로 만들어 거래소로 전송될 수 있게 합니다.
                    print(f"📝 {market} {buy_type} 수동 주문 → 필드 유효성 검사")
                    required_columns = ["market", "target_price", "buy_amount", "buy_units", "buy_type"]
                    missing_columns = [col for col in required_columns if pd.isna(row[col]) or row[col] == ""]

                    if missing_columns:
                        raise ValueError(f"[❌ 에러] {market} - {buy_type} 수동 주문에 누락된 필드가 있습니다: {missing_columns}")

                    buy_log_df.loc[row_index, "filled"] = "update"

                # Case 4: 예기치 않은 상태일 경우 오류를 발생시켜 문제를 파악합니다.
                else:
                    raise ValueError(f"[❌ 에러] {market} - {buy_type} 주문의 filled 상태가 예외적입니다: '{filled}'")

    # 새로운 주문이 있다면 기존 로그와 결합하여 최종 주문 목록을 만듭니다.
    if new_logs:
        new_rows = buy_log_df.to_dict('records') + new_logs
        buy_log_df = pd.DataFrame(new_rows)

    return buy_log_df

def generate_sell_orders(setting_df: pd.DataFrame, holdings: dict, sell_log_df: pd.DataFrame) -> pd.DataFrame:
    """
    # --- [전략의 핵심 ②: 매도 전략] ---
    # "기계적 이익 실현" 전략에 따라 매도 주문을 생성하거나, 기존 주문을 조정합니다.
    # 보유한 코인의 평균 매입 단가를 기준으로, 정해진 수익률에 도달하면 즉시 매도합니다.
    """
    print("[casino_strategy.py] generate_sell_orders() 호출됨")

    updated_df = sell_log_df.copy()

    for _, row in setting_df.iterrows():
        market = row["market"]

        # 보유 중인 코인이 아니면 매도 전략을 실행하지 않습니다.
        if market not in holdings:
            continue

        # --- [매도 가격 계산] --- #
        # 보유 코인의 평균 매입 단가(평단)와 수량을 가져옵니다.
        h = holdings[market]
        avg_buy_price = round(h["avg_price"], 8)
        quantity = round(h["balance"], 8)
        
        # 설정된 목표 수익률(예: 0.5%)을 바탕으로 목표 매도 가격을 계산합니다.
        take_profit_pct = row["take_profit_pct"]
        target_price = round(avg_buy_price * (1 + take_profit_pct), 2)

        # --- [매도 주문 생성/수정] --- #
        # 이미 매도 주문이 나가있는지 확인합니다.
        existing_idx = updated_df[updated_df["market"] == market].index

        if not existing_idx.empty:
            idx = existing_idx[0]
            existing = updated_df.loc[idx]

            # 기존 매도 주문이 있고, 보유 현황에 변경이 없다면 아무것도 하지 않습니다.
            is_same = (
                round(existing["avg_buy_price"], 8) == avg_buy_price and
                round(existing["quantity"], 8) == quantity and
                round(existing["target_sell_price"], 2) == target_price
            )

            if is_same:
                print(f"✅ {market} → 보유 정보와 동일 → 유지")
                continue

            # 만약 추가 매수로 평단이나 수량이 바뀌었다면, 새로운 목표가로 매도 주문을 수정합니다.
            print(f"✏️ {market} → 기존과 차이 있음 → 수정")
            updated_df.loc[idx, "avg_buy_price"] = avg_buy_price
            updated_df.loc[idx, "quantity"] = quantity
            updated_df.loc[idx, "target_sell_price"] = target_price
            updated_df.loc[idx, "filled"] = "update"

        # 기존 매도 주문이 없다면, 새로 계산된 목표가로 신규 매도 주문을 생성합니다.
        else:
            print(f"🆕 {market} → 새로운 sell_log 생성")
            new_row = {
                "market": market,
                "avg_buy_price": avg_buy_price,
                "quantity": quantity,
                "target_sell_price": target_price,
                "sell_uuid": None,
                "filled": "update"
            }
            new_rows = updated_df.to_dict('records')
            new_rows.append(new_row)
            updated_df = pd.DataFrame(new_rows)

    return updated_df
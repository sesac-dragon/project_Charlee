# utils/price_utils.py

from decimal import Decimal, ROUND_HALF_UP

def get_tick_size(price: float, market: str = "KRW", ticker: str = "") -> float:
    """
    입력된 가격에 따라 업비트의 호가 단위를 반환합니다.
    """
    special_tickers_100_1000 = {
        'ADA', 'ALGO', 'BLUR', 'CELO', 'ELF', 'EOS', 'GRS', 'GRT', 'ICX',
        'MANA', 'MINA', 'POL', 'SAND', 'SEI', 'STG', 'TRX'
    }

    base_ticker = ticker.replace("KRW-", "")

    if market != "KRW":
        raise ValueError("현재는 KRW 마켓만 지원됩니다.")

    if price >= 2_000_000:
        return 1000
    elif price >= 1_000_000:
        return 500
    elif price >= 500_000:
        return 100
    elif price >= 100_000:
        return 50
    elif price >= 10_000:
        return 10
    elif price >= 1_000:
        return 0.5 if base_ticker in special_tickers_100_1000 else 1
    elif price >= 100:
        return 0.1 if base_ticker in special_tickers_100_1000 else 1
    elif price >= 10:
        return 0.01
    elif price >= 1:
        return 0.001
    elif price >= 0.1:
        return 0.0001
    elif price >= 0.01:
        return 0.00001
    elif price >= 0.001:
        return 0.000001
    elif price >= 0.0001:
        return 0.0000001
    else:
        return 0.00000001


def adjust_price_to_tick(price: float, market: str = "KRW", ticker: str = "") -> float:
    """
    호가 단위를 기반으로 가격을 반올림하여 보정합니다.
    """
    tick_size = Decimal(str(get_tick_size(price, market, ticker)))
    decimal_price = Decimal(str(price))
    adjusted = (decimal_price / tick_size).quantize(Decimal('1'), rounding=ROUND_HALF_UP) * tick_size
    return float(adjusted)

import requests
from fake_useragent import UserAgent

ua = UserAgent()

headers = {
        "User-Agent": ua.random,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive"
}


def get_btc_price_usd():
    url = "https://api-mainnet.magiceden.io/v2/cryptoTicker/price"
    response = requests.get(url, headers=headers)
    data = response.json()
    print(data)
    
    # Extract BTC price from the results
    for result in data['results']:
        if result['symbol'] == "BTCUSDT":
            return float(result['price'])
    return None  # In case BTCUSDT is not found

get_btc_price_usd()
import requests

# Adding headers to mimic a browser request
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:104.0) Gecko/20100101 Firefox/104.0",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.5",
    "Connection": "keep-alive"
}

# Making the GET request with headers
response = requests.get("https://api-mainnet.magiceden.io/v2/ord/btc/tokens?offset=100&limit=100&collectionSymbol[]=bitcoin-puppets&sortBy=priceAsc&disablePendingTransactions=false&showAll=true", headers=headers)

# Printing the response content
print(response.json())

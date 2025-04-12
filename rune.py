import requests

url = "https://api-mainnet.magiceden.dev/v2/ord/btc/activities?limit=40&offset=20&ownerAddress=bc1p7w6hl96guwz7l407papwva82xwd9c2tps5afvpj0m8evtqzwl49skmqkzz&kind=buying_broadcasted"

headers = {"accept": "application/json", "Authorization" : "Bearer 4a02b503-2fdc-4cd3-a053-9d06e81f1c8e"}

response = requests.get(url, headers=headers)

print(response.text)
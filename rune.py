import requests

url = "https://api-mainnet.magiceden.dev/v2/ord/btc/runes/wallet/activities/bc1p5a8vd6c50hcx9qfpwhzzqqm7lhzae4krddqjutz6zftu2jf0p0sqne3tyd?offset=600"

headers = {"accept": "application/json", "Authorization" : "Bearer 4a02b503-2fdc-4cd3-a053-9d06e81f1c8e"}

response = requests.get(url, headers=headers)

print(response.text)
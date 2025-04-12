import requests
import json as js
from fake_useragent import UserAgent

ua = UserAgent()

url = "https://api-mainnet.magiceden.dev/v2/ord/btc/activities?limit=40&ownerAddress=bc1p7w6hl96guwz7l407papwva82xwd9c2tps5afvpj0m8evtqzwl49skmqkzz&kind[]=buying_broadcasted&kind[]=buying_broadcast_dropped&kind[]=mint_broadcasted&kind[]=list&kind[]=delist&kind[]=create&kind[]=transfer&kind[]=utxo_invalidated&kind[]=utxo_split_broadcasted&kind[]=utxo_extract_broadcasted&kind[]=offer_placed&kind[]=offer_cancelled&kind[]=offer_accepted_broadcasted&kind[]=coll_offer_fulfill_broadcasted&kind[]=coll_offer_created&kind[]=coll_offer_edited&kind[]=coll_offer_cancelled"

headers = {
    "User-Agent": ua.random,
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.5",
    "Connection": "keep-alive",
    "Authorization": "Bearer 4a02b503-2fdc-4cd3-a053-9d06e81f1c8e",
    "Content-Type": "application/json",
}

response = requests.get(url, headers=headers)

# Check if request was successful
if response.status_code == 200:
    data = response.json()
    # Write to a file
    with open("magiceden_output.json", "w", encoding="utf-8") as f:
        js.dump(data, f, indent=4)
    print("Data written to magiceden_output.json")
else:
    print(f"Request failed with status code {response.status_code}")

import requests
import time
from fake_useragent import UserAgent

# Initialize the UserAgent object
ua = UserAgent()

# URL
url = "https://api-mainnet.magiceden.io/v2/ord/btc/tokens?offset=100&limit=100&collectionSymbol[]=bitcoin-puppets&sortBy=priceAsc&disablePendingTransactions=false&showAll=true"

# Function to handle the GET request with a fake user-agent
def send_request(url, retries=3):
    for attempt in range(retries):
        try:
            headers = {
                "User-Agent": ua.random,  # Generate a random user-agent
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "en-US,en;q=0.5",
                "Connection": "keep-alive"
            }
            response = requests.get(url, headers=headers)
            response.raise_for_status()  # Raises HTTPError if the response code is not 200
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Request failed on attempt {attempt + 1}: {e}")
            if attempt + 1 < retries:
                time.sleep(2)  # Wait before retrying
            else:
                return None

# Sending 100 requests with random user-agents
successful_requests = 0
for i in range(100):
    print(f"Sending request {i + 1} with user-agent: {ua.random}")
    data = send_request(url)
    if data:
        successful_requests += 1

print(f"Successfully completed {successful_requests} out of 100 requests.")

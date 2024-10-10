from io import BytesIO
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
import numpy as np
from datetime import datetime
import requests
from fake_useragent import UserAgent

ua = UserAgent()

headers = {
        "User-Agent": ua.random,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive"
}

def plot_price_chart(prices, timestamps):
    fig, ax = plt.subplots(figsize=(10, 5))

    # Plot the price data
    ax.plot(timestamps, prices, color='green', zorder=1)

    # Setting the title and labels with white color
    ax.set_title('', color='white', fontsize=14)
    ax.set_xlabel('Time', color='white', fontsize=12)
    ax.set_ylabel('Price', color='white', fontsize=12)  # Indicating prices in SATS

    # Dark background for the plot
    fig.patch.set_facecolor('black')  # Set figure background to dark
    ax.set_facecolor('black')  # Set axes background to dark

    # Set tick label color and size
    ax.tick_params(axis='x', colors='white', labelsize=10, rotation=45)  # Rotate x-axis labels for better visibility
    ax.tick_params(axis='y', colors='white', labelsize=10)

    # Add horizontal grid lines
    ax.grid(axis='y', color='gray', linestyle='--', linewidth=0.7)

    # Add a maximum number of ticks on the x-axis to avoid clustering
    ax.xaxis.set_major_locator(MaxNLocator(nbins=8))  # Adjust the number of ticks as needed

    # Adding the "Brain Box" text as a background with reduced opacity
    ax.text(0.5, 0.5, '@brainboxintel', transform=ax.transAxes,
            fontsize=60, color='gray', alpha=0.2,
            ha='center', va='center', rotation=30, zorder=0)

    # Save the figure to a buffer
    buf = BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', facecolor=fig.get_facecolor())  # Save with dark background
    buf.seek(0)
    plt.close()

    return buf


def plot_ordinals_price_chart(data):
    # Extract timestamps and maxFP values
    timestamps = [datetime.utcfromtimestamp(item["ts"] / 1000) for item in data]  # Convert to human-readable datetime
    maxFP = [int(item["maxFP"]) / 1_000_000 for item in data]

    plt.figure(figsize=(10, 5))
    
    # Using step plot for ordinals maxFP
    plt.step(timestamps, maxFP, color='magenta', where='post')  # Step plot for a trading chart look

    # Setting the title and labels with white color
    plt.title('', color='white', fontsize=14)
    plt.xlabel('Time', color='white', fontsize=12)
    plt.ylabel('Price (BTC)', color='white', fontsize=12)

    # Dark background for the plot
    plt.gcf().set_facecolor('black')
    plt.gca().set_facecolor('black')

    # Set tick label color and size
    plt.xticks(color='white', fontsize=10, rotation=45)
    plt.yticks(color='white', fontsize=10)

    # Add horizontal grid lines
    plt.grid(axis='y', color='gray', linestyle='--', linewidth=0.7)

    # Add a maximum number of ticks on the x-axis to avoid clustering
    ax = plt.gca()
    ax.xaxis.set_major_locator(MaxNLocator(nbins=8))

    # Adding the "@brainboxintel" watermark text in the background
    ax.text(0.5, 0.5, '@brainboxintel', transform=ax.transAxes,
            fontsize=60, color='gray', alpha=0.2,
            ha='center', va='center', rotation=30, zorder=0)

    # Save the figure to a buffer
    buf = BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', facecolor='black')
    buf.seek(0)
    plt.close()
    
    return buf


def get_btc_price_usd():
    headers = {
        "User-Agent": ua.random,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive"
    }
    url = "https://api-mainnet.magiceden.io/v2/cryptoTicker/price"
    response = requests.get(url, headers=headers)
    data = response.json()
    
    # Extract BTC price from the results
    for result in data['results']:
        if result['symbol'] == "BTCUSDT":
            return float(result['price'])
    return None  # In case BTCUSDT is not found

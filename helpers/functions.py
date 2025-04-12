from io import BytesIO
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
from datetime import datetime
import requests
from fake_useragent import UserAgent
import httpx

ua = UserAgent()

headers = {
    "User-Agent": ua.random,
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.5",
    "Connection": "keep-alive",
}


def plot_price_chart(price_data, floor_price_sats):
    fig, ax = plt.subplots(figsize=(10, 5))

    prices = [(entry["maxFP"] * 100_000) for entry in price_data]
    timestamps = [datetime.fromtimestamp(entry["ts"] / 1000) for entry in price_data]

    current_price_sats = floor_price_sats

    ax.plot(timestamps, prices, color="green", zorder=1, label="Max Floor Price")

    ax.axhline(
        y=current_price_sats,
        color="red",
        linestyle="--",
        label=f"Current Price: {current_price_sats} SATS",
    )

    ax.text(
        timestamps[-1],
        current_price_sats,
        f"{current_price_sats:.0f} SATS",
        fontsize=12,
        color="white",
        bbox=dict(facecolor="red", alpha=0.5),
    )

    ax.set_title("", color="white", fontsize=14)
    ax.set_xlabel("Time", color="white", fontsize=12)
    ax.set_ylabel("Price (SATS)", color="white", fontsize=12)

    fig.patch.set_facecolor("black")
    ax.set_facecolor("black")

    ax.tick_params(axis="x", colors="white", labelsize=10, rotation=45)
    ax.tick_params(axis="y", colors="white", labelsize=10)

    ax.grid(axis="y", color="gray", linestyle="--", linewidth=0.7)

    ax.xaxis.set_major_locator(MaxNLocator(nbins=8))

    ax.text(
        0.5,
        0.5,
        "@virgintool",
        transform=ax.transAxes,
        fontsize=60,
        color="gray",
        alpha=0.2,
        ha="center",
        va="center",
        rotation=30,
        zorder=0,
    )

    buf = BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight", facecolor=fig.get_facecolor())
    buf.seek(0)
    plt.close()

    return buf


def plot_ordinals_price_chart(data, current_price_btc):
    timestamps = [
        datetime.utcfromtimestamp(item["ts"] / 1000) for item in data[1:]
    ]
    maxFP = [
        int(item["maxFP"]) / 100_000_000 for item in data[1:]
    ]

    plt.figure(figsize=(10, 5))

    plt.step(
        timestamps, maxFP, color="magenta", where="post"
    )

    plt.axhline(
        y=current_price_btc,
        color="yellow",
        linestyle="--",
        alpha=0.6,
        label=f"Current Price: {current_price_btc:.8f} BTC",
    )

    plt.title("", color="white", fontsize=14)
    plt.xlabel("Time", color="white", fontsize=12)
    plt.ylabel("Price (BTC)", color="white", fontsize=12)

    plt.gcf().set_facecolor("black")
    plt.gca().set_facecolor("black")

    plt.xticks(color="white", fontsize=10, rotation=45)
    plt.yticks(color="white", fontsize=10)

    plt.grid(axis="y", color="gray", linestyle="--", linewidth=0.7)

    ax = plt.gca()
    ax.xaxis.set_major_locator(MaxNLocator(nbins=8))
    ax.yaxis.set_major_locator(
        MaxNLocator(nbins=15)
    )

    ax.text(
        0.5,
        0.5,
        "@virgintool",
        transform=ax.transAxes,
        fontsize=60,
        color="gray",
        alpha=0.2,
        ha="center",
        va="center",
        rotation=30,
        zorder=0,
    )

    legend = plt.legend(loc="upper left", framealpha=0.5)

    buf = BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight", facecolor="black")
    buf.seek(0)
    plt.close()

    return buf


def get_btc_price_usd():
    headers = {
        "User-Agent": ua.random,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive",
        "Authorization": "Bearer 4a02b503-2fdc-4cd3-a053-9d06e81f1c8e",
    }
    url = "https://api-mainnet.magiceden.dev/v2/cryptoTicker/price"
    response = requests.get(url, headers=headers)

    try:
        data = response.json()
    except requests.exceptions.JSONDecodeError as e:
        print("Error decoding JSON:", e)
        return None

    if "results" in data:
        for result in data["results"]:
            if result["symbol"] == "BTCUSDT":
                print(result["price"])
                return float(result["price"])

    return None


def safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default

def safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default

async def fetch_data(url, headers):
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        return response

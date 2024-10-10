import os
import requests
import discord
from datetime import datetime
from discord import Option
from discord.ext import commands
# from discord.ui import Button, View
from fake_useragent import UserAgent
from helpers.constants import rune_endpoints, ord_endpoints
from helpers.functions import plot_price_chart, plot_ordinals_price_chart, get_btc_price_usd
from dotenv import load_dotenv

load_dotenv()
DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')

ua = UserAgent()
intents = discord.Intents.default()
intents.messages = True
bot = discord.Bot(intents=intents)


@bot.command(name="help", description="Get help with using the bot")
async def help_command(ctx):
    embed = discord.Embed(
        title="Help - Brain Box Bot",
        description="Here are the commands available on the bot.",
        color=discord.Color.purple()
    )
    
    # Adding details about each command
    embed.add_field(name="/help", value="Returns list of available commands", inline=False)
    embed.add_field(
        name="/floor", 
        value="Retrieve the floor price for either 'runes' or 'ordinals' with a specific slug.\n"
              "Usage: `/floor asset_type=<runes|ordinals> slug=<asset_slug>`", 
        inline=False
    )
    embed.add_field(
        name="Created By", 
        value="[Tobi TheRevolutionary](https://tobitherevolutionary.pythonanywhere.com)", 
        inline=False
    )
    embed.set_footer(text="Need more help? Contact the creator via the portfolio link!")

    await ctx.send(embed=embed)

@bot.command(name="floor", description="Retrieve floor price for either Runes or Ordinals with a specific slug")
async def floor(ctx: discord.ApplicationContext, 
                asset_type: Option(str, "Select asset type", choices=["runes", "ordinals"]),  # type: ignore
                slug: Option(str, "The slug of the asset"),  # type: ignore
                timeframe: Option(str, "Select timeframe", choices=["1 Day", "1 Week", "1 Month", "All Time"])):  # Add timeframe option # type: ignore

    if asset_type == "runes":
        rune_name = slug

        # Normalize the rune name
        if '•' in rune_name:
            rune_name = rune_name.replace('•', '').upper()
        if '.' in rune_name:
            rune_name = rune_name.replace('.', '').upper()

        headers = {
            "User-Agent": ua.random,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive"
        }

        response = requests.get(rune_endpoints['info'](rune_name), headers=headers)  # Replace with the actual endpoint
        if response.status_code != 200:
            embed = discord.Embed(
                title="Uh oh!",
                description="Looks like something went wrong, how about trying that again?",
                color=discord.Color.red()
            )
            await ctx.respond(embed=embed)
            return

        # Parse the JSON response
        data = response.json()

        # Normalize the data
        floor_price_sats = float(data['floorUnitPrice']['formatted'])
        best_offer_sats = float(data['bestOfferPrice']['formatted'])
        market_cap_btc = f"{data.get('marketCap', 0)}"  # Format market cap in USD
        btc_price_usd = get_btc_price_usd()
        market_cap_usd = f"{float(market_cap_btc) * btc_price_usd:.2f}"
        total_supply = f"{int(data.get('totalSupply', 0)):,.0f}"  # Format total supply as a regular number
        volume_1d = f"${data['volume'].get('1d', 0):,.0f}"  # Format 1d volume in USD
        volume_7d = f"${data['volume'].get('7d', 0):,.0f}"  # Format 7d volume in USD
        volume_30d = f"${data['volume'].get('30d', 0):,.0f}"  # Format 30d volume in USD
        volume_all = f"${data['volume'].get('all', 0):,.0f}"  # Format all-time volume in USD

        # Normalize transaction counts with commas for readability
        txn_count_1d = f"{data['txnCount'].get('1d', 0):,}"  # Format 1-day transaction count
        txn_count_7d = f"{data['txnCount'].get('7d', 0):,}"  # Format 7-day transaction count
        txn_count_30d = f"{data['txnCount'].get('30d', 0):,}"  # Format 30-day transaction count

        # Create the embed with rune information
        embed = discord.Embed(
            title=f"Rune Information: {data['name']}",
            color=discord.Color.purple()
        )
        embed.add_field(name="Rune Symbol", value=data.get("symbol", "N/A"), inline=True)
        embed.add_field(name="Ticker", value=data.get("ticker", "N/A"), inline=True)
        embed.add_field(name="Total Supply", value=total_supply, inline=True)
        embed.add_field(name="Floor Price (SATS)", value=f"{floor_price_sats} SATS", inline=True)
        embed.add_field(name="Best Offer Price (SATS)", value=f"{best_offer_sats} SATS", inline=True)
        embed.add_field(name="Market Cap ($)", value=market_cap_usd, inline=True)
        embed.add_field(name="Holder Count", value=data.get("holderCount", "N/A"), inline=True)
        embed.add_field(name="Pending Transactions", value=data.get("pendingTxnCount", "N/A"), inline=True)
        embed.add_field(name="Transaction Count (1d)", value=txn_count_1d, inline=True)
        embed.add_field(name="Transaction Count (7d)", value=txn_count_7d, inline=True)
        embed.add_field(name="Transaction Count (30d)", value=txn_count_30d, inline=True)
        embed.add_field(name="Volume (1d)", value=volume_1d, inline=True)
        embed.add_field(name="Volume (7d)", value=volume_7d, inline=True)
        embed.add_field(name="Volume (30d)", value=volume_30d, inline=True)
        embed.add_field(name="Volume (All)", value=volume_all, inline=True)

        # If there's an image URI, add it to the embed
        if data.get("imageURI"):
            embed.set_thumbnail(url=data["imageURI"])

        embed.set_footer(text="Elevate Others to Elevate Yourself - Zayn")

        # Fetch the chart based on the selected timeframe
        chart_endpoint = None
        if timeframe == "1 Day":
            chart_endpoint = rune_endpoints['1d_chart'](rune_name)
        elif timeframe == "1 Week":
            chart_endpoint = rune_endpoints['1w_chart'](rune_name)
        elif timeframe == "1 Month":
            chart_endpoint = rune_endpoints['1m_chart'](rune_name)
        elif timeframe == "All Time":
            chart_endpoint = rune_endpoints['all_time'](rune_name)
        

        price_response = requests.get(chart_endpoint)  # Replace with the actual price endpoint
        if price_response.status_code == 200:
            price_data = price_response.json()

            # Extract maxFP values and corresponding timestamps
            prices = [entry["maxFP"] for entry in price_data]  # Convert to SATS
            timestamps = [datetime.fromtimestamp(entry["ts"] / 1000).strftime('%H:%M') for entry in price_data]

            # Generate the plot
            price_chart = plot_price_chart(prices, timestamps)

            # Send the chart image in an embed
            file = discord.File(price_chart, filename="price_chart.png")
            embed.add_field(name="Price Chart", value=f"Here is the {timeframe} price chart for this rune:", inline=False)
            embed.set_image(url="attachment://price_chart.png")
            await ctx.send(file=file, embed=embed)

        else:
            await ctx.respond("Failed to retrieve price data. Please try again later.")

    elif asset_type == "ordinals":
        ord_name = slug

        headers = {
            "User-Agent": ua.random,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive"
        }

        info_response = requests.get(ord_endpoints['info'](ord_name), headers=headers)
        if info_response.status_code != 200:
            embed = discord.Embed(
                title="Uh oh!",
                description="Looks like something went wrong, how about trying that again?",
                color=discord.Color.red()
            )
            await ctx.respond(embed=embed)
            print(info_response.text)
            return

        # Parse the JSON response
        info_data = info_response.json()
        print(info_data)

        holders = info_data['owners']
        total_volume_btc = f"{float(info_data['totalVolume']):.4f} BTC"
        total_listed = int(info_data['totalListed'])
        pending_transactions = info_data['pendingTransactions']
        floor_price_sats = int(info_data['floorPrice'])
        floor_price_btc = floor_price_sats / 100_000_000
        formatted_price = f"{floor_price_btc:.4f}"

        # Fetch additional data
        misc_response = requests.get(ord_endpoints['misc'](ord_name), headers=headers)
        if misc_response.status_code != 200:
            embed = discord.Embed(
                title="Uh oh!",
                description="Something went wrong fetching additional data.",
                color=discord.Color.red()
            )
            await ctx.respond(embed=embed)
            return

        misc_data = misc_response.json()
        print(misc_data)

        name = misc_data['name']
        image = misc_data['imageURI']

        # Create the embed with ordinal information
        embed = discord.Embed(
            title=f"Ordinal Information: {name}",
            color=discord.Color.purple()
        )

        # Fetch the chart based on the selected timeframe
        chart_endpoint = None
        if timeframe == "1 Day":
            chart_endpoint = ord_endpoints['1d_chart'](ord_name)
        elif timeframe == "1 Week":
            chart_endpoint = ord_endpoints['1w_chart'](ord_name)
        elif timeframe == "1 Month":
            chart_endpoint = ord_endpoints['1m_chart'](ord_name)
        elif timeframe == "All Time":
            chart_endpoint = ord_endpoints['all_time'](ord_name)

        price_response = requests.get(chart_endpoint, headers=headers)
        if price_response.status_code != 200:
            await ctx.respond("Failed to retrieve price data. Please try again later.")
            return

        price_data = price_response.json()
        prices = [entry['maxFP'] for entry in price_data]  # Convert to SATS

        # Generate the plot
        price_chart = plot_ordinals_price_chart(price_data)

        # Add fields to embed with ordinal information
        embed.add_field(name="Floor Price", value=formatted_price, inline=True)
        embed.add_field(name="Volume", value=total_volume_btc, inline=True)
        embed.add_field(name="Holders", value=holders, inline=True)
        embed.add_field(name="Listed", value=total_listed, inline=True)
        embed.add_field(name="Pending Transactions", value=pending_transactions, inline=True)
        embed.set_thumbnail(url=image)

        # Send the chart image in an embed
        file = discord.File(price_chart, filename="price_chart.png")
        embed.add_field(name="Price Chart", value=f"Here is the {timeframe} price chart for this ordinal:", inline=False)
        embed.set_image(url="attachment://price_chart.png")
        await ctx.send(file=file, embed=embed)

        embed.set_footer(text="Elevate Others to Elevate Yourself - Zayn")


bot.run(DISCORD_BOT_TOKEN)
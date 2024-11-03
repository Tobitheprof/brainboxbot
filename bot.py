import os
import requests
import logging
import aiohttp
import discord
from discord import Option
from discord.ext import commands
from discord.ext import commands, tasks
from tweeterpy import TweeterPy
from collections import defaultdict
from bs4 import BeautifulSoup
from discord.ui import Button, View, Modal, InputText
from discord import Interaction
from typing import List, Dict
from fake_useragent import UserAgent
from helpers.constants import (
    rune_endpoints,
    ord_endpoints,
    rune_mint_tracker_endpoints,
)
from helpers.functions import (
    plot_price_chart,
    plot_ordinals_price_chart,
    get_btc_price_usd,
)
from dotenv import load_dotenv
import json
import os

load_dotenv()
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
WALLET_DATA_FILE = "wallet_tracking_data.json"
USER_WALLET_FILE = "user_wallet_data_file.json"

ua = UserAgent()
intents = discord.Intents.default()
intents.messages = True
bot = discord.Bot(intents=intents)
data = {}

DEV_MODE = True


"""
IN-CODE SUPORTERS
"""
class DeleteButton(discord.ui.Button):
    def __init__(self, author_id):
        super().__init__(style=discord.ButtonStyle.secondary, emoji="❌")
        self.author_id = author_id

    async def callback(self, interaction: discord.Interaction):
        # Only the author can delete the message
        if interaction.user.id == self.author_id:
            await interaction.message.delete()
        else:
            await interaction.response.send_message(
                "You don't have permission to delete this message.", ephemeral=True
            )

class DeleteView(discord.ui.View):
    def __init__(self, author_id):
        super().__init__()
        # Add the DeleteButton to the view
        self.add_item(DeleteButton(author_id))

# Admin check decorator
def is_admin(ctx: discord.ApplicationContext):
    return ctx.author.guild_permissions.administrator


# Load wallet data from file, if it exists
def load_wallet_data():
    global tracked_wallets, transaction_history, output_channels
    try:
        with open(WALLET_DATA_FILE, "r") as f:
            data = json.load(f)
            tracked_wallets = data.get("tracked_wallets", {})
            transaction_history = data.get("transaction_history", {})
            output_channels = data.get("output_channels", {})  # Load channel-specific data
    except FileNotFoundError:
        tracked_wallets = {}
        transaction_history = {}
        output_channels = {}

# Save wallet data to file
def save_wallet_data():
    global tracked_wallets, transaction_history, output_channels
    
    # Ensure there are no duplicate transaction IDs in `transaction_history`
    for guild_channel, wallet_data in transaction_history.items():
        for channel_id, wallets in wallet_data.items():
            for wallet_address, transactions in wallets.items():
                # Remove duplicates by converting the list to a set, then back to a list
                unique_transactions = list(set(transactions))
                transaction_history[guild_channel][channel_id][wallet_address] = unique_transactions

    # Save data to file
    data = {
        "tracked_wallets": tracked_wallets,
        "transaction_history": transaction_history,
        "output_channels": output_channels,  # Save channel-specific data
    }
    
    with open(WALLET_DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("bot.log"),  # Log to a file
        logging.StreamHandler(),  # Print to console
    ],
)

@bot.event
async def on_ready():
    logging.info(f"Bot logged in as {bot.user}")

    try:
        load_wallet_data()
        logging.info("Tracking Wallet Data Loaded Successfully")
    except Exception as e:
        logging.error(f"Error loading wallet data: {e}")

    try:
        load_runes_data()
    except Exception as e:
        logging.error(f"Error loading runes data: {e}")

    try:
        check_wallet_transactions.start()
        logging.info("Wallet Tracking Task Started Successfully")
    except Exception as e:
        logging.error(f"Error starting wallet tracking task: {e}")

    # try:
    #     runes_mint_tracker.start()
    #     logging.info("Rune Mint Tracker Task Started Successfully")
    # except Exception as e:
    #     logging.error(f"Error starting rune mint tracker task: {e}")

    logging.info("Bot is fully operational.")
"""
END 
"""



"""
MISC Commands - START;
These are commands that are not tied to collective functions like the others for PnL and Such;
"""

@bot.command(name="help", description="Get help with using the bot")
async def help_command(ctx):
    await ctx.defer(ephemeral=True)  # Defer response to indicate processing

    embed = discord.Embed(
        title="Help - Virgin",
        description="Here are the commands available on the bot.",
        color=discord.Color(int("008000", 16)),
    )

    # Adding details about each command
    embed.add_field(
        name="/help", value="Returns a list of available commands", inline=False
    )
    embed.add_field(
        name="/floor",
        value="Retrieve the floor price for either 'runes' or 'ordinals' with a specific slug.\n"
        "Usage: `/floor asset_type=<runes|ordinals> slug=<asset_slug> timeframe=<timeframe>`",
        inline=False,
    )
    embed.add_field(
        name="/setchannel",
        value="Set the channel for wallet tracking updates (Admin only).\nUsage: `/setchannel channel=<channel>`",
        inline=False,
    )
    embed.add_field(
        name="/addwallet",
        value="Add a wallet to track (Admin only).\n"
        "Usage: `/addwallet name=<wallet_name> wallet_address=<wallet_address> track_mint=<true|false> track_buy=<true|false|both> track_sell=<true|false|both>`",
        inline=False,
    )
    embed.add_field(
        name="/satsvb", value="Get the network fees on Bitcoin. \n Usage: `/satsvb`"
    )
    embed.add_field(
        name="/xhistory",
        value="Get past usernames on an X account. \n Usage: `/xhistory username=<username>`",
    )
    embed.add_field(
        name="/deletewallet",
        value="Delete a tracked wallet (Admin only).\nUsage: `/deletewallet wallet_name=<wallet_name>`",
        inline=False,
    )
    embed.add_field(
        name="/listwallets", value="List all tracked wallets (Admin only)", inline=False
    )
    embed.add_field(
        name="/runesmint", value="Set a channel where rune mint notifications would be sent in a server (Admin only)", inline=False
    )
    embed.set_author(name="Virgin", icon_url=bot.user.avatar.url)
    embed.set_footer(
        text="Powered by Brain Box Intel",
        icon_url="https://www.brainboxintel.xyz/static/assets/img/brainboxintel.jpg",
    )

    await ctx.send(embed=embed, view=DeleteView(author_id=ctx.author.id), ephemeral=True)  # Make response visible only to the command caller

@bot.command(
    name="xhistory",
    description="Get previous usernames associated with the specified X (Twitter) account",
)
async def xhistory(ctx: discord.ApplicationContext, username: Option(str, "X (Twitter) Username")):  # type: ignore
    try:

        await ctx.defer()
        headers = {
            "User-Agent": ua.random,
        }
        twitter = TweeterPy()

        user_id = twitter.get_user_id(username)

        url = f"https://botsentinel.com/profile/{user_id}"
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")

            change_history_section = soup.find(
                "h3", string="Twitter Handle Change History"
            )
            if change_history_section:
                change_history_div = change_history_section.find_next(
                    "div", class_="card-body"
                )

                username_changes = change_history_div.find_all("div", class_="media")

                embed = discord.Embed(
                    title=f"Username History for @{username}",
                    color=discord.Color(int("008000", 16)),
                )

                history_text = ""
                for change in username_changes:
                    username_change = change.find("h6", class_="mediafont").get_text(
                        strip=True
                    )
                    change_date = change.find("span", class_="d-block").get_text(
                        strip=True
                    )
                    previous, current = username_change.split("→")

                    history_text += f"[{previous.strip()}](https://twitter.com/{previous.strip()}) → [{current.strip()}](https://twitter.com/{current.strip()})\nChanged on: {change_date}\n\n"

                if history_text:
                    embed.add_field(
                        name="Previous Username Changes",
                        value=history_text,
                        inline=False,
                    )

                embed.add_field(
                    name="Current Username",
                    value=f"[{username}](https://twitter.com/{username}) (current)",
                    inline=False,
                )

                await ctx.respond(embed=embed, view=DeleteView(author_id=ctx.author.id))
            else:
                await ctx.followup.send(
                    f"No Twitter handle change history found for @{username}."
                )
        else:
            await ctx.followup.send(
                f"Failed to retrieve profile details (status code: {response.status_code})."
            )
    except Exception as e:
        await ctx.followup.send(f"An error occurred: {str(e)}")


@bot.command(name="satsvb", description="Get network fees on bitcoin")
async def satsvb(ctx: discord.ApplicationContext):
    """Fetches and displays Bitcoin network fees in an embed."""

    await ctx.defer()

    try:
        headers = {"User-Agent": ua.random}

        url = "http://mempool.space/api/v1/fees/recommended"

        response = requests.get(url, headers=headers)
        response.raise_for_status()
        fees = response.json()

        embed = discord.Embed(
            title="Bitcoin Network Fees", color=discord.Color(int("008000", 16))
        )

        priority_mapping = {
            "High Priority": fees["fastestFee"],
            "Medium Priority": fees["halfHourFee"],
            "Low Priority": fees["hourFee"],
            "No Priority": fees["minimumFee"],
        }

        for priority, sat_per_vb in priority_mapping.items():
            embed.add_field(
                name=f"{priority}", value=f"{sat_per_vb} sat/vB", inline=True
            )

        embed.set_footer(
            text="Powered by Brain Box Intel",
            icon_url="https://www.brainboxintel.xyz/static/assets/img/brainboxintel.jpg",
        )

        await ctx.respond(embed=embed, view=DeleteView(author_id=ctx.author.id))

    except Exception as e:
        embed = discord.Embed(
            title="Uh oh!",
            description=f"Looks like something went wrong, how about trying that again?{e}",
            color=discord.Color.red(),
        )
        embed.set_footer(
            text="Powered by Brain Box Intel",
            icon_url="https://www.brainboxintel.xyz/static/assets/img/brainboxintel.jpg",
        )

        await ctx.respond(embed=embed, view=DeleteView(author_id=ctx.author.id))


@bot.command(
    name="floor",
    description="Retrieve floor price for either Runes or Ordinals with a specific slug",
)
async def floor(
    ctx: discord.ApplicationContext,
    asset_type: Option(str, "Select asset type", choices=["runes", "ordinals"]),  # type: ignore
    slug: Option(str, "The slug of the asset"),  # type: ignore
    timeframe: Option(
        str,
        "Select timeframe",
        choices=["1 Day", "1 Week", "1 Month", "All Time"],
        default="All Time",
    ),# type: ignore
):  # Add timeframe option 
    
    await ctx.defer()
    


    if asset_type == "runes":
        rune_name = slug

        # Normalize the rune name
        if "•" in rune_name:
            rune_name = rune_name.replace("•", "").upper()
        if "." in rune_name:
            rune_name = rune_name.replace(".", "").upper()

        headers = {
            "User-Agent": ua.random,
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive",
            "Authorization": "Bearer 4a02b503-2fdc-4cd3-a053-9d06e81f1c8e",
        }

        response = requests.get(
            rune_endpoints["info"](rune_name), headers=headers
        )  # Replace with the actual endpoint
        print(response.json())
        if response.status_code != 200:
            embed = discord.Embed(
                title="Uh oh!",
                description="Looks like something went wrong, how about trying that again?",
                color=discord.Color.red(),
            )
            await ctx.respond(embed=embed)
            return

        data = response.json()

        floor_price_sats = float((data["floorUnitPrice"]["formatted"]))
        market_cap_btc = f"{data.get('marketCap', 0)}"
        btc_price_usd = get_btc_price_usd()
        market_cap_usd = f"{float(market_cap_btc) * btc_price_usd:,.0f}"
        total_supply = f"{int(data.get('totalSupply', 0)):,.0f}"
        embed = discord.Embed(
            title=f"Rune Information: {data['name']}",
            color=discord.Color(int("008000", 16)),
        )
        embed.add_field(name="Price", value=f"{floor_price_sats:.3f} SATS", inline=True)
        embed.add_field(name="Market Cap ($)", value=market_cap_usd, inline=True)
        embed.add_field(name="Total Supply", value=total_supply, inline=True)
        embed.add_field(
            name="Holder Count", value=data.get("holderCount", "N/A"), inline=True
        )
        embed.add_field(
            name="Pending Transactions",
            value=data.get("pendingTxnCount", "N/A"),
            inline=True,
        )
        embed.add_field(
            name="Rune Symbol", value=data.get("symbol", "N/A"), inline=True
        )

        if data.get("imageURI"):
            embed.set_thumbnail(url=data["imageURI"])

        embed.set_footer(
            text="Powered by Brain Box Intel",
            icon_url="https://www.brainboxintel.xyz/static/assets/img/brainboxintel.jpg",
        )

        chart_endpoint = None
        if timeframe == "1 Day":
            chart_endpoint = rune_endpoints["1d_chart"](rune_name)
        elif timeframe == "1 Week":
            chart_endpoint = rune_endpoints["1w_chart"](rune_name)
        elif timeframe == "1 Month":
            chart_endpoint = rune_endpoints["1m_chart"](rune_name)
        elif timeframe == "All Time":
            chart_endpoint = rune_endpoints["all_time"](rune_name)

        price_response = requests.get(chart_endpoint)
        if price_response.status_code == 200:
            view = View()

            view.add_item(
            discord.ui.Button(
                label="",
                url=f"https://magiceden.io/runes/{data['name']}",
                emoji="<:magiceden:1301265248396902453>",
            )
            )
            # view.add_item(
            #     discord.ui.Button(
            #         label="Geniidata",
            #         url=f"https://geniidata.com/ordinals/runes/{data['name']}",
            #         emoji="<:geniidata:1301270589826273334>",
            #     )
            # )
            delete_button = DeleteButton(author_id=ctx.author.id)
            view.add_item(delete_button)

            price_data = price_response.json()

            prices = price_data

            price_sats_dec = f"{floor_price_sats:.3f}"

            price_chart = plot_price_chart(prices, price_sats_dec)

            file = discord.File(price_chart, filename="price_chart.png")
            embed.add_field(
                name="Price Chart",
                value=f"Here is the {timeframe} price chart for this rune:",
                inline=False,
            )
            embed.set_image(url="attachment://price_chart.png")
            embed.set_footer(
            text="Powered by Brain Box Intel",
            icon_url="https://www.brainboxintel.xyz/static/assets/img/brainboxintel.jpg",
            )
            await ctx.respond(file=file, embed=embed, view=view)

        else:
            await ctx.respond("Failed to retrieve price data. Please try again later.")

    elif asset_type == "ordinals":
        ord_name = slug

        headers = {
            "User-Agent": ua.random,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive",
            "Authorization": "Bearer 4a02b503-2fdc-4cd3-a053-9d06e81f1c8e",
        }

        info_response = requests.get(ord_endpoints["info"](ord_name), headers=headers)
        if info_response.status_code != 200:
            embed = discord.Embed(
                title="Uh oh!",
                description="Looks like something went wrong, how about trying that again?",
                color=discord.Color.red(),
            )
            await ctx.respond(embed=embed)
            print(info_response.text)
            return

        # Parse the JSON response
        info_data = info_response.json()

        holders = info_data["owners"]
        total_volume_btc = (
            f"{float(info_data['totalVolume']) / 100_000_000.000 :.4f} BTC"
        )
        total_listed = int(info_data["totalListed"])
        pending_transactions = info_data["pendingTransactions"]
        floor_price_sats = int(info_data["floorPrice"])
        floor_price_btc = floor_price_sats / 100_000_000
        formatted_price = f"{floor_price_btc:.4f}"

        # Fetch additional data
        misc_response = requests.get(ord_endpoints["misc"](ord_name), headers=headers)
        if misc_response.status_code != 200:
            embed = discord.Embed(
                title="Uh oh!",
                description="Something went wrong fetching additional data.",
                color=discord.Color.red(),
            )
            await ctx.respond(embed=embed)
            return

        misc_data = misc_response.json()
        print(misc_data)

        name = misc_data["name"]
        image = misc_data["imageURI"]

        # Create the embed with ordinal information
        embed = discord.Embed(
            title=f"Ordinal Information: {name}", color=discord.Color(int("008000", 16))
        )

        view = View()

        view.add_item(
        discord.ui.Button(
            label="",
            url=f"https://magiceden.io/ordinals/marketplace/{str(misc_data['symbol'])}",
            emoji="<:magiceden:1301265248396902453>",
        )
        )
        view.add_item(
            discord.ui.Button(
                label="",
                url=f"https://bestinslot.xyz/ordinals/collections/{str(misc_data['symbol'].lower())}",
                emoji="<:bestinslot:1301265540765192223>",
            )
        )
        # view.add_item(
        #     discord.ui.Button(
        #         label="Geniidata",
        #         url=f"https://geniidata.com/ordinals/runes/{data['name']}",
        #         emoji="<:geniidata:1301270589826273334>",
        #     )
        # )
        delete_button = DeleteButton(author_id=ctx.author.id)
        view.add_item(delete_button)


        # Fetch the chart based on the selected timeframe
        chart_endpoint = None
        if timeframe == "1 Day":
            chart_endpoint = ord_endpoints["1d_chart"](ord_name)
        elif timeframe == "1 Week":
            chart_endpoint = ord_endpoints["1w_chart"](ord_name)
        elif timeframe == "1 Month":
            chart_endpoint = ord_endpoints["1m_chart"](ord_name)
        elif timeframe == "All Time":
            chart_endpoint = ord_endpoints["all_time"](ord_name)

        price_response = requests.get(chart_endpoint, headers=headers)
        if price_response.status_code != 200:
            await ctx.respond("Failed to retrieve price data. Please try again later.")
            return

        price_data = price_response.json()
        prices = [entry["maxFP"] for entry in price_data]  # Convert to SATS

        # Generate the plot
        price_chart = plot_ordinals_price_chart(price_data, floor_price_btc)

        # Add fields to embed with ordinal information
        embed.add_field(name="Floor Price", value=formatted_price, inline=True)
        embed.add_field(name="Volume", value=total_volume_btc, inline=True)
        embed.add_field(name="Holders", value=holders, inline=True)
        embed.add_field(name="Listed", value=total_listed, inline=True)
        embed.add_field(
            name="Pending Transactions", value=pending_transactions, inline=True
        )
        embed.set_thumbnail(url=image)

        # Send the chart image in an embed
        file = discord.File(price_chart, filename="price_chart.png")
        embed.add_field(
            name="Price Chart",
            value=f"Here is the {timeframe} price chart for this ordinal:",
            inline=False,
        )
        embed.set_image(url="attachment://price_chart.png")
        embed.set_footer(
            text="Powered by Brain Box Intel",
            icon_url="https://www.brainboxintel.xyz/static/assets/img/brainboxintel.jpg",
        )
        await ctx.respond(
            file=file, embed=embed, view=view
        )
        
"""
MISC Commands - END;
"""


"""
Wallet Tracking Logic, Admin; Start
"""
tracked_wallets = {}

@bot.command(
    name="setchannel",
    description="Set the channel for wallet tracking updates (Admin only)"
)
@commands.check(is_admin)
async def setchannel(interaction: discord.Interaction, channel: Option(discord.TextChannel, "Select the channel")):  # type: ignore
    await interaction.response.defer(ephemeral=True)
    
    guild_id = interaction.guild.id
    channel_id = channel.id
    key = f"{guild_id}-{channel_id}"  # Use a string key for JSON compatibility

    global output_channels
    output_channels[key] = channel_id  # Store the channel ID with the guild-channel string key
    save_wallet_data()  # Save to JSON immediately

    embed = discord.Embed(
        title="Tracking Channel Set ✅",
        description=f"Wallet tracking updates will now be sent to **{channel.mention}**",
        color=discord.Color.green()
    )
    await interaction.followup.send(embed=embed, ephemeral=True)  # Make response visible only to the command caller

class AddWalletModal(Modal):
    def __init__(self, original_context: discord.ApplicationContext):
        super().__init__(title="Add Wallet Details")
        self.original_context = original_context

        # Text input fields for required information
        self.name = InputText(
            label="Wallet Name", placeholder="Enter the wallet's name", required=True
        )
        self.wallet_address = InputText(
            label="Taproot Wallet Address",
            placeholder="Enter the wallet address",
            required=True,
        )
        self.track_mint = InputText(
            label="Track Mints (True/False)",
            placeholder="Enter 'True' or 'False'",
            required=True,
        )
        self.track_buy = InputText(
            label="Track Buys (true/false/both)",
            placeholder="Enter 'true', 'false', or 'both'",
            required=True,
        )
        self.track_sell = InputText(
            label="Track Sells (true/false/both)",
            placeholder="Enter 'true', 'false', or 'both'",
            required=True,
        )

        # Add inputs to modal
        self.add_item(self.name)
        self.add_item(self.wallet_address)
        self.add_item(self.track_mint)
        self.add_item(self.track_buy)
        self.add_item(self.track_sell)

    async def on_submit(self, interaction: Interaction):
        # Extract data from modal and validate input
        name = self.name.value
        wallet_address = self.wallet_address.value

        # Validation for boolean fields
        track_mint = self.track_mint.value.lower() == "true"
        if self.track_buy.value.lower() in ["true", "false", "both"]:
            track_buy = self.track_buy.value.lower()
        else:
            await interaction.response.send_message(
                "Invalid input for Track Buys. Please enter 'true', 'false', or 'both'."
            )
            return

        if self.track_sell.value.lower() in ["true", "false", "both"]:
            track_sell = self.track_sell.value.lower()
        else:
            await interaction.response.send_message(
                "Invalid input for Track Sells. Please enter 'true', 'false', or 'both'."
            )
            return

        # Call addwallet command directly with validated inputs
        await addwallet(
            self.original_context,
            name,
            wallet_address,
            track_mint,
            track_buy,
            track_sell,
        )

@bot.command(name="addwallet", description="Add a wallet to track (Admin only)")
@commands.check(is_admin)  # Limit to admins
async def addwallet(
    ctx: discord.ApplicationContext,
    name: Option(str, "Name for the wallet"),  # type: ignore
    wallet_address: Option(str, "Taproot Wallet Address"),  # type: ignore
    track_mint: Option(bool, "Track mints (inscriptions)?", choices=[True, False]),  # type: ignore
    track_buy: Option(str, "Track buys?", choices=["true", "false", "both"]),  # type: ignore
    track_sell: Option(str, "Track sells?", choices=["true", "false", "both"]), # type: ignore
):  # type: ignore
    guild_id = ctx.guild.id
    channel_id = ctx.channel.id
    key = f"{guild_id}-{channel_id}"  # Use a string key for JSON compatibility

    global tracked_wallets

    # Defer the response to indicate the bot is processing the command
    await ctx.defer(ephemeral=True)

    # Ensure the tracked_wallets for the specific channel/guild exists
    if key not in tracked_wallets:
        tracked_wallets[key] = {}

    # Set tracking options for buys and sells
    track_buy = True if track_buy == "true" else False if track_buy == "false" else "both"
    track_sell = True if track_sell == "true" else False if track_sell == "false" else "both"

    # Add the wallet to the channel's tracked wallets
    tracked_wallets[key][wallet_address] = {
        "name": name,
        "track_mint": track_mint,
        "track_buy": track_buy,
        "track_sell": track_sell,
    }

    save_wallet_data()
    await ctx.respond(
        f"Wallet '{name}' added to tracking list for this channel.",
        ephemeral=True  # Make response visible only to the command caller
    )

@bot.command(name="deletewallet", description="Delete a tracked wallet by address (Admin only)")
@commands.check(is_admin)
async def deletewallet(
    ctx: discord.ApplicationContext,
    wallet_address: Option(str, "Address of the wallet to delete"),  # type: ignore
):  # type: ignore
    guild_id = ctx.guild.id
    channel_id = ctx.channel.id
    key = f"{guild_id}-{channel_id}"  # Use a string key

    global tracked_wallets

    # Defer the response to indicate the bot is processing the command
    await ctx.defer(ephemeral=True)

    # Check if the key exists and delete the wallet by address
    if key in tracked_wallets:
        if wallet_address in tracked_wallets[key]:
            del tracked_wallets[key][wallet_address]
            save_wallet_data()
            await ctx.respond(
                f"Wallet with address '{wallet_address}' deleted from tracking list.",
                ephemeral=True  # Make the response visible only to the user who called the command
            )
            return

    await ctx.respond(
        f"Wallet with address '{wallet_address}' not found in tracking list.",
        ephemeral=True  # Make the response visible only to the user who called the command
    )

@bot.command(name="listwallets", description="List all tracked wallets (Admin only)")
@commands.check(is_admin)
async def listwallets(ctx: discord.ApplicationContext):  # type: ignore
    guild_id = ctx.guild.id
    channel_id = ctx.channel.id
    key = f"{guild_id}-{channel_id}"  # Use a string key

    global tracked_wallets

    # Defer the response to indicate the bot is processing the command
    await ctx.defer(ephemeral=True)

    if key not in tracked_wallets or not tracked_wallets[key]:
        embed = discord.Embed(
            title="Nothing to see here ❌",
            description="No wallet(s) is/are currently being tracked in this channel. Add some wallets to get started with tracking by running the **/addwallet** command.",
            color=discord.Color.red(),
        )

        button = Button(label="Add Wallet", style=discord.ButtonStyle.primary)

        async def addwallet_modal_callback(interaction: Interaction):
            modal = AddWalletModal(original_context=ctx)
            await interaction.response.send_modal(modal)

        button.callback = addwallet_modal_callback
        view = View()
        view.add_item(button)

        await ctx.respond(embed=embed, view=view, ephemeral=True)  # Make response visible only to the command caller
        return

    embed = discord.Embed(title="Tracked Wallets 💳", color=discord.Color.blue())
    for address, info in tracked_wallets[key].items():
        track_str = ""
        if info["track_mint"]:
            track_str += "Mint "
        if info["track_buy"]:
            track_str += "Buy "
        if info["track_sell"]:
            track_str += "Sell "
        embed.add_field(
            name=info["name"],
            value=f"**Address:** {address}\n**Tracking:** {track_str.strip()}",
            inline=False,
        )

    await ctx.respond(embed=embed, ephemeral=True)  # Make response visible only to the command caller


# Dictionary to store transaction history for each guild/channel
transaction_history: Dict[str, Dict[str, Dict[str, List[str]]]] = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))

async def process_inscription_sales(wallet_address, wallet_info, item, guild_id, channel_id):
    if guild_id not in transaction_history: #Be sure to initialize transaction hisotry
        transaction_history[guild_id] = {}
    if channel_id not in transaction_history[guild_id]:
        transaction_history[guild_id][channel_id] = {}
    if wallet_address not in transaction_history[guild_id][channel_id]:
        transaction_history[guild_id][channel_id][wallet_address] = []

    txn_id = item['inscription_id']  # Assuming 'inscription_id' is the transaction ID field

    # Check if the transaction ID is already tracked
    if txn_id not in transaction_history[guild_id][channel_id][wallet_address]:
        transaction_history[guild_id][channel_id][wallet_address].append(txn_id)
        
        embed_inscription_sales = discord.Embed(
            title=f"{wallet_info.get('name', 'Unknown')} {'Bought' if item.get('to') == wallet_address else 'Sold'} {item.get('inscription_name', 'N/A')} with number #{item.get('inscription_number', 'N/A')}",
            color=(discord.Color.blue() if item.get("to") == wallet_address else discord.Color.red()),
        )
        ins_id = item.get("inscription_id", "N/A")
        embed_inscription_sales.add_field(name="Price (BTC)", value=(int(item.get("psbt_sale", 0)) / 100_000_000), inline=False)
        embed_inscription_sales.add_field(name="Price ($)", value=(int(item.get("psbt_sale", 0)) / 100_000_000) * get_btc_price_usd(), inline=False)
        embed_inscription_sales.set_image(url=f"https://ord-mirror.magiceden.dev/content/{ins_id}")
        embed_inscription_sales.add_field(name="Inscription ID", value=item.get("inscription_id", "N/A"), inline=False)
        embed_inscription_sales.add_field(name="Category", value="Inscriptions")
        embed_inscription_sales.set_footer(text="Powered by Brain Box Intel", icon_url="https://www.brainboxintel.xyz/static/assets/img/brainboxintel.jpg")


        # Send notification to the channel
        channel = bot.get_channel(channel_id)
        if channel:
            await channel.send(embed=embed_inscription_sales)
    
    else:
        pass


async def process_inscriptions(wallet_address, wallet_info, item, guild_id, channel_id):
    # Ensure the transaction_history structure is initialized
    if guild_id not in transaction_history:
        transaction_history[guild_id] = {}
    if channel_id not in transaction_history[guild_id]:
        transaction_history[guild_id][channel_id] = {}
    if wallet_address not in transaction_history[guild_id][channel_id]:
        transaction_history[guild_id][channel_id][wallet_address] = []

    inscription_id = item['inscription_id']  # Assuming 'inscription_id' is the transaction ID field

    # Check if the inscription ID is already tracked
    if inscription_id not in transaction_history[guild_id][channel_id][wallet_address]:
        transaction_history[guild_id][channel_id][wallet_address].append(inscription_id)
        embed_inscription = discord.Embed(
            title=f"{wallet_info.get('name', 'Unknown')} 'Inscribed' Inscription with number #{item.get('inscription_number', 'N/A')}",
            color=(discord.Color.blue() if item.get("to") == wallet_address else discord.Color.red()),
        )

        brc20_info = item.get("brc20_info")
        if brc20_info:  # Check if brc-20 data is present
            brc20_text = f"""**p:** "BRC-20"\n**op:** "transfer"\n**tick:** "{brc20_info.get('tick', 'N/A')}"\n**amt:** "{int(brc20_info.get('amount', 'N/A'))}" """
            embed_inscription.add_field(name="BRC-20 Info", value=brc20_text, inline=False)
        else:
            ins_id = item.get("inscription_id", "N/A")
            embed_inscription.set_image(url=f"https://bis-ord-content.fra1.cdn.digitaloceanspaces.com/ordinals/{ins_id}")

        embed_inscription.add_field(name="Inscription ID", value=item.get("inscription_id", "N/A"), inline=False)
        embed_inscription.add_field(name="Category", value="Inscriptions")
        embed_inscription.set_footer(text="Powered by Brain Box Intel", icon_url="https://www.brainboxintel.xyz/static/assets/img/brainboxintel.jpg")
        
        # Send notification to the channel
        channel = bot.get_channel(channel_id)
        if channel:
            await channel.send(embed=embed_inscription)
    
    else:
        pass


async def process_brc20_transactions(wallet_address, wallet_info, item, guild_id, channel_id):
    # Ensure the transaction_history structure is initialized
    if guild_id not in transaction_history:
        transaction_history[guild_id] = {}
    if channel_id not in transaction_history[guild_id]:
        transaction_history[guild_id][channel_id] = {}
    if wallet_address not in transaction_history[guild_id][channel_id]:
        transaction_history[guild_id][channel_id][wallet_address] = []

    transaction_id = item['tx_id']  # Assuming 'id' is the transaction ID field

    # Check if the transaction ID is already tracked
    if transaction_id not in transaction_history[guild_id][channel_id][wallet_address]:
        transaction_history[guild_id][channel_id][wallet_address].append(transaction_id)
        
        tick = item.get("tick", "Unknown")
        amount = float(item.get("amount", 0.000))
        psbt_price = item.get("psbt_price", 0)
        action = "Bought" if item.get("new_wallet") == wallet_address else "Sold"

        embed_brc20 = discord.Embed(
            title=f"{wallet_info.get('name', 'Unknown')} {action} {amount} {tick}",
            color=(discord.Color.green() if item.get("new_wallet") == wallet_address else discord.Color.red()),
        )
        embed_brc20.add_field(name="Amount", value=f"{amount} units", inline=True)
        embed_brc20.add_field(name="Price (BTC)", value=(psbt_price / 100_000_000), inline=False)
        embed_brc20.add_field(name="Price (USD)", value=(psbt_price / 100_000_000) * get_btc_price_usd(), inline=False)
        embed_brc20.add_field(name="Category", value="BRC20", inline=True)
        embed_brc20.set_footer(text="Powered by Brain Box Intel", icon_url="https://www.brainboxintel.xyz/static/assets/img/brainboxintel.jpg")

        # Send notification to the channel
        channel = bot.get_channel(channel_id)
        if channel:
            await channel.send(embed=embed_brc20)
    
    else:
        pass


async def process_rune_transactions(wallet_address, wallet_info, item, guild_id, channel_id):
    # Ensure the transaction_history structure is initialized
    if guild_id not in transaction_history:
        transaction_history[guild_id] = {}
    if channel_id not in transaction_history[guild_id]:
        transaction_history[guild_id][channel_id] = {}
    if wallet_address not in transaction_history[guild_id][channel_id]:
        transaction_history[guild_id][channel_id][wallet_address] = []

    transaction_id = item['tx_id']  # Assuming 'rune_id' is the transaction ID field

    # Check if the transaction ID is already tracked
    if transaction_id not in transaction_history[guild_id][channel_id][wallet_address]:
        transaction_history[guild_id][channel_id][wallet_address].append(transaction_id)
        
        rune = item.get("rune", {})
        wallet_from = item.get("wallet_from", "Unknown")
        wallet_to = item.get("wallet_to", "Unknown")
        rune_name = rune.get("rune_name", "Unknown")
        action = "Bought" if wallet_to == wallet_address else "Sold"

        embed_runes = discord.Embed(
            title=f"{wallet_info.get('name', 'Unknown')} {action} {rune_name} #{rune.get('rune_number', 'Unknown')}",
            color=(discord.Color.green() if wallet_to == wallet_address else discord.Color.red()),
        )
        embed_runes.add_field(name="Sale Price (BTC)", value=(item.get("sale_price_sats", 0) / 100_000_000), inline=False)
        embed_runes.add_field(name="Price ($)", value=(item.get("sale_price_sats", 0) / 100_000_000) * get_btc_price_usd(), inline=False)
        embed_runes.set_image(url=f"https://ord-mirror.magiceden.dev/content/{item.get('deploy_txid', 'N/A')}")
        embed_runes.add_field(name="Rune ID", value=rune.get("rune_id", "N/A"), inline=False)
        embed_runes.add_field(name="Category", value="Runes")
        embed_runes.set_footer(text="Powered by Brain Box Intel", icon_url="https://www.brainboxintel.xyz/static/assets/img/brainboxintel.jpg")

        # Send notification to the channel
        channel = bot.get_channel(channel_id)
        if channel:
            await channel.send(embed=embed_runes)
    
    else:
        pass


# Dictionary to store the most recent transactions for each wallet
recent_transactions = defaultdict(list)

@tasks.loop(seconds=5)  # Check for new transactions every 5 seconds
async def check_wallet_transactions():
    global tracked_wallets, transaction_history, output_channels, recent_transactions

    headers = {
        "User-Agent": ua.random,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive",
    }

    async with aiohttp.ClientSession() as session:  # Open a session to reuse connections
        for guild_id, wallets in tracked_wallets.items():
            channel_id = output_channels.get(guild_id)  # Get the output channel ID for this guild
            for wallet_address, wallet_info in wallets.items():
                # Initialize recent transactions for this wallet if not already done
                if wallet_address not in recent_transactions:
                    recent_transactions[wallet_address] = []

                # Fetching inscription sales
                inscription_sales_url = f"https://v2api.bestinslot.xyz/wallet/history?page=1&address={wallet_address}"
                async with session.get(inscription_sales_url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        for item in data.get("items", [])[:1]:
                            await process_inscription_sales(wallet_address, wallet_info, item, guild_id, channel_id)

                            # Store recent transactions
                            recent_transactions[wallet_address].append(item)

                # Fetching inscriptions
                inscriptions_url = f"https://v2api.bestinslot.xyz/wallet/history?page=1&address={wallet_address}&activity=1"
                async with session.get(inscriptions_url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        for item in data.get("items", [])[:1]:
                            await process_inscriptions(wallet_address, wallet_info, item, guild_id, channel_id)

                # Fetching BRC-20 transactions
                brc20_transactions_url = f"https://v2api.bestinslot.xyz/wallet/history-brc20?page=1&address={wallet_address}"
                async with session.get(brc20_transactions_url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        for item in data.get("items", [])[:1]:
                            await process_brc20_transactions(wallet_address, wallet_info, item, guild_id, channel_id)

                            # Store recent transactions
                            recent_transactions[wallet_address].append(item)

                # Fetching rune transactions
                rune_transactions_url = f"https://v2api.bestinslot.xyz/rune/activity?page=1&address={wallet_address}&include_rune=true"
                async with session.get(rune_transactions_url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        for item in data.get("items", [])[:1]:
                            await process_rune_transactions(wallet_address, wallet_info, item, guild_id, channel_id)

                            # Store recent transactions
                            recent_transactions[wallet_address].append(item)
                            # Keep only the last two transactions

    save_wallet_data()
"""
Wallet Tracking Logic - End;
"""


"""
USER WALLET LOGIC FOR PnL - START
"""
# TODO: FIx this 
# try:
#     with open(USER_WALLET_FILE, 'r') as f:
#         wallets = json.load(f)
# except FileNotFoundError:
#     wallets = {}


# @bot.command(name="adduserwallets", description="Add wallets",)
# async def adduserwallets(ctx: discord.ApplicationContext,
#                         wallet_name: Option(str, "Name of the wallet"),  # type: ignore
#                         wallet_address: Option(str, "Wallet address")):  # type: ignore

#     await ctx.defer(ephemeral=True)  # Defer the response to show "thinking" indicator

#     guild_id = str(ctx.guild.id)  # Use ctx.channel.id if you want it to be channel-specific
#     if guild_id not in wallets:
#         wallets[guild_id] = []

#     for existing_wallet in wallets[guild_id]:
#         if existing_wallet["name"] == wallet_name or existing_wallet["address"] == wallet_address:
#             embed = discord.Embed(title="Error ❌", description="A wallet with this name or address already exists.", color=discord.Color.red())
#             await ctx.respond(embed=embed, ephemeral=True)  # Respond with error and make it private
#             return

#     wallets[guild_id].append({"name": wallet_name, "address": wallet_address})

#     with open(USER_WALLET_FILE, 'w') as f:
#         json.dump(wallets, f, indent=4)

#     embed = discord.Embed(title="Wallet Added ✅", description=f"Wallet '{wallet_name}' with address '{wallet_address}' added successfully!", color=discord.Color.green())
#     await ctx.respond(embed=embed, ephemeral=True)  # Final response to end the "thinking" indicator


# @bot.command(name="managewallets", description="Delete a wallet")
# async def managewallets(
#     ctx: discord.ApplicationContext,
#     wallet_address: Option(str, "Address of the wallet to delete"), # type: ignore
# ):
#     guild_id = str(ctx.guild.id)

#     if guild_id not in wallets or not wallets[guild_id]:
#         embed = discord.Embed(
#             title="Error", description="No wallets found.", color=discord.Color.red()
#         )
#         await ctx.respond(embed=embed)
#         return

#     wallet_to_delete = None
#     for wallet in wallets[guild_id]:
#         if wallet["address"] == wallet_address:
#             wallet_to_delete = wallet
#             break

#     if wallet_to_delete is None:
#         embed = discord.Embed(
#             title="Error",
#             description="Wallet with the provided address not found.",
#             color=discord.Color.red(),
#         )
#         await ctx.respond(embed=embed)
#         return

#     # Check if the user is the one who added the wallet or if they are an admin

#     wallets[guild_id].remove(wallet_to_delete)

#     with open(USER_WALLET_FILE, "w") as f:
#         json.dump(wallets, f, indent=4)

#     embed = discord.Embed(
#         title="Wallet Deleted 🚮",
#         description=f"Wallet with address '{wallet_address}' deleted successfully!\n",
#         color=discord.Color.green(),
#     )
#     await ctx.respond(embed=embed)


# @bot.command(name="viewwallets", description="View all the wallets")
# async def viewwallets(
#     ctx: discord.ApplicationContext,
#     search: Option(str, "Search for a wallet by name", required=False, default=""), # type: ignore
# ):
#     await ctx.defer()

#     guild_id = str(ctx.guild.id)

#     if guild_id not in wallets or not wallets[guild_id]:
#         embed = discord.Embed(
#             title="Wallets", description="No wallets found.", color=discord.Color.blue()
#         )
#         await ctx.respond(embed=embed, ephemeral=True)
#         return

#     filtered_wallets = wallets[guild_id]
#     if search:
#         filtered_wallets = [
#             wallet
#             for wallet in wallets[guild_id]
#             if search.lower() in wallet["name"].lower()
#         ]

#     if not filtered_wallets:
#         embed = discord.Embed(
#             title="Wallets",
#             description="No wallets found matching your search criteria.",
#             color=discord.Color.blue(),
#         )
#         await ctx.respond(embed=embed, ephemeral=True)
#         return

#     wallet_list = "\n".join(
#         [f"{wallet['name']} ({wallet['address']})" for wallet in filtered_wallets]
#     )
#     embed = discord.Embed(
#         title="Wallets",
#         description=f"**Wallets:**\n{wallet_list}",
#         color=discord.Color.blue(),
#     )
#     await ctx.respond(embed=embed, ephemeral=True)

# @bot.command(
#     name="profit",
#     description="Calculate collective profits of everyone who took part in a trade",
# )
# async def profit(
#     ctx: discord.ApplicationContext,
#     asset_type: Option(str, "Select asset type", choices=["rune", "ordinal"]),  # type: ignore
#     asset_slug: Option(
#         str, "Enter the asset slug (rune name or ordinal collection symbol)"
#     ), # type: ignore
# ):  # type: ignore
#     await ctx.defer()
    
#     headers = {
#         "User-Agent": ua.random,
#         "Accept": "application/json, text/plain, */*",
#         "Authorization": "Bearer 4a02b503-2fdc-4cd3-a053-9d06e81f1c8e",
#     }

#     if asset_type == "rune":
#         spaced_rune = asset_slug


#     if asset_type == "rune":
#         asset_slug = asset_slug.replace("•", "").upper()


#     guild_id = str(ctx.guild.id)

#     if guild_id not in wallets or not wallets[guild_id]:
#         await ctx.respond("No wallets found for this server.")
#         return

#     async with aiohttp.ClientSession() as session:
#         if asset_type == "rune":
#             price_url = f"https://api-mainnet.magiceden.dev/v2/ord/btc/runes/market/{asset_slug}/info"
#         else:
#             price_url = f"https://api-mainnet.magiceden.dev/v2/ord/btc/stat?collectionSymbol={asset_slug}"

#         total_profit_btc = 0
#         total_profit_usd = 0
#         wallets_with_asset = 0
#         total_buy_price = 0
#         total_sell_price = 0
#         total_realized_pnl_btc = 0
#         buy_count = 0
#         sell_count = 0

#         for wallet in wallets[guild_id]:
#             wallet_address = wallet["address"]
#             url = (
#                 f"https://v2api.bestinslot.xyz/rune/activity?page=1&address={wallet_address}&include_rune=true"
#                 if asset_type == "rune"
#                 else f"https://v2api.bestinslot.xyz/wallet/history?page=1&address={wallet_address}"
#             )

#             async with session.get(url) as response:
#                 if response.status == 200:
#                     data = await response.json()
#                 else:
#                     await ctx.respond("Failed to fetch asset data.")
#                     return

#             async with session.get(price_url, headers=headers) as price_response:
#                 if price_response.status == 200:
#                     price_data = await price_response.json()
#                     current_price_sats = float(
#                         price_data["floorUnitPrice"]["formatted"]
#                         if asset_type == "rune"
#                         else price_data["floorPrice"]
#                     )
#                     current_price_btc = current_price_sats / 100000000
#                 else:
#                     await ctx.respond("Failed to fetch current price data.")
#                     return

#             most_recent_buy = None
#             most_recent_sell = None
#             # spaced_rune = data['items']['rune']['spaced_rune_name']
#             for item in data["items"]:
#                 if asset_type == "rune":
#                     if (
#                         item["wallet_to"] == wallet_address
#                         and item["rune"]["rune_name"].lower() == asset_slug.lower()
#                     ):
#                         if (
#                             most_recent_buy is None
#                             or item["ts"] > most_recent_buy["ts"]
#                         ):
#                             most_recent_buy = item
#                 else:
#                     if (
#                         item["to"] == wallet_address
#                         and item["inscription_name"].lower() == asset_slug.lower()
#                     ):
#                         if (
#                             most_recent_buy is None
#                             or item["ts"] > most_recent_buy["ts"]
#                         ):
#                             most_recent_buy = item

#             for item in data["items"]:
#                 if asset_type == "rune":
#                     if (
#                         item["wallet_to"] != wallet_address
#                         and item["rune"]["rune_name"].lower() == asset_slug.lower()
#                         and most_recent_buy
#                         and item["ts"] > most_recent_buy["ts"]
#                     ):
#                         if (
#                             most_recent_sell is None
#                             or item["ts"] > most_recent_sell["ts"]
#                         ):
#                             most_recent_sell = item
#                 else:
#                     if (
#                         item["to"] != wallet_address
#                         and item["inscription_name"].lower() == asset_slug.lower()
#                         and most_recent_buy
#                         and item["ts"] > most_recent_buy["ts"]
#                     ):
#                         if (
#                             most_recent_sell is None
#                             or item["ts"] > most_recent_sell["ts"]
#                         ):
#                             most_recent_sell = item

#             if most_recent_buy:
#                 buy_price_sats = float(
#                     most_recent_buy["sale_price_sats"]
#                     if asset_type == "rune"
#                     else most_recent_buy["psbt_sale"]
#                 )
#                 buy_price_btc = buy_price_sats / 100000000
#                 total_buy_price += buy_price_btc
#                 buy_count += 1

#                 if most_recent_sell:
#                     sell_price_sats = float(
#                         most_recent_sell["sale_price_sats"]
#                         if asset_type == "rune"
#                         else most_recent_sell["psbt_sale"]
#                     )
#                     sell_price_btc = sell_price_sats / 100000000
#                     profit_btc = sell_price_btc - buy_price_btc
#                     total_profit_btc += profit_btc
#                     total_sell_price += sell_price_btc
#                     total_realized_pnl_btc += profit_btc
#                     sell_count += 1
#                     wallets_with_asset += 1
#                 else:
#                     profit_btc = current_price_btc - buy_price_btc
#                     total_profit_btc += profit_btc
#                     wallets_with_asset += 1
#         average_buy_price = total_buy_price / buy_count if buy_count else 0
#         average_sell_price = total_sell_price / sell_count if sell_count else 0
#         average_realized_pnl_btc = (
#             total_realized_pnl_btc / sell_count if sell_count else 0
#         )

#         btc_price_usd = get_btc_price_usd()
#         total_profit_usd = total_profit_btc * btc_price_usd
#         average_realized_pnl_usd = average_realized_pnl_btc * btc_price_usd

#         # --- Image creation code starts here ---

#         from PIL import Image, ImageDraw, ImageFont
#         import requests
#         from io import BytesIO

#         # Load the image
#         image_path = 'output_image.png'
#         image = Image.open(image_path)

#         # Define font path, font size, and text color
#         font_path = "vt323.ttf"  # Path to custom font file (.ttf)
#         font_size = 110          # Font size
#         text_color = (255, 255, 255)  # Default color: White

#         # Load the font
#         try:
#             font = ImageFont.truetype(font_path, font_size)
#         except IOError:
#             print("Font file not found, using default font.")
#             font = ImageFont.load_default()

#         # Create a drawing context
#         draw = ImageDraw.Draw(image)

#         # Define each text and position based on approximate layout
#         wallets_with_asset_value = wallets_with_asset  # The number of wallets that bought
#         average_sold_value = average_sell_price  # Average sell price calculated in the command
#         realized_profit = total_realized_pnl_btc  # Realized profit in BTC
#         remaining_profit = total_profit_btc - total_realized_pnl_btc  # Remaining profit
#         potential_profit = f"{total_profit_btc:.4f}BTC, (${total_profit_usd:.2f}), {((total_profit_btc / total_buy_price) * 100) if total_buy_price > 0 else 0:.1f}%"  # Potential profit

#         # Update the texts_with_positions list with actual values
#         texts_with_positions = [
#             (spaced_rune, (1025, 340), (213, 177, 36)),             # Wallets that bought
#             (str(wallets_with_asset_value), (1950, 434)),  # Wallets that bought
#             (f"{average_sold_value:.5f}BTC", (1950, 570)),  # Average sold value
#             (f"{realized_profit:.4f}BTC", (1950, 712)),  # Realized Profit
#             (f"{remaining_profit:.4f}BTC", (1950, 848)),  # Remaining profit
#             (f"{potential_profit}", (1086, 1280), (213, 177, 36))  # Potential profit (BTC), potential profit ($), percentage gain (%) 
#         ]

#         # Add each text to the image
#         for i, (text, position, *color) in enumerate(texts_with_positions):
#             # Use the specified color if provided, otherwise default to text_color
#             fill_color = color[0] if color else text_color
#             draw.text(position, text, fill=fill_color, font=font)

#         # --- Add user profile picture and username ---
#         user_profile_pic_url = str(ctx.author.avatar.url)
#         response = requests.get(user_profile_pic_url)
#         profile_pic = Image.open(BytesIO(response.content)).resize((100, 100))

#         # Create a mask for the circular shape
#         mask = Image.new('L', profile_pic.size, 0)
#         draw_mask = ImageDraw.Draw(mask)

#         # Define the bounding box for the circle
#         draw_mask.ellipse((0, 0) + profile_pic.size, fill=255)

#         # Ensure the profile picture has an alpha channel
#         profile_pic = profile_pic.convert("RGBA")

#         # Apply the mask to make it circular
#         profile_pic.putalpha(mask)
        
#         # Define position for the profile picture
#         profile_pic_position = (1400, 1400)  # Adjust coordinates as needed
#         username = ctx.author.name
#         username_position = (1520, 1490)  # Adjust x-coordinate as needed
#         draw.text(username_position, username, fill=text_color, font=font)

#         # Calculate the width of the username text
#         username_width = draw.textlength(username, font=font)

#         # Define position for the profile picture next to the username
#         profile_pic_position = (username_position[0] - profile_pic.width - 10, username_position[1] - (profile_pic.height // 2) + (font.size // 2))  
#         image.paste(profile_pic, profile_pic_position, profile_pic)

#         # --- Image creation code ends here ---

#         # Save the new image with text overlay
#         output_path = 'out.png'
#         image.save(output_path)

#         # Send the image to the Discord channel
#         await ctx.respond(file=discord.File(output_path))
                                             
"""
USER WALLET LOGIC FOR PnL - END
"""


"""
RUNE TRACKING LOGIC - START
All of the code below, until the point marked end represents the rune tracking logic. DO NOT TOUCH unless you know what you are doing;
"""
def load_runes_data():
    """Load the runes data from a JSON file if it exists."""
    global data
    if os.path.exists("runes_mint_data.json"):
        with open("runes_mint_data.json", "r") as f:
            data = json.load(f)
    else:
        # Do not initialize any structure here to prevent auto-creation of the file
        data = {}

def save_data():
    # Only save guilds that have at least one tracking channel configured
    data_to_save = {guild_id: channels for guild_id, channels in data.items() if channels}
    with open("data.json", "w") as f:
        json.dump(data_to_save, f, indent=4)

def get_last_sent_percentage(guild_id, rune_id):
    """Get the last sent percentage for a specific rune in a specific guild."""
    guild_id_str = str(guild_id)
    rune_id_str = str(rune_id)
    if guild_id_str in data and rune_id_str in data[guild_id_str]:
        return data[guild_id_str][rune_id_str].get("last_sent_percentage", 0)
    return 0

def set_last_sent_percentage(guild_id, rune_id, percentage):
    """Update the last sent percentage for a specific rune in a specific guild."""
    guild_id_str = str(guild_id)
    rune_id_str = str(rune_id)
    if guild_id_str not in data:
        data[guild_id_str] = {}
    if rune_id_str not in data[guild_id_str]:
        data[guild_id_str][rune_id_str] = {"sent": {}, "last_sent_percentage": 0}
    data[guild_id_str][rune_id_str]["last_sent_percentage"] = percentage
    save_data()

def get_tracking_channels(guild):
    guild_id = str(guild.id)
    
    # Ensure we are only fetching valid channel IDs (numerical strings) from data[guild_id]
    channels = [
        guild.get_channel(int(channel_id))
        for channel_id in data.get(guild_id, {})
        if channel_id.isdigit()  # Filter to ensure it's a valid channel ID
    ]
    
    return [channel for channel in channels if channel is not None]

def get_sent_status(guild_id, rune_id, target):
    """Check if a specific target percentage has been sent for a specific rune in a specific guild."""
    guild_id_str = str(guild_id)
    rune_id_str = str(rune_id)
    if guild_id_str in data and rune_id_str in data[guild_id_str]:
        return data[guild_id_str][rune_id_str].get("sent", {}).get(str(target), False)
    return False

def set_sent_status(guild_id, rune_id, target):
    """Set the sent status for a specific target percentage for a specific rune in a specific guild."""
    guild_id_str = str(guild_id)
    rune_id_str = str(rune_id)
    if guild_id_str not in data:
        data[guild_id_str] = {}
    if rune_id_str not in data[guild_id_str]:
        data[guild_id_str][rune_id_str] = {"sent": {}, "last_sent_percentage": 0}
    data[guild_id_str][rune_id_str]["sent"][str(target)] = True
    save_data()


@bot.command(
    name="runesmint",
    description="Set the channel for runes mint tracking updates (Admin only)",
)
@commands.check(is_admin)  # Limit to admins
async def runesmint(ctx: discord.ApplicationContext, channel: Option(discord.TextChannel, "Select the channel")):  # type: ignore
    guild_id = str(ctx.guild.id)
    channel_id = str(channel.id)

    # Only add guild and channel data if the command is called with a specified channel
    if guild_id not in data:
        data[guild_id] = {}
    
    # Set the specified channel for mint tracking in the guild
    data[guild_id][channel_id] = True
    save_data()

    # Start the tracking task if not already running
    if not runes_mint_tracker.is_running():
        runes_mint_tracker.start()

    await ctx.respond(
        f"Runes mint tracking updates will now be sent to {channel.mention}"
    )

def format_rune_message(rune_data, percentage):
    """Formats the runes mint update as a Discord embed."""
    name = rune_data["spaced_rune"]
    symbol = rune_data["symbol"]

    # Create an embed
    embed = discord.Embed(
        title=f"{name} Mint Update",  # Embed title
        description=f"{symbol} has minted {percentage:.2f}%!",
        color=discord.Color(int("008000", 16)),
    )

    # Add fields to the embed
    embed.add_field(name="Holders", value=f"{rune_data['holders']}", inline=False)
    embed.add_field(
        name="Remaining Supply",
        value=f"{int(rune_data['remaining'])} of {int(rune_data['max_supply'])} left",
        inline=False,
    )
    embed.add_field(
        name="Premine Percentage",
        value=f"{rune_data.get('preminePercentage', 0)}%",
        inline=False,
    )

    embed.set_footer(
        text="Powered by Brain Box Intel",
        icon_url="https://www.brainboxintel.xyz/static/assets/img/brainboxintel.jpg",
    )

    return embed


async def send_rune_mint_update(channel, rune_data, percentage):
    """Sends the formatted runes mint update as an embed with buttons."""
    embed = format_rune_message(rune_data, percentage)
    if embed:
        view = discord.ui.View()
        view.add_item(
            discord.ui.Button(
                label="",
                url=f"https://luminex.io/rune/{rune_data['spaced_rune']}",
                emoji="<:luminex:1301265996161745016>",
            )
        )
        view.add_item(
            discord.ui.Button(
                label="",
                url=f"https://satosea.xyz/en/rune/{rune_data['id']}",
                emoji="<:satosea:1301266022606835854>",
            )
        )
        view.add_item(
            discord.ui.Button(
                label="",
                url=f"https://geniidata.com/ordinals/runes/{rune_data['rune']}",
                emoji="<:geniidata:1301270589826273334>",
            )
        )
        view.add_item(
            discord.ui.Button(
                label="",
                url=f"https://www.ord.io/{rune_data['rune']}?showcase-tab=minting&tab=mint",
                emoji="<:ordio:1301266067339083848>",
            )
        )
        view.add_item(
            discord.ui.Button(
                label="",
                url=f"https://runeblaster.io/{rune_data['rune']}",
                emoji="<:runeblaster:1301269901453037611>",
            )
        )

        await channel.send(embed=embed, view=view)



@tasks.loop(seconds=5)
async def runes_mint_tracker():
    try:
        # If no guilds with tracking channels exist, stop the tracker
        if not any(data[guild_id] for guild_id in data):
            runes_mint_tracker.stop()
            return

        with requests.Session() as session:
            response = session.get(rune_mint_tracker_endpoints["hot_runes"])
            response.raise_for_status()
            runes_data = response.json().get("data", [])

            for rune in runes_data:
                rune_id = str(rune.get("tick", ""))
                percentage = rune.get("progress", 0)
                target_percentages = [10, 25, 50, 80]
                print(rune_id)

                for target in target_percentages:
                    if target <= percentage < target + 0.9:
                        for guild in bot.guilds:
                            guild_id = str(guild.id)

                            # Skip guilds that do not have tracking channels set
                            if guild_id not in data or not data[guild_id]:
                                continue

                            last_sent = get_last_sent_percentage(guild_id, rune_id)

                            if not get_sent_status(guild_id, rune_id, target):
                                session.cookies.clear()
                                details_response = session.get(
                                    rune_mint_tracker_endpoints["rune_details"](
                                        str(rune_id)
                                    )
                                )
                                rune_details = details_response.json().get("data", {})

                                for channel in get_tracking_channels(guild):
                                    await send_rune_mint_update(
                                        channel, rune_details, percentage
                                    )

                                set_last_sent_percentage(guild_id, rune_id, target)
                                set_sent_status(guild_id, rune_id, target)
                                break
                        break
    except Exception as e:
        print(f"Error fetching runes mint data: {e}")

"""
RUNE TRACKING LOGIC - END
"""

bot.run(DISCORD_BOT_TOKEN)

import os
import httpx
import requests
import json
import logging
import aiohttp
import discord
from discord import Option
from discord.ext import commands
from discord.ext import commands, tasks
from collections import defaultdict
from discord.ui import Button, View, Modal, InputText
from discord import Interaction
from typing import List, Dict
from functools import wraps
from io import BytesIO
from fake_useragent import UserAgent
from PIL import Image, ImageDraw, ImageFont
from helpers.constants import (
    rune_endpoints,
    ord_endpoints,
    rune_mint_tracker_endpoints,
)
from helpers.functions import (
    plot_price_chart,
    plot_ordinals_price_chart,
    get_btc_price_usd,
    safe_float,
    safe_int
)
from dotenv import load_dotenv


load_dotenv()
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
WALLET_DATA_FILE = "./data/wallet_tracking_data.json"
USER_WALLET_FILE = "./data/user_wallet_data_file.json"

ua = UserAgent()
intents = discord.Intents.default()
intents.messages = True
bot = discord.Bot(intents=intents)
data = {}

DEV_MODE = True


"""
IN-CODE SUPORTERS
"""

# Allowed user IDs as integers ONLY!
ALLOWED_USERS = [947265286426493000, 1040550234629095464]

async def is_allowed_user(interaction: discord.Interaction):
    """Checks if the user is in the allowed users list."""
    return interaction.user.id in ALLOWED_USERS

@bot.command(name="add_server", description="Add a server to the allowed list.")
@commands.check(is_allowed_user)
async def add_server(interaction: discord.Interaction, server_id: str):
    data = {"allowed_servers": []}

    try:
        with open("./data/allowed_servers.json", "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        pass

    allowed_servers = data.get("allowed_servers", [])

    if server_id in allowed_servers:
        embed = discord.Embed(
            title="Server Already Allowed",
            description=f"The server with ID `{server_id}` is already in the allowed list.",
            color=discord.Color.orange()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    allowed_servers.append(server_id)
    data["allowed_servers"] = allowed_servers

    with open("./data/allowed_servers.json", "w") as f:
        json.dump(data, f, indent=4)

    embed = discord.Embed(
        title="Server Added",
        description=f"Server with ID `{server_id}` has been successfully added to the allowed list.",
        color=discord.Color.green()
    )
    embed.set_footer(text="Powered by Brain Box Intel", icon_url="https://www.brainboxintel.xyz/static/assets/img/brainboxintel.jpg")
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.command(name="remove_server", description="Remove a server from the allowed list.")
@commands.check(is_allowed_user)
async def remove_server(interaction: discord.Interaction, server_id: str):
    # Load the allowed servers from JSON
    try:
        with open("./data/allowed_servers.json", "r") as f:
            data = json.load(f)
            allowed_servers = data.get("allowed_servers", [])
    except FileNotFoundError:
        allowed_servers = []

    if server_id not in allowed_servers:
        embed = discord.Embed(
            title="Server Not Found",
            description=f"The server with ID `{server_id}` is not in the allowed list.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    allowed_servers.remove(server_id)
    data["allowed_servers"] = allowed_servers

    with open("./data/allowed_servers.json", "w") as f:
        json.dump(data, f, indent=4)

    embed = discord.Embed(
        title="Server Removed",
        description=f"Server with ID `{server_id}` has been successfully removed from the allowed list.",
        color=discord.Color.green()
    )
    embed.set_footer(text="Powered by Brain Box Intel", icon_url="https://www.brainboxintel.xyz/static/assets/img/brainboxintel.jpg")
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.command(name="list_servers", description="List all servers in the allowed list.")
@commands.check(is_allowed_user)
async def list_servers(interaction: discord.Interaction):
    try:
        with open("./data/allowed_servers.json", "r") as f:
            data = json.load(f)
            allowed_servers = data.get("allowed_servers", [])
    except FileNotFoundError:
        allowed_servers = [] 

    if not allowed_servers:
        embed = discord.Embed(
            title="Allowed Servers",
            description="No servers are currently in the allowed list.",
            color=discord.Color.red()
        )
        embed.set_footer(text="Powered by Brain Box Intel", icon_url="https://www.brainboxintel.xyz/static/assets/img/brainboxintel.jpg")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    server_list = "\n".join(allowed_servers)
    embed = discord.Embed(
        title="Allowed Servers",
        description=server_list,
        color=discord.Color.blue()
    )
    embed.set_footer(text="Powered by Brain Box Intel", icon_url="https://www.brainboxintel.xyz/static/assets/img/brainboxintel.jpg")

    await interaction.response.send_message(embed=embed, ephemeral=True)


def allowed_server_only():
    def decorator(func):
        @wraps(func)
        async def wrapper(interaction: discord.Interaction, *args, **kwargs):
            try:
                with open("./data/allowed_servers.json", "r") as f:
                    data = json.load(f)
                    allowed_servers = data.get("allowed_servers", [])
            except FileNotFoundError:
                allowed_servers = []
            
            if str(interaction.guild.id) not in allowed_servers:
                await interaction.response.send_message("This server does not have access to use this bot.", ephemeral=True)
                return
            
            return await func(interaction, *args, **kwargs)
        return wrapper
    return decorator


def load_overlay_config():
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(base_dir, "./server_configs/server_overlays.json"), "r") as file:
            overlay_config = json.load(file)

        for key, config in overlay_config.items():
            if "image_path" in config:
                config["image_path"] = os.path.join(base_dir, config["image_path"])
            if "font_path" in config:
                config["font_path"] = os.path.join(base_dir, config["font_path"])

        return overlay_config
    except FileNotFoundError:
        return {}
    
overlay_config = load_overlay_config()

def get_server_overlay(guild_id):
    return overlay_config.get(str(guild_id), overlay_config["default"])

class DeleteButton(discord.ui.Button):
    def __init__(self, author_id):
        super().__init__(style=discord.ButtonStyle.secondary, emoji="❌")
        self.author_id = author_id

    async def callback(self, interaction: discord.Interaction):
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

    try:
        runes_mint_tracker.start()
        logging.info("Runes Mint Tracking Task Started Successfully")
    except Exception as e:
        logging.error(f"Error starting runes mint tracking task: {e}")

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
@allowed_server_only()
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

    await ctx.respond(embed=embed, view=DeleteView(author_id=ctx.author.id), ephemeral=True)

@bot.command(name="satsvb", description="Get network fees on bitcoin")
@allowed_server_only()
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
@allowed_server_only()
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

            price_sats_dec = float(f"{floor_price_sats:.3f}")

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
        prices = [entry["maxFP"] for entry in price_data]

        # Generate the plot
        price_chart = plot_ordinals_price_chart(price_data, floor_price_btc)

        embed.add_field(name="Floor Price", value=formatted_price, inline=True)
        embed.add_field(name="Volume", value=total_volume_btc, inline=True)
        embed.add_field(name="Holders", value=holders, inline=True)
        embed.add_field(name="Listed", value=total_listed, inline=True)
        embed.add_field(
            name="Pending Transactions", value=pending_transactions, inline=True
        )
        embed.set_thumbnail(url=image)

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
@allowed_server_only()
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
@allowed_server_only()
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
@allowed_server_only()
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
            embed = discord.Embed(
                title="Wallet Deleted 🚮",
                description=f"Wallet with address **{wallet_address}** has been deleted",
                color=discord.Color.red()
                )
            embed.set_footer(text="Powered by Brain Box Intel", icon_url="https://www.brainboxintel.xyz/static/assets/img/brainboxintel.jpg")
            await ctx.respond(
                embed=embed,
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
            track_str += "Mint(s) "
        if info["track_buy"]:
            track_str += "Buy(s) "
        if info["track_sell"]:
            track_str += "Sell(s) "
        embed.add_field(
            name=f"Wallet Name: {info['name']}",
            value=f"**Address:** {address}\n**Tracking:** {track_str.strip()}",
            inline=False,
        )
        embed.set_footer(text="Powered by Brain Box Intel", icon_url="https://www.brainboxintel.xyz/static/assets/img/brainboxintel.jpg")


    await ctx.respond(embed=embed, ephemeral=True)  # Make response visible only to the command caller

# Dictionary to store transaction history for each guild/channel
transaction_history: Dict[str, Dict[str, Dict[str, List[str]]]] = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))

async def process_inscription_sales(wallet_address, wallet_info, item, guild_id, channel_id):
    try:
        if guild_id not in transaction_history:
            transaction_history[guild_id] = {}
        if channel_id not in transaction_history[guild_id]:
            transaction_history[guild_id][channel_id] = {}
        if wallet_address not in transaction_history[guild_id][channel_id]:
            transaction_history[guild_id][channel_id][wallet_address] = []

        txn_id = item.get('inscription_id', None)
        if not txn_id:
            print("Missing 'inscription_id' in item:", item)
            return

        if txn_id not in transaction_history[guild_id][channel_id][wallet_address]:
            transaction_history[guild_id][channel_id][wallet_address].append(txn_id)

            try:
                brc20_info = item.get("brc20_info", {})
                transfer_info = brc20_info.get("transfer_info", {})
                is_brc20 = (
                    item.get("inscription_name") is None
                    and transfer_info.get("tick") is not None
                )
            except AttributeError as e:
                # print(f"Error while checking BRC-20 info: {e}")
                is_brc20 = False

            if is_brc20:
                tick = transfer_info.get("tick", "N/A")
                amount = safe_float(transfer_info.get("amount"))
                psbt_sale = safe_int(item.get("psbt_sale"), default=0) / 100_000_000
                btc_price_usd = get_btc_price_usd()

                embed_brc20 = discord.Embed(
                    title=f"{wallet_info.get('name', 'Unknown')} {'Bought' if item.get('to') == wallet_address else 'Sold'} {tick} (BRC-20)",
                    color=(discord.Color.blue() if item.get("to") == wallet_address else discord.Color.red()),
                )
                embed_brc20.add_field(name="Price (BTC)", value=f"{psbt_sale:.8f}", inline=False)
                embed_brc20.add_field(name="Amount (QTY)", value=f"{amount:.2f}", inline=False)
                embed_brc20.add_field(
                    name="Price ($)",
                    value=f"{psbt_sale * btc_price_usd:.2f}" if psbt_sale > 0 else "N/A",
                    inline=False,
                )
                embed_brc20.set_image(url=f"https://ord-mirror.magiceden.dev/content/{txn_id}")
                embed_brc20.add_field(name="Inscription ID", value=txn_id, inline=False)
                embed_brc20.add_field(name="Category", value="BRC-20")
                embed_brc20.set_footer(
                    text="Powered by Brain Box Intel",
                    icon_url="https://www.brainboxintel.xyz/static/assets/img/brainboxintel.jpg",
                )

                channel = bot.get_channel(channel_id)
                if channel:
                    await channel.send(embed=embed_brc20)

            else:
                inscription_name = item.get("inscription_name", "N/A")
                inscription_number = item.get("inscription_number", "N/A")
                psbt_sale = safe_int(item.get("psbt_sale"), default=0) / 100_000_000
                btc_price_usd = get_btc_price_usd()

                embed_inscription_sales = discord.Embed(
                    title=f"{wallet_info.get('name', 'Unknown')} {'Bought' if item.get('to') == wallet_address else 'Sold'} {inscription_name} #{inscription_number}",
                    color=(discord.Color.blue() if item.get("to") == wallet_address else discord.Color.red()),
                )
                embed_inscription_sales.add_field(name="Price (BTC)", value=f"{psbt_sale:.8f}", inline=False)
                embed_inscription_sales.add_field(
                    name="Price ($)",
                    value=f"{psbt_sale * btc_price_usd:.2f}" if psbt_sale > 0 else "N/A",
                    inline=False,
                )
                embed_inscription_sales.set_image(url=f"https://ord-mirror.magiceden.dev/content/{txn_id}")
                embed_inscription_sales.add_field(name="Inscription ID", value=txn_id, inline=False)
                embed_inscription_sales.add_field(name="Category", value="Inscriptions")
                embed_inscription_sales.set_footer(
                    text="Powered by Brain Box Intel",
                    icon_url="https://www.brainboxintel.xyz/static/assets/img/brainboxintel.jpg",
                )

                channel = bot.get_channel(channel_id)
                if channel:
                    await channel.send(embed=embed_inscription_sales)
    except Exception as e:
        logging.error(
            
            f"""Error occured at the point of inscription sales processing. Here is a detailed traceback: 
            {e}
            """   
        )

        
async def process_inscriptions(wallet_address, wallet_info, item, guild_id, channel_id):
    try:
        if guild_id not in transaction_history:
            transaction_history[guild_id] = {}
        if channel_id not in transaction_history[guild_id]:
            transaction_history[guild_id][channel_id] = {}
        if wallet_address not in transaction_history[guild_id][channel_id]:
            transaction_history[guild_id][channel_id][wallet_address] = []

        inscription_id = item.get("inscription_id", None)
        if not inscription_id:
            print("Missing 'inscription_id' in item:", item)
            return

        if inscription_id not in transaction_history[guild_id][channel_id][wallet_address]:
            transaction_history[guild_id][channel_id][wallet_address].append(inscription_id)

            is_brc20 = False
            mint_info = {}

            try:
                mint_info = item.get("brc20_info", {}).get("mint_info", {})
                is_brc20 = (
                    item.get("inscription_name") is None
                    and mint_info.get("tick") is not None
                )
            except AttributeError as e:
                print(f"Error accessing mint_info: {e}")

            inscription_number = item.get("inscription_number", "N/A")
            inscription_name = item.get("inscription_name", "N/A")
            title = f"{wallet_info.get('name', 'Unknown')} 'Inscribed' {inscription_name} with number {inscription_number}"

            if is_brc20:
                tick = mint_info.get("tick", "N/A")
                amount = safe_float(mint_info.get("amount"), default=0.0) / 100_000_000
                mint_wallet = mint_info.get("mint_wallet", "N/A")

                embed_brc20 = discord.Embed(
                    title=f"{title} (BRC-20 Mint: {tick})",
                    color=(discord.Color.blue() if mint_wallet == wallet_address else discord.Color.red()),
                )
                embed_brc20.add_field(name="Mint Amount (QTY)", value=f"{amount:.2f}", inline=False)
                embed_brc20.add_field(name="Mint Wallet", value=mint_wallet, inline=False)
                embed_brc20.add_field(name="Inscription ID", value=inscription_id, inline=False)
                embed_brc20.add_field(name="Category", value="BRC-20")
                embed_brc20.set_footer(
                    text="Powered by Brain Box Intel",
                    icon_url="https://www.brainboxintel.xyz/static/assets/img/brainboxintel.jpg",
                )

                channel = bot.get_channel(channel_id)
                if channel:
                    await channel.send(embed=embed_brc20)

            else:
                embed_inscription = discord.Embed(
                    title=title,
                    color=(discord.Color.blue() if item.get("to") == wallet_address else discord.Color.red()),
                )
                embed_inscription.add_field(name="Inscription ID", value=inscription_id, inline=False)
                embed_inscription.add_field(name="Category", value="Inscriptions")
                embed_inscription.set_footer(
                    text="Powered by Brain Box Intel",
                    icon_url="https://www.brainboxintel.xyz/static/assets/img/brainboxintel.jpg",
                )

                channel = bot.get_channel(channel_id)
                if channel:
                    await channel.send(embed=embed_inscription)
    
    except Exception as e:
        logging.error(
            
            f"""Error occured at the point of inscription processing. Here is a detailed traceback: 
            {e}
            """   
        )


async def process_rune_transactions(wallet_address, wallet_info, item, guild_id, channel_id):
    try:
        if guild_id not in transaction_history:
            transaction_history[guild_id] = {}
        if channel_id not in transaction_history[guild_id]:
            transaction_history[guild_id][channel_id] = {}
        if wallet_address not in transaction_history[guild_id][channel_id]:
            transaction_history[guild_id][channel_id][wallet_address] = []

        transaction_id = item['tx_id']

        if transaction_id not in transaction_history[guild_id][channel_id][wallet_address]:
            transaction_history[guild_id][channel_id][wallet_address].append(transaction_id)
            
            rune = item.get("rune", {})
            wallet_to = item.get("wallet_to", "Unknown")
            rune_name = rune.get("spaced_rune_name", "Unknown")
            rune_symbol = item.get("symbol", "N/A")
            action = "Bought" if wallet_to == wallet_address else "Sold"

            embed_runes = discord.Embed(
                title=f"{wallet_info.get('name', 'Unknown')} {action} {rune_name} {rune_symbol} #{rune.get('rune_number', 'Unknown')}",
                color=(discord.Color.green() if wallet_to == wallet_address else discord.Color.red()),
            )
            embed_runes.add_field(name="Sale Price (BTC)", value=(item.get("sale_price_sats", 0) / 100_000_000), inline=False)
            embed_runes.add_field(
                name="Price ($)", 
                value=f"{(item.get('sale_price_sats', 0) / 100_000_000) * get_btc_price_usd():.2f}", 
                inline=False
            )        
            embed_runes.set_image(url=f"https://ord-mirror.magiceden.dev/content/{item.get('deploy_txid', 'N/A')}")
            embed_runes.add_field(name="Rune ID", value=rune.get("rune_id", "N/A"), inline=False)
            embed_runes.add_field(name="Category", value="Runes")
            embed_runes.set_footer(text="Powered by Brain Box Intel", icon_url="https://www.brainboxintel.xyz/static/assets/img/brainboxintel.jpg")

            channel = bot.get_channel(channel_id)
            if channel:
                await channel.send(embed=embed_runes)
    
    except Exception as e:
        logging.error(
            
            f"""Error occured at the point of runes processing. Here is a detailed traceback: 
            {e}
            """   
        )
        

recent_transactions = defaultdict(list)

@tasks.loop(seconds=5)
async def check_wallet_transactions():
    global tracked_wallets, transaction_history, output_channels, recent_transactions

    headers = {
        "User-Agent": ua.random,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive",
    }

    async with aiohttp.ClientSession() as session:
        tracked_wallets_snapshot = list(tracked_wallets.items())
        output_channels_snapshot = output_channels.copy()

        for guild_id, wallets in tracked_wallets_snapshot:
            channel_id = output_channels_snapshot.get(guild_id)
            if channel_id is None:
                continue
            
            for wallet_address, wallet_info in list(wallets.items()):
                if wallet_address not in recent_transactions:
                    recent_transactions[wallet_address] = []

                inscription_sales_url = f"https://v2api.bestinslot.xyz/wallet/history?page=1&address={wallet_address}"
                async with session.get(inscription_sales_url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        items = data.get("items", [])
                        if items:
                            for item in items[:1]:
                                await process_inscription_sales(wallet_address, wallet_info, item, guild_id, channel_id)
                                recent_transactions[wallet_address].append(item)

                inscriptions_url = f"https://v2api.bestinslot.xyz/wallet/history?page=1&address={wallet_address}&activity=1"
                async with session.get(inscriptions_url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        items = data.get("items", [])
                        if items:
                            for item in items[:1]:
                                await process_inscriptions(wallet_address, wallet_info, item, guild_id, channel_id)

                rune_transactions_url = f"https://v2api.bestinslot.xyz/rune/activity?page=1&address={wallet_address}&include_rune=true"
                async with session.get(rune_transactions_url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        items = data.get("items", [])
                        if items:
                            for item in items[:1]:
                                await process_rune_transactions(wallet_address, wallet_info, item, guild_id, channel_id)
                                recent_transactions[wallet_address].append(item)

    save_wallet_data()


async def send_no_transactions_message(channel_id, wallet_info, transaction_type):
    """Send a message indicating that no transactions of a specific type were found."""
    embed_no_transactions = discord.Embed(
        title=f"No {transaction_type} Found ❌",
        description=f"{wallet_info.get('name', 'Unknown')} did not process any {transaction_type}",
        color=discord.Color.orange()
    )
    embed_no_transactions.set_footer(text="Powered by Brain Box Intel", icon_url="https://www.brainboxintel.xyz/static/assets/img/brainboxintel.jpg")

    channel = bot.get_channel(channel_id)
    if channel:
        await channel.send(embed=embed_no_transactions)

"""
Wallet Tracking Logic - End;
"""


"""
USER WALLET LOGIC FOR PnL - START
"""
# Function to create a circular avatar
async def create_circular_avatar(avatar_url):
    async with aiohttp.ClientSession() as session:
        async with session.get(avatar_url) as response:
            avatar_data = BytesIO(await response.read())
            avatar_img = Image.open(avatar_data).convert("RGBA")

            # Create a circular mask
            mask = Image.new("L", avatar_img.size, 0)
            draw = ImageDraw.Draw(mask)
            draw.ellipse((0, 0, avatar_img.size[0], avatar_img.size[1]), fill=255)

            circular_avatar = Image.new("RGBA", avatar_img.size)
            circular_avatar.paste(avatar_img, (0, 0), mask)
            return circular_avatar

async def overlay_with_user_info(
    image_path,
    output_path,
    texts_with_coordinates,
    default_font_path,
    username,
    avatar_url,
    avatar_coordinates,
    username_coordinates,
    avatar_size=(100, 100),  # Default size
):
    try:
        img = Image.open(image_path)
        draw = ImageDraw.Draw(img)

        for entry in texts_with_coordinates:
            text = entry["text"]
            coordinates = entry["coordinates"]
            color = entry["color"]
            font_size = entry.get("font_size", 40)

            font = ImageFont.truetype(default_font_path, font_size)
            draw.text(coordinates, text, fill=color, font=font)

        # Create and resize the avatar based on the config
        circular_avatar = await create_circular_avatar(avatar_url)
        circular_avatar = circular_avatar.resize(avatar_size)

        # Paste the avatar onto the image
        img.paste(circular_avatar, avatar_coordinates, circular_avatar)

        # Draw the username
        font = ImageFont.truetype(default_font_path, 50)
        draw.text(username_coordinates, username, fill=(0, 0, 0), font=font)

        # Save the final image
        img.save(output_path)
    except Exception as e:
        print(f"Error: {e}")

try:
    with open(USER_WALLET_FILE, 'r') as f:
        wallets = json.load(f)
except FileNotFoundError:
    wallets = {}

@bot.command(name="adduserwallets", description="Add wallets")
async def adduserwallets(ctx: discord.ApplicationContext,
                         wallet_name: Option(str, "Name of the wallet"), #type: ignore
                         wallet_address: Option(str, "Wallet address")): #type: ignore
    await ctx.defer(ephemeral=True)

    guild_id = str(ctx.guild.id) 
    user_id = str(ctx.author.id) 

    if guild_id not in wallets:
        wallets[guild_id] = {}

    if user_id not in wallets[guild_id]:
        wallets[guild_id][user_id] = []

    for existing_wallet in wallets[guild_id][user_id]:
        if existing_wallet["name"] == wallet_name or existing_wallet["address"] == wallet_address:
            embed = discord.Embed(title="Error ❌", description="A wallet with this name or address already exists.", color=discord.Color.red())
            await ctx.respond(embed=embed, ephemeral=True)
            return

    wallets[guild_id][user_id].append({"name": wallet_name, "address": wallet_address})

    with open(USER_WALLET_FILE, 'w') as f:
        json.dump(wallets, f, indent=4)

    embed = discord.Embed(
        title="Wallet Added ✅",
        description=f"Wallet **'{wallet_name}'** with address **'{wallet_address}'** added successfully!",
        color=discord.Color.green()
    )
    embed.set_footer(text="Powered by Brain Box Intel", icon_url="https://www.brainboxintel.xyz/static/assets/img/brainboxintel.jpg")
    await ctx.respond(embed=embed, ephemeral=True)

@bot.command(name="managewallets", description="Delete a wallet")
async def managewallets(ctx: discord.ApplicationContext,
                        wallet_address: Option(str, "Address of the wallet to delete")): #type: ignore
    guild_id = str(ctx.guild.id)
    user_id = str(ctx.author.id)

    if guild_id not in wallets or user_id not in wallets[guild_id] or not wallets[guild_id][user_id]:
        embed = discord.Embed(title="Error", description="No wallets found.", color=discord.Color.red())
        await ctx.respond(embed=embed, ephemeral=True)
        return

    wallet_to_delete = next((wallet for wallet in wallets[guild_id][user_id] if wallet["address"] == wallet_address), None)

    if wallet_to_delete is None:
        embed = discord.Embed(title="Error", description="Wallet with the provided address not found.", color=discord.Color.red())
        await ctx.respond(embed=embed, ephemeral=True)
        return

    wallets[guild_id][user_id].remove(wallet_to_delete)

    with open(USER_WALLET_FILE, "w") as f:
        json.dump(wallets, f, indent=4)

    embed = discord.Embed(title="Wallet Deleted 🚮", description=f"Wallet with address '{wallet_address}' deleted successfully!", color=discord.Color.green())
    embed.set_footer(text="Powered by Brain Box Intel", icon_url="https://www.brainboxintel.xyz/static/assets/img/brainboxintel.jpg")
    await ctx.respond(embed=embed, ephemeral=True)

@bot.command(name="viewwallets", description="View all the wallets")
async def viewwallets(
    ctx: discord.ApplicationContext,
    search: Option(str, "Search for a wallet by name", required=False, default="") #type:ignore
):
    await ctx.defer(ephemeral=True)

    guild_id = str(ctx.guild.id)
    user_id = str(ctx.author.id)

    # Check if the user has wallets
    if guild_id not in wallets or user_id not in wallets[guild_id] or not wallets[guild_id][user_id]:
        embed = discord.Embed(
            title="No Wallets Found",
            description="You haven't added any wallets yet.",
            color=discord.Color.blue()
        )
        await ctx.respond(embed=embed, ephemeral=True)
        return

    # Filter wallets by the search term if provided
    filtered_wallets = wallets[guild_id][user_id]
    if search:
        filtered_wallets = [
            wallet for wallet in filtered_wallets if search.lower() in wallet["name"].lower()
        ]

    # Handle case where no wallets match the search
    if not filtered_wallets:
        embed = discord.Embed(
            title="No Matches Found",
            description=f"No wallets found matching **'{search}'**.",
            color=discord.Color.blue()
        )
        await ctx.respond(embed=embed, ephemeral=True)
        return

    # Prepare a formatted list of wallets
    wallet_list = "\n".join(
        [
            f"**{index + 1}. {wallet['name']}**\n`{wallet['address']}`"
            for index, wallet in enumerate(filtered_wallets)
        ]
    )

    # Build the embed message
    embed = discord.Embed(
        title="Your Wallets",
        description=wallet_list,
        color=discord.Color.green()
    )
    embed.set_footer(text="Powered by Brain Box Intel", icon_url="https://www.brainboxintel.xyz/static/assets/img/brainboxintel.jpg")
    await ctx.respond(embed=embed, ephemeral=True)


# @bot.command(
#     name="profit",
#     description="Calculate collective profits of everyone who took part in a trade",
# )
# async def profit(
#     ctx: discord.ApplicationContext,
#     asset_type: Option(str, "Select asset type", choices=["rune"]),  # type: ignore
#     asset_slug: Option(
#         str, "Enter the asset slug (rune name or ordinal collection symbol)"
#     ),  # type: ignore
# ):  # type: ignore
#     await ctx.defer()

#     headers = {
#         "User-Agent": ua.random,
#         "Accept": "application/json",
#         "Authorization": "Bearer 4a02b503-2fdc-4cd3-a053-9d06e81f1c8e",
#     }

#     if asset_type == "rune":
#         spaced_rune = asset_slug
#         asset_slug = asset_slug.replace("•", "").upper()

#     guild_id = str(ctx.guild.id)
#     overlay = get_server_overlay(guild_id)
#     user_id = str(ctx.author.id)

#     image_path = overlay.get("image_path", "./blank.jpg")
#     font_path = overlay.get("font_path", "./LoveYaLikeASister.ttf")
#     text_coordinates = overlay.get("text_coordinates", [])
#     avatar_coordinates = overlay.get("avatar_coordinates", [1200, 1870])
#     username_coordinates = overlay.get("username_coordinates", [1300, 1880])
#     avatar_size = overlay.get("avatar_size", [100, 100])

#     # Check if the user has wallets
#     if guild_id not in wallets or user_id not in wallets[guild_id] or not wallets[guild_id][user_id]:
#         await ctx.respond("You have not added any wallets to calculate profits.", ephemeral=True)
#         return
    
#     user_wallets = wallets[guild_id][user_id]

#     async with aiohttp.ClientSession() as session:
#         if asset_type == "rune":
#             price_url = f"https://api-mainnet.magiceden.dev/v2/ord/btc/runes/market/{asset_slug}/info"
#         else:
#             price_url = f"https://api-mainnet.magiceden.dev/v2/ord/btc/stat?collectionSymbol={asset_slug}"

#         total_bought_btc = 0
#         total_sold_btc = 0
#         total_quantity_bought = 0
#         total_quantity_sold = 0

#         for wallet in user_wallets:
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

#             # Process transactions
#             for item in data["items"]:
#                 if asset_type == "rune":
#                     is_buy = item["wallet_to"] == wallet_address and item["rune"]["rune_name"].lower() == asset_slug.lower()
#                     is_sell = item["wallet_to"] != wallet_address and item["rune"]["rune_name"].lower() == asset_slug.lower()
#                 else:
#                     is_buy = item["to"] == wallet_address and item["inscription_name"].lower() == asset_slug.lower()
#                     is_sell = item["to"] != wallet_address and item["inscription_name"].lower() == asset_slug.lower()

#                 if is_buy:
#                     buy_price_sats = float(item["sale_price_sats"])
#                     quantity_bought = float(item.get("amount", 1))
#                     total_bought_btc += buy_price_sats / 100000000
#                     total_quantity_bought += quantity_bought

#                 elif is_sell:
#                     sell_price_sats = float(item["sale_price_sats"])
#                     quantity_sold = float(item.get("amount", 1))
#                     total_sold_btc += sell_price_sats / 100000000
#                     total_quantity_sold += quantity_sold

#         holding_quantity = total_quantity_bought - total_quantity_sold
#         holding_btc = holding_quantity * current_price_btc
#         holding_usd = holding_btc * get_btc_price_usd()

#         total_bought_btc = max(total_bought_btc, 1e-8)

#         if total_quantity_sold == 0:
#             pnl_btc = holding_btc - total_bought_btc
#         else:
#             if total_quantity_bought == 0:
#                 # Handle the edge case where total_quantity_bought is zero
#                 realized_pnl_btc = 0  # Or another appropriate default value
#                 unrealized_pnl_btc = holding_btc  # Assuming no cost basis
#             else:
#                 realized_pnl_btc = total_sold_btc - (total_quantity_sold / total_quantity_bought * total_bought_btc)
#                 unrealized_pnl_btc = holding_btc - (holding_quantity / total_quantity_bought * total_bought_btc)
            
#             pnl_btc = realized_pnl_btc + unrealized_pnl_btc

#         pnl_usd = pnl_btc * get_btc_price_usd()
#         pnl_percentage = (pnl_btc / total_bought_btc) * 100

#         # Overlay text preparation
#         text_keys = ["asset_name", "total_bought", "total_sold", "holdings", "pnl"]
#         text_values = [
#             f"{spaced_rune}" if asset_type == "rune" else asset_slug,
#             f"{total_bought_btc:.4f} (${total_bought_btc * get_btc_price_usd():.2f})",
#             f"{total_sold_btc:.4f} (${total_sold_btc * get_btc_price_usd():.2f})",
#             f"{holding_btc:.4f} (${holding_usd:.2f})",
#             f"{pnl_btc:.4f} (${pnl_usd:.2f}) ({pnl_percentage:.2f}%)",
#         ]

#         texts_with_coordinates = []
#         for i, text_key in enumerate(text_keys):
#             if i < len(text_coordinates):
#                 coordinate = text_coordinates[i]
#                 texts_with_coordinates.append({
#                     "text": text_values[i],
#                     "coordinates": tuple(coordinate["coordinates"]),
#                     "color": tuple(coordinate["color"]),
#                     "font_size": coordinate["font_size"],
#                 })

#         output_path = f"./output/profit_overlay_{guild_id}.jpg"
#         os.makedirs(os.path.dirname(output_path), exist_ok=True)

#         await overlay_with_user_info(
#             image_path,
#             output_path,
#             texts_with_coordinates,
#             font_path,
#             username=str(ctx.author.name),
#             avatar_url=ctx.author.avatar.url,
#             avatar_coordinates=tuple(avatar_coordinates),
#             username_coordinates=tuple(username_coordinates),
#             avatar_size=tuple(avatar_size),
#         )

#         if os.path.exists(output_path):
#             with open(output_path, "rb") as file:
#                 await ctx.respond(file=discord.File(file, os.path.basename(output_path)))
#             os.remove(output_path)
#         else:
#             await ctx.respond("Failed to generate the overlay image.")


# @bot.command(
#     name="profit",
#     description="Calculate collective profits of everyone who took part in a trade",
# )
# async def profit(
#     ctx: discord.ApplicationContext,
#     asset_type: Option(str, "Select asset type", choices=["rune"]),  # type: ignore
#     asset_slug: Option(
#         str, "Enter the asset slug (rune name or ordinal collection symbol)"
#     ),  # type: ignore
# ):  # type: ignore
#     await ctx.defer()

#     headers = {
#         "Accept": "application/json",
#         "Authorization": "Bearer 4a02b503-2fdc-4cd3-a053-9d06e81f1c8e",  # Example token
#     }

#     # If it's a rune, remove the "•" and uppercase it (store a "spaced_rune" for display).
#     if asset_type == "rune":
#         spaced_rune = asset_slug
#         asset_slug = asset_slug.replace("•", "").upper()

#     guild_id = str(ctx.guild.id)
#     overlay = get_server_overlay(guild_id)
#     user_id = str(ctx.author.id)

#     image_path = overlay.get("image_path", "./blank.jpg")
#     font_path = overlay.get("font_path", "./LoveYaLikeASister.ttf")
#     text_coordinates = overlay.get("text_coordinates", [])
#     avatar_coordinates = overlay.get("avatar_coordinates", [1200, 1870])
#     username_coordinates = overlay.get("username_coordinates", [1300, 1880])
#     avatar_size = overlay.get("avatar_size", [100, 100])

#     # Check if the user has any wallets
#     if (
#         guild_id not in wallets
#         or user_id not in wallets[guild_id]
#         or not wallets[guild_id][user_id]
#     ):
#         await ctx.respond("You have not added any wallets to calculate profits.", ephemeral=True)
#         return

#     user_wallets = wallets[guild_id][user_id]

#     # -------------------------------------------------------------------------
#     # Initialize counters
#     # -------------------------------------------------------------------------
#     total_bought_btc = 0.0
#     total_sold_btc = 0.0
#     total_quantity_bought = 0.0
#     total_quantity_sold = 0.0

#     async with httpx.AsyncClient() as client:
#         # Determine which Magic Eden URL to fetch the current price
#         if asset_type == "rune":
#             price_url = f"https://api-mainnet.magiceden.dev/v2/ord/btc/runes/market/{asset_slug}/info"
#         else:
#             # For ordinal collections, example endpoint:
#             price_url = f"https://api-mainnet.magiceden.dev/v2/ord/btc/stat?collectionSymbol={asset_slug}"

#         # Fetch current floor price data
#         price_response = await client.get(price_url, headers=headers)
#         print("Price status code:", price_response.status_code)
#         print("Price response text:", price_response.text[:500])

#         if price_response.status_code != 200:
#             await ctx.respond(
#                 f"Failed to fetch current price data (status={price_response.status_code})."
#             )
#             return

#         try:
#             price_data = price_response.json()
#         except json.decoder.JSONDecodeError:
#             await ctx.respond(
#                 f"Failed to parse JSON for price data. Response snippet: {price_response.text[:200]}"
#             )
#             return

#         # Extract floor price from response
#         if asset_type == "rune":
#             if (
#                 "floorUnitPrice" not in price_data
#                 or "formatted" not in price_data["floorUnitPrice"]
#             ):
#                 await ctx.respond(f"No valid floor price data found for rune: {asset_slug}.")
#                 return
#             current_price_sats = float(price_data["floorUnitPrice"]["formatted"])
#         else:
#             if "floorPrice" not in price_data:
#                 await ctx.respond(f"No valid floor price data found for: {asset_slug}.")
#                 return
#             current_price_sats = float(price_data["floorPrice"])

#         current_price_btc = current_price_sats / 100_000_000

#         # ---------------------------------------------------------------------
#         # For each wallet, fetch transaction data and tally buys / sells / sends / receives
#         # ---------------------------------------------------------------------
#         for wallet in user_wallets:
#             wallet_address = wallet["address"]
#             url = (
#                 f"https://api-mainnet.magiceden.dev/v2/ord/btc/runes/wallet/activities/{wallet_address}?offset=0"
#             )

#             response = await client.get(url, headers=headers)
#             if response.status_code != 200:
#                 await ctx.respond("Failed to fetch asset data.")
#                 print("Transaction data error:", response.text)
#                 return

#             print("Transaction data response:", response.text[:500])
#             data = response.json()

#             # data is expected to be a list of items
#             for item in data:
#                 # Only consider this asset
#                 if item["rune"].upper() != asset_slug:
#                     continue

#                 transaction_kind = item["kind"]
#                 quantity = float(item.get("amount", 0))
#                 listed_price_sats = float(item.get("listedPrice", 0))

#                 # ------------------------------------------------------------
#                 # 1) BUY
#                 #    "buying_broadcasted" or "buy_broadcasted"
#                 #    newOwner must match the wallet address
#                 # ------------------------------------------------------------
#                 is_buy = (
#                     transaction_kind in ("buying_broadcasted", "buy_broadcasted")
#                     and item.get("newOwner") == wallet_address
#                     and listed_price_sats > 0
#                 )
#                 if is_buy:
#                     total_quantity_bought += quantity
#                     total_bought_btc += (listed_price_sats / 100_000_000)
#                     continue

#                 # ------------------------------------------------------------
#                 # 2) SELL
#                 #    "create_sell_order"
#                 #    oldOwner must match the wallet address
#                 # ------------------------------------------------------------
#                 is_sell = (
#                     transaction_kind == "create_sell_order"
#                     and item.get("oldOwner") == wallet_address
#                     and listed_price_sats > 0
#                 )
#                 if is_sell:
#                     total_quantity_sold += quantity
#                     total_sold_btc += (listed_price_sats / 100_000_000)
#                     continue

#                 # ------------------------------------------------------------
#                 # 3) SENT (transfer out, not a sale)
#                 #    "sent"
#                 #    oldOwner = wallet address
#                 #    => reduce holdings with no revenue
#                 # ------------------------------------------------------------
#                 is_sent = (
#                     transaction_kind == "sent"
#                     and item.get("oldOwner") == wallet_address
#                 )
#                 if is_sent:
#                     total_quantity_sold += quantity
#                     # No revenue => total_sold_btc unchanged
#                     continue

#                 # ------------------------------------------------------------
#                 # 4) (Optional) RECEIVED (transfer in, not a buy)
#                 #    "received"
#                 #    newOwner = wallet address
#                 #    => increase holdingswith zero cost
#                 # ------------------------------------------------------------
#                 is_received = (
#                     transaction_kind == "received"
#                     and item.get("newOwner") == wallet_address
#                 )
#                 if is_received:
#                     total_quantity_bought += quantity
#                     # No cost => total_bought_btc unchanged
#                     continue

#     # -------------------------------------------------------------------------
#     # Now calculate how many are still held and figure out realized/unrealized PnL
#     # -------------------------------------------------------------------------
#     # The quantity in the user's possession:
#     holding_quantity = total_quantity_bought - total_quantity_sold

#     # Market value (in BTC) of the remaining holdings:
#     holding_btc = holding_quantity * current_price_btc

#     # Market value (in USD) of the remaining holdings:
#     holding_usd = holding_btc * get_btc_price_usd()

#     # Avoid divide-by-zero if user never bought anything
#     total_bought_btc = max(total_bought_btc, 1e-8)

#     # If user never sold anything, entire PnL is unrealized
#     if total_quantity_sold == 0:
#         pnl_btc = holding_btc - total_bought_btc
#     else:
#         # If user somehow sold without buying, treat the entire holding as unrealized
#         if total_quantity_bought == 0:
#             realized_pnl_btc = 0
#             unrealized_pnl_btc = holding_btc
#         else:
#             # Realized PnL = what we got from sells - fraction of our total cost
#             # fraction = (total_quantity_sold / total_quantity_bought)
#             realized_pnl_btc = (
#                 total_sold_btc
#                 - (total_quantity_sold / total_quantity_bought * total_bought_btc)
#             )
#             # Unrealized PnL = value of holdings - fraction of total cost
#             # fraction = (holding_quantity / total_quantity_bought)
#             unrealized_pnl_btc = (
#                 holding_btc
#                 - (holding_quantity / total_quantity_bought * total_bought_btc)
#             )
#         pnl_btc = realized_pnl_btc + unrealized_pnl_btc

#     pnl_usd = pnl_btc * get_btc_price_usd()
#     pnl_percentage = (pnl_btc / total_bought_btc) * 100

#     # -------------------------------------------------------------------------
#     # Prepare text overlay
#     # -------------------------------------------------------------------------
#     text_keys = ["asset_name", "total_bought", "total_sold", "holdings", "pnl"]
#     text_values = [
#         f"{spaced_rune}" if asset_type == "rune" else asset_slug,
#         f"{total_bought_btc:.4f} (${total_bought_btc * get_btc_price_usd():.2f})",
#         f"{total_sold_btc:.4f} (${total_sold_btc * get_btc_price_usd():.2f})",
#         f"{holding_btc:.4f} (${holding_usd:.2f})",
#         f"{pnl_btc:.4f} (${pnl_usd:.2f}) ({pnl_percentage:.2f}%)",
#     ]

#     texts_with_coordinates = []
#     for i, text_key in enumerate(text_keys):
#         if i < len(text_coordinates):
#             coordinate = text_coordinates[i]
#             texts_with_coordinates.append({
#                 "text": text_values[i],
#                 "coordinates": tuple(coordinate["coordinates"]),
#                 "color": tuple(coordinate["color"]),
#                 "font_size": coordinate["font_size"],
#             })

#     output_path = f"./output/profit_overlay_{guild_id}.jpg"
#     os.makedirs(os.path.dirname(output_path), exist_ok=True)

#     await overlay_with_user_info(
#         image_path,
#         output_path,
#         texts_with_coordinates,
#         font_path,
#         username=str(ctx.author.name),
#         avatar_url=ctx.author.avatar.url,
#         avatar_coordinates=tuple(avatar_coordinates),
#         username_coordinates=tuple(username_coordinates),
#         avatar_size=tuple(avatar_size),
#     )

#     if os.path.exists(output_path):
#         with open(output_path, "rb") as file:
#             await ctx.respond(file=discord.File(file, os.path.basename(output_path)))
#         os.remove(output_path)
#     else:
#         await ctx.respond("Failed to generate the overlay image.")


@bot.command(
    name="profit",
    description="Calculate collective profits of everyone who took part in a trade",
)
async def profit(
    ctx: discord.ApplicationContext,
    asset_type: Option(str, "Select asset type", choices=["rune"]),  # type: ignore
    asset_slug: Option(
        str, "Enter the asset slug (rune name or ordinal collection symbol)"
    ),  # type: ignore
):
    """
    Slash command to calculate total PnL and holdings for a given asset.

    Key points:
      - We use `listedPrice` for the cost in sats (converted to BTC).
      - `amount` is the quantity of the asset.
      - We classify SELL if:
         * kind in ["buying_broadcasted", "buy_broadcasted", "sent"]  (example set)
         * oldOwner == wallet
         * newOwner != wallet
      - We classify BUY if:
         * kind in ["buying_broadcasted", "buy_broadcasted"]
         * newOwner == wallet
    """
    await ctx.defer()

    # Example token (remove/replace if not needed)
    headers = {
        "Accept": "application/json",
        "Authorization": "Bearer 4a02b503-2fdc-4cd3-a053-9d06e81f1c8e",
    }

    # If it's a rune, remove "•" and uppercase it (but keep a 'spaced_rune' for display).
    if asset_type == "rune":
        spaced_rune = asset_slug
        asset_slug = asset_slug.replace("•", "").upper()
    else:
        spaced_rune = asset_slug

    guild_id = str(ctx.guild.id)
    user_id = str(ctx.author.id)

    # Overlay config (update to match your environment)
    overlay = get_server_overlay(guild_id)
    image_path = overlay.get("image_path", "./blank.jpg")
    font_path = overlay.get("font_path", "./LoveYaLikeASister.ttf")
    text_coordinates = overlay.get("text_coordinates", [])
    avatar_coordinates = overlay.get("avatar_coordinates", [1200, 1870])
    username_coordinates = overlay.get("username_coordinates", [1300, 1880])
    avatar_size = overlay.get("avatar_size", [100, 100])

    # Check if the user has any wallets stored
    if (
        guild_id not in wallets
        or user_id not in wallets[guild_id]
        or not wallets[guild_id][user_id]
    ):
        await ctx.respond("You have not added any wallets to calculate profits.", ephemeral=True)
        return

    user_wallets = wallets[guild_id][user_id]

    # -------------------------------------------------------------------------
    # Initialize counters (for both quantity and price)
    # -------------------------------------------------------------------------
    total_bought_sats = 0
    total_sold_sats = 0
    total_quantity_bought = 0.0
    total_quantity_sold = 0.0

    # Optional: track how many times we buy or sell
    buy_transaction_count = 0
    sell_transaction_count = 0

    # Define which `kind` values qualify as "SELL" for your logic
    SELL_KINDS = ["buying_broadcasted", "buy_broadcasted"]
    BUY_KINDS = ["buying_broadcasted", "buy_broadcasted"]

    async with httpx.AsyncClient() as client:
        # 1) Fetch current floor price for the asset
        if asset_type == "rune":
            price_url = f"https://api-mainnet.magiceden.dev/v2/ord/btc/runes/market/{asset_slug}/info"
        else:
            price_url = f"https://api-mainnet.magiceden.dev/v2/ord/btc/stat?collectionSymbol={asset_slug}"

        price_response = await client.get(price_url, headers=headers)
        if price_response.status_code != 200:
            await ctx.respond(
                f"Failed to fetch current price data (status={price_response.status_code})."
            )
            return

        try:
            price_data = price_response.json()
        except json.decoder.JSONDecodeError:
            await ctx.respond(
                f"Failed to parse JSON for price data. Response snippet: {price_response.text[:200]}"
            )
            return

        # 2) Extract floor price in sats
        if asset_type == "rune":
            if (
                "floorUnitPrice" not in price_data
                or "formatted" not in price_data["floorUnitPrice"]
            ):
                await ctx.respond(f"No valid floor price data found for rune: {asset_slug}.")
                return
            current_price_sats = float(price_data["floorUnitPrice"]["formatted"])
        else:
            if "floorPrice" not in price_data:
                await ctx.respond(f"No valid floor price data found for: {asset_slug}.")
                return
            current_price_sats = float(price_data["floorPrice"])

        # Convert the floor price sats → BTC
        current_price_btc = current_price_sats / 1e8

        # ---------------------------------------------------------------------
        # For each wallet, gather transaction data
        # ---------------------------------------------------------------------
        for wallet in user_wallets:
            wallet_address = wallet["address"]
            tx_url = (
                f"https://api-mainnet.magiceden.dev/v2/ord/btc/runes/wallet/activities/{wallet_address}?offset=0"
            )

            tx_response = await client.get(tx_url, headers=headers)
            if tx_response.status_code != 200:
                await ctx.respond("Failed to fetch asset data.")
                return

            data = tx_response.json()
            if not isinstance(data, list):
                # We expect 'data' to be a list
                continue

            for item in data:
                # Must match the desired asset
                if item.get("rune", "").upper() != asset_slug:
                    continue

                transaction_kind = item.get("kind", "").lower()
                old_owner = item.get("oldOwner", "")
                new_owner = item.get("newOwner", "")

                # The quantity of the asset
                quantity = float(item.get("amount", 1.0))

                # The cost in sats: "listedPrice"
                price_sats = float(item.get("listedPrice", 0))
                if price_sats <= 0:
                    continue  # skip invalid price

                # ------------------------------------------------------------
                # BUY condition
                # ------------------------------------------------------------
                is_buy = (
                    transaction_kind in BUY_KINDS
                    and new_owner == wallet_address
                )
                if is_buy:
                    buy_transaction_count += 1
                    total_quantity_bought += quantity
                    total_bought_sats += price_sats
                    continue

                # ------------------------------------------------------------
                # SELL condition
                #   includes checking transaction_kind in SELL_KINDS
                #   oldOwner == wallet_address, newOwner != wallet_address
                # ------------------------------------------------------------
                is_sell = (
                    transaction_kind in SELL_KINDS
                    and old_owner == wallet_address
                    and new_owner != wallet_address
                )
                if is_sell:
                    sell_transaction_count += 1
                    total_quantity_sold += quantity
                    total_sold_sats += price_sats
                    continue

                # Otherwise ignore

    # -------------------------------------------------------------------------
    # Convert total sats → BTC
    # -------------------------------------------------------------------------
    total_bought_btc = total_bought_sats / 1e8
    total_sold_btc = total_sold_sats / 1e8

    # Calculate how many of the asset you hold
    holding_quantity = (total_quantity_bought - total_quantity_sold) / 100_000_000
    if holding_quantity < 0:
        holding_quantity = 0

    # Current holding value (in BTC and USD)
    holding_btc = holding_quantity * current_price_btc
    holding_usd = holding_btc * get_btc_price_usd()

    # -------------------------------------------------------------------------
    # PnL Calculations
    # -------------------------------------------------------------------------
    # Avoid dividing by zero
    total_bought_btc = max(total_bought_btc, 1e-12)

    if total_quantity_sold == 0:
        # Entire PnL is unrealized
        pnl_btc = holding_btc - total_bought_btc
    else:
        if total_quantity_bought == 0:
            # Edge case: sold something without buying
            realized_pnl_btc = 0.0
            unrealized_pnl_btc = holding_btc
        else:
            realized_pnl_btc = (
                total_sold_btc
                - (total_quantity_sold / total_quantity_bought * total_bought_btc)
            )
            unrealized_pnl_btc = (
                holding_btc
                - (holding_quantity / total_quantity_bought * total_bought_btc)
            )
        pnl_btc = realized_pnl_btc + unrealized_pnl_btc

    pnl_usd = pnl_btc * get_btc_price_usd()
    pnl_percentage = (pnl_btc / total_bought_btc) * 100

    # -------------------------------------------------------------------------
    # Prepare overlay text
    # -------------------------------------------------------------------------
    text_keys = ["asset_name", "total_bought", "total_sold", "holdings", "pnl"]
    text_values = [
        f"{spaced_rune}" if asset_type == "rune" else asset_slug,
        f"{total_bought_btc:.4f} (${total_bought_btc * get_btc_price_usd():.2f})",
        f"{total_sold_btc:.4f} (${total_sold_btc * get_btc_price_usd():.2f})",
        f"{holding_btc:.4f} (${holding_usd:.2f})",
        f"{pnl_btc:.4f} (${pnl_usd:.2f}) ({pnl_percentage:.2f}%)",
    ]

    texts_with_coordinates = []
    for i, text_key in enumerate(text_keys):
        if i < len(text_coordinates):
            coord_cfg = text_coordinates[i]
            texts_with_coordinates.append({
                "text": text_values[i],
                "coordinates": tuple(coord_cfg["coordinates"]),
                "color": tuple(coord_cfg["color"]),
                "font_size": coord_cfg["font_size"],
            })

    # Generate overlay
    output_path = f"./output/profit_overlay_{guild_id}.jpg"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    await overlay_with_user_info(
        image_path,
        output_path,
        texts_with_coordinates,
        font_path,
        username=str(ctx.author.name),
        avatar_url=(ctx.author.avatar.url if ctx.author.avatar else ""),
        avatar_coordinates=tuple(avatar_coordinates),
        username_coordinates=tuple(username_coordinates),
        avatar_size=tuple(avatar_size),
    )

    summary = (
        f"**Buy transactions:** {buy_transaction_count}\n"
        f"**Sell transactions:** {sell_transaction_count}\n"
    )
    await ctx.send(content=summary)

    # Send image
    if os.path.exists(output_path):
        with open(output_path, "rb") as file:
            await ctx.respond(file=discord.File(file, os.path.basename(output_path)))
        os.remove(output_path)
    else:
        await ctx.respond("Failed to generate the overlay image.")
        return

    # Finally, show buy/sell transaction counts (optional).

    

"""
USER WALLET LOGIC FOR PnL - END
"""


"""
RUNE TRACKING LOGIC - START
"""
def load_runes_data():
    """Load the runes data from a JSON file if it exists."""
    global data
    if os.path.exists("./data/runes_mint_data.json"):
        with open("./data/runes_mint_data.json", "r") as f:
            data = json.load(f)
    else:
        # Do not initialize any structure here to prevent auto-creation of the file
        data = {}

def save_data():
    # Only save guilds that have at least one tracking channel configured
    data_to_save = {guild_id: channels for guild_id, channels in data.items() if channels}
    with open("./data/data.json", "w") as f:
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
@allowed_server_only()
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


    embed = discord.Embed(
        title="Tracking Channel Set ✅",
        description=f"Runes mint tracking updates will now be sent to {channel.mention}",
        color= discord.Colour.green()
    )
    embed.set_footer(text="Powered by Brain Box Intel", icon_url="https://www.brainboxintel.xyz/static/assets/img/brainboxintel.jpg")

    
    await ctx.respond(
        embed=embed
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
                target_percentages = [30, 50, 80, 90]
                # print(rune_id)

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

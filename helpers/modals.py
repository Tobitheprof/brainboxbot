from discord.ui import Button, View, Modal, TextInput
from discord import Interaction
import discord


class AddWalletModal(Modal):
    def __init__(self, original_context: discord.ApplicationContext):
        super().__init__(title="Add Wallet Details")
        self.original_context = original_context

        # Modal fields
        self.name = TextInput(
            label="Wallet Name", placeholder="Enter the wallet's name", required=True
        )
        self.wallet_address = TextInput(
            label="Taproot Wallet Address",
            placeholder="Enter the wallet address",
            required=True,
        )
        self.track_mint = TextInput(
            label="Track Mints", placeholder="Enter 'True' or 'False'", required=True
        )
        self.track_buy = TextInput(
            label="Track Buys",
            placeholder="Enter 'true', 'false', or 'both'",
            required=True,
        )
        self.track_sell = TextInput(
            label="Track Sells",
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
        # Extract data from modal and pass to addwallet command
        name = self.name.value
        wallet_address = self.wallet_address.value
        track_mint = self.track_mint.value.lower() == "true"
        track_buy = self.track_buy.value
        track_sell = self.track_sell.value

        # Call addwallet command directly
        await addwallet(
            self.original_context,
            name,
            wallet_address,
            track_mint,
            track_buy,
            track_sell,
        )

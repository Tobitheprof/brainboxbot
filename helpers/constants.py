# All Endpoints for Rune specific operations
rune_endpoints = {
    "info": lambda rune_name: f"https://api-mainnet.magiceden.dev/v2/ord/btc/runes/market/{rune_name}/info",
    "1m_chart": lambda rune_name: f"https://stats-mainnet.magiceden.io/collection_stats/getCollectionTimeSeriesV2/{rune_name}?edge_cache=true&resolution=1h&numOfDays=30&chain=bitcoin&protocol=rune",
    "1w_chart": lambda rune_name: f"https://stats-mainnet.magiceden.io/collection_stats/getCollectionTimeSeriesV2/{rune_name}?edge_cache=true&resolution=30m&numOfDays=7&chain=bitcoin&protocol=rune",
    "1d_chart": lambda rune_name: f"https://stats-mainnet.magiceden.io/collection_stats/getCollectionTimeSeriesV2/{rune_name}?edge_cache=true&resolution=10m&numOfDays=1&chain=bitcoin&protocol=rune",
    "all_time": lambda rune_name: f"https://stats-mainnet.magiceden.io/collection_stats/getCollectionTimeSeriesV2/{rune_name}?edge_cache=true&resolution=1d&numOfDays=360&chain=bitcoin&protocol=rune",
}

# All Endpoints for Ord Specific Operations
ord_endpoints = {
    "info": lambda ord_name: f"https://api-mainnet.magiceden.dev/v2/ord/btc/stat?collectionSymbol={ord_name}",
    "1m_chart": lambda ord_name: f"https://stats-mainnet.magiceden.io/collection_stats/getCollectionTimeSeriesV2/{ord_name}?edge_cache=true&resolution=1h&numOfDays=30&chain=bitcoin",
    "1w_chart": lambda ord_name: f"https://stats-mainnet.magiceden.io/collection_stats/getCollectionTimeSeriesV2/{ord_name}?edge_cache=true&resolution=30m&numOfDays=7&chain=bitcoin",
    "1d_chart": lambda ord_name: f"https://stats-mainnet.magiceden.io/collection_stats/getCollectionTimeSeriesV2/{ord_name}?edge_cache=true&resolution=10m&numOfDays=1&chain=bitcoin",
    "all_time": lambda ord_name: f"https://stats-mainnet.magiceden.io/collection_stats/getCollectionTimeSeriesV2/{ord_name}?edge_cache=true&resolution=1d&numOfDays=360&chain=bitcoin",
    "misc": lambda ord_name: f"https://api-mainnet.magiceden.dev/v2/ord/btc/collections/{ord_name}",
}

# Wallet Tracker Endpoints
wallet_tracker_endpoints = {
    "history": lambda wallet_address: f"https://v2api.bestinslot.xyz/wallet/history?page=1&address={wallet_address}",  # inscriptions
    "history_brc": lambda wallet_address: f"https://v2api.bestinslot.xyz/wallet/history-brc20?page=1&address={wallet_address}",  # BRC20
    "history_rune": lambda wallet_address: f"https://v2api.bestinslot.xyz/rune/activity?page=1&address={wallet_address}&include_rune=true",  # history_rune
}

inscriptions = {
    "inscriptions": lambda wallet_address: f"https://v2api.bestinslot.xyz/wallet/history?page=1&address={wallet_address}&activity=1",
}

# Rune Mint Tracker

rune_mint_tracker_endpoints = {
    "hot_runes": "https://api-runes.satosea.xyz/api/v1/mempool/nextHot",
    "rune_details": lambda rune_id: f"https://api-runes.satosea.xyz/api/v1/rune/info/{rune_id}",
}

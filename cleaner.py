import json

input_file = "wallet_data.json"
output_file = "addresses_with_tags.txt"

with open(input_file, "r", encoding="utf-8") as file:
    data = json.load(file)


if "data" in data and "list" in data["data"]:
    blocks = data["data"]["list"]
elif "list" in data:
    blocks = data["list"]
else:
    raise KeyError("Could not find the 'list' key in the JSON structure.")

unique_addresses_with_tags = {}
for block in blocks:
    for item in block["list"]:
        address = item["address"]
        tags = item.get("tags", [])
        if address not in unique_addresses_with_tags:
            unique_addresses_with_tags[address] = set(tags) 
        else:
            unique_addresses_with_tags[address].update(tags)

with open(output_file, "w", encoding="utf-8") as file:
    for address, tags in unique_addresses_with_tags.items():
        file.write(f"{address}: {', '.join(tags)}\n")

print(f"Addresses with tags saved to '{output_file}'.")

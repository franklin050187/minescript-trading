import os
import json
import csv
from craft_calc import find_profitable_crafts
from arbiter import find_profitable_trades

uid_name = "xxx"  # placeholder, will be set to timestamp in test.py
order_filenmae = f"orders_raw_{uid_name}.csv"
order_path = os.path.join(
    r"C:\Users\User\AppData\Roaming\.minecraft\minescript", order_filenmae
)
# if file does not exist, find orders_raw_*.csv and use the most recent one
if not os.path.exists(order_path):
    files = [f for f in os.listdir(r"C:\Users\User\AppData\Roaming\.minecraft\minescript") if f.startswith("orders_raw_") and f.endswith(".csv")]
    if files:
        latest_file = max(files, key=lambda x: os.path.getctime(os.path.join(r"C:\Users\User\AppData\Roaming\.minecraft\minescript", x)))
        order_path = os.path.join(r"C:\Users\User\AppData\Roaming\.minecraft\minescript", latest_file)
        print(f"Using most recent orders file: {order_path}")
    else:
        print("No orders file found.")
ah_filename = f"ah_raw_{uid_name}.csv"
ah_path = os.path.join(
    r"C:\Users\User\AppData\Roaming\.minecraft\minescript", ah_filename
)
if not os.path.exists(ah_path):
    files = [f for f in os.listdir(r"C:\Users\User\AppData\Roaming\.minecraft\minescript") if f.startswith("ah_raw_") and f.endswith(".csv")]
    if files:
        latest_file = max(files, key=lambda x: os.path.getctime(os.path.join(r"C:\Users\User\AppData\Roaming\.minecraft\minescript", x)))
        ah_path = os.path.join(r"C:\Users\User\AppData\Roaming\.minecraft\minescript", latest_file)
        print(f"Using most recent AH file: {ah_path}")
    else:
        print("No AH file found.")
recipes_filename = "recipes.json"
recipes_path = os.path.join(
    r"C:\Users\User\AppData\Roaming\.minecraft\minescript", recipes_filename
)
ah_rows = csv.DictReader(open(ah_path, "r", encoding="utf-8"))
order_rows = csv.DictReader(open(order_path, "r", encoding="utf-8"))
recipes = json.load(open(recipes_path, "r", encoding="utf-8"))

# profit = find_profitable_crafts(recipes, ah_rows, order_rows)
profit = find_profitable_trades(ah_rows, order_rows)
for data in profit:
    # Find recipe that produces this item_id
    matching_recipe = None
    for recipe_name, recipe_data in recipes.items():
        if recipe_data.get("result", {}).get("id") == data["item_id"]:
            matching_recipe = recipe_data
            break

    blacklist_items = {
        "minecraft:netherite_sword",
        "minecraft:netherite_pickaxe",
        "minecraft:netherite_axe",
        "minecraft:netherite_shovel",
        "minecraft:netherite_hoe",
        "minecraft:netherite_boots",
        "minecraft:netherite_leggings",
        "minecraft:netherite_chestplate",
        "minecraft:netherite_helmet",
        "minecraft:tipped_arrow",
        "minecraft:diamond_horse_armor",
        "minecraft:splash_potion",
        "minecraft:filled_map",
        "minecraft:potion",
        "minecraft:glass",
    }

    recipe = matching_recipe
    if recipe is not None:
        if recipe["category"] in (
            "equipment",
        ) or not recipe:
            continue
    if data["item_id"] in blacklist_items:
        continue
    print(f"{data['item_id']} | profit={data['profit']:.2f} | buy={data['buy']:.2f} | sell={data['sell']:.2f} | ah qt: {data['quantity']} | ah total price: {data['total_price']}")
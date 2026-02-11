import time
import orders
from system.lib import minescript as m
from minescript_plus import Screen, Trading, Inventory
import os
import sys
import ast
import lib_nbt
import csv
from arbiter import find_profitable_trades
from buy_item import buy_item

sys.stdout.reconfigure(encoding="utf-8", errors="ignore")

DELAY = 0.1

# AH
def ensure_lowest_price():
    max_attempts = 5

    for attempt in range(max_attempts):
        try:
            items = m.container_get_items()
            cauldron = next((item for item in items if item.slot == 47), None)

            if not cauldron or not cauldron.nbt:
                m.echo("❌ Cauldron or NBT missing")
                return False

            # Sanitize NBT string (kills surrogates safely)
            nbt = cauldron.nbt.encode("utf-8", "ignore").decode("utf-8")

            # Split by lore entries
            lore_blocks = nbt.split("extra:")

            for block in lore_blocks:
                if "Lowest Price" in block and "#00FC88" in block:
                    # m.echo("✓ Lowest Price sort is already selected")
                    return True

            m.echo(
                f"Sorting not set to Lowest Price "
                f"(attempt {attempt + 1}/{max_attempts}), clicking slot 47"
            )

            Inventory.click_slot(47)
            time.sleep(0.8)

        except Exception as e:
            m.echo(f"⚠ Error checking sort: {e}")
            if attempt < max_attempts - 1:
                time.sleep(0.5)
            else:
                return False

    m.echo("✗ Failed to ensure Lowest Price sort")
    return False

# AH
def init_search_all_ah(item_name):
    try:
        m.execute(f"/ah {item_name}")
        time.sleep(1)  # Wait for the Orders screen to load

        current_screen = m.screen_name()
        if "Page" not in current_screen:
            # m.echo(f"AH screen not loaded properly. Screen: {current_screen}")
            return []
        if not ensure_lowest_price():
            m.echo("Warning: Could not confirm Lowest Price sort is selected")
        Inventory.click_slot(49) # refresh page to ensure NBT is loaded
        time.sleep(0.5)
    except Exception as e:
        m.echo(f"Error initializing AH search: {e}")
        return []

# parse data 
def parse_itemstack_nbt(itemstack_str: str) -> dict:
    try:
        snbt = extract_nbt_string(itemstack_str)
        return lib_nbt.parse_snbt(snbt)
    except Exception as e:
        # m.echo(f"Error parsing ItemStack NBT: {e}")
        return {}

def extract_nbt_string(itemstack_str: str) -> str:
    """
    Extracts the raw SNBT string from ItemStack(..., nbt='...', ...)
    """
    try:
        tree = ast.parse(itemstack_str, mode="eval")
        call = tree.body  # ItemStack(...)

        for kw in call.keywords:
            if kw.arg == "nbt":
                return ast.literal_eval(kw.value)

        raise ValueError("nbt field not found")
    except Exception as e:
        # m.echo(f"Error extracting NBT string: {e}")
        return ""

def flatten_lore_line(line) -> str:
    try:
        if isinstance(line, str):
            return line
        if isinstance(line, dict) and "extra" in line:
            return "".join(part.get("text", "") for part in line["extra"])
        return ""
    except Exception as e:
        # m.echo(f"Error flattening lore line: {e}")
        return ""

def extract_ah_info_from_item(item):
    try:
        if not is_valid_order(item):
            return None

        if item.slot >= 45:
            return None

        nbt = lib_nbt.parse_snbt(item.nbt)

        lore = nbt["components"].get("minecraft:lore", [])

        def flatten(line):
            if isinstance(line, str):
                return line
            if isinstance(line, dict) and "extra" in line:
                return "".join(p.get("text", "") for p in line["extra"])
            return ""

        lines = [flatten(l) for l in lore if l]

        price = extract_price_from_lore(lines)
        quantity = nbt.get("count", 1)

        # -------------------------------------------------
        # CASE 1: Normal item
        # -------------------------------------------------
        if "shulker_box" not in nbt["id"]:
            return {
                "slot": item.slot,
                "item_id": nbt["id"],
                "price_total": price,
                "quantity": quantity,
                "price_per": price / quantity if quantity > 0 else price
            }

        # -------------------------------------------------
        # CASE 2: Shulker box
        # -------------------------------------------------
        container_items = nbt["components"].get("minecraft:container", [])

        if not container_items:
            return None

        # collect unique item ids
        unique_ids = set()
        total_quantity = 0

        for entry in container_items:
            inner_item = entry.get("item", {})
            inner_id = inner_item.get("id")
            inner_count = inner_item.get("count", 1)

            if not inner_id:
                continue

            unique_ids.add(inner_id)
            total_quantity += inner_count

        # if more than one item type → drop
        if len(unique_ids) != 1:
            return None

        # single item type → aggregate
        single_item_id = unique_ids.pop()

        return {
            "slot": item.slot,
            "item_id": single_item_id,
            "price_total": price,
            "quantity": total_quantity,
            "price_per": price / total_quantity if total_quantity > 0 else price
        }

    except Exception:
        return None

def extract_price_from_lore(lines: list[str]) -> int:
    for line in lines:
        if line.startswith("Price:"):
            value = line.replace("Price:", "").replace("$", "").strip()
            return parse_compact_number(value)

    raise ValueError("Price line not found")

def parse_compact_number(s: str) -> int:
    s = s.strip().lower()

    if s.endswith("k"):
        return int(float(s[:-1]) * 1_000)
    if s.endswith("m"):
        return int(float(s[:-1]) * 1_000_000)
    if s.endswith("b"):
        return int(float(s[:-1]) * 1_000_000_000)

    return int(float(s))

def is_valid_order(item):
    return (
        item is not None
        and item.nbt
        and item.item != "minecraft:air"
    )



def search_all_ah(max_pages=100, uid_name="fast"):
    order_filenmae = f"orders_raw_{uid_name}.csv"
    order_path = os.path.join(
        r"C:\Users\User\AppData\Roaming\.minecraft\minescript", order_filenmae
    )

    if not os.path.exists(order_path):
        files = [f for f in os.listdir(r"C:\Users\User\AppData\Roaming\.minecraft\minescript") if f.startswith("orders_raw_") and f.endswith(".csv")]
        if files:
            latest_file = max(files, key=lambda x: os.path.getctime(os.path.join(r"C:\Users\User\AppData\Roaming\.minecraft\minescript", x)))
            order_path = os.path.join(r"C:\Users\User\AppData\Roaming\.minecraft\minescript", latest_file)
            # print(f"Using most recent orders file: {order_path}")
        else:
            print("No orders file found.")

    watchlist_filename = "watch.csv"
    watch_path = os.path.join(
        r"C:\Users\User\AppData\Roaming\.minecraft\minescript", watchlist_filename
    )
    

    # order_rows = csv.DictReader(open(order_path, "r", encoding="utf-8"))
    watch_rows = csv.DictReader(open(watch_path, "r", encoding="utf-8")) if os.path.exists(watch_path) else []
    all_items = []
    page = 0
    retry_attempts = 0
    max_retries = 1
    while page <= max_pages:
        # m.echo(f"Page {page + 1} loaded")
        items = m.container_get_items()
        if not items:
            # m.echo(f"⚠ No items found on page {page + 1}, retrying... (attempt {retry_attempts + 1}/{max_retries})")
            if retry_attempts < max_retries - 1:
                time.sleep(DELAY)  # exponential backoff
                retry_attempts += 1
                continue
            else:
                m.echo("✗ Failed to load items after multiple attempts, stopping.")
                break
        page_items = [i for i in items if i and i.nbt and i.slot < 47]
        all_items.extend(page_items)
        for order in page_items:
            # m.echo(f"Processing slot {order.slot}...")
            data = extract_ah_info_from_item(order)
            # m.echo(f"Extracted data from slot {order.slot}: {data}")
            if data:
                # result = find_profitable_trades([data], order_rows=order_rows)  # pass the data to
                result = find_profitable_trades([data], order_rows=watch_rows)  # pass the data to
                if result:
                    m.echo(f"!!!!!!!!!!!!!!! PROFITABLE TRADE FOUND for slot {order.slot} !!!!!!!!!!!!!!!")
                    m.echo([result])
                    # m.echo([result])
                    # m.echo([result])
                    m.echo(f"!!!!!!!!!!!!!!! PROFITABLE TRADE FOUND for slot {order.slot} !!!!!!!!!!!!!!!")
                    # time.sleep(500)
                    buy_order = buy_item(order.slot)
                    # m.echo(f"Buy order result for slot {order.slot}: {buy_order}")
                    if buy_order:
                        m.echo(f"Successfully bought item from slot {order.slot}")
                        # log bough item
                        log_buy = f"log_buy.csv"
                        log_path = os.path.join(
                            r"C:\Users\User\AppData\Roaming\.minecraft\minescript", log_buy
                        )
                        timestamp = int(time.time())
                        # display as YYYY-MM-DD:HH:MM:SS
                        time_of_action = time.strftime("%Y-%m-%d:%H:%M:%S", time.localtime(timestamp))
                        with open(log_path, "a", newline="", encoding="utf-8") as f:
                            writer = csv.writer(f)
                            writer.writerow([order.slot, data["item_id"], data["price_total"], data["quantity"], time_of_action])
                    else:
                        m.echo(f"Failed to buy item from slot {order.slot}")
                    # break  # only buy one item for testing

        # if page >= max_pages:
        #     m.echo("Reached max_pages limit, stopping.")
        #     retry_attempts = 0
        #     break

        arrow = next((i for i in items if i.slot == 53 and i.nbt), None)
        if not arrow:

            if retry_attempts < max_retries:
                # m.echo(f"⚠ No next page arrow found, retrying... (attempt {retry_attempts + 1}/{max_retries})")
                Inventory.click_slot(49) # refresh page to try to load NBT
                retry_attempts += 1
                time.sleep(DELAY)  # exponential backoff

                continue
            # m.echo("No next page arrow found, reached end of orders.")
            break
        retry_attempts = 0



        Inventory.click_slot(53) # click next page
        time.sleep(DELAY)

        page += 1

    return all_items

def save_ah_to_csv(orders, save_path):
    fieldnames = [
            "slot",
            "item_id",
            "price_total",
            "quantity",
            "price_per",
    ]

    try:
        with open(save_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for order in orders:
                writer.writerow(order)

        # m.echo(f"Saved CSV order data to {save_path}")

    except Exception as e:
        m.echo(f"Error writing CSV: {e}")

# var
file_name = f"ah_raw_{int(time.time())}.csv"
save_path = os.path.join(
    r"C:\Users\User\AppData\Roaming\.minecraft\minescript", file_name
)

def get_ah_data(uid_name="fast", max_pages=1000, item_search=" "):
    # main
    file_name = f"ah_raw_{uid_name}.csv"
    save_path = os.path.join(
        r"C:\Users\User\AppData\Roaming\.minecraft\minescript", file_name
    )
    # m.echo("Initializing AH search...")
    init_search_all_ah(item_search)
    # m.echo("Extracting AH data...")
    orders = search_all_ah(max_pages=max_pages, uid_name=uid_name)
    m.echo(f"Processing {len(orders)} AH entries...")
    data_list = []

    for order in orders:
        data = extract_ah_info_from_item(order)
        if data:
            data_list.append(data)

    # m.echo(f"Saving AH data to {save_path}...")
    # save_ah_to_csv(data_list, save_path)
    # m.echo(f"Saved raw AH data to {save_path}")
    Screen.close_screen()

import time
from system.lib import minescript as m
from minescript_plus import Screen, Trading, Inventory
import os
import sys
import ast
import lib_nbt
import csv

sys.stdout.reconfigure(encoding="utf-8", errors="ignore")


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
                    m.echo("✓ Lowest Price sort is already selected")
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
            m.echo(f"AH screen not loaded properly. Screen: {current_screen}")
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
        m.echo(f"Error parsing ItemStack NBT: {e}")
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
        m.echo(f"Error extracting NBT string: {e}")
        return ""

def flatten_lore_line(line) -> str:
    try:
        if isinstance(line, str):
            return line
        if isinstance(line, dict) and "extra" in line:
            return "".join(part.get("text", "") for part in line["extra"])
        return ""
    except Exception as e:
        m.echo(f"Error flattening lore line: {e}")
        return ""

def extract_ah_info_from_item(item) -> dict:
    try:
        if not is_valid_order(item):
            return None

        nbt = lib_nbt.parse_snbt(item.nbt)

        lore = nbt["components"]["minecraft:lore"]

        def flatten(line):
            if isinstance(line, str):
                return line
            if isinstance(line, dict) and "extra" in line:
                return "".join(p.get("text", "") for p in line["extra"])
            return ""

        lines = [flatten(l) for l in lore if l]

        # ignore slot 45 and above since they are not orders
        if item.slot >= 45:
            return None
        
        # parse remaining quantity
        price = extract_price_from_lore(lines)
        quantity = nbt.get("count", 1)

        return {
            "slot": item.slot,
            "item_id": nbt["id"],
            "price_total": price,
            "quantity": quantity,
            "price_per": price / quantity if quantity > 0 else price
        }

    except Exception as e:
        m.echo(f"Parse error slot {item.slot}: {e}")
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

def search_all_ah(max_pages=100):
    all_items = []
    page = 0
    retry_attempts = 0
    max_retries = 3
    while page < max_pages:
        m.echo(f"Page {page + 1} loaded")
        # time.sleep(0.1) # wait for refresh
        items = m.container_get_items()
        page_items = [i for i in items if i and i.nbt and i.slot < 47]
        all_items.extend(page_items)

        arrow = next((i for i in items if i.slot == 53 and i.nbt), None)
        if not arrow:
            if retry_attempts < max_retries:
                m.echo(f"⚠ No next page arrow found, retrying... (attempt {retry_attempts + 1}/{max_retries})")
                Inventory.click_slot(49) # refresh page to try to load NBT
                time.sleep(0.1)
                retry_attempts += 1
                continue
            m.echo("No next page arrow found, reached end of orders.")
            break
        retry_attempts = 0

        Inventory.click_slot(53) # click next page
        time.sleep(0.1)
        # Inventory.click_slot(49) # refresh page to ensure NBT is loaded
        # time.sleep(0.1)
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

        m.echo(f"Saved CSV order data to {save_path}")

    except Exception as e:
        m.echo(f"Error writing CSV: {e}")

# var
file_name = f"ah_raw_{int(time.time())}.csv"
save_path = os.path.join(
    r"C:\Users\User\AppData\Roaming\.minecraft\minescript", file_name
)


def get_ah_data_ok(uid_name=None, max_pages=1000, item_search=" "):
    # main
    file_name = f"ah_raw_{uid_name}.csv"
    save_path = os.path.join(
        r"C:\Users\User\AppData\Roaming\.minecraft\minescript", file_name
    )
    m.echo("Initializing AH search...")
    init_search_all_ah(item_search)
    m.echo("Extracting AH data...")
    orders = search_all_ah(max_pages=max_pages)
    m.echo(f"Processing {len(orders)} AH entries...")
    data_list = []

    for order in orders:
        data = extract_ah_info_from_item(order)
        if data:
            data_list.append(data)

    m.echo(f"Saving AH data to {save_path}...")
    save_ah_to_csv(data_list, save_path)
    m.echo(f"Saved raw AH data to {save_path}")
    Screen.close_screen()

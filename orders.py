import time
from system.lib import minescript as m
from minescript_plus import Screen, Inventory
import os
import sys
import lib_nbt
import csv

sys.stdout.reconfigure(encoding="utf-8", errors="ignore")

DELAY = 0.1

def ensure_most_paid_sort():
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
                if "Most Money" in block and "#00FC88" in block:
                    m.echo("✓ Most Paid sort is already selected")
                    return True

            m.echo(
                f"Sorting not set to Most Paid "
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

    m.echo("✗ Failed to ensure Most Paid sort")
    return False

def init_search_all_orders(item_name):
    try:
        m.execute(f"/orders {item_name}")
        time.sleep(1)  # Wait for the Orders screen to load

        current_screen = m.screen_name()
        if "Page" not in current_screen:
            m.echo(f"Orders screen not loaded properly. Screen: {current_screen}")
            return []
        if not ensure_most_paid_sort():
            m.echo("Warning: Could not confirm Most Paid sort is selected")
        Inventory.click_slot(49) # refresh page to ensure NBT is loaded
        time.sleep(0.5)
    except Exception as e:
        m.echo(f"Error initializing Orders search: {e}")
        return []

def extract_order_info_from_item(item, page) -> dict:
    try:
        if not is_valid_order(item):
            file_name = f"debug_orders.txt"
            save_path = os.path.join(
                r"C:\Users\User\AppData\Roaming\.minecraft\minescript", file_name
            )
            with open(save_path, "a", encoding="utf-8") as f:
                f.write(f"Invalid item: {item}\n")
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

        if len(lines) < 6:
            return None  # not a real order

        # ignore slot 45 and above since they are not orders
        if item.slot >= 45:
            return None
        
        # parse remaining quantity
        qty = parse_delivered_line(lines[2])
        price = parse_price_line(lines[1])

        return {
            "slot": item.slot,
            "item_id": nbt["id"],
            "price_each": price,
            "quantity": qty["remaining"],
            "page": page,
        }

    except Exception as e:
        return None

def parse_price_line(line: str) -> int:
    nosign = line.replace("$", "").strip()
    clean = nosign.replace("each", "").strip()
    price = parse_compact_number(clean)
    return price

def parse_delivered_line(line: str) -> dict:
    """
    Input: '7.91K/10K Delivered'
    Output: delivered, total, remaining
    """
    clean = line.replace("Delivered", "").strip()

    delivered_str, total_str = clean.split("/", 1)

    delivered = parse_compact_number(delivered_str)
    total = parse_compact_number(total_str)

    remaining = max(total - delivered, 0)

    return {
        "delivered": delivered,
        "total": total,
        "remaining": remaining,
    }

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

def page_signature_from_container(items):
    sig = set()

    for item in items:
        if not item or not hasattr(item, "slot"):
            continue

        # Only order slots
        if item.slot >= 45:
            continue

        sig.add((
            item.slot,
            item.item,          # minecraft:elytra
            item.count
        ))

    return sig

def search_all_orders(max_pages=100):
    all_items = []
    page = 0

    state = "LOAD_PAGE"
    retry_attempts = 0
    max_retries = 5
    min_price_threshold = 100  # stops if price is too low, to avoid stalling on junk pages
    last_signature = None
    current_page_items = []

    while state != "END":
        # m.echo(f"Current state: {state}, page: {page + 1}, total items: {len(all_items)}")
        # ---------------- LOAD PAGE ----------------
        if state == "LOAD_PAGE":
            m.echo(f"Loading page {page + 1}")
            time.sleep(DELAY)
            items = m.container_get_items()

            if not items:
                state = "RETRY"
                continue

            state = "PARSE_PAGE"

        # ---------------- PARSE PAGE ----------------
        elif state == "PARSE_PAGE":
            current_page_items = []
            stop_due_to_price = False

            for item in items:
                if not item or not hasattr(item, "slot"):
                    continue

                if item.slot < 45:
                    data = extract_order_info_from_item(item, page)
                    if not data:
                        continue

                    price = data.get("price_each")
                    if price is not None and price < min_price_threshold:
                        m.echo(
                            f"Low price detected ({price}) on item {data.get('item_id')} "
                            f"→ stopping pagination"
                        )
                        stop_due_to_price = True
                        break

                    current_page_items.append(data)

            if not current_page_items:
                state = "RETRY"
                continue
            
            if stop_due_to_price:
                state = "END"
                continue
            
            signature = page_signature_from_container(items)
            # Detect page stall
            if signature == last_signature:
                m.echo("Page signature unchanged → possible stall")
                state = "RETRY"
                continue

            # Valid new page
            all_items.extend(current_page_items)
            last_signature = signature
            retry_attempts = 0

            state = "NEXT_PAGE"

        # ---------------- NEXT PAGE ----------------
        elif state == "NEXT_PAGE":
            arrow = next(
                (i for i in items if i and hasattr(i, "slot") and i.slot == 53),
                None
            )

            if not arrow:
                m.echo("No next page arrow → end of orders")
                state = "END"
                continue

            if page + 1 >= max_pages:
                m.echo("Max page limit reached")
                state = "END"
                continue

            Inventory.click_slot(53)
            page += 1
            state = "LOAD_PAGE"

        # ---------------- RETRY ----------------
        elif state == "RETRY":
            retry_attempts += 1

            if retry_attempts > max_retries:
                m.echo("Max retries reached → stopping")
                state = "END"
                continue

            m.echo(f"Retrying page {page + 1} (attempt {retry_attempts}/{max_retries})")
            Inventory.click_slot(49)  # refresh
            time.sleep(DELAY * retry_attempts)

            state = "LOAD_PAGE"

    return all_items

def save_orders_to_csv(orders, save_path):
    fieldnames = [
        "slot",
        "item_id",
        "price_each",
        "quantity",
        "page",
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

def get_orders(uid_name=None, max_pages=1000, item_search=" "):
    # main
    file_name = f"orders_raw_{uid_name}.csv"
    save_path = os.path.join(
        r"C:\Users\User\AppData\Roaming\.minecraft\minescript", file_name
    )
    m.echo("Initializing Orders search...")
    init_search_all_orders(item_search)
    m.echo("Extracting order data...")
    orders = search_all_orders(max_pages=max_pages)
    m.echo(f"Processing {len(orders)} orders...")
    data_list = []
    for order in orders:
        # data = extract_order_info_from_item(order)
        if order:
            data_list.append(order)
    m.echo(f"Saving order data to {save_path}...")
    save_orders_to_csv(data_list, save_path)
    m.echo(f"Saved raw order data to {save_path}")
    Screen.close_screen()

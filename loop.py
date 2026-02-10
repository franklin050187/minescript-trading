import time
from orders import get_orders
from ah import get_ah_data_ok
# from craft_calc import find_profitable_crafts
# import json
import csv
from system.lib import minescript as m
import os
from ah_fly import get_ah_data
i = 0

while i < 50:  # Run 10 iterations for testing
    m.echo(f"--- Iteration {i + 1} ---")
    timeuid = int(time.time())
    uid_name = timeuid
    # uid_name = "260209"
    max_pages = 1000
    order_filenmae = f"orders_raw_{uid_name}.csv"
    order_path = os.path.join(
        r"C:\Users\User\AppData\Roaming\.minecraft\minescript", order_filenmae
    )

    ah_filename = f"ah_raw_{uid_name}.csv"
    ah_path = os.path.join(
        r"C:\Users\User\AppData\Roaming\.minecraft\minescript", ah_filename
    )
    recipes_filename = "recipes.json"
    recipes_path = os.path.join(
        r"C:\Users\User\AppData\Roaming\.minecraft\minescript", recipes_filename
    )

    

    watchlist_filename = "watch.csv"
    watch_path = os.path.join(
        r"C:\Users\User\AppData\Roaming\.minecraft\minescript", watchlist_filename
    )
    watch_rows = csv.DictReader(open(watch_path, "r", encoding="utf-8")) if os.path.exists(watch_path) else []

    for item in watch_rows:
        max_pages = 10  # only fetch the first page for watchlist items
        m.echo(f"Watching item: {item['item_id']} with price {item['price_each']}")
        item_search = item['item_id'].replace("minecraft:", "")
        get_ah_data(uid_name=uid_name, max_pages=max_pages, item_search=item_search)

    max_pages = 500
    item_search = " "
    m.echo("Fetching orders...")
    get_orders(uid_name=uid_name, max_pages=max_pages, item_search=item_search)
    m.echo("Fetching AH data...")
    get_ah_data_ok(uid_name=uid_name, max_pages=max_pages, item_search=item_search)
    i += 1
    # jump
    m.press_key_bind("key.jump", True)
    time.sleep(0.1)
    m.press_key_bind("key.jump", False)

m.echo("Finished all iterations.")
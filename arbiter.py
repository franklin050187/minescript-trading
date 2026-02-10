from collections import Counter, defaultdict

def build_ah_price_map(ah_rows):
    ah_price = {}
    for r in ah_rows:
        item = r["item_id"]
        price = float(r["price_per"])
        qt = int(r["quantity"])
        total_price = int(r["price_total"])
        if item not in ah_price or price < ah_price[item]["price_per"]:
            ah_price[item] = {"price_per": price, "quantity": qt, "total_price": total_price}

    return ah_price

def build_sell_price_map(order_rows):
    sell_price = {}
    for r in order_rows:
        item = r["item_id"]
        price = float(r["price_each"])
        if item not in sell_price or price > sell_price[item]:
            sell_price[item] = price
    return sell_price

def find_profitable_trades(ah_rows, order_rows):
    ah_price = build_ah_price_map(ah_rows)
    sell_price = build_sell_price_map(order_rows)
    trades = []
    for item_id, sell in sell_price.items():
        if item_id not in ah_price:
            continue
        buy = ah_price[item_id]["price_per"]
        if buy < sell:
            profit = sell - buy
            
            trades.append({
                "item_id": item_id,
                "buy": buy,
                "sell": sell,
                "profit": profit,
                "quantity": ah_price[item_id]["quantity"],
                "total_price": ah_price[item_id]["total_price"]
            })
    
    trades.sort(key=lambda x: x["profit"], reverse=True)
    return trades

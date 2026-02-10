# minescript-trading

Usage : 
Run \loop to scan watchlist items, buy under set price and then scan orders and ah to export data to csv.

# orders.py
scan orders and export to csv, browse N page or until price per item is below 100
can be set to scan a specific item

# ah.py
scan ah and export to csv, browse N page
can be set to scan a specific item

# ah_fly.py
scan ah and buy item from watch list when price in watchlist is good on the fly
can be set to scan a specific item

# checker.py
Compares orders and ah file to find quick profit.
Warning : some ah item might have been sold, some orders listing might have expired, always double check !

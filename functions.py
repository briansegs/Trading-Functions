import ccxt
import json
import pandas as pd
import config as c
from datetime import date, datetime, timezone, tzinfo
import time, schedule

kucoin = ccxt.kucoin({
    'enableRateLimit': True,
    'apiKey': c.API_KEY,
    'secret': c.API_SECRET,
})

# Params:
symbol = 'BTC-USDT'
pos_size = 100 # 125, 75,
params = {'timeInForce': 'PostOnly'}
target = 35
max_loss = -55
vol_decimal = .4

# Ask and bid:
def ask_bid(symbol=symbol):
    ob = kucoin.fetch_order_book(symbol)
    #print(ob)

    bid = ob['bids'][0][0]
    ask = ob['asks'][0][0]

    print(f'This is the ask for {symbol}: {ask}')

    return ask, bid # ask_bid()[0] = ask, [1] = bid

#ask_bid()
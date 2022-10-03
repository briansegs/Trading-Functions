from operator import index
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
    'password': c.API_PASSPHRASE,
})

# Params:
symbol = 'BTC-USDT'
pos_size = 100 # 125, 75,
params = {'timeInForce': 'PostOnly'}
target = 35
max_loss = -55
vol_decimal = .4

# For dataframe:
timeframe = '4h'
limit = 100
sma = 20

index_pos = 1

# Time between trades
pause_time = 60


# ask_bid()[0] = ask, [1] = bid
# ask_bid(symbol) if none given, uses defaults
def ask_bid(symbol=symbol):
    ob = kucoin.fetch_order_book(symbol)

    bid = ob['bids'][0][0]
    ask = ob['asks'][0][0]

    print(f'This is the ask for {symbol}: {ask}')

    return ask, bid
# 6:16
# df_sma(symbol, timeframe, limit, sma): # if not passed, uses defaults
# Returns: dataframe(df_sma) with sma and trade signal
def df_sma(symbol=symbol, timeframe=timeframe, limit=limit, sma=sma):
    print('starting...')
    bars = kucoin.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)

    df_sma = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df_sma['timestamp'] = pd.to_datetime(df_sma['timestamp'], unit='ms')

    #Dataframe SMA
    df_sma[f'sma{sma}_{timeframe}'] = df_sma.close.rolling(sma).mean()

    bid = ask_bid(symbol)[1]
    # if bid < the sma then = BEARISH, if bid > sma = BULLISH
    # if sma > bid = SELL, if  sma < bid = BUY
    df_sma.loc[df_sma[f'sma{sma}_{timeframe}']>bid, 'signal'] = 'SELL'
    df_sma.loc[df_sma[f'sma{sma}_{timeframe}']<bid, 'signal'] = 'BUY'

    print(df_sma)
    return df_sma

# 25:00
# Notes:
#   - Doesn't work for ccxt.kucoin
#   - Might work for ccxt.kucoinfutures
#   - Needs work...
# TODO: Test with ccxt.kucoinfutures
# TODO: make a function that loops through dictionary and assigns index to symbol
# open_positions(open_positions, openpos_bool, openpos_size, long):
def open_positions(symbol=symbol):

    # what is the position index for that symbol?
    # 43:00
    if symbol == 'uBTCUSD':
        index_pos = 3
    elif symbol == 'APEUSD':
        index_pos = 1
    elif symbol == 'ETHUSD':
        index_pos = 2
    elif symbol == 'DOGEUSD':
        index_pos = 0
    else:
        index_pos = None

    params = {'type':'swap', 'code':'USD'}
    phe_bal = kucoin.fetch_balance(params=params)
    open_positions = phe_bal['info']['data']['positions']
    #print(open_positions)

    openpos_side = open_positions[index_pos]['side'] # btc [3] [0] = doge, [1] ape
    openpos_size = open_positions[index_pos]['size']
    #print(open_positions)

    if openpos_side == ('Buy'):
        openpos_bool = True
        long = True
    elif openpos_side == ('Sell'):
        openpos_bool = True
        long = False
    else:
        openpos_bool = False
        long = None

    print(f'open_positions... | openpos_bool: {openpos_bool} | openpos_size: {openpos_size} | long: {long}')

    return open_positions, openpos_bool, openpos_size, long

# 36:00
# Notes:
#   - kill_switch() needs open_positions() to work correctly
# kill_switch: pass in (symbol) if no symbol uses default
def kill_switch(symbol=symbol):
    print(f'starting the kill switch for {symbol}')
    openposi = open_positions(symbol)[1] # true or false
    long = open_positions(symbol)[3]# true or false
    kill_size = open_positions(symbol)[2]# size of open position

    print(f'openposi {openposi}, long {long}, size {kill_size}')

    while openposi == True:
        print('starting kill switch loop til limit fil..')
        temp_df = pd.DataFrame()
        print('just made a temp df')

        #kucoin.cancel_all_orders(symbol)
        openposi = open_positions(symbol)[1]
        long = open_positions(symbol)[3]# true or false
        kill_size = open_positions(symbol)[2]
        kill_size = int(kill_size)

        ask = ask_bid(symbol)[0]
        bid = ask_bid(symbol)[1]

        if long == False:
            #kucoin.create_limit_buy_order(symbol, kill_size, bid, params)
            print(f'just made a BUY to CLOSE order of {kill_size} {symbol} at ${bid}')
            print(f'sleeping for 30 seconds to see of it fills..')
            time.sleep(30)
        elif long == True:
            #kucoin.create_limit_sell_order(symbol, kill_size, ask, params)
            print(f'just made a SELL to CLOSE order of {kill_size} {symbol} at ${ask}')
            print('sleeping for 30 seconds to see of it fills..')
            time.sleep(30)
        else:
            print('++++++ SOMETHING I DIDNT EXPECT IN KILL SWITCH FUNCTION')

        openposi = open_positions(symbol)[1]

# 50:00
# sleep_on_close:
#   - pulls closed orders
#   - if last close was in last 59min then sleep for 1min
#   - sincelasttrade = minutes since last trade
#   - puase in mins
def sleep_on_close(symbol=symbol, pause_time=pause_time):
    closed_orders = kucoin.fetch_closed_orders(symbol)
    #print(closed_orders)

    for ord in closed_orders[-1::-1]:
        sincelasttrade = pause_time - 1 # how long we pause

        filled = False

        status = ord['info']['ordStatus']
        txttime = ord['info']['transactTimes']
        txttime = int(txttime)
        txttime = round((txttime/1000000000)) # bc in nanoseconds
        print(f'for {symbol} this is the status of the order {status} with epoch {txttime}')
        print('next iteration...')
        print('--------')

        if status == 'Filled':
            print('FOUND the order with last fill..')
            print(f'for {symbol} this is the time {txttime} this is the orderstatus {status}')
            orderbook = kucoin.fetch_order_book(symbol)
            ex_timestamp = orderbook['timestamp'] # in ms
            ex_timestamp = int(ex_timestamp/1000)
            print('---- below is the transaction time then exchange epoch time')
            print(txttime)
            print(ex_timestamp)

            time_spread = (ex_timestamp - txttime)/60

            if time_spread < sincelasttrade:
                #print('time since last trade is less than time spread')
                ##if in posis true, put a close order here
                #if in_pos == True:
                sleepy = round(sincelasttrade-time_spread)*60
                sleepy_min = sleepy/60

                print(f'the time spread is less than {sincelasttrade} mins its been {time_spread}mins.. so we SlEEP')
                time.sleep(60)

            else:
                print(f'its been {time_spread} mins since last fill so not sleeping cuz since last trade is {sincelasttrade}')
            break
        else:
            continue

    print(f'done with the sleep on close function for {symbol}..')
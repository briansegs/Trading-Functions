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

# For dataframe:
timeframe = '4h'
limit = 100
sma = 20


# ask_bid()[0] = ask, [1] = bid
# ask_bid(symbol) if none given, uses defaults
def ask_bid(symbol=symbol):
    ob = kucoin.fetch_order_book(symbol)

    bid = ob['bids'][0][0]
    ask = ob['asks'][0][0]

    print(f'This is the ask for {symbol}: {ask}')

    return ask, bid

# Dataframe SMA: 6:16
# Returns: dataframe(df_sma) with sma and trade signal
# Call: df_sma(symbol, timeframe, limit, sma) # if not passed, uses defaults
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

#23:30
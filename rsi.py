from kucoin_futures.client import Market
from datetime import datetime
import numpy as np
import pandas as pd
import json

api_key = '671647ad5913dd0001518e91'
api_secret = '0c48f805-39ec-49db-b97a-ea3a6595789b'
api_passphrase = 'VL.45E29ZqN4czL'

client = Market(key=api_key, secret=api_secret, passphrase=api_passphrase)

with open('config.json', 'r') as file:
    config_data = json.load(file)
    
coin = config_data.get("coin")
tf = config_data.get("tf")
n_periods = config_data.get("n_periods")

def calculate_rsi():
    klines = client.get_kline_data(symbol=coin, granularity=tf)
    for el in klines:
        el[0] = datetime.fromtimestamp(int(el[0])/1000)

    df = pd.DataFrame({
        'dt': [x[0] for x in klines],
        'open': [x[1] for x in klines],
        'close': [x[4] for x in klines]
    })

    df['u'] = np.where(df.close > df.open, df.close - df.open, 0)
    df['d'] = np.where(df.close < df.open, df.open - df.close, 0)

    df[f'ema_{n_periods}_u'] = df.u.ewm(alpha=1/n_periods, adjust=True).mean()
    df[f'ema_{n_periods}_d'] = df.d.ewm(alpha=1/n_periods, adjust=True).mean()

    df['rs'] = df[f'ema_{n_periods}_u'] / df[f'ema_{n_periods}_d']
    df['rsi'] = 100 - 100 / (1 + df['rs'])

    return df['rsi'].tail(1).values[0]
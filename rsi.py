#либы
from kucoin_futures.client import Market
from datetime import datetime
import numpy as np
import pandas as pd
import json

#параметры API(подключения к KuCoin)
api_key = '671647ad5913dd0001518e91'
api_secret = '0c48f805-39ec-49db-b97a-ea3a6595789b'  
api_passphrase = 'VL.45E29ZqN4czL'

#клиент KuCoin
client = Market(key=api_key, secret=api_secret, passphrase=api_passphrase)

#параметры расчета RSI
with open('config.json', 'r') as file:
    config_data = json.load(file)
    
coin = config_data.get("coin")
tf = config_data.get("tf")
n_periods = config_data.get("n_periods")

# print(coin)
# print(tf)
# print(n_periods)


def calculate_rsi():

    klines = client.get_kline_data(symbol = coin, granularity = tf) #свеча
    for el in klines:
        el[0] = datetime.fromtimestamp(int(el[0])/1000)


    df = pd.DataFrame( #таблица c датой, ценой открытия, ценой закрытия
        data = {
            'dt' : list(map(lambda x: x[0], klines)),
            'open' : list(map(lambda x: x[1], klines)),
            'close' : list(map(lambda x: x[4], klines))
        },
    )

    #вот тут брал формулу расчета https://www.tinkoff.ru/invest/help/educate/trading/about/rsi/ ( раздел как рассчитывается показатель RSI)

    df['u'] = np.where(
        df.close > df.open, df.close - df.open, 0
    )

    df['d'] = np.where(
        df.close < df.open, df.open - df.close, 0
    )


    df[f'ema_{n_periods}_u'] = df.u.ewm(alpha=1/n_periods, adjust=True,).mean() #вот тут не уверен с параметрами, особенно alpha
    df[f'ema_{n_periods}_d'] = df.d.ewm(alpha=1/n_periods, adjust=True).mean() #вот тут не уверен с параметрами, особенно alpha

    df['rs'] = df[f'ema_{n_periods}_u']/df[f'ema_{n_periods}_d']
    df['rsi'] = 100 - 100/(1+df['rs'])

    return df['rsi'].tail(1).values[0]


# rsi = calculate_rsi()
# print(rsi)
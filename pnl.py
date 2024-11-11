from rsi import calculate_rsi
from kucoin_futures.client import Trade
import telebot
from telebot import types
import time
from datetime import datetime
import json
import pymssql

#параметры API(подключения к KuCoin)
api_key = '671647ad5913dd0001518e91'
api_secret = '0c48f805-39ec-49db-b97a-ea3a6595789b'  
api_passphrase = 'VL.45E29ZqN4czL'

#клиент KuCoin
client = Trade(key=api_key, secret=api_secret, passphrase=api_passphrase)
with open('config.json', 'r') as file:
    config_data = json.load(file)
coin = config_data['coin']


def current_position():
    res = client.get_all_position()
    # keys = ['symbol', 'realisedPnl']
    # res_ = {}
    # for k,v in res.items():
    #     if k in keys:
    #         res_[k]=v
    return res

def calculate_24h_pnl():
    import pandas as pd
    import datetime
    res = client.get_24h_done_order()
    print(res)
    res = pd.json_normalize(res)
    print(res)
    res['createdAt'] = res['createdAt'].apply(lambda x: datetime.datetime.fromtimestamp(x / 1000).strftime('%H:%M'))
    res['endAt'] = res['endAt'].apply(lambda x: datetime.datetime.fromtimestamp(x / 1000).strftime('%H:%M'))

    def calculate_total_pnl(df):
        df['value'] = pd.to_numeric(df['value'], errors='coerce')
        
        total_pnl = 0
        open_position = None
        entry_price = None

        maker_fee = 0.0002
        taker_fee = 0.0006

        for index, row in df.iterrows():
            if open_position is None:
                # Открытие новой позиции
                open_position = row['side']
                entry_price = row['value']                
            else:
                # Закрытие позиции
                if (open_position == 'buy' and row['side'] == 'sell') or (open_position == 'sell' and row['side'] == 'buy'):
                    if open_position == 'buy':
                        pnl = row['value'] - entry_price
                        pnl -= row['value']*taker_fee + entry_price*maker_fee
                    else:
                        pnl = entry_price - row['value']
                        pnl -= row['value']*taker_fee + entry_price*maker_fee
                    total_pnl += pnl
                    
                    # Сброс позиции после её закрытия
                    open_position = None
                    entry_price = None

        # Если осталась открытая позиция, она не включена в итоговый PnL
        if open_position is not None:
            print(f"Warning: There is an open {open_position} position that hasn't been closed yet.")

        return round(total_pnl, 3)

    total_pnl = calculate_total_pnl(res)
    return total_pnl



#res = current_position()
# res = client.get_all_position()[0]
# print(res)
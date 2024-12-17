from rsi import calculate_rsi
from kucoin_futures.client import Trade
import telebot
from telebot import types
import time
from datetime import datetime
import json
import pymssql

#параметры API(подключения к KuCoin) !!!
api_key = '671647ad5913dd0001518e91'
api_secret = '0c48f805-39ec-49db-b97a-ea3a6595789b'  
api_passphrase = 'VL.45E29ZqN4czL'

#bot KEY
bot_key = "7473391752:AAGAs30m3u_opiNbzJVvE-OhOGYRBmRm4Zg"

#клиент KuCoin
client = Trade(key=api_key, secret=api_secret, passphrase=api_passphrase)
bot = telebot.TeleBot(token=bot_key)

#конфиги
with open('config.json', 'r') as file:
    config_data = json.load(file)
    
coin = config_data.get("coin")
leverage = config_data.get("leverage")
size = config_data.get("size")
up_border = config_data.get("up_border")
short_close_border = config_data.get("short_close_border")
low_border = config_data.get("low_border")
long_stop_border = config_data.get("long_stop_border")
is_running = False
time_sleep = 5


# Функция для запуска процесса торговли
def start_trading_process(chat_id):
    global is_running, open_counter, close_counter
    if is_running:
        bot.send_message(chat_id, "Торговля уже запущена.")
        return

    is_running = True
    bot.send_message(chat_id, f"Поиск сделки по {coin}")
    open_counter = 0
    close_counter = 0

    try:
        while is_running:
            current_rsi = calculate_rsi()
            try:
                positions = client.get_all_position()
                open_position = isinstance(positions, list) and len(positions) > 0
            except Exception as e:
                bot.send_message(chat_id, f"Ошибка получения позиций: {e}")
                open_position = False

            if open_position:
                position = positions[0]
                long_position = position['currentQty'] > 0
                short_position = position['currentQty'] < 0
            else:
                long_position = short_position = False

            # Открытие позиций
            if not open_position:
                try:
                    if current_rsi >= up_border:
                        client.create_market_order(coin, 'sell', leverage, size=size)
                        open_counter += 1
                        bot.send_message(chat_id, f"Открыта короткая позиция по {coin}")
                    elif current_rsi <= low_border:
                        client.create_market_order(coin, 'buy', leverage, size=size)
                        open_counter += 1
                        bot.send_message(chat_id, f"Открыта длинная позиция по {coin}")
                except Exception as e:
                    bot.send_message(chat_id, f"Ошибка при открытии позиции: {e}")

            # Закрытие позиций
            if open_position:
                try:
                    if long_position and current_rsi >= long_stop_border:
                        client.create_market_order(coin, 'sell', leverage, size=size)
                        close_counter += 1
                        bot.send_message(chat_id, f"Закрыта длинная позиция по {coin}")
                    elif short_position and current_rsi <= short_close_border:
                        client.create_market_order(coin, 'buy', leverage, size=size)
                        close_counter += 1
                        bot.send_message(chat_id, f"Закрыта короткая позиция по {coin}")
                except Exception as e:
                    bot.send_message(chat_id, f"Ошибка при закрытии позиции: {e}")

            # Отправка обновления статуса
            status_message = (
                f"RSI: {round(current_rsi, 2)}\n"
                f"Открытых сделок: {open_counter}\n"
                f"Закрытых сделок: {close_counter}"
            )
            bot.send_message(chat_id, status_message)

            time.sleep(time_sleep)
    except Exception as e:
        bot.send_message(chat_id, f"Произошла ошибка в торговом цикле: {e}")
        is_running = False

# Функция для остановки процесса торговли
def stop_trading_process(chat_id):
    global is_running, open_counter, close_counter
    if not is_running:
        bot.send_message(chat_id, "Торговля уже остановлена.")
        return

    is_running = False
    print('IS_RUNNING', is_running)
    
    # Закрытие позиций
    try:
        positions = client.get_all_position()
        open_position = isinstance(positions, list) and len(positions) > 0
        if open_position:
            position = positions[0]
            if position['currentQty'] > 0:
                client.create_market_order(coin, 'sell', leverage, size=size)
                bot.send_message(chat_id, f"Закрыта длинная позиция по {coin}")
            elif position['currentQty'] < 0:
                client.create_market_order(coin, 'buy', leverage, size=size)
                bot.send_message(chat_id, f"Закрыта короткая позиция по {coin}")
        
        bot.send_message(chat_id, f"--Робот остановлен. Все позиции закрыты.--\n")
    except Exception as e:
        bot.send_message(chat_id, f"Ошибка при закрытии позиций: {e}")
    
    # Вычисление PnL
    try:
        rev = calculate_24h_pnl()
        if rev >= 0:
            bot.send_message(chat_id, f"Ваш профит составил {rev} USDT")
        else:
            bot.send_message(chat_id, f"Ваш убыток составил {rev} USDT")
    except Exception as e:
        bot.send_message(chat_id, f"Ошибка при вычислении PnL: {e}")

# Функия показывающая текущую позицию
def current_position():
    res = client.get_all_position()
    # keys = ['symbol', 'realisedPnl']
    # res_ = {}
    # for k,v in res.items():
    #     if k in keys:
    #         res_[k]=v
    return res

# Функия показывающая прибыль
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
import os
import datetime
from collections import defaultdict

import telebot
from telebot import types
import time
import json
from dotenv import load_dotenv
import pandas as pd
from sqlalchemy import create_engine, text

from utils import (
    read_config,
    write_config,
    create_main_menu_markup,
    create_stock_choose,
    main_menu_button
)
from stocks import BinanceStock, BybitStock, KucoinStock
import pprint


load_dotenv()
os.environ['SQL_USER'] = 'cloud_user'

engine = create_engine(f"postgresql+psycopg2://{os.environ['SQL_USER']}:{os.environ['SQL_PASS']}@{os.environ['SQL_HOST']}/{os.environ['SQL_DATABASE']}")
print(f"postgresql+psycopg2://{os.environ['SQL_USER']}:{os.environ['SQL_PASS']}@{os.environ['SQL_HOST']}/{os.environ['SQL_DATABASE']}")
# conn = engine.raw_connection()
# cur = conn.cursor()

bot_key = os.environ["BOT_KEY"]
prices = [types.LabeledPrice(label='Поддержать проект', amount=150)]
bot = telebot.TeleBot(token=bot_key)

# параметры расчета RSI
CONFIG_FILE = "config.json"
with open("config.json", "r") as file:
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
configs = defaultdict(lambda: config_data)
clients = defaultdict(lambda: None)

coin_mapping = {
    "ton": "TONUSDT",
    "sol": "SOLUSDT",
    "btc": "BTCUSDT",
}


@bot.callback_query_handler(lambda query: query.data in ["HFT"])
def handle_accel(query):
    user_id = query.from_user.id
    configs[user_id]['tf'] = 1
    configs[user_id]['n_periods'] = 6
    # write_config(config_data)


@bot.callback_query_handler(lambda query: query.data in ["MFT"])
def handle_accel(query):
    user_id = query.from_user.id
    configs[user_id]['tf'] = 5
    configs[user_id]['n_periods'] = 12
    # write_config(config_data)   


@bot.callback_query_handler(lambda query: query.data in ["LFT"])
def handle_accel(query):
    user_id = query.from_user.id
    configs[user_id]['tf'] = 15
    configs[user_id]['n_periods'] = 14
    # write_config(config_data)        


@bot.message_handler(commands=["start"])
def handle_start(message):
    # user_id = message.from_user.id
    # if not is_active_user(user_id):
    #     text_to_print = "У вас нет активной подписки"
    #     markup = types.InlineKeyboardMarkup()
    #     itembtn_str0 = types.InlineKeyboardButton(
    #         "О СЕРВИСЕ", url='https://glens-organization-1.gitbook.io/rsioboarding/about'
    #     )
    #     markup.add(itembtn_str0)  
    #     itembtn_str1 = types.InlineKeyboardButton(
    #         "ЧТО ТЫ ПОЛУЧИШЬ?", url='https://glens-organization-1.gitbook.io/rsioboarding/benefits'
    #     )
    #     markup.add(itembtn_str1)        
    #     itembtn_str = types.InlineKeyboardButton(
    #         "Оплатить подписку", callback_data="buy"
    #     )
    #     markup.add(itembtn_str)
    #     itembtn_str_ = types.InlineKeyboardButton(
    #         "ПОДДЕРЖКА 🧑‍💻", url = "t.me/@gordeevlabs"
    #     )
    #     markup.add(itembtn_str_)        
    #     #bot.send_message(message.chat.id, text=text_to_print, reply_markup=markup)
    #     bot.send_audio(
    #         message.chat.id, 
    #         audio=open('Послушай.mp3', 'rb'), 
    #         caption="У вас нет активной подписки\nНачни с голосового сообщения :)",
    #         reply_markup=markup)
    # else:
    text_to_print = "Log In"
    markup = types.InlineKeyboardMarkup()
    itembtn_str0 = types.InlineKeyboardButton("Авторизоваться на bybit", callback_data="init_client")
    markup.add(itembtn_str0)
    #markup = create_main_menu_markup()
    bot.send_message(message.chat.id, text=text_to_print, reply_markup=markup)


@bot.callback_query_handler(lambda query: query.data in ["back", "choose_stock"])
def back_button_logic(query):
    user_id = query.from_user.id
    text_to_print = "Выберите биржу"
    markup = create_stock_choose()
    bot.edit_message_text(
        chat_id=user_id,
        text=text_to_print,
        message_id=query.message.id,
        reply_markup=markup,
    )


@bot.callback_query_handler(lambda query: query.data in ["binance", "bybit", "kucoin"])
def handle_start_trading_stock(query):
    user_id = query.from_user.id
    configs[user_id]['stock'] = query.data
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("OK", callback_data="menu"))
    markup.add(types.InlineKeyboardButton("назад", callback_data="choose_stock"))
    bot.edit_message_text(
        chat_id=user_id,
        text=f"Выбранная биржа {configs[user_id]['stock']}",
        message_id=query.message.id,
        reply_markup=markup,
    )
    

@bot.callback_query_handler(lambda query: query.data in ["init_client"])
def handle_start_trading_stock(query):
    global clients
    user_id = query.from_user.id
    args = [bot, user_id, handle_start, configs[user_id], engine]
    if configs[user_id]['stock'] == "binance":
        if configs[user_id]['coin'][-1] == 'M':
            configs[user_id]['coin'] = configs[user_id]['coin'][:-1]
        clients[user_id] = BinanceStock(*args)
    elif configs[user_id]['stock'] == "bybit":
        if configs[user_id]['coin'][-1] == 'M':
            configs[user_id]['coin'] = configs[user_id]['coin'][:-1]
        clients[user_id] = BybitStock(*args)
    else:
        if configs[user_id]['coin'][-1] != 'M':
            configs[user_id]['coin'] = configs[user_id]['coin'] + "M"
        clients[user_id] = KucoinStock(*args)
    clients[user_id].get_keys(query.message.id)


@bot.callback_query_handler(lambda query: query.data in ["menu"])
def handle_menu(query):
    markup = create_main_menu_markup()
    user_id = query.from_user.id
    response = "Главное меню"
    bot.edit_message_text(
        chat_id=user_id,
        text=response,
        message_id=query.message.id,
        reply_markup=markup,
    )


@bot.callback_query_handler(lambda query: query.data in ["buy"])
def handle_buy(query):
    user_id = query.from_user.id
    bot.send_invoice(
        chat_id=user_id, 
        title='Поддержать проект', 
        description='Поддержать проект бота',
        invoice_payload='subs 1 month',
        currency='XTR',
        prices=prices,
        provider_token=None,
    )

@bot.callback_query_handler(lambda query: query.data in ["accelerate"])
def handle_accel(query):
    user_id = query.from_user.id
    lev = int(configs[user_id]['leverage'])
    configs[user_id]['leverage'] = lev*2
    # write_config(config_data)

@bot.callback_query_handler(lambda query: query.data in ["downgrade"])
def handle_accel(query):
    user_id = query.from_user.id
    lev = int(configs[user_id]['leverage'])
    new_lev = int(lev/2) if lev > 1 else 1
    configs[user_id]['leverage'] = new_lev
    # write_config(config_data)    


@bot.pre_checkout_query_handler(func=lambda query: True)
def checkout(pre_checkout_query):
    bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True,
                                  error_message="Произошла ошибка.")


@bot.message_handler(content_types=['successful_payment'])
def got_payment(message):
    response = "Вы оплатили подписку ✅"
    user_id = message.from_user.id
    if not is_active_user(user_id):
        with engine.begin() as connection:
            connection.execute(text(f'DELETE FROM subs WHERE subs_id = {user_id}'))
            connection.commit()

        with engine.begin() as connection:
            start = datetime.datetime.now()
            end = start + datetime.timedelta(days=30)
            parameters = {
                "subs_id": user_id,
                "date_start": start.strftime("%Y-%m-%d %H:%M:%S"),
                "date_end": end.strftime("%Y-%m-%d %H:%M:%S"),
            }
            connection.execute(text('INSERT INTO subs (subs_id, date_start, date_end) VALUES (:subs_id, :date_start, :date_end)'), parameters)
            connection.commit()
    else:
        with engine.begin() as connection:
            update_query = f"""
                UPDATE subs 
                SET date_end = date_end + INTERVAL'30 days'
                WHERE subs_id = {user_id}
            """
            connection.execute(text(update_query))
            connection.commit()
    
    with engine.begin() as connection:
        query = f"""
            SELECT * 
            FROM subs 
            WHERE subs_id = {user_id}
        """
        df = pd.read_sql_query(query, connection)
    end_time = df['date_end'][0]

    response += '\n' + f'Ваша подписка закончится `{end_time}`'
    markup = types.InlineKeyboardMarkup()
    itembtn_str = types.InlineKeyboardButton("Главное меню", callback_data="menu")
    markup.add(itembtn_str)

    bot.send_message(
        chat_id=message.chat.id,
        text=response,
        reply_markup=markup,
        parse_mode="Markdown",
    )


@bot.callback_query_handler(lambda query: query.data in ["subscription_status"])
def handle_subscription_status(query):
    user_id = query.from_user.id
    if not is_active_user(user_id):
        response = "У вас нет активной подписки"
    else:
        with engine.begin() as connection:
            sql_query = f"""
                SELECT * 
                FROM subs 
                WHERE subs_id = {user_id}
            """
            df = pd.read_sql_query(sql_query, connection)
        end_time = df['date_end'][0]
        response = f'Ваша подписка закончится `{end_time}`'
    
    markup = types.InlineKeyboardMarkup()
    itembtn_str = types.InlineKeyboardButton("Главное меню", callback_data="menu")
    markup.add(itembtn_str)

    bot.edit_message_text(
        chat_id=user_id,
        text=response,
        message_id=query.message.id,
        reply_markup=markup,
        parse_mode="Markdown",
        
    )


def is_active_user(user_id):
    with engine.begin() as conn:
        query = f"""
            SELECT * 
            FROM subs 
            WHERE subs_id = {user_id}
                AND date_end > '{datetime.datetime.now()}'
        """
        df = pd.read_sql_query(query, conn)
    return not df.empty


# Обработчик нажатия кнопки "Запуск🚀🚀🚀"
@bot.message_handler(func=lambda message: message.text == "Запуск🚀🚀🚀")
def handle_start_trading(message):
    user_id = message.from_user.id
    if clients[user_id]:
        clients[user_id].start_trading_process(message.chat.id, message)
    else:
        markup = main_menu_button()
        bot.edit_message_text("Не указан клиент 🚫", message.chat.id, message.id, reply_markup=markup)


# Обработчик нажатия кнопки "start"
@bot.callback_query_handler(lambda query: query.data == "start")
def handle_start_callback(query):
    user_id = query.from_user.id
    if clients[user_id]:
        clients[user_id].start_trading_process(user_id, query.message)
    else:
        markup = main_menu_button()
        bot.edit_message_text("Не указан клиент 🚫", user_id, query.message.id, reply_markup=markup)


# Обработчик нажатия кнопки "STOP❌❌❌"
@bot.message_handler(func=lambda message: message.text == "STOP❌❌❌")
def handle_stop(message):
    user_id = message.from_user.id
    if clients[user_id]:
        clients[user_id].stop_trading_process(message.chat.id, message)
    else:
        markup = main_menu_button()
        bot.edit_message_text("Не указан клиент 🚫", message.chat.id, message.id, reply_markup=markup)


# Обработчик нажатия кнопки "stop"
@bot.callback_query_handler(lambda query: query.data == "stop")
def handle_stop_callback(query):
    user_id = query.from_user.id
    if clients[user_id]:
        clients[user_id].stop_trading_process(user_id, query.message)
    else:
        markup = main_menu_button()
        bot.edit_message_text("Не указан клиент 🚫", user_id, query.message.id, reply_markup=markup)


@bot.callback_query_handler(lambda query: query.data in ["choose_pair"])
def back_button_logic2(query):
    user_id = query.from_user.id
    text_to_print = "Выберите пару"
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("TON", callback_data="ton"))
    markup.add(types.InlineKeyboardButton("SOL", callback_data="sol"))
    markup.add(types.InlineKeyboardButton("BTC", callback_data="btc"))
    markup.add(types.InlineKeyboardButton("назад", callback_data="menu"))
    bot.edit_message_text(
        chat_id=user_id,
        text=text_to_print,
        message_id=query.message.id,
        reply_markup=markup,
    )

@bot.callback_query_handler(lambda query: query.data in ["ton", "sol", "btc"])
def handle_start_trading(query):
    user_id = query.from_user.id
    coin = coin_mapping[query.data]
    configs[user_id]['coin'] = coin
    if clients[user_id]:
        clients[user_id].config = configs[user_id]
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("OK", callback_data="menu"))
    markup.add(types.InlineKeyboardButton("назад", callback_data="choose_pair"))
    bot.edit_message_text(
        chat_id=user_id,
        text=f"Выбранная монета {coin}",
        message_id=query.message.id,
        reply_markup=markup,
    )


@bot.callback_query_handler(lambda query: query.data in ["leaderboard"])
def handle_leaderboard(query):
    user_id = query.from_user.id
    sql_query = f"""
        SELECT subs_id,
               pnl, 
               dense_rank() over (order by pnl DESC) as rank_num
          FROM leaderboard 
         WHERE stock_type = '{clients[user_id].type}'
               and date_pnl > '{datetime.datetime.now() - datetime.timedelta(hours=24)}'
    """
    with engine.begin() as conn:
        df = pd.read_sql_query(sql_query, conn)

    leadeboard_text = df.head(5).to_markdown(index=False)
    leadeboard_text = f'`{leadeboard_text}`'
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Назад", callback_data="menu"))
    bot.edit_message_text(
        chat_id=query.from_user.id,
        text=f"Лидерборд\n" + leadeboard_text,
        message_id=query.message.id,
        reply_markup=markup,
        parse_mode="Markdown",
    )




# @bot.callback_query_handler(lambda query: query.data in ["back", "choose_size"])
# def back_button_logic3(query):
#     text_to_print = "Выберите размер позиции"
#     markup = types.InlineKeyboardMarkup()
#     markup.add(types.InlineKeyboardButton("Введите кол-во USDT", callback_data="enter_usdt"))
#     markup.add(types.InlineKeyboardButton("Введите плечо", callback_data="enter_leverage"))
#     markup.add(types.InlineKeyboardButton("назад", callback_data="menu"))
#     bot.edit_message_text(
#         chat_id=user_id,
#         text=text_to_print,
#         message_id=query.message.id,
#         reply_markup=markup,
#     )

    

@bot.callback_query_handler(lambda query: query.data in ["back", "choose_size"])
def handle_choose_size(query):
    user_id = query.from_user.id
    chat_id = user_id
    message_id = query.message.id
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("назад", callback_data="menu"))
    msg = bot.edit_message_text(
        chat_id=user_id,
        text="Введите деп",
        message_id=query.message.id,
        reply_markup=markup
    )
    bot.register_next_step_handler(msg, change_value, chat_id, message_id, query.data)

def change_value(msg, chat_id, message_id, query_data):
    bot.delete_message(msg.from_user.id, msg.message_id, timeout=1000)
    user_id = msg.from_user.id
    configs[user_id]['size'] = int(msg.text)
    if clients[user_id]:
        clients[user_id].config = configs[user_id]
    text_to_print = f"Обновленное значение для поля size\nЗначение {configs[user_id]['size']}"
    #text_to_print += '\nДля обновления значения еще раз нажмите кнопку "Назад" и выберете соответствующий параметр'
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("назад", callback_data="choose_size"))
    msg = bot.edit_message_text(
        chat_id=chat_id,
        text=text_to_print,
        message_id=message_id,
        reply_markup=markup
    )


@bot.callback_query_handler(lambda query: query.data == "settings")
def lessgo(query):
    user_id = query.from_user.id
    response = ""
    for key, value in configs[user_id].items():
        if key in ['stock', 'coin', 'leverage', 'size']:
            response += f"{key}: {value}\n"

    markup = types.InlineKeyboardMarkup()
    itembtn_str1 = types.InlineKeyboardButton("назад", callback_data="menu")
    markup.add(
        itembtn_str1,
    )
    bot.edit_message_text(
        chat_id=user_id,
        text=response,
        message_id=query.message.id,
        reply_markup=markup,
    )


@bot.callback_query_handler(lambda query: query.data == "pos")
def lessgo(query):
    user_id = query.from_user.id
    if clients[user_id]:
        res = str(clients[user_id].current_position())  # kucoin
        markup = types.InlineKeyboardMarkup()
        itembtn_str1 = types.InlineKeyboardButton("назад", callback_data="menu")
        markup.add(
            itembtn_str1,
        )
        bot.edit_message_text(
            chat_id=user_id,
            text=res,
            message_id=query.message.id,
            reply_markup=markup,
        )
    else:
        markup = main_menu_button()
        bot.edit_message_text("Не указан клиент 🚫", user_id, query.message.id, reply_markup=markup)


@bot.message_handler(commands=["pos"])
def lessgo(message):
    user_id = message.from_user.id
    if clients[user_id]:
        res = clients[user_id].current_position()
        bot.send_message(message.chat.id, f"{res}")
    else:
        markup = main_menu_button()
        bot.edit_message_text("Не указан клиент 🚫", message.chat.id, message.id, reply_markup=markup)
    


@bot.callback_query_handler(lambda query: query.data == "24h_pnl")
def lessgo(query):
    user_id = query.from_user.id
    if clients[user_id]:
        res = clients[user_id].calculate_24h_pnl()
        markup = types.InlineKeyboardMarkup()
        itembtn_str1 = types.InlineKeyboardButton("назад", callback_data="menu")
        markup.add(
            itembtn_str1,
        )
        bot.edit_message_text(
            chat_id=user_id,
            text=f"{res} USDT",
            message_id=query.message.id,
            reply_markup=markup,
        )
    else:
        markup = main_menu_button()
        bot.edit_message_text("Не указан клиент 🚫", user_id, query.message.id, reply_markup=markup)


@bot.message_handler(commands=["24h_pnl"])
def lessgo(message):
    user_id = message.from_user.id
    if clients[user_id]:
        res = clients[user_id].calculate_24h_pnl()
        bot.send_message(message.chat.id, f"{res} USDT")
    else:
        markup = main_menu_button()
        bot.edit_message_text("Не указан клиент 🚫", message.chat.id, message.id, reply_markup=markup)


# Запуск бота
while True:
    try:
        bot.polling(none_stop=True)
    except Exception as e:
        print(e)
        time.sleep(15)

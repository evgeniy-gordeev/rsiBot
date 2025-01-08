import os
import datetime

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

engine = create_engine(f"postgresql+psycopg2://{os.environ['SQL_USER']}:{os.environ['SQL_PASS']}@{os.environ['SQL_HOST']}/{os.environ['SQL_DATABASE']}")
# conn = engine.raw_connection()
# cur = conn.cursor()

bot_key = os.environ["BOT_KEY"]
prices = [types.LabeledPrice(label='Подписка на 1 месяц', amount=150)]
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
client = None

coin_mapping = {
    "ton": "TONUSDT",
    "sol": "SOLUSDT",
    "btc": "BTCUSDT",
}


@bot.message_handler(commands=["start"])
def handle_start(message):
    user_id = message.from_user.id
    if not is_active_user(user_id):
        text_to_print = "У вас нет активной подписки"
        markup = types.InlineKeyboardMarkup()
        itembtn_str = types.InlineKeyboardButton(
            "Оплатить подписку", callback_data="buy"
        )
        markup.add(itembtn_str)
        bot.send_message(message.chat.id, text=text_to_print, reply_markup=markup)
    else:
        text_to_print = "Главное меню"
        markup = create_main_menu_markup()
        bot.send_message(message.chat.id, text=text_to_print, reply_markup=markup)


@bot.callback_query_handler(lambda query: query.data in ["back", "choose_stock"])
def back_button_logic(query):
    text_to_print = "Выберите биржу"
    markup = create_stock_choose()
    bot.edit_message_text(
        chat_id=query.from_user.id,
        text=text_to_print,
        message_id=query.message.id,
        reply_markup=markup,
    )


@bot.callback_query_handler(lambda query: query.data in ["binance", "bybit", "kucoin"])
def handle_start_trading_stock(query):
    config_data['stock'] = query.data
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("OK", callback_data="menu"))
    markup.add(types.InlineKeyboardButton("назад", callback_data="choose_stock"))
    bot.edit_message_text(
        chat_id=query.from_user.id,
        text=f"Выбранная биржа {config_data['stock']}",
        message_id=query.message.id,
        reply_markup=markup,
    )
    

@bot.callback_query_handler(lambda query: query.data in ["init_client"])
def handle_start_trading_stock(query):
    global client
    args = [bot, query.from_user.id, handle_start, config_data]
    if config_data['stock'] == "binance":
        if config_data['coin'][-1] == 'M':
            config_data['coin'] = config_data['coin'][:-1]
        client = BinanceStock(*args)
    elif config_data['stock'] == "bybit":
        if config_data['coin'][-1] == 'M':
            config_data['coin'] = config_data['coin'][:-1]
        client = BybitStock(*args)
    else:
        if config_data['coin'][-1] != 'M':
            config_data['coin'] = config_data['coin'] + "M"
        client = KucoinStock(*args)
    client.get_keys(query.message.id)


@bot.callback_query_handler(lambda query: query.data in ["menu"])
def handle_menu(query):
    markup = create_main_menu_markup()
    response = "Главное меню"
    bot.edit_message_text(
        chat_id=query.from_user.id,
        text=response,
        message_id=query.message.id,
        reply_markup=markup,
    )


@bot.callback_query_handler(lambda query: query.data in ["buy"])
def handle_buy(query):
    bot.send_invoice(
        chat_id=query.from_user.id, 
        title='Подписка на 1 месяц', 
        description='Подписка на бот на 1 месяц',
        invoice_payload='subs 1 month',
        currency='XTR',
        prices=prices,
        provider_token=None,
    )


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
        chat_id=query.from_user.id,
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
    if client:
        client.start_trading_process(message.chat.id)
    else:
        markup = main_menu_button()
        bot.edit_message_text("Не указан клиент 🚫", message.chat.id, message.id, reply_markup=markup)


# Обработчик нажатия кнопки "start"
@bot.callback_query_handler(lambda query: query.data == "start")
def handle_start_callback(query):
    if client:
        client.start_trading_process(query.from_user.id, query.message)
    else:
        markup = main_menu_button()
        bot.edit_message_text("Не указан клиент 🚫", query.from_user.id, query.message.id, reply_markup=markup)


# Обработчик нажатия кнопки "STOP❌❌❌"
@bot.message_handler(func=lambda message: message.text == "STOP❌❌❌")
def handle_stop(message):
    if client:
        client.stop_trading_process(message.chat.id, message)
    else:
        markup = main_menu_button()
        bot.edit_message_text("Не указан клиент 🚫", message.chat.id, message.id, reply_markup=markup)


# Обработчик нажатия кнопки "stop"
@bot.callback_query_handler(lambda query: query.data == "stop")
def handle_stop_callback(query):
    if client:
        client.stop_trading_process(query.from_user.id, query.message)
    else:
        markup = main_menu_button()
        bot.edit_message_text("Не указан клиент 🚫", query.from_user.id, query.message.id, reply_markup=markup)


@bot.callback_query_handler(lambda query: query.data in ["choose_pair"])
def back_button_logic2(query):
    text_to_print = "Выберите пару"
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("TON", callback_data="ton"))
    markup.add(types.InlineKeyboardButton("SOL", callback_data="sol"))
    markup.add(types.InlineKeyboardButton("BTC", callback_data="btc"))
    markup.add(types.InlineKeyboardButton("назад", callback_data="menu"))
    bot.edit_message_text(
        chat_id=query.from_user.id,
        text=text_to_print,
        message_id=query.message.id,
        reply_markup=markup,
    )

@bot.callback_query_handler(lambda query: query.data in ["ton", "sol", "btc"])
def handle_start_trading(query):
    coin = coin_mapping[query.data]
    config_data['coin'] = coin
    if client:
        client.config = config_data
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("OK", callback_data="menu"))
    markup.add(types.InlineKeyboardButton("назад", callback_data="choose_pair"))
    bot.edit_message_text(
        chat_id=query.from_user.id,
        text=f"Выбранная монета {coin}",
        message_id=query.message.id,
        reply_markup=markup,
    )


@bot.callback_query_handler(lambda query: query.data in ["back", "choose_size"])
def back_button_logic3(query):
    text_to_print = "Выберите размер позиции"
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Введите кол-во USDT", callback_data="enter_usdt"))
    markup.add(types.InlineKeyboardButton("Введите плечо", callback_data="enter_leverage"))
    markup.add(types.InlineKeyboardButton("назад", callback_data="menu"))
    bot.edit_message_text(
        chat_id=query.from_user.id,
        text=text_to_print,
        message_id=query.message.id,
        reply_markup=markup,
    )
    

@bot.callback_query_handler(lambda query: query.data in ["enter_usdt", "enter_leverage"])
def handle_choose_size(query):
    chat_id = query.from_user.id
    message_id = query.message.id
    if query.data == "enter_usdt": 
        text_to_print = f"Введите новое значение для поля size\nТекущее значение {config_data['size']}"
    else:
        text_to_print = f"Введите новое значение для поля leverage\nТекущее значение {config_data['leverage']}"

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("назад", callback_data="choose_size"))
    msg = bot.edit_message_text(
        chat_id=query.from_user.id,
        text=text_to_print,
        message_id=query.message.id,
        reply_markup=markup
    )
    bot.register_next_step_handler(msg, change_value, chat_id, message_id, query.data)

def change_value(msg, chat_id, message_id, query_data):
    bot.delete_message(msg.from_user.id, msg.message_id, timeout=1000)
    if query_data == "enter_usdt": 
        config_data['size'] = int(msg.text)
        if client:
            client.config = config_data
        text_to_print = f"Обновленное значение для поля size\nЗначение {config_data['size']}"
    else:
        config_data['leverage'] = msg.text
        if client:
            client.config = config_data
        text_to_print = f"Обновленное значение для поля leverage\nЗначение {config_data['leverage']}"
    text_to_print += '\nДля обновления значения еще раз нажмите кнопку "Назад" и выберете соответствующий параметр'
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("назад", callback_data="choose_size"))
    msg = bot.edit_message_text(
        chat_id=chat_id,
        text=text_to_print,
        message_id=message_id,
        reply_markup=markup
    )


@bot.callback_query_handler(lambda query: query.data == "set")
def lessgo(query):
    bot.clear_step_handler(query.message)
    with open("config.json", "r") as file:
        config_data = json.load(file)
    markup = types.InlineKeyboardMarkup()
    msg = "Введите новое значение для какого-либо поля в формате 'поле значение'\n\n"
    msg += "Текущие поля\n"
    for key, value in config_data.items():
        msg += f"{key}: {value}\n"
        markup.add(types.InlineKeyboardButton(key, callback_data=f"ch*{key}"))

    itembtn_str1 = types.InlineKeyboardButton("назад", callback_data="menu")
    markup.add(
        itembtn_str1,
    )
    msg = bot.edit_message_text(
        chat_id=query.from_user.id,
        text=msg,
        message_id=query.message.id,
        reply_markup=markup,
    )
    # bot.register_next_step_handler(msg,test,msg)


@bot.callback_query_handler(lambda query: query.data[:2] == "ch")
def lessgo(query):
    key = query.data.split("*")[1]
    with open("config.json", "r") as file:
        config_data = json.load(file)
    markup = types.InlineKeyboardMarkup()
    msg = f"Введите новое значение для поля {key}\n"
    msg += f"Текущее значение {config_data[key]}"
    itembtn_str1 = types.InlineKeyboardButton("назад", callback_data="set")
    markup.add(
        itembtn_str1,
    )
    msg = bot.edit_message_text(
        chat_id=query.from_user.id,
        text=msg,
        message_id=query.message.id,
        reply_markup=markup,
    )
    bot.register_next_step_handler(msg, test, msg, key)


def test(message, old_msg, key):
    markup = types.InlineKeyboardMarkup()
    itembtn_str1 = types.InlineKeyboardButton("назад", callback_data="set")
    markup.add(itembtn_str1)
    field = key
    bot.delete_message(chat_id=message.from_user.id, message_id=message.id)
    value = message.text
    # print(field,value)
    config = read_config()
    try:
        if isinstance(config[field], int):
            value = int(value)
        elif isinstance(config[field], float):
            value = float(value)
    except ValueError:
        print("gasdasz")
        bot.edit_message_text(
            chat_id=message.chat.id,
            text="Некорректное значение для данного поля.",
            message_id=old_msg.id,
            reply_markup=markup,
        )
        return
    print("gz")
    config[field] = value
    write_config(config)
    bot.edit_message_text(
        chat_id=message.chat.id,
        text=f"Поле '{field}' успешно обновлено на '{value}'.",
        message_id=old_msg.id,
        reply_markup=markup,
    )


@bot.message_handler(commands=["set"])
def set_config_value(message):
    msg_parts = message.text.split()
    if len(msg_parts) != 3:
        bot.reply_to(message, "Используйте формат команды: /set <поле> <значение>")
        return
    field = msg_parts[1]
    value = msg_parts[2]

    config = read_config()
    if field not in config:
        bot.reply_to(message, f"Поле '{field}' не найдено в конфигурации.")
        return

    try:
        if isinstance(config[field], int):
            value = int(value)
        elif isinstance(config[field], float):
            value = float(value)
    except ValueError:
        bot.reply_to(message, "Некорректное значение для данного поля.")
        return

    config[field] = value
    write_config(config)

    bot.reply_to(message, f"Поле '{field}' успешно обновлено на '{value}'.")


@bot.callback_query_handler(lambda query: query.data == "settings")
def lessgo(query):
    response = ""
    for key, value in config_data.items():
        if key in ['stock', 'coin', 'leverage', 'size']:
            response += f"{key}: {value}\n"

    markup = types.InlineKeyboardMarkup()
    itembtn_str1 = types.InlineKeyboardButton("назад", callback_data="menu")
    markup.add(
        itembtn_str1,
    )
    bot.edit_message_text(
        chat_id=query.from_user.id,
        text=response,
        message_id=query.message.id,
        reply_markup=markup,
    )


@bot.message_handler(commands=["setting"])
def lessgo(message):
    with open("config.json", "r") as file:
        config_data = json.load(file)
    print(config_data)
    response = ""
    for key, value in config_data.items():
        response += f"{key}: {value}\n"

    bot.send_message(message.chat.id, response)


@bot.callback_query_handler(lambda query: query.data == "pos")
def lessgo(query):
    if client:
        res = str(client.current_position())  # kucoin
        markup = types.InlineKeyboardMarkup()
        itembtn_str1 = types.InlineKeyboardButton("назад", callback_data="menu")
        markup.add(
            itembtn_str1,
        )
        bot.edit_message_text(
            chat_id=query.from_user.id,
            text=res,
            message_id=query.message.id,
            reply_markup=markup,
        )
    else:
        markup = main_menu_button()
        bot.edit_message_text("Не указан клиент 🚫", query.from_user.id, query.message.id, reply_markup=markup)


@bot.message_handler(commands=["pos"])
def lessgo(message):
    if client:
        res = client.current_position()
        bot.send_message(message.chat.id, f"{res}")
    else:
        markup = main_menu_button()
        bot.edit_message_text("Не указан клиент 🚫", message.chat.id, message.id, reply_markup=markup)
    


@bot.callback_query_handler(lambda query: query.data == "24h_pnl")
def lessgo(query):
    if client:
        res = client.calculate_24h_pnl()
        markup = types.InlineKeyboardMarkup()
        itembtn_str1 = types.InlineKeyboardButton("назад", callback_data="menu")
        markup.add(
            itembtn_str1,
        )
        bot.edit_message_text(
            chat_id=query.from_user.id,
            text=f"{res} USDT",
            message_id=query.message.id,
            reply_markup=markup,
        )
    else:
        markup = main_menu_button()
        bot.edit_message_text("Не указан клиент 🚫", query.from_user.id, query.message.id, reply_markup=markup)


@bot.message_handler(commands=["24h_pnl"])
def lessgo(message):
    if client:
        res = client.calculate_24h_pnl()
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

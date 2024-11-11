from kucoin_futures.client import Trade
import telebot
from telebot import types
import time
import json


from pnl import calculate_24h_pnl
from rsi import calculate_rsi
from utils import read_config, write_config, create_main_menu_markup

#параметры API(подключения к KuCoin)
api_key = '671647ad5913dd0001518e91'
api_secret = '0c48f805-39ec-49db-b97a-ea3a6595789b'  
api_passphrase = 'VL.45E29ZqN4czL'
print(api_key)

#клиент KuCoin
client = Trade(key=api_key, secret=api_secret, passphrase=api_passphrase)
print(client)
bot = telebot.TeleBot(token="7473391752:AAGAs30m3u_opiNbzJVvE-OhOGYRBmRm4Zg")

#параметры расчета RSI
CONFIG_FILE = "config.json"
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



@bot.message_handler(commands=['start'])
def handle_start(message):
    markup = create_main_menu_markup()
    response = "ГЛАВНОЕ МЕНЮ"
    bot.send_message(message.chat.id, text=response, reply_markup=markup)

@bot.callback_query_handler(lambda query: query.data == "menu")
def handle_menu(query):
    markup = create_main_menu_markup()
    response = "ГЛАВНОЕ МЕНЮ"
    bot.edit_message_text(chat_id=query.from_user.id, text=response, message_id=query.message.id, reply_markup=markup)




@bot.message_handler(func=lambda message: message.text == "Запуск🚀🚀🚀")
def lessgo(message):
    
    global is_running
    is_running=True
    bot.reply_to(message, f"Поиск сделки по {coin}")

    # try:
    #     symbol = coin[:-1]  # Ожидается формат "/chart BTCUSDT"
    #     screenshot = get_tradingview_chart(symbol)
    #     with open(screenshot, 'rb') as img:
    #         bot.send_photo(message.chat.id, img)
    # except IndexError:
    #     bot.reply_to(message, "Пожалуйста, укажите символ валюты, например /chart BTCUSDT")

    open_counter = 0
    close_counter = 0
    current_rsi = calculate_rsi()
    bot.send_message(message.chat.id, f"rsi {round(current_rsi, 2)}\nоткртых сделок {open_counter}\nзакрытых сделок {close_counter}")
    
    while is_running:
        #константы
        current_rsi = calculate_rsi()
        open_position = isinstance(client.get_all_position(), list)
        if open_position:
            long_position = client.get_all_position()[0]['currentQty'] > 0 
            short_position = client.get_all_position()[0]['currentQty'] < 0 
        #открытие
        if open_position==False:
            try:
                if current_rsi >= up_border:
                    client.create_market_order(coin, 'sell', leverage, size = size)
                    open_counter += 1
                if current_rsi <= low_border:
                    client.create_market_order(coin, 'buy', leverage, size = size)
                    open_counter += 1
                else:
                    pass
            except Exception as e:
                print(e)
        #закрытие
        if open_position==True:
            try:
                if long_position:
                    if current_rsi >= long_stop_border:
                        client.create_market_order(coin, 'sell', leverage, size = size)
                        close_counter += 1
                if short_position:
                    if current_rsi <= short_close_border:
                        client.create_market_order(coin, 'buy', leverage, size = size)
                        close_counter += 1                     
            except Exception as e:
                print(e)
        
        bot.send_message(message.chat.id, f"rsi {round(current_rsi,2)}\nоткртых сделок {open_counter}\nзакрытых сделок {close_counter}")
        time.sleep(time_sleep)
                    
@bot.callback_query_handler(lambda query: query.data == "start")
def lessgo(query):
    global is_running
    is_running=True
    bot.reply_to(query.message, f"Поиск сделки по {coin}")

    # try:
    #     symbol = coin[:-1]  # Ожидается формат "/chart BTCUSDT"
    #     screenshot = get_tradingview_chart(symbol)
    #     with open(screenshot, 'rb') as img:
    #         bot.send_photo(message.chat.id, img)
    # except IndexError:
    #     bot.reply_to(message, "Пожалуйста, укажите символ валюты, например /chart BTCUSDT")

    open_counter = 0
    close_counter = 0
    current_rsi = calculate_rsi()
    bot.send_message(query.from_user.id, f"rsi {round(current_rsi, 2)}\nоткртых сделок {open_counter}\nзакрытых сделок {close_counter}")

    while is_running:
        #константы
        current_rsi = calculate_rsi()
        open_position = isinstance(client.get_all_position(), list)
        if open_position:
            long_position = client.get_all_position()[0]['currentQty'] > 0 
            short_position = client.get_all_position()[0]['currentQty'] < 0 
        #открытие
        if open_position==False:
            try:
                if current_rsi >= up_border:
                    client.create_market_order(coin, 'sell', leverage, size = size)
                    open_counter += 1
                if current_rsi <= low_border:
                    client.create_market_order(coin, 'buy', leverage, size = size)
                    open_counter += 1
                else:
                    pass
            except Exception as e:
                print(e)
        #закрытие
        if open_position==True:
            try:
                if long_position:
                    if current_rsi >= long_stop_border:
                        client.create_market_order(coin, 'sell', leverage, size = size)
                        close_counter += 1
                if short_position:
                    if current_rsi <= short_close_border:
                        client.create_market_order(coin, 'buy', leverage, size = size)
                        close_counter += 1                     
            except Exception as e:
                print(e)
        markup = types.InlineKeyboardMarkup()
        itembtn_str1 = types.InlineKeyboardButton('stop', callback_data='stop')
        markup.add(itembtn_str1,)
        bot.send_message(query.from_user.id, f"rsi {round(current_rsi,2)}\nоткртых сделок {open_counter}\nзакрытых сделок {close_counter}")
        time.sleep(time_sleep)






@bot.message_handler(func=lambda message: message.text == "STOP❌❌❌")
def handle_stop(message):
    #отсановка
    global is_running
    is_running = False
    print('IS RANIN', is_running)
    #закрытие
    try:
        open_position = isinstance(client.get_all_position(), list)
        if open_position==True:
            if client.get_all_position()[0]['currentQty'] > 0:
                client.create_market_order(coin, 'sell', leverage, size = size)
            else:
                client.create_market_order(coin, 'buy', leverage, size = size)                

        bot.reply_to(message, text = f"--Робот удален. Все койны проданы.--\n")
    except Exception as e:
        print(e)
    #pnl
    try:
        rev = calculate_24h_pnl()
        if rev >= 0:
            bot.reply_to(message, f"Ваш профит составил {rev} USDT") 
        else:
            bot.reply_to(message, f"Ваш убыток составил {rev} USDT") 
    except Exception as e:
        print(e)

@bot.callback_query_handler(lambda query: query.data == "stop")
def lessgo(query):
    global is_running
    is_running = False
    print('IS RANIN', is_running)
    #закрытие
    try:
        open_position = isinstance(client.get_all_position(), list)
        if open_position==True:
            if client.get_all_position()[0]['currentQty'] > 0:
                client.create_market_order(coin, 'sell', leverage, size = size)
            else:
                client.create_market_order(coin, 'buy', leverage, size = size)                

        msg = f"--Робот удален. Все койны проданы.--\n"
    except Exception as e:
        return
    #pnl
    try:
        rev = calculate_24h_pnl()
        if rev >= 0:
            msg += f"Ваш профит составил {rev} USDT"
        else:
            msg += f"Ваш убыток составил {rev} USDT"
    except Exception as e:
        return
    markup = types.InlineKeyboardMarkup()
    itembtn_str1 = types.InlineKeyboardButton('назад', callback_data='menu')
    markup.add(itembtn_str1,)
    #bot.edit_message_text(chat_id=query.from_user.id, text=msg, message_id=query.message.id, reply_markup=markup)
    bot.send_message(chat_id=query.from_user.id, text=msg)



@bot.callback_query_handler(lambda query: query.data == "set")
def lessgo(query):
    bot.clear_step_handler(query.message)
    with open('config.json', 'r') as file:
        config_data = json.load(file)
    markup = types.InlineKeyboardMarkup()
    msg = "Введите новое значение для какого-либо поля в формате 'поле значение'\n\n"
    msg += "Текущие поля\n"
    for key, value in config_data.items():
        msg += f"{key}: {value}\n"
        markup.add(types.InlineKeyboardButton(key, callback_data=f'ch*{key}'))
    
    itembtn_str1 = types.InlineKeyboardButton('назад', callback_data='menu')
    markup.add(itembtn_str1,)
    msg = bot.edit_message_text(chat_id=query.from_user.id, text=msg, message_id=query.message.id, reply_markup=markup)
    #bot.register_next_step_handler(msg,test,msg)

@bot.callback_query_handler(lambda query: query.data[:2] == "ch")
def lessgo(query):
    key = query.data.split('*')[1]
    with open('config.json', 'r') as file:
        config_data = json.load(file)
    markup = types.InlineKeyboardMarkup()
    msg = f"Введите новое значение для поля {key}\n"
    msg += f"Текущее значение {config_data[key]}"
    itembtn_str1 = types.InlineKeyboardButton('назад', callback_data='set')
    markup.add(itembtn_str1,)
    msg = bot.edit_message_text(chat_id=query.from_user.id, text=msg, message_id=query.message.id, reply_markup=markup)
    bot.register_next_step_handler(msg,test,msg,key)

def test(message,old_msg,key):
    markup = types.InlineKeyboardMarkup()
    itembtn_str1 = types.InlineKeyboardButton('назад', callback_data='set')
    markup.add(itembtn_str1)
    field = key
    bot.delete_message(chat_id=message.from_user.id,message_id=message.id)
    value = message.text
    #print(field,value)
    config = read_config()
    try:
        if isinstance(config[field], int):
            value = int(value)
        elif isinstance(config[field], float):
            value = float(value)
    except ValueError:
        print('gasdasz')
        bot.edit_message_text(chat_id=message.chat.id, text="Некорректное значение для данного поля.", message_id=old_msg.id, reply_markup=markup)
        return
    print('gz')
    config[field] = value
    write_config(config)
    bot.edit_message_text(chat_id=message.chat.id, text=f"Поле '{field}' успешно обновлено на '{value}'.", message_id=old_msg.id, reply_markup=markup)

@bot.message_handler(commands=['set'])
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
    with open('config.json', 'r') as file:
        config_data = json.load(file)
    response = ""
    for key, value in config_data.items():
        response += f"{key}: {value}\n"
    
    markup = types.InlineKeyboardMarkup()
    itembtn_str1 = types.InlineKeyboardButton('назад', callback_data='menu')
    markup.add(itembtn_str1,)
    bot.edit_message_text(chat_id=query.from_user.id, text=response, message_id=query.message.id, reply_markup=markup)


@bot.message_handler(commands=['setting'])
def lessgo(message):
    with open('config.json', 'r') as file:
        config_data = json.load(file)
    print(config_data)
    response = ""
    for key, value in config_data.items():
        response += f"{key}: {value}\n"
    
    bot.send_message(message.chat.id, response)




@bot.callback_query_handler(lambda query: query.data == "pos")
def lessgo(query):
    # from pnl import current_position
    # res = current_position()
    #res = client.get_position_details(coin)['symbol']
    res = str(client.get_all_position())
    markup = types.InlineKeyboardMarkup()
    itembtn_str1 = types.InlineKeyboardButton('назад', callback_data='menu')
    markup.add(itembtn_str1,)
    bot.edit_message_text(chat_id=query.from_user.id, text=res, message_id=query.message.id, reply_markup=markup)

@bot.message_handler(commands=['pos'])
def lessgo(message):
    # from pnl import current_position
    # res = current_position()
    #res = client.get_position_details(coin)
    res = client.get_all_position()
    bot.send_message(message.chat.id, f"{res}")





@bot.callback_query_handler(lambda query: query.data == "24h_pnl")
def lessgo(query):
    from pnl import calculate_24h_pnl
    res = calculate_24h_pnl()
    markup = types.InlineKeyboardMarkup()
    itembtn_str1 = types.InlineKeyboardButton('назад', callback_data='menu')
    markup.add(itembtn_str1,)
    bot.edit_message_text(chat_id=query.from_user.id, text=f"{res} USDT", message_id=query.message.id, reply_markup=markup)

@bot.message_handler(commands=['24h_pnl'])
def lessgo(message):
    from pnl import calculate_24h_pnl
    res = calculate_24h_pnl()
    bot.send_message(message.chat.id, f"{res} USDT")



# Запуск бота
while True:
    try:
        bot.polling(none_stop=True)
    except Exception as e:
        print(e)
        time.sleep(15)

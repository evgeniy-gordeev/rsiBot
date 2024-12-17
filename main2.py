from kucoin_futures.client import Trade
import telebot
from telebot import types
import time
import json


from kucoin import start_trading_process, stop_trading_process, current_position, calculate_24h_pnl
from rsi import calculate_rsi
from utils import read_config, write_config, create_main_menu_markup

#параметры API(подключения к KuCoin) !!!
api_key = '671647ad5913dd0001518e91'
api_secret = '0c48f805-39ec-49db-b97a-ea3a6595789b'  
api_passphrase = 'VL.45E29ZqN4czL'

#bot KEY
bot_key = "7473391752:AAGAs30m3u_opiNbzJVvE-OhOGYRBmRm4Zg"

#клиент KuCoin
client = Trade(key=api_key, secret=api_secret, passphrase=api_passphrase)
bot = telebot.TeleBot(token=bot_key)

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



# Обработчик нажатия кнопки "Запуск🚀🚀🚀"
@bot.message_handler(func=lambda message: message.text == "Запуск🚀🚀🚀")
def handle_start_trading(message):
    start_trading_process(message.chat.id)

# Обработчик нажатия кнопки "start"
@bot.callback_query_handler(lambda query: query.data == "start")
def handle_start_callback(query):
    start_trading_process(query.from_user.id)
    

# Обработчик нажатия кнопки "STOP❌❌❌"
@bot.message_handler(func=lambda message: message.text == "STOP❌❌❌")
def handle_stop(message):
    stop_trading_process(message.chat.id)

# Обработчик нажатия кнопки "stop"
@bot.callback_query_handler(lambda query: query.data == "stop")
def handle_stop_callback(query):
    stop_trading_process(query.from_user.id)



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
    res = str(client.get_all_position()) #kucoin
    markup = types.InlineKeyboardMarkup()
    itembtn_str1 = types.InlineKeyboardButton('назад', callback_data='menu')
    markup.add(itembtn_str1,)
    bot.edit_message_text(chat_id=query.from_user.id, text=res, message_id=query.message.id, reply_markup=markup)

@bot.message_handler(commands=['pos'])
def lessgo(message):
    res = client.get_all_position() #kucoin
    bot.send_message(message.chat.id, f"{res}")



@bot.callback_query_handler(lambda query: query.data == "24h_pnl")
def lessgo(query):
    res = calculate_24h_pnl()
    markup = types.InlineKeyboardMarkup()
    itembtn_str1 = types.InlineKeyboardButton('назад', callback_data='menu')
    markup.add(itembtn_str1,)
    bot.edit_message_text(chat_id=query.from_user.id, text=f"{res} USDT", message_id=query.message.id, reply_markup=markup)

@bot.message_handler(commands=['24h_pnl'])
def lessgo(message):
    res = calculate_24h_pnl() #kucoin
    bot.send_message(message.chat.id, f"{res} USDT")



# Запуск бота
while True:
    try:
        bot.polling(none_stop=True)
    except Exception as e:
        print(e)
        time.sleep(15)

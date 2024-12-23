import json
import os
from telebot import types

CONFIG_FILE = "config.json"

def read_config(CONFIG_FILE):
    """Чтение конфигурации из файла."""
    if not os.path.exists(CONFIG_FILE):
        raise FileNotFoundError(f"Конфигурационный файл {CONFIG_FILE} не найден.")
    
    try:
        with open(CONFIG_FILE, 'r') as file:
            return json.load(file)
    except json.JSONDecodeError:
        raise ValueError(f"Ошибка при чтении данных из файла {CONFIG_FILE}. Некорректный формат JSON.")
    except Exception as e:
        raise RuntimeError(f"Не удалось прочитать файл {CONFIG_FILE}: {e}")

def write_config(data):
    """Запись конфигурации в файл."""
    try:
        with open(CONFIG_FILE, 'w') as file:
            json.dump(data, file, indent=4)
    except Exception as e:
        raise RuntimeError(f"Не удалось записать данные в файл {CONFIG_FILE}: {e}")


def create_main_menu_markup():
    markup = types.InlineKeyboardMarkup()
    itembtn_str1 = types.InlineKeyboardButton('Запуск🚀🚀🚀', callback_data='start')
    itembtn_str2 = types.InlineKeyboardButton('STOP❌❌❌', callback_data='stop')
    itembtn_str3 = types.InlineKeyboardButton('отобразить настройки', callback_data='settings')
    itembtn_str4 = types.InlineKeyboardButton('изменить настройки', callback_data='set')
    itembtn_str5 = types.InlineKeyboardButton('отобразить позицию', callback_data='pos')
    itembtn_str6 = types.InlineKeyboardButton('calculate_24h_pnl', callback_data='24h_pnl')
    markup.add(itembtn_str1, itembtn_str2)
    markup.add(itembtn_str3)
    markup.add(itembtn_str4)
    markup.add(itembtn_str5)
    markup.add(itembtn_str6)
    return markup

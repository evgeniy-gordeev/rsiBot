import json
import os
from telebot import types

CONFIG_FILE = "config.json"


def read_config(CONFIG_FILE):
    """Чтение конфигурации из файла."""
    if not os.path.exists(CONFIG_FILE):
        raise FileNotFoundError(f"Конфигурационный файл {CONFIG_FILE} не найден.")

    try:
        with open(CONFIG_FILE, "r") as file:
            return json.load(file)
    except json.JSONDecodeError:
        raise ValueError(
            f"Ошибка при чтении данных из файла {CONFIG_FILE}. Некорректный формат JSON."
        )
    except Exception as e:
        raise RuntimeError(f"Не удалось прочитать файл {CONFIG_FILE}: {e}")


def write_config(data):
    """Запись конфигурации в файл."""
    try:
        with open(CONFIG_FILE, "w") as file:
            json.dump(data, file, indent=4)
    except Exception as e:
        raise RuntimeError(f"Не удалось записать данные в файл {CONFIG_FILE}: {e}")


def create_main_menu_markup():
    markup = types.InlineKeyboardMarkup()
    itembtn_str0 = types.InlineKeyboardButton("Запуск клиента", callback_data="init_client")
    itembtn_str1 = types.InlineKeyboardButton("Запуск🚀🚀🚀", callback_data="start")
    itembtn_str2 = types.InlineKeyboardButton("STOP❌❌❌", callback_data="stop")
    itembtn_str3 = types.InlineKeyboardButton(
        "Отобразить настройки", callback_data="settings"
    )
    itembtn_str4 = types.InlineKeyboardButton("изменить настройки", callback_data="set")
    itembtn_str5 = types.InlineKeyboardButton("Отобразить позицию", callback_data="pos")
    itembtn_str6 = types.InlineKeyboardButton(
        "calculate_24h_pnl", callback_data="24h_pnl"
    )
    itembtn_str7 = types.InlineKeyboardButton(
        "Выбрать биржу", callback_data="choose_stock"
    )
    itembtn_str8 = types.InlineKeyboardButton(
        "Поддержать проект", callback_data="buy"
    )
    itembtn_str9 = types.InlineKeyboardButton(
        "Статус подписки", callback_data="subscription_status"
    )
    itembtn_str10 = types.InlineKeyboardButton(
        "Выбрать пару", callback_data="choose_pair"
    )
    itembtn_str11 = types.InlineKeyboardButton(
        "Выбрать size", callback_data="choose_size"
    )
    itembtn_str12 = types.InlineKeyboardButton(
        "О СЕРВИСЕ", url='https://glens-organization-1.gitbook.io/rsioboarding/quickstart'
    )
    # itembtn_str_ = types.InlineKeyboardButton(
    #     "TECH SUPPORT 🧑‍💻", url = "t.me/@gordeevlabs"
    # )
    # markup.add(itembtn_str_)
    itembtn_str__ = types.InlineKeyboardButton(
        "НОВОСТИ", url = "t.me/@tradestartegies700"
    )
    itembtn_str___ = types.InlineKeyboardButton(
        "ОТЗЫВЫ", url = "t.me/@vacuum_feedback"
    )
    itembtn_str____ = types.InlineKeyboardButton(
        "БАГИ 🐞", url = "t.me/@vacuum_issues"
    )                                   
    markup.add(itembtn_str7,itembtn_str10,itembtn_str11)
    markup.add(itembtn_str0)
    markup.add(itembtn_str1, itembtn_str2)
    markup.add(itembtn_str3)
    markup.add(itembtn_str5, itembtn_str6)
    markup.add(itembtn_str8)
    markup.add(itembtn_str12, itembtn_str__)
    #markup.add(itembtn_str_)
    #markup.add(itembtn_str__)
    markup.add(itembtn_str___, itembtn_str____)
    #markup.add(itembtn_str____)      
    return markup



def create_stock_choose():
    markup = types.InlineKeyboardMarkup()
    itembtn_str1 = types.InlineKeyboardButton("Binance", callback_data="binance")
    itembtn_str2 = types.InlineKeyboardButton("Bybit", callback_data="bybit")
    itembtn_str3 = types.InlineKeyboardButton("KuCoin", callback_data="kucoin")
    itembtn_str4 = types.InlineKeyboardButton("Назад", callback_data="menu")
    markup.add(itembtn_str1)
    markup.add(itembtn_str2)
    markup.add(itembtn_str3)
    markup.add(itembtn_str4)
    return markup


def back_menu_button():
    markup = types.InlineKeyboardMarkup()
    itembtn_str1 = types.InlineKeyboardButton("Назад", callback_data="menu")
    markup.add(itembtn_str1)
    return markup


def main_menu_button():
    markup = types.InlineKeyboardMarkup()
    itembtn_str1 = types.InlineKeyboardButton("Главное меню", callback_data="menu")
    markup.add(itembtn_str1)
    return markup

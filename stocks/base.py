from telebot import TeleBot

from utils import create_main_menu_markup
from rsi import calculate_rsi


class BaseStock():
    time_sleep = 5
    is_running = False
    open_counter = 0
    close_counter = 0

    def __init__(self, bot, chat_id, after_init_handle_function, config):
        self.bot: TeleBot = bot 
        self.chat_id = chat_id
        self.after_init = after_init_handle_function
        self.client = None
        self.config = config
        self.calculate_rsi = calculate_rsi
    
    def main_menu(self, message_id):
        markup = create_main_menu_markup()
        response = "ГЛАВНОЕ МЕНЮ"
        self.bot.edit_message_text(chat_id=self.chat_id, text=response, message_id=message_id, reply_markup=markup)

    def start_trading_process(self, chat_id):
        pass

    def stop_trading_process(self, chat_id):
        pass

    def get_all_position(self):
        pass
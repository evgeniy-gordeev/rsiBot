import datetime

from telebot import TeleBot
from sqlalchemy import create_engine, text
from sqlalchemy.engine.base import Engine

from utils import create_main_menu_markup, back_menu_button


class BaseStock:
    time_sleep = 1
    is_running = False
    open_counter = 0
    close_counter = 0

    def __init__(self, bot, chat_id, after_init_handle_function, config, engine):
        self.bot: TeleBot = bot
        self.chat_id = chat_id
        self.after_init = after_init_handle_function
        self.client = None
        self.config = config
        self.back_menu_button = back_menu_button
        self.type = None
        self.open_counter=0
        self.close_counter=0
        self.deposit=0
        self.is_running=False
        self.session_pnl = 0
        self.animation = [
            "[■□□□□□□□□□]",
            "[■■□□□□□□□□]",
            "[■■■□□□□□□□]",
            "[■■■■□□□□□□]",
            "[■■■■■□□□□□]",
            "[■■■■■■□□□□]",
            "[■■■■■■■□□□]",
            "[■■■■■■■■□□]",
            "[■■■■■■■■■□]",
            "[■■■■■■■■■■]",
        ]
        self.time_wait = 7
        self.engine: Engine = engine

    def main_menu(self, message_id):
        markup = create_main_menu_markup()
        response = "ГЛАВНОЕ МЕНЮ"
        self.bot.edit_message_text(
            chat_id=self.chat_id,
            text=response,
            message_id=message_id,
            reply_markup=markup,
        )

    def start_trading_process(self, chat_id, message):
        pass

    def stop_trading_process(self, chat_id, message):
        pass

    def get_all_position(self):
        pass

    def update_leaderboard(self, pnl):
        with self.engine.begin() as connection:
            connection.execute(text(f"DELETE FROM leaderboard WHERE subs_id = {self.chat_id} and stock_type = '{self.type}'"))
            connection.commit()

        with self.engine.begin() as connection:
            start = datetime.datetime.now()
            parameters = {
                "subs_id": self.chat_id,
                "date_pnl": start.strftime("%Y-%m-%d %H:%M:%S"),
                "pnl": pnl,
                "stock_type": self.type,
            }
            connection.execute(text('INSERT INTO leaderboard (subs_id, date_pnl, pnl, stock_type) VALUES (:subs_id, :date_pnl, :pnl, :stock_type)'), parameters)
            connection.commit()

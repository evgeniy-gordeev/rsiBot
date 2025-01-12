import time
from datetime import datetime
import pdb

from kucoin_futures.client import Trade, Market, User
from telebot import types
import pandas as pd
import numpy as np

from .base import BaseStock


class KucoinStock(BaseStock):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client: Trade
        self.market: Market
        self.user: User
        self.type = 'kucoin'

    def get_keys(self, message_id, prefix_text=""):
        text = "\n".join(
            [
                "Enter keys in order:",
                "*API_KEY*",
                "*API_SECRET*",
                "*API_PASSPHRASE*",
            ]
        )
        if prefix_text:
            text = "\n".join([prefix_text, text])
        markup = self.back_menu_button()
        msg = self.bot.edit_message_text(
            chat_id=self.chat_id,
            text=text,
            message_id=message_id,
            reply_markup=markup,
            parse_mode="Markdown",
        )
        self.msg = msg
        self.bot.register_next_step_handler(msg, self.parse_api_keys, message_id)

    def parse_api_keys(self, msg, message_id):
        self.api_key, self.api_secret, self.api_passphrase = msg.text.split("\n")
        self.bot.delete_message(self.chat_id, msg.id)
        self.init_client()
        if self.check_client(message_id):
            self.main_menu(message_id)
        else:
            self.get_keys(message_id, "Error 🚫 in your API keys. Please retry.")

    def init_client(self):
        self.client = Trade(
            key=self.api_key,
            secret=self.api_secret,
            passphrase=self.api_passphrase,
        )

        self.market = Market(
            key=self.api_key,
            secret=self.api_secret,
            passphrase=self.api_passphrase,
        )

        self.user = User(
            key=self.api_key,
            secret=self.api_secret,
            passphrase=self.api_passphrase,
        )        

    def check_client(self, message_id):
        for i in range(len(self.animation)):
            text = (
                "Проверка API ключей  " + "\r" + self.animation[i % len(self.animation)]
            )
            self.bot.edit_message_text(
                chat_id=self.chat_id,
                text=text,
                message_id=message_id,
                parse_mode="Markdown",
            )
            time.sleep(0.05)

        try:
            self.client.get_all_position()
            return True
        except:
            return False

    def calculate_rsi(self):
        klines = self.market.get_kline_data(
            symbol=self.config["coin"], granularity=self.config["tf"]
        )

        for el in klines:
            el[0] = datetime.fromtimestamp(int(el[0]) / 1000)

        df = pd.DataFrame(
            {
                "dt": [x[0] for x in klines],
                "open": [x[1] for x in klines],
                "close": [x[4] for x in klines],
            }
        )

        df["u"] = np.where(df.close > df.open, df.close - df.open, 0)
        df["d"] = np.where(df.close < df.open, df.open - df.close, 0)

        df[f'ema_{self.config["n_periods"]}_u'] = df.u.ewm(
            alpha=1 / self.config["n_periods"], adjust=True
        ).mean()
        df[f'ema_{self.config["n_periods"]}_d'] = df.d.ewm(
            alpha=1 / self.config["n_periods"], adjust=True
        ).mean()

        df["rs"] = (
            df[f'ema_{self.config["n_periods"]}_u']
            / df[f'ema_{self.config["n_periods"]}_d']
        )
        df["rsi"] = 100 - 100 / (1 + df["rs"])

        return df["rsi"].tail(1).values[0]

    def start_trading_process(self, chat_id, message):
        if self.is_running:
            msg = self.bot.send_message(chat_id, "Торговля уже запущена.")
            time.sleep(self.time_sleep)
            self.bot.delete_message(self.chat_id, msg.message_id)
            return

        self.is_running = True
        self.bot.edit_message_text(f"Поиск сделки по {self.config['coin']}", chat_id=chat_id, message_id=message.id, reply_markup=message.reply_markup)
        self.open_counter = 0
        self.close_counter = 0
        self.msg_id = None

        try:
            while self.is_running:
                current_rsi = self.calculate_rsi()
                try:
                    positions = self.client.get_all_position()
                    open_position = isinstance(positions, list) and len(positions) > 0
                except Exception as e:
                    msg = self.bot.send_message(chat_id, f"Ошибка получения позиций: {e}")
                    time.sleep(self.time_sleep)
                    self.bot.delete_message(self.chat_id, msg.message_id)
                    open_position = False

                if open_position:
                    position = positions[0]
                    long_position = position["currentQty"] > 0
                    short_position = position["currentQty"] < 0
                else:
                    long_position = short_position = False

                # Открытие позиций
                if not open_position:
                    try:
                        if current_rsi >= self.config["up_border"]:
                            self.client.create_market_order(
                                self.config["coin"],
                                "sell",
                                self.config["leverage"],
                                size=self.config["size"],
                            )
                            self.open_counter += 1
                        elif current_rsi <= self.config["low_border"]:
                            self.client.create_market_order(
                                self.config["coin"],
                                "buy",
                                self.config["leverage"],
                                size=self.config["size"],
                            )
                            self.open_counter += 1
                    except Exception as e:
                        msg = self.bot.send_message(
                            chat_id, f"Ошибка при открытии позиции: {e}"
                        )
                        time.sleep(self.time_sleep)
                        self.bot.delete_message(self.chat_id, msg.message_id)
                        self.stop_trading_process(chat_id, message)

                # Закрытие позиций
                if open_position:
                    try:
                        if (
                            long_position
                            and current_rsi >= self.config["long_stop_border"]
                        ):
                            self.client.create_market_order(
                                self.config["coin"],
                                "sell",
                                self.config["leverage"],
                                size=self.config["size"],
                            )
                            self.close_counter += 1
                        elif (
                            short_position
                            and current_rsi <= self.config["short_close_border"]
                        ):
                            self.client.create_market_order(
                                self.config["coin"],
                                "buy",
                                self.config["leverage"],
                                size=self.config["size"],
                            )
                            self.close_counter += 1
                    except Exception as e:
                        msg = self.bot.send_message(
                            chat_id, f"Ошибка при закрытии позиции: {e}"
                        )
                        time.sleep(self.time_sleep)
                        self.bot.delete_message(self.chat_id, msg.message_id)
                        self.stop_trading_process(chat_id, message)

                # Отправка обновления статуса
                current_price = self.market.get_current_mark_price(symbol=self.config["coin"])['value']
                usdt_balance = self.user.get_account_overview(currency='USDT')['accountEquity']
                deposit = self.config['size']*current_price * int(self.config['leverage'])
                #deposit = usdt_trading_balance if float(usdt_balance) >= usdt_trading_balance else 0   
                # 
                pnl = self.calculate_24h_pnl()
                self.update_leaderboard(pnl)             
                status_message = (
                    f"`{datetime.now().strftime('%H:%M:%S  %d-%m-%Y')}`\n"
                    f"RSI: {round(current_rsi, 2)}\n"                        
                    f"Открытых сделок: {self.open_counter}\n"
                    f"Закрытых сделок: {self.close_counter}\n\n"
                    f"Deposit: {deposit}\n"
                    f"PnL: {pnl}"
                )

                reply_markup = message.reply_markup

                self.bot.edit_message_text(
                    chat_id=chat_id,
                    text=status_message,
                    message_id=message.id,
                    reply_markup=reply_markup,
                    parse_mode="Markdown",
                )

                time.sleep(self.time_sleep)
        except Exception as e:
            msg = self.bot.send_message(chat_id, f"Произошла ошибка в торговом цикле: {e}")
            time.sleep(self.time_sleep)
            self.bot.delete_message(self.chat_id, msg.message_id)
            is_running = False

    # Функция для остановки процесса торговли
    def stop_trading_process(self, chat_id, message):

        if not self.is_running:
            msg = self.bot.send_message(chat_id, "Торговля уже остановлена.")
            time.sleep(self.time_sleep)
            self.bot.delete_message(self.chat_id, msg.message_id)
            return

        self.is_running = False
        print("IS_RUNNING", self.is_running)

        # Закрытие позиций
        try:
            positions = self.client.get_all_position()
            open_position = isinstance(positions, list) and len(positions) > 0
            if open_position:
                position = positions[0]
                if position["currentQty"] > 0:
                    self.client.create_market_order(
                        self.config["coin"],
                        "sell",
                        self.config["leverage"],
                        size=self.config["size"],
                    )
                    self.bot.edit_message_text(f"Закрыта длинная позиция по {self.config['coin']}",
                        chat_id, message_id=message.id, reply_markup=message.reply_markup
                    )
                elif position["currentQty"] < 0:
                    self.client.create_market_order(
                        self.config["coin"],
                        "buy",
                        self.config["leverage"],
                        size=self.config["size"],
                    )
                    self.bot.edit_message_text(f"Закрыта короткая позиция по {self.config['coin']}",
                        chat_id, message_id=message.id, reply_markup=message.reply_markup
                    )

            self.bot.edit_message_text(message.text + '\n--Робот остановлен. Все позиции закрыты.-- \n',
                    chat_id, message_id=message.id, reply_markup=message.reply_markup
                )
        except Exception as e:
            msg = self.bot.send_message(chat_id, f"Ошибка при закрытии позиций: {e}")
            time.sleep(self.time_sleep)
            self.bot.delete_message(self.chat_id, msg.message_id)

        # Вычисление PnL
        try:
            rev = self.calculate_24h_pnl()
            if rev >= 0:
                text_to_add = f"\nВаш профит составил {rev} USDT"
            else:
                text_to_add = f"\nВаш убыток составил {rev} USDT"

            self.bot.edit_message_text(message.text + text_to_add,
                    chat_id, message_id=message.id, reply_markup=message.reply_markup
                )
            
        except Exception as e:
            msg = self.bot.send_message(chat_id, f"Ошибка при вычислении PnL: {e}")
            time.sleep(self.time_sleep)
            self.bot.delete_message(self.chat_id, msg.message_id)

    # Функия показывающая текущую позицию
    def current_position(self):
        res = self.client.get_all_position()
        return res

    # Функия показывающая прибыль
    def calculate_24h_pnl(self):
        res = self.client.get_24h_done_order()
        if not isinstance(res, list):
            return 0
        res = pd.json_normalize(res)

        res["createdAt"] = res["createdAt"].apply(
            lambda x: datetime.fromtimestamp(x / 1000).strftime("%H:%M")
        )
        res["endAt"] = res["endAt"].apply(
            lambda x: datetime.fromtimestamp(x / 1000).strftime("%H:%M")
        )

        def calculate_total_pnl(df):
            df["value"] = pd.to_numeric(df["value"], errors="coerce")

            total_pnl = 0
            open_position = None
            entry_price = None

            maker_fee = 0.0002
            taker_fee = 0.0006

            for index, row in df.iterrows():
                if open_position is None:
                    # Открытие новой позиции
                    open_position = row["side"]
                    entry_price = row["value"]
                else:
                    # Закрытие позиции
                    if (open_position == "buy" and row["side"] == "sell") or (
                        open_position == "sell" and row["side"] == "buy"
                    ):
                        if open_position == "buy":
                            pnl = row["value"] - entry_price
                            pnl -= row["value"] * taker_fee + entry_price * maker_fee
                        else:
                            pnl = entry_price - row["value"]
                            pnl -= row["value"] * taker_fee + entry_price * maker_fee
                        total_pnl += pnl

                        # Сброс позиции после её закрытия
                        open_position = None
                        entry_price = None

            # Если осталась открытая позиция, она не включена в итоговый PnL
            if open_position is not None:
                print(
                    f"Warning: There is an open {open_position} position that hasn't been closed yet."
                )

            return round(total_pnl, 3)

        total_pnl = calculate_total_pnl(res)
        return total_pnl

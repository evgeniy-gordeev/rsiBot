import time
from datetime import datetime
import numpy as np
import pandas as pd
import pdb

from binance.client import Client
from binance.exceptions import BinanceAPIException

from .base import BaseStock


class BinanceStock(BaseStock):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.type = 'binance'

    def get_keys(self, message_id, prefix_text=""):
        text = "\n".join(["Enter keys in order:", "*API_KEY*", "*API_SECRET*"])
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
        self.api_key, self.api_secret = msg.text.split("\n")
        self.bot.delete_message(self.chat_id, msg.id)
        self.init_client()

        if self.check_client(message_id):
            self.main_menu(message_id)
        else:
            self.get_keys(message_id, "Error 🚫 in your API keys. Please retry.")

    def init_client(self):
        self.client = Client(
            api_key=self.api_key,
            api_secret=self.api_secret,
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
            self.client.get_account_status()
            return True
        except BinanceAPIException:
            return False

    def calculate_rsi(self):
        if isinstance(self.config["tf"], int):
            interval = str(self.config["tf"]) + "m"
        else:
            interval = self.config["tf"]
        klines = self.client.get_klines(symbol=self.config["coin"], interval=interval)
        for el in klines:
            el[0] = datetime.fromtimestamp(int(el[0]) / 1000)

        df = pd.DataFrame(
            {
                "dt": [x[0] for x in klines],
                "open": [x[1] for x in klines],
                "close": [x[4] for x in klines],
            }
        )
        df["open"] = df["open"].astype(float)
        df["close"] = df["close"].astype(float)

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
        leverage = int(self.config["leverage"])
        self.msg_id = None

        try:
            while self.is_running:
                current_rsi = self.calculate_rsi()
                try:
                    positions = self.client.futures_position_information()
                    open_position = isinstance(positions, list) and len(positions) > 0
                except Exception as e:
                    msg = self.bot.send_message(chat_id, f"Ошибка получения позиций: {e}")
                    time.sleep(self.time_sleep)
                    self.bot.delete_message(self.chat_id, msg.message_id)
                    open_position = False

                if open_position:
                    position = positions[0]
                    long_position = float(position["positionAmt"]) > 0
                    short_position = float(position["positionAmt"]) < 0
                else:
                    long_position = short_position = False

                # Открытие позиций
                if not open_position:
                    try:
                        if current_rsi >= self.config["up_border"]:
                            self.client.futures_change_leverage(
                                symbol=self.config["coin"], leverage=leverage
                            )
                            self.client.futures_create_order(
                                symbol=self.config["coin"],
                                side="SELL",
                                type="MARKET",
                                quantity=self.config["size"],
                            )
                            self.open_counter += 1
                        elif current_rsi <= self.config["low_border"]:
                            self.client.futures_change_leverage(
                                symbol=self.config["coin"], leverage=leverage
                            )
                            self.client.futures_create_order(
                                symbol=self.config["coin"],
                                side="BUY",
                                type="MARKET",
                                quantity=self.config["size"],
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
                            self.client.futures_change_leverage(
                                symbol=self.config["coin"], leverage=leverage
                            )
                            self.client.futures_create_order(
                                symbol=self.config["coin"],
                                side="SELL",
                                type="MARKET",
                                quantity=self.config["size"],
                            )
                            self.close_counter += 1
                        elif (
                            short_position
                            and current_rsi <= self.config["short_close_border"]
                        ):
                            self.client.futures_change_leverage(
                                symbol=self.config["coin"], leverage=leverage
                            )
                            self.client.futures_create_order(
                                symbol=self.config["coin"],
                                side="BUY",
                                type="MARKET",
                                quantity=self.config["size"],
                            )
                            self.close_counter += 1
                    except Exception as e:
                        msg = self.bot.send_message(
                            chat_id, f"Ошибка при закрытии позиции: {e}"
                        )
                        time.sleep(self.time_sleep)
                        self.bot.delete_message(self.chat_id, msg.message_id)
                        self.stop_trading_process(chat_id, message)

                if self.is_running:
                    # Отправка обновления статуса
                    ticker = self.client.futures_symbol_ticker(symbol=self.config["coin"])
                    current_price = float(ticker['price'])
                    balances = self.client.futures_account_balance()
                    usdt_balance = next((item for item in balances if item['asset'] == 'USDT'), None)
                    usdt_trading_balance = self.config['size']*current_price
                    deposit = usdt_trading_balance if float(usdt_balance['balance']) >= usdt_trading_balance else 0

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
                    # for row in reply_markup.keyboard:
                    #     for i, elem in enumerate(row):
                    #         if elem.callback_data == 'start':
                    #             elem.text = status_message
                    #             # row[i] = elem
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
            self.is_running = False

    # Функция для остановки процесса торговли
    def stop_trading_process(self, chat_id, message):
        if not self.is_running:
            msg = self.bot.send_message(chat_id, "Торговля уже остановлена.")
            time.sleep(self.time_sleep)
            self.bot.delete_message(self.chat_id, msg.message_id)
            return

        self.is_running = False
        print("IS_RUNNING", self.is_running)

        leverage = int(self.config["leverage"])

        # Закрытие позиций
        try:
            positions = self.client.futures_position_information()
            open_position = isinstance(positions, list) and len(positions) > 0
            if open_position:
                position = positions[0]
                if float(position["positionAmt"]) > 0:
                    self.client.futures_change_leverage(
                        symbol=self.config["coin"], leverage=leverage
                    )
                    self.client.futures_create_order(
                        symbol=self.config["coin"],
                        side="SELL",
                        type="MARKET",
                        quantity=self.config["size"],
                    )
                    self.bot.edit_message_text(f"Закрыта длинная позиция по {self.config['coin']}",
                        chat_id, message_id=message.id, reply_markup=message.reply_markup
                    )
                elif float(position["positionAmt"]) < 0:
                    self.client.futures_change_leverage(
                        symbol=self.config["coin"], leverage=leverage
                    )
                    self.client.futures_create_order(
                        symbol=self.config["coin"],
                        side="BUY",
                        type="MARKET",
                        quantity=self.config["size"],
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

            self.bot.edit_message_text(message.text + '\n--Робот остановлен. Все позиции закрыты.--' + text_to_add,
                    chat_id, message_id=message.id, reply_markup=message.reply_markup
                )
            
        except Exception as e:
            msg = self.bot.send_message(chat_id, f"Ошибка при вычислении PnL: {e}")
            time.sleep(self.time_sleep)
            self.bot.delete_message(self.chat_id, msg.message_id)


    # Функия показывающая текущую позицию
    def current_position(self):
        res = self.client.futures_position_information(symbol=self.config["coin"])
        if len(res) > 0:
            return res[0]
        return res

    # Функия показывающая прибыль
    def calculate_24h_pnl(self):
        now = int(datetime.now().timestamp() * 1000)
        now_24h_ago = int((datetime.now().timestamp() - 24 * 60 * 60) * 1000)

        res = self.client.futures_account_trades(
            symbol=self.config["coin"], startTime=now_24h_ago, endTime=now
        )
        res = pd.json_normalize(res)

        if "realizedPnl" in res.columns:
            res["realizedPnl"] = res["realizedPnl"].astype(float)
            total_pnl = float(res["realizedPnl"].sum())
        else:
            total_pnl = 0
        return total_pnl
    
    def calculate_deposit(self):
        now = int(datetime.now().timestamp() * 1000)
        now_24h_ago = int((datetime.now().timestamp() - 24 * 60 * 60) * 1000)

        res = self.client.futures_account_trades(
            symbol=self.config["coin"], startTime=now_24h_ago, endTime=now
        )
        res = pd.json_normalize(res)

        if "realizedPnl" in res.columns:
            res["realizedPnl"] = res["realizedPnl"].astype(float)
            total_pnl = float(res["realizedPnl"].sum())
        else:
            total_pnl = 0
        return total_pnl    

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

    def start_trading_process(self, chat_id):
        if self.is_running:
            self.bot.send_message(chat_id, "Торговля уже запущена.")
            return

        self.is_running = True
        self.bot.send_message(chat_id, f"Поиск сделки по {self.config['coin']}")
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
                    self.bot.send_message(chat_id, f"Ошибка получения позиций: {e}")
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
                        self.bot.send_message(
                            chat_id, f"Ошибка при открытии позиции: {e}"
                        )
                        self.stop_trading_process(chat_id)

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
                        self.bot.send_message(
                            chat_id, f"Ошибка при закрытии позиции: {e}"
                        )
                        self.stop_trading_process(chat_id)

                # Отправка обновления статуса
                status_message = (
                    f"`{datetime.now().strftime("%H:%M:%S  %d-%m-%Y")}`\n"
                    f"RSI: {round(current_rsi, 2)}\n"
                    f"Открытых сделок: {self.open_counter}\n"
                    f"Закрытых сделок: {self.close_counter}"
                )

                if self.msg_id:
                    status_msg = self.bot.edit_message_text(
                        chat_id=chat_id,
                        text=status_message,
                        message_id=self.msg_id,
                        parse_mode="Markdown",
                    )
                else:
                    status_msg = self.bot.send_message(
                        chat_id, status_message, parse_mode="Markdown"
                    )
                    self.msg_id = status_msg.id

                time.sleep(self.time_sleep)
        except Exception as e:
            self.bot.send_message(chat_id, f"Произошла ошибка в торговом цикле: {e}")
            self.is_running = False

    # Функция для остановки процесса торговли
    def stop_trading_process(self, chat_id):

        if not self.is_running:
            self.bot.send_message(chat_id, "Торговля уже остановлена.")
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
                    self.bot.send_message(
                        chat_id, f"Закрыта длинная позиция по {self.config['coin']}"
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
                    self.bot.send_message(
                        chat_id, f"Закрыта короткая позиция по {self.config['coin']}"
                    )

            self.bot.send_message(
                chat_id, f"--Робот остановлен. Все позиции закрыты.--\n"
            )
        except Exception as e:
            self.bot.send_message(chat_id, f"Ошибка при закрытии позиций: {e}")

        # Вычисление PnL
        try:
            rev = self.calculate_24h_pnl()
            if rev >= 0:
                self.bot.send_message(chat_id, f"Ваш профит составил {rev} USDT")
            else:
                self.bot.send_message(chat_id, f"Ваш убыток составил {rev} USDT")
        except Exception as e:
            self.bot.send_message(chat_id, f"Ошибка при вычислении PnL: {e}")

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

from datetime import datetime
import time
import pdb

import pandas as pd
import numpy as np
from pybit.unified_trading import HTTP
from pybit.exceptions import InvalidRequestError

from .base import BaseStock


class BybitStock(BaseStock):
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
        self.client = HTTP(
            testnet=False,
            api_key=self.api_key,
            api_secret=self.api_secret,
        )
        self.client.ignore_codes.add(110043)

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
            self.client.get_account_info()
            return True
        except InvalidRequestError:
            return False

    def calculate_rsi(self):
        klines = self.client.get_kline(
            symbol=self.config["coin"], interval=self.config["tf"], limit=500
        )["result"]["list"]
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
        self.msg_id = None

        try:
            self.client.set_leverage(
                category="linear",
                symbol=self.config["coin"],
                buyLeverage=self.config["leverage"],
                sellLeverage=self.config["leverage"],
            )
        except:
            pass

        try:
            while self.is_running:
                current_rsi = self.calculate_rsi()

                try:
                    positions = self.client.get_positions(
                        category="linear", symbol=self.config["coin"]
                    )
                    positions = positions["result"]["list"]
                    open_position = (
                        isinstance(positions, list)
                        and len(positions) > 0
                        and positions[0]["side"]
                    )
                except Exception as e:
                    msg = self.bot.send_message(chat_id, f"Ошибка получения позиций: {e}")
                    time.sleep(self.time_sleep)
                    self.bot.delete_message(self.chat_id, msg.message_id)
                    open_position = False

                if open_position:
                    position = positions[0]
                    long_position = position["side"] == "Buy"
                    short_position = position["side"] == "Sell"
                else:
                    long_position = short_position = False

                # Открытие позиций
                if not open_position:
                    try:
                        if current_rsi >= self.config["up_border"]:
                            self.client.place_order(
                                category="linear",
                                symbol=self.config["coin"],
                                side="Sell",
                                orderType="Market",
                                qty=self.config["size"],
                            )
                            self.open_counter += 1
                        elif current_rsi <= self.config["low_border"]:
                            self.client.place_order(
                                category="linear",
                                symbol=self.config["coin"],
                                side="Buy",
                                orderType="Market",
                                qty=self.config["size"],
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
                            self.client.place_order(
                                category="linear",
                                symbol=self.config["coin"],
                                side="Sell",
                                orderType="Market",
                                qty=self.config["size"],
                            )
                            self.close_counter += 1

                        elif (
                            short_position
                            and current_rsi <= self.config["short_close_border"]
                        ):
                            self.client.place_order(
                                category="linear",
                                symbol=self.config["coin"],
                                side="Buy",
                                orderType="Market",
                                qty=self.config["size"],
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
                ticker = self.client.get_tickers(category="linear",symbol=self.config["coin"])
                current_price = float(ticker['result']['list'][0]['lastPrice'])
                response = self.client.get_wallet_balance(accountType="UNIFIED")
                coins = response['result']['list'][0]['coin']
                usdt_balance = next((item for item in coins if item['coin'] == 'USDT'), None)
                usdt_trading_balance = self.config['size']*current_price
                deposit =  usdt_trading_balance if float(usdt_balance['usdValue']) >= usdt_trading_balance else 0

                status_message = (
                    f"`{datetime.now().strftime('%H:%M:%S  %d-%m-%Y')}`\n"
                    f"RSI: {round(current_rsi, 2)}\n"                        
                    f"Открытых сделок: {self.open_counter}\n"
                    f"Закрытых сделок: {self.close_counter}\n\n"
                    f"Deposit: {deposit}\n"
                    f"PnL: {self.calculate_24h_pnl()}"
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

        try:
            self.client.set_leverage(
                category="linear",
                symbol=self.config["coin"],
                buyLeverage=self.config["leverage"],
                sellLeverage=self.config["leverage"],
            )
        except:
            pass

        # Закрытие позиций
        try:
            positions = self.client.get_positions(
                category="linear", symbol=self.config["coin"]
            )
            positions = positions["result"]["list"]
            open_position = (
                isinstance(positions, list)
                and len(positions) > 0
                and positions[0]["side"]
            )
            if open_position:
                position = positions[0]
                if position["side"] == "Buy":
                    self.client.place_order(
                        category="linear",
                        symbol=self.config["coin"],
                        side="Sell",
                        orderType="Market",
                        qty=self.config["size"],
                    )
                    self.bot.edit_message_text(f"Закрыта длинная позиция по {self.config['coin']}",
                        chat_id, message_id=message.id, reply_markup=message.reply_markup
                    )
                elif position["side"] == "Sell":
                    self.client.place_order(
                        category="linear",
                        symbol=self.config["coin"],
                        side="Buy",
                        orderType="Market",
                        qty=self.config["size"],
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
        res = self.client.get_positions(category="linear", symbol=self.config["coin"])
        if len(res["result"]["list"]) > 0 and res["result"]["list"][0]["side"]:
            return res["result"]["list"]
        return "Нет открытых позиций"

    # Функия показывающая прибыль
    def calculate_24h_pnl(self):
        now = int(datetime.now().timestamp() * 1000)
        now_24h_ago = int((datetime.now().timestamp() - 24 * 60 * 60) * 1000)

        res = self.client.get_closed_pnl(
            category="linear",
            symbol=self.config["coin"],
            startTime=now_24h_ago,
            endTime=now,
        )

        if len(res["result"]["list"]) > 0:
            total_pnl = float(res["result"]["list"][0]["closedPnl"])
        else:
            total_pnl = 0
        return total_pnl

from datetime import datetime
import time
import pdb

import pandas as pd 
import numpy as np
from pybit.unified_trading import HTTP

from .base import BaseStock 


class BybitStock(BaseStock):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def get_keys(self, message_id):
        text = '\n'.join(["Enter keys in order:", "API_KEY", "API_SECRET"])
        msg = self.bot.edit_message_text(chat_id=self.chat_id, text=text, message_id=message_id)
        self.msg = msg
        self.bot.register_next_step_handler(msg, self.parse_api_keys, message_id)

    def parse_api_keys(self, msg, message_id):
        self.api_key, self.api_secret = msg.text.split("\n")
        self.bot.delete_message(self.chat_id, msg.id)
        self.init_client()
        self.main_menu(message_id)

    def init_client(self):
        self.client = HTTP(
            testnet=False,
            api_key=self.api_key, 
            api_secret=self.api_secret, 
        )
        self.client.ignore_codes.add(110043)
    
    def calculate_rsi(self):
        klines = self.client.get_kline(symbol=self.config['coin'], interval=self.config['tf'], limit=500)['result']['list']
        for el in klines:
            el[0] = datetime.fromtimestamp(int(el[0])/1000)
        
        df = pd.DataFrame({
            'dt': [x[0] for x in klines],
            'open': [x[1] for x in klines],
            'close': [x[4] for x in klines]
        })
        df['open'] = df['open'].astype(float)
        df['close'] = df['close'].astype(float)

        df['u'] = np.where(df.close > df.open, df.close - df.open, 0)
        df['d'] = np.where(df.close < df.open, df.open - df.close, 0)

        df[f'ema_{self.config["n_periods"]}_u'] = df.u.ewm(alpha=1/self.config["n_periods"], adjust=True).mean()
        df[f'ema_{self.config["n_periods"]}_d'] = df.d.ewm(alpha=1/self.config["n_periods"], adjust=True).mean()

        df['rs'] = df[f'ema_{self.config["n_periods"]}_u'] / df[f'ema_{self.config["n_periods"]}_d']
        df['rsi'] = 100 - 100 / (1 + df['rs'])
        return df['rsi'].tail(1).values[0]
            
    def start_trading_process(self, chat_id):
        if self.is_running:
            self.bot.send_message(chat_id, "Торговля уже запущена.")
            return

        self.is_running = True
        self.bot.send_message(chat_id, f"Поиск сделки по {self.config['coin']}")
        self.open_counter = 0
        self.close_counter = 0
        self.msg_id = None

        try:
            self.client.set_leverage(category='linear', 
                                            symbol=self.config['coin'],
                                            buyLeverage=self.config['leverage'], 
                                            sellLeverage=self.config['leverage'])
        except:
            pass

        try:
            while self.is_running:
                current_rsi = self.calculate_rsi()

                try:
                    positions = self.client.get_positions(category='linear', symbol=self.config['coin'])
                    positions = positions['result']['list']
                    open_position = isinstance(positions, list) and len(positions) > 0 and positions[0]['side']
                except Exception as e:
                    self.bot.send_message(chat_id, f"Ошибка получения позиций: {e}")
                    open_position = False

                if open_position:
                    position = positions[0]
                    long_position = position['side'] == 'Buy'
                    short_position = position['side'] == 'Sell'
                else:
                    long_position = short_position = False

                # Открытие позиций
                if not open_position:
                    try:
                        if current_rsi >= self.config['up_border']:
                            self.client.place_order(category='linear', symbol=self.config['coin'], side='Sell', orderType='Market', qty=self.config['size'])
                            self.open_counter += 1
                            # self.bot.send_message(chat_id, f"Открыта короткая позиция по {self.config['coin']}")
                        elif current_rsi <= self.config['low_border']:
                            self.client.place_order(category='linear', symbol=self.config['coin'], side='Buy', orderType='Market', qty=self.config['size'])
                            self.open_counter += 1
                            # self.bot.send_message(chat_id, f"Открыта длинная позиция по {self.config['coin']}")
                    except Exception as e:
                        self.bot.send_message(chat_id, f"Ошибка при открытии позиции: {e}")

                # Закрытие позиций
                if open_position:
                    try:
                        if long_position and current_rsi >= self.config['long_stop_border']:
                            self.client.place_order(category='linear', symbol=self.config['coin'], side='Sell', orderType='Market', qty=self.config['size'])
                            self.close_counter += 1
                            # self.bot.send_message(chat_id, f"Закрыта длинная позиция по {self.config['coin']}")
                        elif short_position and current_rsi <= self.config['short_close_border']:
                            self.client.place_order(category='linear', symbol=self.config['coin'], side='Buy', orderType='Market', qty=self.config['size'])
                            self.close_counter += 1
                            # self.bot.send_message(chat_id, f"Закрыта короткая позиция по {self.config['coin']}")
                    except Exception as e:
                        self.bot.send_message(chat_id, f"Ошибка при закрытии позиции: {e}")

                # Отправка обновления статуса
                status_message = (
                    f"`{datetime.now().strftime('%H:%M:%S  %d-%m-%Y')}`\n"
                    f"RSI: {round(current_rsi, 2)}\n"
                    f"Открытых сделок: {self.open_counter}\n"
                    f"Закрытых сделок: {self.close_counter}"
                )

                if self.msg_id:
                    status_msg = self.bot.edit_message_text(chat_id=chat_id, text=status_message, message_id=self.msg_id, parse_mode='Markdown')
                else:
                    status_msg = self.bot.send_message(chat_id, status_message, parse_mode='Markdown')
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
        print('IS_RUNNING', self.is_running)

        try:
            self.client.set_leverage(category='linear', 
                                    symbol=self.config['coin'],
                                    buyLeverage=self.config['leverage'], 
                                    sellLeverage=self.config['leverage'])
        except:
            pass
        
        # Закрытие позиций
        try:
            positions = self.client.get_positions(category='linear', symbol=self.config['coin'])
            positions = positions['result']['list']
            open_position = isinstance(positions, list) and len(positions) > 0 and positions[0]['side']
            if open_position:
                position = positions[0]
                if position['side'] == 'Buy':
                    self.client.place_order(category='linear', symbol=self.config['coin'], side='Sell', orderType='Market', qty=self.config['size'])
                    self.bot.send_message(chat_id, f"Закрыта длинная позиция по {self.config['coin']}")
                elif position['side'] == 'Sell':
                    self.client.place_order(category='linear', symbol=self.config['coin'], side='Buy', orderType='Market', qty=self.config['size'])
                    self.bot.send_message(chat_id, f"Закрыта короткая позиция по {self.config['coin']}")
            
            self.bot.send_message(chat_id, f"--Робот остановлен. Все позиции закрыты.--\n")
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
        res = self.client.get_positions(category='linear', symbol=self.config['coin'])
        if len(res['result']['list']) > 0 and res['result']['list'][0]['side']:
            return res['result']['list']
        return "Нет открытых позиций"

    # Функия показывающая прибыль
    def calculate_24h_pnl(self):
        now = int(datetime.now().timestamp() * 1000)
        now_24h_ago = int((datetime.now().timestamp() - 24 * 60 * 60) * 1000)

        res = self.client.get_closed_pnl(category='linear', symbol=self.config['coin'], startTime=now_24h_ago, endTime=now)
        
        if len(res['result']['list']) > 0:
            total_pnl = float(res['result']['list'][0]['closedPnl'])
        else:
            total_pnl = 0
        return total_pnl

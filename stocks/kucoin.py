import time

from kucoin_futures.client import Trade

from .base import BaseStock 


class KucoinStock(BaseStock):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def get_keys(self, message_id):
        text = '\n'.join(["Enter keys in order:", "API_KEY", "API_SECRET", "API_PASSPHRASE"])
        msg = self.bot.edit_message_text(chat_id=self.chat_id, text=text, message_id=message_id)
        self.msg = msg
        self.bot.register_next_step_handler(msg, self.parse_api_keys, message_id)

    def parse_api_keys(self, msg, message_id):
        self.api_key, self.api_secret, self.api_passphrase = msg.text.split("\n")
        self.bot.delete_message(self.chat_id, msg.id)
        print(msg)
        print(self.api_key, self.api_secret, self.api_passphrase)
        self.init_client()
        self.main_menu(message_id)

    def init_client(self):
        self.client = Trade(
            key=self.api_key, 
            secret=self.api_secret, 
            passphrase=self.api_passphrase,
        )
        
    def start_trading_process(self, chat_id):
        if self.is_running:
            self.bot.send_message(chat_id, "Торговля уже запущена.")
            return

        self.is_running = True
        self.bot.send_message(chat_id, f"Поиск сделки по {self.config['coin']}")
        self.open_counter = 0
        self.close_counter = 0

        try:
            while self.is_running:
                current_rsi = self.calculate_rsi()
                try:
                    positions = self.client.get_all_position()
                    open_position = isinstance(positions, list) and len(positions) > 0
                except Exception as e:
                    self.bot.send_message(chat_id, f"Ошибка получения позиций: {e}")
                    open_position = False

                if open_position:
                    position = positions[0]
                    long_position = position['currentQty'] > 0
                    short_position = position['currentQty'] < 0
                else:
                    long_position = short_position = False

                # Открытие позиций
                if not open_position:
                    try:
                        if current_rsi >= self.config['up_border']:
                            self.client.create_market_order(self.config['coin'], 'sell', self.config['leverage'], size=self.config['size'])
                            self.open_counter += 1
                            self.bot.send_message(chat_id, f"Открыта короткая позиция по {self.config['coin']}")
                        elif current_rsi <= self.config['low_border']:
                            self.client.create_market_order(self.config['coin'], 'buy', self.config['leverage'], size=self.config['size'])
                            self.open_counter += 1
                            self.bot.send_message(chat_id, f"Открыта длинная позиция по {self.config['coin']}")
                    except Exception as e:
                        self.bot.send_message(chat_id, f"Ошибка при открытии позиции: {e}")

                # Закрытие позиций
                if open_position:
                    try:
                        if long_position and current_rsi >= self.config['long_stop_border']:
                            self.client.create_market_order(self.config['coin'], 'sell', self.config['leverage'], size=self.config['size'])
                            self.close_counter += 1
                            self.bot.send_message(chat_id, f"Закрыта длинная позиция по {self.config['coin']}")
                        elif short_position and current_rsi <= self.config['short_close_border']:
                            self.client.create_market_order(self.config['coin'], 'buy', self.config['leverage'], size=self.config['size'])
                            self.close_counter += 1
                            self.bot.send_message(chat_id, f"Закрыта короткая позиция по {self.config['coin']}")
                    except Exception as e:
                        self.bot.send_message(chat_id, f"Ошибка при закрытии позиции: {e}")

                # Отправка обновления статуса
                status_message = (
                    f"RSI: {round(current_rsi, 2)}\n"
                    f"Открытых сделок: {self.open_counter}\n"
                    f"Закрытых сделок: {self.close_counter}"
                )
                self.bot.send_message(chat_id, status_message)

                time.sleep(self.time_sleep)
        except Exception as e:
            self.bot.send_message(chat_id, f"Произошла ошибка в торговом цикле: {e}")
            is_running = False

    # Функция для остановки процесса торговли
    def stop_trading_process(self, chat_id):

        if not self.is_running:
            self.bot.send_message(chat_id, "Торговля уже остановлена.")
            return

        self.is_running = False
        print('IS_RUNNING', self.is_running)
        
        # Закрытие позиций
        try:
            positions = self.client.get_all_position()
            open_position = isinstance(positions, list) and len(positions) > 0
            if open_position:
                position = positions[0]
                if position['currentQty'] > 0:
                    self.client.create_market_order(self.config['coin'], 'sell', self.config['leverage'], size=self.config['size'])
                    self.bot.send_message(chat_id, f"Закрыта длинная позиция по {self.config['coin']}")
                elif position['currentQty'] < 0:
                    self.client.create_market_order(self.config['coin'], 'buy', self.config['leverage'], size=self.config['size'])
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
        res = self.client.get_all_position()
        # keys = ['symbol', 'realisedPnl']
        # res_ = {}
        # for k,v in res.items():
        #     if k in keys:
        #         res_[k]=v
        return res

    # Функия показывающая прибыль
    def calculate_24h_pnl(self):
        import pandas as pd
        import datetime
        res = self.client.get_24h_done_order()
        print(res)
        res = pd.json_normalize(res)
        print(res)
        res['createdAt'] = res['createdAt'].apply(lambda x: datetime.datetime.fromtimestamp(x / 1000).strftime('%H:%M'))
        res['endAt'] = res['endAt'].apply(lambda x: datetime.datetime.fromtimestamp(x / 1000).strftime('%H:%M'))

        def calculate_total_pnl(df):
            df['value'] = pd.to_numeric(df['value'], errors='coerce')
            
            total_pnl = 0
            open_position = None
            entry_price = None

            maker_fee = 0.0002
            taker_fee = 0.0006

            for index, row in df.iterrows():
                if open_position is None:
                    # Открытие новой позиции
                    open_position = row['side']
                    entry_price = row['value']                
                else:
                    # Закрытие позиции
                    if (open_position == 'buy' and row['side'] == 'sell') or (open_position == 'sell' and row['side'] == 'buy'):
                        if open_position == 'buy':
                            pnl = row['value'] - entry_price
                            pnl -= row['value']*taker_fee + entry_price*maker_fee
                        else:
                            pnl = entry_price - row['value']
                            pnl -= row['value']*taker_fee + entry_price*maker_fee
                        total_pnl += pnl
                        
                        # Сброс позиции после её закрытия
                        open_position = None
                        entry_price = None

            # Если осталась открытая позиция, она не включена в итоговый PnL
            if open_position is not None:
                print(f"Warning: There is an open {open_position} position that hasn't been closed yet.")

            return round(total_pnl, 3)

        total_pnl = calculate_total_pnl(res)
        return total_pnl
from telebot import types
from alarm import add_alarm, delete_alarm, stop_alarm, get_alarms_keyboard, get_status

def register_handlers(bot):
    @bot.message_handler(commands=['start'])
    def handle_start(message):
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)

        button_start = types.KeyboardButton('Поставить будильник')
        button_stop = types.KeyboardButton('Остановить будильник')
        button_status = types.KeyboardButton('Статус')

        keyboard.add(button_start)
        keyboard.add(button_stop, button_status)

        bot.reply_to(message,"👋 Привет! Я бот-будильник.\n\nВыберите действие:",reply_markup=keyboard)

    @bot.message_handler(commands=['stop'])
    def handle_stop(message):
        stop_alarm(bot, message.chat.id)

    def set_alarm_date(message):
        chat_id = message.chat.id
        
        if message.text.startswith('/'):
            if message.text == '/start':
                handle_start(message)
            elif message.text == '/stop':
                handle_stop(message)
            return
        
        if message.text == '❌ Отмена':
            handle_start(message)
            return
        
        alarm_date = message.text.strip()
        try:
            day, month, year = map(int, alarm_date.split('.'))
            if not (1 <= day <= 31 and 1 <= month <= 12 and year >= 2025):
                raise ValueError('Неверная дата')

            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
            keyboard.add(types.KeyboardButton('❌ Отмена'))
            
            msg = bot.send_message(chat_id,'Введите время в формате ЧЧ:ММ\n(например, 14:30)',reply_markup=keyboard)
            bot.register_next_step_handler(msg, lambda m: set_alarm_time(m, alarm_date))
        except:
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
            keyboard.add(types.KeyboardButton('❌ Отмена'))
            
            msg = bot.send_message(chat_id,'❌ Неверный формат даты!\nВведите дату в формате ДД.ММ.ГГГГ\n(например, 03.11.2025)',reply_markup=keyboard)
            bot.register_next_step_handler(msg, set_alarm_date)

    def set_alarm_time(message, alarm_date):
        chat_id = message.chat.id
        
        if message.text.startswith('/'):
            if message.text == '/start':
                handle_start(message)
            elif message.text == '/stop':
                handle_stop(message)
            return
        
        if message.text == '❌ Отмена':
            handle_start(message)
            return
        
        alarm_time = message.text.strip()
        try:
            h, m = map(int, alarm_time.split(':'))
            if not (0 <= h <= 23 and 0 <= m <= 59):
                raise ValueError('Неверное время')
            
            if add_alarm(bot, chat_id, alarm_date, alarm_time):
                pass
            else:
                keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
                keyboard.add(types.KeyboardButton('❌ Отмена'))
                
                msg = bot.send_message(chat_id,'❌ Ошибка при установке будильника!',reply_markup=keyboard)
                bot.register_next_step_handler(msg, set_alarm_date)
                
        except:
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
            keyboard.add(types.KeyboardButton('❌ Отмена'))
            
            msg = bot.send_message(chat_id,'❌ Неверный формат времени!\nВведите время в формате ЧЧ:ММ\n(например, 14:30)',reply_markup=keyboard)
            bot.register_next_step_handler(msg, lambda m: set_alarm_time(m, alarm_date))

    @bot.message_handler(func=lambda message: True)
    def handle_message(message):
        chat_id = message.chat.id

        if message.text == 'Поставить будильник':
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
            keyboard.add(types.KeyboardButton('❌ Отмена'))
            
            msg = bot.reply_to(message,'Введите дату в формате ДД.ММ.ГГГГ\n(например, 05.11.2025)',reply_markup=keyboard)
            bot.register_next_step_handler(msg, set_alarm_date)
        elif message.text == 'Остановить будильник':
            keyboard = get_alarms_keyboard(chat_id)
            if keyboard:
                bot.send_message(chat_id,'🔔 Выберите будильник для удаления:',reply_markup=keyboard)
            else:
                bot.reply_to(message, '❌ Нет установленных будильников')
        elif message.text == 'Статус':
            bot.reply_to(message, get_status(chat_id))
        else:
            bot.reply_to(message, '❌ Нажмите на кнопку')

    @bot.callback_query_handler(func=lambda call: call.data.startswith('delete_'))
    def handle_delete(call):
        try:
            index = int(call.data.split('_')[1])
            delete_alarm(bot, call, index)
        except Exception as e:
            print(f'Ошибка callback: {e}')
            bot.answer_callback_query(call.id, '❌ Ошибка')

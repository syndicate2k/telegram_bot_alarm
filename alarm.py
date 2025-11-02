from scheduler import scheduler
from telebot import types
from datetime import datetime

active_alarms = {}
ringing_alarms = {}

def start_ringing(bot, chat_id, alarm_date, alarm_time):
    ringing_alarms[chat_id] = {'date': alarm_date, 'time': alarm_time}

    interval_job_id = f'ringing_{chat_id}_{alarm_time.replace(":", "")}'
    scheduler.add_job(
        func=send_alarm_message,
        trigger='interval',
        seconds=30,
        args=[bot, chat_id, alarm_time],
        id=interval_job_id,
        replace_existing=True
    )

def send_alarm_message(bot, chat_id, alarm_time):
    if chat_id in ringing_alarms and ringing_alarms[chat_id]:
        bot.send_message(chat_id,f'🔔 ЗВОНОК! Будильник на: {alarm_time}\n\nНапишите /stop чтобы остановить')

def alarm_ring(bot, chat_id, alarm_date, alarm_time):
    start_ringing(bot, chat_id, alarm_date, alarm_time)

def add_alarm(bot, chat_id, alarm_date, alarm_time):
    try:
        day, month, year = map(int, alarm_date.split('.'))
        h, m = map(int, alarm_time.split(':'))

        if not (0 <= h <= 23 and 0 <= m <= 59):
            raise ValueError('Время вне диапазона')

        run_date = datetime(year, month, day, h, m)
        
        if run_date <= datetime.now():
            bot.send_message(chat_id, '⚠️ Дата должна быть в будущем!')
            return False

        if chat_id not in active_alarms:
            active_alarms[chat_id] = []

        alarm_key = f'{alarm_date} {alarm_time}'
        for alarm in active_alarms[chat_id]:
            if alarm['key'] == alarm_key:
                bot.send_message(chat_id, '⚠️ Такой будильник уже установлен')
                return False

        job_id = f'alarm_{chat_id}_{alarm_date.replace(".", "")}_{alarm_time.replace(":", "")}'

        scheduler.add_job(
            func=alarm_ring,
            trigger='date',
            run_date=run_date,
            args=[bot, chat_id, alarm_date, alarm_time],
            id=job_id,
            replace_existing=True
        )

        active_alarms[chat_id].append({
            'date': alarm_date,
            'time': alarm_time,
            'key': alarm_key,
            'job_id': job_id,
            'run_date': run_date
        })

        bot.send_message(
            chat_id,
            f'✅ Будильник установлен\n'
            f'📅 Дата: {alarm_date}\n'
            f'⏰ Время: {alarm_time}\n\n'
            f'Всего будильников: {len(active_alarms[chat_id])}'
        )
        return True

    except ValueError as e:
        return False

def delete_alarm(bot, call, index):
    chat_id = call.message.chat.id

    try:
        if chat_id in active_alarms and 0 <= index < len(active_alarms[chat_id]):
            alarm = active_alarms[chat_id][index]
            try:
                scheduler.remove_job(alarm['job_id'])
            except:
                pass

            try:
                interval_job_id = f"ringing_{chat_id}_{alarm['time'].replace(':', '')}"
                scheduler.remove_job(interval_job_id)
            except:
                pass

            active_alarms[chat_id].pop(index)

            bot.answer_callback_query(call.id)
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=call.message.message_id,
                text=f'✅ Будильник на {alarm["date"]} {alarm["time"]} удален!\n\n'
                     f'Осталось: {len(active_alarms[chat_id])}'
            )
            return True
        else:
            bot.answer_callback_query(call.id, '❌ Ошибка')
            return False
    except Exception as e:
        bot.answer_callback_query(call.id, f'❌ Ошибка: {str(e)}')
        return False

def stop_alarm(bot, chat_id):
    if chat_id in ringing_alarms and ringing_alarms[chat_id]:
        ringing_info = ringing_alarms[chat_id]
        alarm_date = ringing_info['date']
        alarm_time = ringing_info['time']
        
        for alarm in active_alarms.get(chat_id, []):
            try:
                interval_job_id = f"ringing_{chat_id}_{alarm['time'].replace(':', '')}"
                scheduler.remove_job(interval_job_id)
            except:
                pass

        if chat_id in active_alarms:
            for i, alarm in enumerate(active_alarms[chat_id]):
                if alarm['date'] == alarm_date and alarm['time'] == alarm_time:
                    try:
                        scheduler.remove_job(alarm['job_id'])
                    except:
                        pass
                    active_alarms[chat_id].pop(i)
                    break

        ringing_alarms[chat_id] = False
        bot.send_message(
            chat_id, 
            f'✅ Будильник на {alarm_date} {alarm_time} остановлен!'
        )
        return True
    else:
        bot.send_message(chat_id, '❌ Будильник не звонит')
        return False

def get_alarms_keyboard(chat_id):
    if chat_id not in active_alarms or len(active_alarms[chat_id]) == 0:
        return None

    keyboard = types.InlineKeyboardMarkup()
    for i, alarm in enumerate(active_alarms[chat_id]):
        button = types.InlineKeyboardButton(
            text=f'❌ {alarm["date"]} {alarm["time"]}',
            callback_data=f'delete_{i}'
        )
        keyboard.add(button)

    return keyboard

def get_status(chat_id):
    if chat_id not in active_alarms or len(active_alarms[chat_id]) == 0:
        return '❌ Будильники не установлены'

    status_text = '🔔 Активные будильники:\n\n'

    for i, alarm in enumerate(active_alarms[chat_id], 1):
        ringing = '🔔 ЗВОНИТ!' if (chat_id in ringing_alarms and ringing_alarms[chat_id]) else ''
        status_text += f'{i}. 📅 {alarm["date"]} ⏰ {alarm["time"]} {ringing}\n'

    status_text += f'\nВсего: {len(active_alarms[chat_id])}'

    return status_text

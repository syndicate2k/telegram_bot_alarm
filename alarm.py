from scheduler import scheduler
from telebot import types
from datetime import datetime
from database import (
    db_add_alarm, db_get_user_alarms, db_deactivate_alarm_by_job,
    db_deactivate_alarm_by_id, db_set_ringing, db_clear_ringing, db_get_ringing
)


def start_ringing(bot, chat_id, alarm_date, alarm_time):
    db_set_ringing(chat_id, alarm_date, alarm_time)

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
    if db_get_ringing(chat_id):
        bot.send_message(chat_id, f'🔔 ЗВОНОК! Будильник на: {alarm_time}\n\nНапишите /stop чтобы остановить')


def alarm_ring(bot, chat_id, alarm_date, alarm_time, job_id):
    db_deactivate_alarm_by_job(job_id)
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

        job_id = f'alarm_{chat_id}_{alarm_date.replace(".", "")}_{alarm_time.replace(":", "")}'

        result = db_add_alarm(chat_id, alarm_date, alarm_time, job_id, run_date)

        if result is None:
            bot.send_message(chat_id, '❌ Лимит: у вас уже 100 активных будильников!')
            return False

        if result == -1:
            bot.send_message(chat_id, '⚠️ Такой будильник уже установлен')
            return False

        scheduler.add_job(
            func=alarm_ring,
            trigger='date',
            run_date=run_date,
            args=[bot, chat_id, alarm_date, alarm_time, job_id],
            id=job_id,
            replace_existing=True
        )

        alarms = db_get_user_alarms(chat_id)
        bot.send_message(
            chat_id,
            f'✅ Будильник установлен\n'
            f'📅 Дата: {alarm_date}\n'
            f'⏰ Время: {alarm_time}\n\n'
            f'Всего будильников: {len(alarms)}'
        )
        return True

    except ValueError:
        return False


def delete_alarm(bot, call, index):
    chat_id = call.message.chat.id
    try:
        alarms = db_get_user_alarms(chat_id)

        if 0 <= index < len(alarms):
            alarm = alarms[index]

            try:
                scheduler.remove_job(alarm['job_id'])
            except:
                pass

            try:
                interval_job_id = f"ringing_{chat_id}_{alarm['alarm_time'].replace(':', '')}"
                scheduler.remove_job(interval_job_id)
            except:
                pass

            db_deactivate_alarm_by_id(alarm['id'])
            db_clear_ringing(chat_id)

            remaining = db_get_user_alarms(chat_id)
            bot.answer_callback_query(call.id)
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=call.message.message_id,
                text=f'✅ Будильник на {alarm["alarm_date"]} {alarm["alarm_time"]} удален!\n\n'
                     f'Осталось: {len(remaining)}'
            )
            return True
        else:
            bot.answer_callback_query(call.id, '❌ Ошибка')
            return False
    except Exception as e:
        bot.answer_callback_query(call.id, f'❌ Ошибка: {str(e)}')
        return False


def stop_alarm(bot, chat_id):
    ringing = db_get_ringing(chat_id)
    if ringing:
        alarm_date = ringing['alarm_date']
        alarm_time = ringing['alarm_time']

        alarms = db_get_user_alarms(chat_id)
        for alarm in alarms:
            try:
                interval_job_id = f"ringing_{chat_id}_{alarm['alarm_time'].replace(':', '')}"
                scheduler.remove_job(interval_job_id)
            except:
                pass

        try:
            interval_job_id = f"ringing_{chat_id}_{alarm_time.replace(':', '')}"
            scheduler.remove_job(interval_job_id)
        except:
            pass

        db_clear_ringing(chat_id)
        bot.send_message(chat_id, f'✅ Будильник на {alarm_date} {alarm_time} остановлен!')
        return True
    else:
        bot.send_message(chat_id, '❌ Будильник не звонит')
        return False


def get_alarms_keyboard(chat_id):
    alarms = db_get_user_alarms(chat_id)
    if not alarms:
        return None

    keyboard = types.InlineKeyboardMarkup()
    for i, alarm in enumerate(alarms):
        button = types.InlineKeyboardButton(
            text=f'❌ {alarm["alarm_date"]} {alarm["alarm_time"]}',
            callback_data=f'delete_{i}'
        )
        keyboard.add(button)

    return keyboard


def get_status(chat_id):
    alarms = db_get_user_alarms(chat_id)
    if not alarms:
        return '❌ Будильники не установлены'

    ringing = db_get_ringing(chat_id)
    status_text = '🔔 Активные будильники:\n\n'

    for i, alarm in enumerate(alarms, 1):
        is_ringing = (
            ringing and
            ringing['alarm_date'] == alarm['alarm_date'] and
            ringing['alarm_time'] == alarm['alarm_time']
        )
        ring_mark = ' 🔔 ЗВОНИТ!' if is_ringing else ''
        status_text += f'{i}. 📅 {alarm["alarm_date"]} ⏰ {alarm["alarm_time"]}{ring_mark}\n'

    status_text += f'\nВсего: {len(alarms)}'
    return status_text


def restore_alarms(bot):
    from database import db_get_all_active_alarms
    alarms = db_get_all_active_alarms()
    restored = 0
    skipped = 0

    for alarm in alarms:
        run_date = datetime.fromisoformat(alarm['run_date'])
        if run_date <= datetime.now():
            db_deactivate_alarm_by_id(alarm['id'])
            skipped += 1
            continue

        scheduler.add_job(
            func=alarm_ring,
            trigger='date',
            run_date=run_date,
            args=[bot, alarm['chat_id'], alarm['alarm_date'], alarm['alarm_time'], alarm['job_id']],
            id=alarm['job_id'],
            replace_existing=True
        )
        restored += 1


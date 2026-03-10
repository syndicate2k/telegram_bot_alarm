import telebot
from config import TOKEN
from handlers import register_handlers
from scheduler import scheduler
from database import init_db
from alarm import restore_alarms


bot = telebot.TeleBot(TOKEN)
register_handlers(bot)

if __name__ == '__main__':
    init_db()
    restore_alarms(bot)
    try:
        bot.polling(none_stop=True)
    except KeyboardInterrupt:
        scheduler.shutdown()

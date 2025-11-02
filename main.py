import telebot
from config import TOKEN
from handlers import register_handlers
from scheduler import scheduler

bot = telebot.TeleBot(TOKEN)
register_handlers(bot)

if __name__ == '__main__':
    try:
        bot.polling(none_stop=True)
    except KeyboardInterrupt:
        scheduler.shutdown()

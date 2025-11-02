from apscheduler.schedulers.background import BackgroundScheduler
from config import TIMEZONE

scheduler = BackgroundScheduler(timezone=TIMEZONE)
scheduler.start()

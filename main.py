import json
import logging
import datetime
from zoneinfo import ZoneInfo
from telegram.ext import Application, CommandHandler, ContextTypes

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

DAYS_RU = {
    0: "Понедельник",
    1: "Вторник",
    2: "Среда",
    3: "Четверг",
    4: "Пятница",
    5: "Суббота",
    6: "Воскресенье"
}

MONTHS_RU = {
    1: "января",
    2: "февраля",
    3: "марта",
    4: "апреля",
    5: "мая",
    6: "июня",
    7: "июля",
    8: "августа",
    9: "сентября",
    10: "октября",
    11: "ноября",
    12: "декабря"
}

class Data:
    
    def load_config(self):
        try:
            with open('config.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Ошибка загрузки конфига: {e}")
            return None

    def get_next_run_time(self, hour, minute, days):
        now = datetime.datetime.now(ZoneInfo("Europe/Moscow"))
        for delta in range(7):
            candidate = now + datetime.timedelta(days=delta)
            if candidate.weekday() in days:
                return candidate.replace(hour=hour, minute=minute, second=0, microsecond=0)
        return now.replace(hour=hour, minute=minute, second=0, microsecond=0) + datetime.timedelta(days=7)
    
class Bot:
    
    def __init__(self, data: Data):
        self.data = data

    async def start_command(self, update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("Бот для опросов запущен!")

    async def send_poll_job(self, context: ContextTypes.DEFAULT_TYPE):
        poll_data = context.job.data
        now = datetime.datetime.now(ZoneInfo("Europe/Moscow"))
        tomorrow = now + datetime.timedelta(days=1) 
        
        weekday = DAYS_RU[tomorrow.weekday()]
        date_str = f"{tomorrow.day} {MONTHS_RU[tomorrow.month]}"
        question = f"🏸 Игра {weekday}, {date_str} 🏸"

        try:
            await context.bot.send_poll(
                chat_id=poll_data['channel_id'],
                question=question,
                options=poll_data['options'],
                is_anonymous=poll_data.get('is_anonymous', True),
                allows_multiple_answers=poll_data.get('allows_multiple_answers', False)
            )
            logger.info(f"Опрос отправлен: {question}")
        except Exception as e:
            logger.error(f"Ошибка отправки опроса: {e}")

        hour, minute = map(int, poll_data['time'].split(':'))
        
        next_run = self.data.get_next_run_time(hour, minute, poll_data['days'])
        
        if next_run <= tomorrow + datetime.timedelta(days=7):
            next_run += datetime.timedelta(weeks=1)
        
        context.job_queue.run_once(self.send_poll_job, when=next_run, data=poll_data)
        logger.info(f"Опрос перепланирован на: {next_run.strftime('%Y-%m-%d %H:%M')}")

    def main(self):
        config = self.data.load_config()
        TOKEN = config.get('token')
        application = Application.builder().token(TOKEN).build()
        application.add_handler(CommandHandler("start", self.start_command))
        if config and 'polls' in config:
            self.schedule_polls(application, config['polls'])
        else:
            logger.warning("Конфиг не загружен или нет опросов")

        logger.info("Бот запускается...")
        application.run_polling()
        
    def schedule_polls(self, application, polls):
        for poll in polls:
            try:
                hour, minute = map(int, poll['time'].split(':'))
                next_run = self.data.get_next_run_time(hour, minute, poll['days'])
                application.job_queue.run_once(self.send_poll_job, when=next_run, data=poll)
                logger.info(f"Запланирован опрос на {next_run} по дням {poll['days']}")
            except Exception as e:
                logger.error(f"Ошибка планирования опроса: {e}")
                
if __name__ == "__main__":
        Bot(Data()).main()

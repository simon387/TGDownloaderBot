from telegram.constants import ParseMode
from telegram.ext import Application
from src.util import Constants


# Override App Class
class BotApp(Application):
	async def stop(self):
		await super().stop()
		if Constants.SEND_START_AND_STOP_MESSAGE == 'true':
			await self.bot.send_message(chat_id=Constants.TELEGRAM_GROUP_ID, text=Constants.STOP_MESSAGE, parse_mode=ParseMode.HTML)
			await self.bot.send_message(chat_id=Constants.TELEGRAM_DEVELOPER_CHAT_ID, text=Constants.STOP_MESSAGE, parse_mode=ParseMode.HTML)

from telegram.constants import ParseMode
from telegram.ext import Application
import constants as c


# Override App Class
class BotApp(Application):
	async def stop(self):
		await super().stop()
		if c.SEND_START_AND_STOP_MESSAGE == 'true':
			# await self.bot.send_message(chat_id=c.TELEGRAM_GROUP_ID, text=c.STOP_MESSAGE, parse_mode=ParseMode.HTML)
			await self.bot.send_message(chat_id=c.TELEGRAM_DEVELOPER_CHAT_ID, text=c.STOP_MESSAGE, parse_mode=ParseMode.HTML)

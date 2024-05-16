import os
import signal

from telegram import Update
from telegram.ext import CallbackContext

from src.service.log_service import log_bot_event
from src.util import Constants as C


async def send_shutdown(update: Update, context: CallbackContext):
	log_bot_event(update, 'send_shutdown')
	if update.effective_user.id == int(C.TELEGRAM_DEVELOPER_CHAT_ID):
		os.kill(os.getpid(), signal.SIGINT)
	else:
		await context.bot.send_message(chat_id=update.effective_chat.id, text=C.ERROR_NO_GRANT_SHUTDOWN)

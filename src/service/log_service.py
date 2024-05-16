import logging as log

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CallbackContext

from src.util import Constants as C


# v1.0, highest but custom
def log_bot_event(update: Update, method_name: str):
	msg = 'No message, just a click'
	if update.message is not None:
		msg = update.message.text
	user = update.effective_user.first_name
	uid = update.effective_user.id
	log.info(f"[method={method_name}] Got this message from {user} [id={str(uid)}]: {msg}")


async def post_init(app: Application):
	version = get_version()
	log.info(f"Starting TGDownloaderBot, {version}")
	if C.SEND_START_AND_STOP_MESSAGE == C.TRUE:
		await app.bot.send_message(chat_id=C.TELEGRAM_GROUP_ID, text=C.STARTUP_MESSAGE + version, parse_mode=ParseMode.HTML)
		await app.bot.send_message(chat_id=C.TELEGRAM_DEVELOPER_CHAT_ID, text=C.STARTUP_MESSAGE + version, parse_mode=ParseMode.HTML)


# noinspection PyUnusedLocal
async def post_shutdown(app: Application):
	log.info(f"Shutting down the bot")


async def send_version(update: Update, context: CallbackContext):
	log_bot_event(update, 'send_version')
	await context.bot.send_message(chat_id=update.effective_chat.id, text=get_version() + C.VERSION_MESSAGE)


def get_version():
	with open("changelog.txt") as f:
		firstline = f.readline().rstrip()
	return firstline

import html
import json
import logging as log
import os
import sys
import time as time_os
import traceback

import telegram.error
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from yt_dlp.extractor import telegram

from src.util import Constants as C


# Log the error and send a telegram message to notify the developer. Attemp to restart the bot too
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
	# Log the error before we do anything else, so we can see it even if something breaks.
	log.error(msg="Exception while handling an update:", exc_info=context.error)
	# No Network, no sent message!
	if not isinstance(context.error, telegram.error.NetworkError) and not isinstance(context.error, telegram.error.TimedOut):
		if C.SEND_ERROR_TO_DEV == C.TRUE or C.SEND_ERROR_TO_USER == C.TRUE:
			# traceback.format_exception returns the usual python message about an exception, but as a
			# list of strings rather than a single string, so we have to join them together.
			tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
			tb_string = C.EMPTY.join(tb_list)
			# Build the message with some markup and additional information about what happened.
			update_str = update.to_dict() if isinstance(update, Update) else str(update)
			await context.bot.send_message(chat_id=C.TELEGRAM_DEVELOPER_CHAT_ID, text=f"An exception was raised while handling an update")
			if update_str != C.NONE:
				await send_error_message(update, context, f"{C.PRE}update = {html.escape(json.dumps(update_str, indent=2, ensure_ascii=False))}{C.PRC}")
			if context.chat_data != {}:
				await send_error_message(update, context, f"{C.PRE}context.chat_data = {html.escape(str(context.chat_data))}{C.PRC}")
			if context.user_data != {}:
				await send_error_message(update, context, f"{C.PRE}context.user_data = {html.escape(str(context.user_data))}{C.PRC}")
			await send_error_message(update, context, f"{C.PRE}{html.escape(tb_string)}{C.PRC}")
	# Restart the bot
	if C.RESTART_FLAG == C.TRUE:
		time_os.sleep(5.0)
		os.execl(sys.executable, sys.executable, *sys.argv)


async def send_error_message(update: Update, context: ContextTypes.DEFAULT_TYPE, message):
	max_length = 4096  # Maximum allowed length for a message
	chunks = [message[i:i + max_length] for i in range(0, len(message), max_length)]
	# Send each chunk as a separate message
	for chunk in chunks:
		if not chunk.startswith(C.PRE):
			chunk = C.PRE + chunk
		if not chunk.endswith(C.PRC):
			chunk += C.PRC
		# Finally, send the message
		if C.SEND_ERROR_TO_DEV == C.TRUE:
			await context.bot.send_message(chat_id=C.TELEGRAM_DEVELOPER_CHAT_ID, text=chunk, parse_mode=ParseMode.HTML)
		if C.SEND_ERROR_TO_USER == C.TRUE and update is not None:
			if update.effective_chat.id:
				await context.bot.send_message(chat_id=update.effective_chat.id, text=chunk, parse_mode=ParseMode.HTML)

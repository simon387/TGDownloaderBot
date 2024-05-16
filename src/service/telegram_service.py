import base64
import logging as log
import re

import validators
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.error import TelegramError
from telegram.ext import CallbackContext

from src.service.ftp_service import upload_to_ftp
from src.service.link_service import contains_valid_url, extract_first_url
from src.service.log_service import log_bot_event
from src.util import Constants as C


async def chat_check(update: Update, context: CallbackContext):
	if hasattr(update.message, 'text'):
		log_bot_event(update, 'chat_check')
		msg = update.message.text
		url = extract_first_url(msg)
		if url is not None and validators.url(url) and contains_valid_url(url):
			await show_download_buttons(update, context, False, url)


async def show_download_buttons(update: Update, context: CallbackContext, answer_with_error=True, msg=C.EMPTY):
	log_bot_event(update, 'download')
	if msg == C.EMPTY:
		msg = C.SPACE.join(context.args).strip()
	if contains_valid_url(msg):
		if "https://www.youtube." in msg and "/watch?" in msg:
			msg = re.sub('&list=.+', C.EMPTY, msg)  # cleans link
		#
		keyboard = [
			[
				InlineKeyboardButton("Download Audio", callback_data=C.MP3),
				InlineKeyboardButton("Download Video", callback_data=C.MP4),
			]
		]
		mu = InlineKeyboardMarkup(keyboard)
		txt = f'<a href="tg://btn/{str(base64.urlsafe_b64encode(msg.encode(C.UTF8)))}">\u200b</a>{C.VALID_LINK_MESSAGE}'
		message_id = update.message.id
		await context.bot.send_message(chat_id=update.effective_chat.id, text=txt, reply_markup=mu, parse_mode=ParseMode.HTML, reply_to_message_id=message_id)
	else:
		if answer_with_error:
			await context.bot.send_message(chat_id=update.effective_chat.id, text=C.ERROR_CANT_DOWNLOAD)


# send media to telegram chat
async def send_media(mode, file_path, context, update):
	if mode == C.MP3:
		file_path = f'{file_path[:-4]}.m4a'
		log.info(f"Sending audio file: {file_path}")
		try:
			await context.bot.send_audio(chat_id=update.effective_chat.id, audio=file_path)
		except TelegramError:
			await upload_to_ftp(update, context, file_path)
	else:
		log.info(f"Sending video file: {file_path}")
		try:
			await context.bot.send_video(chat_id=update.effective_chat.id, video=file_path)
		except TelegramError:
			await upload_to_ftp(update, context, file_path)

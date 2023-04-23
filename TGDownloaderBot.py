import base64
import html
import json
import logging as log
import os
import re
import signal
import sys
import time as time_os
import traceback
from logging.handlers import RotatingFileHandler

import validators
import yt_dlp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CallbackContext, CommandHandler, ContextTypes, Application, AIORateLimiter, CallbackQueryHandler, MessageHandler, \
	filters

import Constants
from BotApp import BotApp

log.basicConfig(
	handlers=[
		RotatingFileHandler(
			'_TGDownloaderBot.log',
			maxBytes=10240000,
			backupCount=5
		),
		log.StreamHandler()
	],
	format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
	level=Constants.LOG_LEVEL
)


async def send_version(update: Update, context: CallbackContext):
	log_bot_event(update, 'send_version')
	await context.bot.send_message(chat_id=update.effective_chat.id, text=get_version() + Constants.VERSION_MESSAGE)


async def send_shutdown(update: Update, context: CallbackContext):
	log_bot_event(update, 'send_shutdown')
	if update.effective_user.id == int(Constants.TELEGRAM_DEVELOPER_CHAT_ID):
		os.kill(os.getpid(), signal.SIGINT)
	else:
		await context.bot.send_message(chat_id=update.effective_chat.id, text=Constants.ERROR_NO_GRANT_SHUTDOWN)


async def post_init(app: Application):
	version = get_version()
	log.info(f"Starting TGDownloaderBot, {version}")
	if Constants.SEND_START_AND_STOP_MESSAGE == 'true':
		await app.bot.send_message(chat_id=Constants.TELEGRAM_GROUP_ID, text=Constants.STARTUP_MESSAGE + version, parse_mode=ParseMode.HTML)
		await app.bot.send_message(chat_id=Constants.TELEGRAM_DEVELOPER_CHAT_ID, text=Constants.STARTUP_MESSAGE + version, parse_mode=ParseMode.HTML)


async def post_shutdown(app: Application):
	log.info(f"Shutting down, bot id={str(app.bot.id)}")


def log_bot_event(update: Update, method_name: str):
	msg = update.message.text
	user = update.effective_user.first_name
	uid = update.effective_user.id
	log.info(f"[method={method_name}] Got this message from {user} [id={str(uid)}]: {msg}")


# Log the error and send a telegram message to notify the developer. Attemp to restart the bot too
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
	# Log the error before we do anything else, so we can see it even if something breaks.
	log.error(msg="Exception while handling an update:", exc_info=context.error)
	# traceback.format_exception returns the usual python message about an exception, but as a
	# list of strings rather than a single string, so we have to join them together.
	tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
	tb_string = "".join(tb_list)
	# Build the message with some markup and additional information about what happened.
	# You might need to add some logic to deal with messages longer than the 4096 character limit.
	update_str = update.to_dict() if isinstance(update, Update) else str(update)
	message = (
		f"An exception was raised while handling an update\n"
		f"<pre>update = {html.escape(json.dumps(update_str, indent=2, ensure_ascii=False))}"
		"</pre>\n\n"
		f"<pre>context.chat_data = {html.escape(str(context.chat_data))}</pre>\n\n"
		f"<pre>context.user_data = {html.escape(str(context.user_data))}</pre>\n\n"
		f"<pre>{html.escape(tb_string)}</pre>"
	)
	message = message[:4300]  # truncate to prevent error
	if message.count('</pre>') % 2 != 0:
		message += '</pre>'
	# Finally, send the message
	await context.bot.send_message(chat_id=Constants.TELEGRAM_DEVELOPER_CHAT_ID, text=message, parse_mode=ParseMode.HTML)
	# Restart the bot
	time_os.sleep(5.0)
	os.execl(sys.executable, sys.executable, *sys.argv)


def get_version():
	with open("changelog.txt") as f:
		firstline = f.readline().rstrip()
	return firstline


async def chat_check(update: Update, context: CallbackContext):
	if hasattr(update.message, 'text'):
		log_bot_event(update, 'chat_check')
		msg = update.message.text
		if validators.url(msg) and validate(msg):
			await download(update, context, False, msg)


async def download(update: Update, context: CallbackContext, answer_with_error=True, msg=''):
	log_bot_event(update, 'download')
	if msg == '':
		msg = Constants.SPACE.join(context.args).strip()
	if validators.url(msg):
		if validate(msg):
			# clean
			if "https://www.youtube." in msg and "/watch?" in msg:
				msg = re.sub('&list=.+', '', msg)
			#
			keyboard = [
				[
					InlineKeyboardButton("Download Audio", callback_data=Constants.MP3),
					InlineKeyboardButton("Download Video", callback_data=Constants.MP4),
				]
			]
			reply_markup = InlineKeyboardMarkup(keyboard)
			text = f'<a href="tg://btn/{str(base64.urlsafe_b64encode(msg.encode(Constants.UTF8)))}">\u200b</a>{Constants.VALID_LINK_MESSAGE}'
			await context.bot.send_message(chat_id=update.effective_chat.id, text=text, reply_markup=reply_markup, parse_mode='HTML')
		else:
			if answer_with_error:
				await context.bot.send_message(chat_id=update.effective_chat.id, text=Constants.ERROR_CANT_DOWNLOAD)
	else:
		if answer_with_error:
			await context.bot.send_message(chat_id=update.effective_chat.id, text=Constants.ERROR_NOT_VALID_URL)


def validate(msg):
	return ("https://www.youtube." in msg and "/watch?" in msg) or \
		"https://www.youtube.com/shorts/" in msg or \
		"https://youtube.com/shorts/" in msg or \
		"facebook.com/" in msg or \
		"https://fb.watch/" in msg or \
		"https://www.instagram.com/" in msg or \
		"https://www.tiktok.com/" in msg or \
		"https://vm.tiktok.com/" in msg


async def keyboard_callback(update: Update, context: CallbackContext):
	query = update.callback_query
	mode = query.data
	url = str(base64.urlsafe_b64decode(query.message.entities[0].url[11:]))[2:-1]
	await query.answer(f'selected: download from {url}')
	paths = {
		'home': 'download'
	}
	if mode == Constants.MP3:
		ydl_opts = {
			'format': 'm4a/bestaudio/best',
			# ℹ️ See help(yt_dlp.postprocessor) for a list of available Postprocessors and their arguments
			'postprocessors': [{  # Extract audio using ffmpeg
				'key': 'FFmpegExtractAudio',
				'preferredcodec': 'm4a',
			}],
			'restrictfilenames': True,
			'paths': paths,
		}
	else:
		ydl_opts = {
			'paths': paths,
		}
	with yt_dlp.YoutubeDL(ydl_opts) as ydl:
		info = ydl.extract_info(url, download=False)
		file_path = ydl.prepare_filename(info)
		log.info(f"Downloaded file into {file_path}")
		ydl.process_info(info)
	if mode == Constants.MP3:
		file_path = f'{file_path[:-4]}.m4a'
		log.info(f"Sending audio file: {file_path}")
		await context.bot.send_audio(chat_id=update.effective_chat.id, audio=file_path)
	else:
		log.info(f"Sending video file: {file_path}")
		await context.bot.send_video(chat_id=update.effective_chat.id, video=file_path)


if __name__ == '__main__':
	application = ApplicationBuilder() \
		.token(Constants.TOKEN) \
		.application_class(BotApp) \
		.post_init(post_init) \
		.post_shutdown(post_shutdown) \
		.rate_limiter(AIORateLimiter(max_retries=Constants.AIO_RATE_LIMITER_MAX_RETRIES)) \
		.http_version(Constants.HTTP_VERSION) \
		.get_updates_http_version(Constants.HTTP_VERSION) \
		.build()
	application.add_handler(CommandHandler('version', send_version))
	application.add_handler(CommandHandler('shutdown', send_shutdown))
	application.add_handler(CommandHandler('download', download))
	application.add_handler(CallbackQueryHandler(keyboard_callback))
	application.add_handler(MessageHandler(filters.TEXT, chat_check))
	application.add_error_handler(error_handler)
	application.run_polling(allowed_updates=Update.ALL_TYPES)

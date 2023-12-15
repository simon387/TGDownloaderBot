import base64
import ftplib
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
from telegram.error import TelegramError
from telegram.ext import ApplicationBuilder, CallbackContext, CommandHandler, ContextTypes, Application, AIORateLimiter, CallbackQueryHandler, MessageHandler, \
	filters
from yt_dlp import DownloadError

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

if Constants.LOG_LEVEL <= log.INFO:
	log.getLogger('httpx').setLevel(log.WARNING)


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


# v1.0, highest but custom
def log_bot_event(update: Update, method_name: str):
	msg = 'No message, just a click'
	if update.message is not None:
		msg = update.message.text
	user = update.effective_user.first_name
	uid = update.effective_user.id
	log.info(f"[method={method_name}] Got this message from {user} [id={str(uid)}]: {msg}")


# Log the error and send a telegram message to notify the developer. Attemp to restart the bot too
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
	# Log the error before we do anything else, so we can see it even if something breaks.
	log.error(msg="Exception while handling an update:", exc_info=context.error)
	if Constants.SEND_ERROR_TO_DEV == 'true' or Constants.SEND_ERROR_TO_USER == 'true':
		# traceback.format_exception returns the usual python message about an exception, but as a
		# list of strings rather than a single string, so we have to join them together.
		tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
		tb_string = "".join(tb_list)
		# Build the message with some markup and additional information about what happened.
		update_str = update.to_dict() if isinstance(update, Update) else str(update)
		await context.bot.send_message(chat_id=Constants.TELEGRAM_DEVELOPER_CHAT_ID, text=f"An exception was raised while handling an update")
		await send_error_message(update, context, f"<pre>update = {html.escape(json.dumps(update_str, indent=2, ensure_ascii=False))}</pre>")
		await send_error_message(update, context, f"<pre>context.chat_data = {html.escape(str(context.chat_data))}</pre>")
		await send_error_message(update, context, f"<pre>context.user_data = {html.escape(str(context.user_data))}</pre>")
		await send_error_message(update, context, f"<pre>{html.escape(tb_string)}</pre>")
	# Restart the bot
	time_os.sleep(5.0)
	os.execl(sys.executable, sys.executable, *sys.argv)


async def send_error_message(update: Update, context: ContextTypes.DEFAULT_TYPE, message):
	max_length = 4096  # Maximum allowed length for a message
	chunks = [message[i:i + max_length] for i in range(0, len(message), max_length)]
	# Send each chunk as a separate message
	for chunk in chunks:
		if not chunk.startswith('<pre>'):
			chunk = '<pre>' + chunk
		if not chunk.endswith('</pre>'):
			chunk += '</pre>'
		# Finally, send the message
		if Constants.SEND_ERROR_TO_DEV == 'true':
			await context.bot.send_message(chat_id=Constants.TELEGRAM_DEVELOPER_CHAT_ID, text=chunk, parse_mode=ParseMode.HTML)
		if Constants.SEND_ERROR_TO_USER == 'true' and update is not None:
			if update.effective_chat.id:
				await context.bot.send_message(chat_id=update.effective_chat.id, text=chunk, parse_mode=ParseMode.HTML)


def get_version():
	with open("changelog.txt") as f:
		firstline = f.readline().rstrip()
	return firstline


async def chat_check(update: Update, context: CallbackContext):
	if hasattr(update.message, 'text'):
		log_bot_event(update, 'chat_check')
		msg = update.message.text
		url = extract_first_url(msg)
		if url is not None and validators.url(url) and validate(url):
			await download(update, context, False, url)


def extract_first_url(text):
	url_pattern = re.compile(r"https?://(?:[a-zA-Z]|[0-9]|[$-_]|[!*\\(),])+")
	matches = re.findall(url_pattern, text)
	if matches:
		return matches[0]
	else:
		return None


async def download(update: Update, context: CallbackContext, answer_with_error=True, msg=''):
	log_bot_event(update, 'download')
	if msg == '':
		msg = Constants.SPACE.join(context.args).strip()
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
		mu = InlineKeyboardMarkup(keyboard)
		txt = f'<a href="tg://btn/{str(base64.urlsafe_b64encode(msg.encode(Constants.UTF8)))}">\u200b</a>{Constants.VALID_LINK_MESSAGE}'
		await context.bot.send_message(chat_id=update.effective_chat.id, text=txt, reply_markup=mu, parse_mode='HTML', reply_to_message_id=update.message.id)
	else:
		if answer_with_error:
			await context.bot.send_message(chat_id=update.effective_chat.id, text=Constants.ERROR_CANT_DOWNLOAD)


def validate(msg):
	return is_from_yt(msg) or \
		"facebook.com/" in msg or \
		"https://fb.watch/" in msg or \
		"https://www.instagram.com/" in msg or \
		"https://www.tiktok.com/" in msg or \
		"https://vm.tiktok.com/" in msg or \
		"https://twitter.com/" in msg


def is_from_yt(url):
	return ("https://www.youtube." in url and "/watch?" in url) or \
		"https://www.youtube.com/shorts/" in url or \
		"https://youtube.com/shorts/" in url or \
		"https://youtu.be/" in url


async def click_callback(update: Update, context: CallbackContext):
	log_bot_event(update, 'click_callback')
	query = update.callback_query
	mode = query.data
	url = str(base64.urlsafe_b64decode(query.message.entities[0].url[11:]))[2:-1]
	await query.answer(f'selected: download from {url}')
	paths = {
		'home': 'download'
	}
	if mode == Constants.MP3:
		ydl_opts = {  # for audio
			'format': 'm4a/bestaudio/best',
			# See help(yt_dlp.postprocessor) for a list of available Postprocessors and their arguments
			'postprocessors': [{  # Extract audio using ffmpeg
				'key': 'FFmpegExtractAudio',
				'preferredcodec': 'm4a',
			}],
			'restrictfilenames': True,
			'paths': paths,
			'trim_file_name': 16,
			'windowsfilenames': True,
		}
	else:
		ydl_opts = {  # for video
			'restrictfilenames': True,
			'paths': paths,
			'trim_file_name': 16,
			'windowsfilenames': True,
		}
	if is_from_yt(url):
		ydl_opts['username'] = Constants.YOUTUBE_USER
		ydl_opts['password'] = Constants.YOUTUBE_PASS
		if Constants.COOKIES_PATH != Constants.EMPTY:
			ydl_opts['cookiesfrombrowser'] = Constants.COOKIES_PATH
	try:
		file_path = download_with_yt_dlp(ydl_opts, url)
	except DownloadError:
		log.error(Constants.ERROR_DOWNLOAD)
		ydl_opts['format'] = "18"
		file_path = download_with_yt_dlp(ydl_opts, url)
	if mode == Constants.MP3:
		file_path = f'{file_path[:-4]}.m4a'
		log.info(f"Sending audio file: {file_path}")
		try:
			await context.bot.send_audio(chat_id=update.effective_chat.id, audio=file_path)
		except TelegramError:
			await upload_file_ftp(update, context, file_path)
	else:
		log.info(f"Sending video file: {file_path}")
		try:
			await context.bot.send_video(chat_id=update.effective_chat.id, video=file_path)
		except TelegramError:
			await upload_file_ftp(update, context, file_path)


def download_with_yt_dlp(ydl_opts, url):
	with yt_dlp.YoutubeDL(ydl_opts) as ydl:
		info = ydl.extract_info(url, download=False)
		file_path = ydl.prepare_filename(info)
		log.info(f"Downloaded file into {file_path}")
		ydl.process_info(info)
	return file_path


async def upload_file_ftp(update: Update, context: CallbackContext, local_file_path):
	await context.bot.send_message(chat_id=update.effective_chat.id, text=Constants.FTP_MESSAGE_START)
	ftp = ''
	try:
		ftp = ftplib.FTP(Constants.FTP_HOST)
		ftp.login(Constants.FTP_USER, Constants.FTP_PASS)
		ftp.cwd(Constants.FTP_REMOTE_FOLDER)
		with open(local_file_path, 'rb') as file:
			remote_file = re.sub(r"\s+", "_", local_file_path.replace('download\\', '').replace('download/', ''))
			ftp.storbinary('STOR ' + remote_file, file)
		log.info('Upload ok')
		await context.bot.send_message(chat_id=update.effective_chat.id, text=Constants.FTP_MESSAGE_OK + Constants.FTP_URL + remote_file)
	except ftplib.all_errors as e:
		log.info('Upload ko:', str(e))
		await context.bot.send_message(chat_id=update.effective_chat.id, text=Constants.ERROR_UPLOAD + str(e))
	finally:
		ftp.quit()


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
	application.add_handler(CallbackQueryHandler(click_callback))
	application.add_handler(MessageHandler(filters.TEXT, chat_check))
	application.add_error_handler(error_handler)
	application.run_polling(allowed_updates=Update.ALL_TYPES)

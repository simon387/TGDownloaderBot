import base64
import ftplib
import html
import json
import logging as log
import os
import random
import re
import signal
import string
import subprocess
import sys
import time
import time as time_os
import traceback
from logging.handlers import RotatingFileHandler

import myjdapi
import telegram
import validators
import yt_dlp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.error import TelegramError
from telegram.ext import ApplicationBuilder, CallbackContext, CommandHandler, ContextTypes, Application, AIORateLimiter, CallbackQueryHandler, MessageHandler, \
	filters
# noinspection PyProtectedMember
from yt_dlp import DownloadError

import Constants as C
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
	level=C.LOG_LEVEL
)

if C.LOG_LEVEL <= log.INFO:
	log.getLogger('httpx').setLevel(log.WARNING)


async def send_version(update: Update, context: CallbackContext):
	log_bot_event(update, 'send_version')
	await context.bot.send_message(chat_id=update.effective_chat.id, text=get_version() + C.VERSION_MESSAGE)


async def send_shutdown(update: Update, context: CallbackContext):
	log_bot_event(update, 'send_shutdown')
	if update.effective_user.id == int(C.TELEGRAM_DEVELOPER_CHAT_ID):
		os.kill(os.getpid(), signal.SIGINT)
	else:
		await context.bot.send_message(chat_id=update.effective_chat.id, text=C.ERROR_NO_GRANT_SHUTDOWN)


async def post_init(app: Application):
	version = get_version()
	log.info(f"Starting TGDownloaderBot, {version}")
	if C.SEND_START_AND_STOP_MESSAGE == C.TRUE:
		await app.bot.send_message(chat_id=C.TELEGRAM_GROUP_ID, text=C.STARTUP_MESSAGE + version, parse_mode=ParseMode.HTML)
		await app.bot.send_message(chat_id=C.TELEGRAM_DEVELOPER_CHAT_ID, text=C.STARTUP_MESSAGE + version, parse_mode=ParseMode.HTML)


# noinspection PyUnusedLocal
async def post_shutdown(app: Application):
	log.info(f"Shutting down the bot")


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
			await show_download_buttons(update, context, False, url)


def extract_first_url(text):
	url_pattern = re.compile(r"https?://(?:[a-zA-Z]|[0-9]|[$-_]|[!*\\(),])+")
	matches = re.findall(url_pattern, text)
	if matches:
		return matches[0]
	else:
		return None


async def show_download_buttons(update: Update, context: CallbackContext, answer_with_error=True, msg=C.EMPTY):
	log_bot_event(update, 'download')
	if msg == C.EMPTY:
		msg = C.SPACE.join(context.args).strip()
	if validate(msg):
		# clean
		if "https://www.youtube." in msg and "/watch?" in msg:
			msg = re.sub('&list=.+', C.EMPTY, msg)
		#
		keyboard = [
			[
				InlineKeyboardButton("Download Audio", callback_data=C.MP3),
				InlineKeyboardButton("Download Video", callback_data=C.MP4),
			]
		]
		mu = InlineKeyboardMarkup(keyboard)
		txt = f'<a href="tg://btn/{str(base64.urlsafe_b64encode(msg.encode(C.UTF8)))}">\u200b</a>{C.VALID_LINK_MESSAGE}'
		await context.bot.send_message(chat_id=update.effective_chat.id, text=txt, reply_markup=mu, parse_mode='HTML', reply_to_message_id=update.message.id)
	else:
		if answer_with_error:
			await context.bot.send_message(chat_id=update.effective_chat.id, text=C.ERROR_CANT_DOWNLOAD)


def validate(msg):
	return is_from_yt(msg) or \
		"facebook.com/" in msg or \
		"https://fb.watch/" in msg or \
		"https://www.instagram.com/" in msg or \
		"https://www.tiktok.com/" in msg or \
		"https://vm.tiktok.com/" in msg or \
		"https://twitter.com/" in msg or \
		"https://x.com/" in msg


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
	ydl_opts = get_ydl_opts(mode)
	if is_from_yt(url):
		ydl_opts['username'] = C.YOUTUBE_USER
		ydl_opts['password'] = C.YOUTUBE_PASS
		if C.COOKIES_PATH != C.EMPTY:
			ydl_opts['cookiesfrombrowser'] = C.COOKIES_PATH
	try:
		await context.bot.send_message(chat_id=update.effective_chat.id, text=C.WAIT_MESSAGE)
		file_path = download_with_yt_dlp(ydl_opts, url)
	except DownloadError:
		log.error(C.ERROR_DOWNLOAD)
		ydl_opts['format'] = "18"
		file_path = download_with_yt_dlp(ydl_opts, url)
	except Exception as e:
		file_path = await download_with_you_get(e, url)
	if file_path is not None:
		await context.bot.send_message(chat_id=update.effective_chat.id, text=C.DOWNLOAD_COMPLETE_MESSAGE)
		await send_media(mode, file_path, context, update)
	else:
		file_path = download_with_jdownloader(url, mode)
		if file_path is not None:
			await context.bot.send_message(chat_id=update.effective_chat.id, text=C.DOWNLOAD_COMPLETE_MESSAGE)
			await send_media(mode, file_path, context, update)
		else:
			await context.bot.send_message(chat_id=update.effective_chat.id, text=C.DOWNLOAD_JSON_ERROR)


async def send_media(mode, file_path, context, update):
	if mode == C.MP3:
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


def get_ydl_opts(mode):
	paths = {
		'home': 'download'
	}
	if mode == C.MP3:
		return {  # for audio
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
		return {  # for video
			'restrictfilenames': True,
			'paths': paths,
			'trim_file_name': 16,
			'windowsfilenames': True,
		}


async def download_with_you_get(e, url):
	path = C.YOU_GET_DWN_PATH_PREFIX + generate_random_string(16)
	log.error('Switching to you-get due to Download KO:', str(e))
	command = ["you-get", "-k", "-f", "-o", path, "-O", C.VIDEO_FILE_NAME, url]
	log.info(f"you-get -k -f -o {path} -O {C.VIDEO_FILE_NAME} {url}")
	result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
	if result.returncode == 0:
		log.info("Command executed successfully!")
		log.info("Output:")
		log.info(result.stdout)
		path_assoluto = os.path.abspath(path)
		file_path = find_file_with_prefix(path_assoluto)
		return os.path.join(path, file_path)
	else:
		log.error("Error executing command:")
		log.error(result.stderr)
	return None


def generate_random_string(length):
	letters = string.ascii_letters
	return C.EMPTY.join(random.choice(letters) for _ in range(length))


def find_file_with_prefix(path):
	files = os.listdir(path)
	for file in files:
		if file.startswith(C.VIDEO_FILE_NAME + "."):
			return file
	return None


def download_with_yt_dlp(ydl_opts, url):
	with yt_dlp.YoutubeDL(ydl_opts) as ydl:
		info = ydl.extract_info(url, download=False)
		file_path = ydl.prepare_filename(info)
		log.info(f"Downloaded file into {file_path}")
		ydl.process_info(info)
	return file_path


def download_with_jdownloader(url, mode):
	jd = myjdapi.Myjdapi()
	jd.set_app_key("EXAMPLE")
	jd.connect(C.JDOWNLOADER_USER, C.JDOWNLOADER_PASS)
	jd.update_devices()
	device = jd.get_device(C.JDOWNLOADER_DEVICE_NAME)
	#
	delete_files_in_directory(C.JDOWNLOADER_DOWNLOAD_PATH)
	#
	device.linkgrabber.add_links(
		params=[{
			"autostart": True,
			"links": url,
			"packageName": None,
			"extractPassword": None,
			"priority": "DEFAULT",
			"downloadPassword": None,
			"destinationFolder": C.JDOWNLOADER_DOWNLOAD_PATH,
			"overwritePackagizerRules": False
		}])
	# wait_for_file
	wait_for_file(C.JDOWNLOADER_DOWNLOAD_PATH, mode)
	#
	if mode == C.MP3:
		return get_first_file_by_extension(C.JDOWNLOADER_DOWNLOAD_PATH, "mp3")
	else:
		return get_first_file_by_extension(C.JDOWNLOADER_DOWNLOAD_PATH, "mp4")


def delete_files_in_directory(directory):
	files = os.listdir(directory)
	for file_name in files:
		file_path = os.path.join(directory, file_name)
		try:
			if os.path.isfile(file_path):
				os.remove(file_path)
				log.info(f"Deleted {file_path}")
		except Exception as e:
			log.error(f"Error deleting {file_path}: {e}")


def wait_for_file(directory, mode):
	if mode == C.MP3:
		extension = "mp3"
	else:
		extension = "mp4"
	while True:
		files = [file for file in os.listdir(directory) if file.endswith("." + extension)]
		if files:
			log.info("Files detected in directory:")
			for file in files:
				log.info(file)
			return files
		else:
			log.info(f"No {extension.upper()} files detected in directory {directory}")
		time.sleep(1)  # Adjust the sleep time as needed


def get_first_file_by_extension(directory, extension):
	for file_name in os.listdir(directory):
		if file_name.endswith(extension):
			return os.path.join(directory, file_name)
	return None  # Return None if no file with the specified extension is found


async def upload_file_ftp(update: Update, context: CallbackContext, local_file_path):
	await context.bot.send_message(chat_id=update.effective_chat.id, text=C.FTP_MESSAGE_START)
	ftp = C.EMPTY
	try:
		ftp = ftplib.FTP(C.FTP_HOST)
		ftp.login(C.FTP_USER, C.FTP_PASS)
		ftp.cwd(C.FTP_REMOTE_FOLDER)
		with open(local_file_path, 'rb') as file:
			remote_file = re.sub(r"\s+", "_", local_file_path.replace('download\\', C.EMPTY).replace('download/', C.EMPTY))
			ftp.storbinary('STOR ' + remote_file, file)
		log.info('Upload ok')
		await context.bot.send_message(chat_id=update.effective_chat.id, text=C.FTP_MESSAGE_OK + C.FTP_URL + remote_file)
	except ftplib.all_errors as e:
		log.info('Upload ko:', str(e))
		await context.bot.send_message(chat_id=update.effective_chat.id, text=C.ERROR_UPLOAD + str(e))
	finally:
		ftp.quit()


if __name__ == '__main__':
	application = ApplicationBuilder() \
		.token(C.TOKEN) \
		.application_class(BotApp) \
		.post_init(post_init) \
		.post_shutdown(post_shutdown) \
		.rate_limiter(AIORateLimiter(max_retries=C.AIO_RATE_LIMITER_MAX_RETRIES)) \
		.http_version(C.HTTP_VERSION) \
		.get_updates_http_version(C.HTTP_VERSION) \
		.build()
	application.add_handler(CommandHandler('version', send_version))
	application.add_handler(CommandHandler('shutdown', send_shutdown))
	application.add_handler(CommandHandler('download', show_download_buttons))
	application.add_handler(CallbackQueryHandler(click_callback))
	application.add_handler(MessageHandler(filters.TEXT, chat_check))
	application.add_error_handler(error_handler)
	application.run_polling(allowed_updates=Update.ALL_TYPES)

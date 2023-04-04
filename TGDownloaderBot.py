import html
import json
import logging as log
import os
import re
import subprocess
import sys
import time as time_os
import traceback
from logging.handlers import RotatingFileHandler

import validators
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CallbackContext, CommandHandler, ContextTypes, Application, AIORateLimiter, filters, MessageHandler, \
	CallbackQueryHandler

import constants as c
from BotApp import BotApp

log.basicConfig(
	handlers=[
		RotatingFileHandler(
			'TGDownloaderBot.log',
			maxBytes=10240000,
			backupCount=5
		),
		log.StreamHandler()
	],
	format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
	level=c.LOG_LEVEL
)


async def send_version(update: Update, context: CallbackContext):
	log_bot_event(update, 'send_version')
	await context.bot.send_message(chat_id=update.effective_chat.id, text=get_version() + c.VERSION_MESSAGE)


async def unknown_command(update: Update, context: CallbackContext):
	log_bot_event(update, 'unknown_command')
	await context.bot.send_message(chat_id=update.effective_chat.id, text=c.ERROR_UNKNOWN_COMMAND_MESSAGE)


async def post_init(app: Application):
	version = get_version()
	log.info("Starting TGDownloaderBot, " + version)
	if c.SEND_START_AND_STOP_MESSAGE == 'true':
		# await app.bot.send_message(chat_id=c.TELEGRAM_GROUP_ID, text=c.STARTUP_MESSAGE + version, parse_mode=ParseMode.HTML)
		await app.bot.send_message(chat_id=c.TELEGRAM_DEVELOPER_CHAT_ID, text=c.STARTUP_MESSAGE + version, parse_mode=ParseMode.HTML)


async def post_shutdown(app: Application):
	log.info("Shutting down, bot id=" + str(app.bot.id))


def log_bot_event(update: Update, method_name: str):
	msg = update.message.text
	user = update.effective_user.first_name
	uid = update.effective_user.id
	log.info("[method=" + method_name + '] Got this message from ' + user + "[id=" + str(uid) + "]" + ": " + msg)


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
	await context.bot.send_message(chat_id=c.TELEGRAM_DEVELOPER_CHAT_ID, text=message, parse_mode=ParseMode.HTML)
	# Restart the bot
	time_os.sleep(5.0)
	os.execl(sys.executable, sys.executable, *sys.argv)


def get_version():
	with open("changelog.txt") as f:
		firstline = f.readline().rstrip()
	return firstline


async def download(update: Update, context: CallbackContext):
	log_bot_event(update, 'download')
	message = c.SPACE.join(context.args).strip()
	if validators.url(message):
		if "https://www.youtube." in message and "/watch?" in message:
			keyboard = [
				[
					InlineKeyboardButton("Download mp3", callback_data='MP3' + message),
					InlineKeyboardButton("Download Video", callback_data='MP4' + message),
				]
			]
			reply_markup = InlineKeyboardMarkup(keyboard)
			await context.bot.send_message(chat_id=update.effective_chat.id, text=c.YT_OK_MESSAGE, reply_markup=reply_markup)
		else:
			await context.bot.send_message(chat_id=update.effective_chat.id, text="I can't download this!")
	else:
		await context.bot.send_message(chat_id=update.effective_chat.id, text="This is not a valid url!")


async def keyboard_callback(update: Update, context: CallbackContext):
	query = update.callback_query
	prefix = query.data[0:3]
	url = query.data[3:]
	await query.answer(f'selected: download from {url}')

	if prefix == 'MP3':
		result = subprocess.run(["yt-dlp.exe", "-x", "--restrict-filenames", "--audio-format", "mp3", url], capture_output=True, text=True)
		log.info("The exit code was: " + str(result.returncode))
		log.info("stdout: " + result.stdout)
		log.info("stderr: " + result.stderr)
		file_name = get_file_name(result.stdout)
		if file_name != '':
			await context.bot.send_audio(chat_id=update.effective_chat.id, audio=file_name)
		else:
			await context.bot.send_message(chat_id=update.effective_chat.id, text="Error on downloading stuffs!")
	else:
		await context.bot.send_message(chat_id=update.effective_chat.id, text="Ancora non posso scaricare video!")


def get_file_name(test_str):
	regex = r"\S+\.mp3"
	matches = re.finditer(regex, test_str, re.MULTILINE)
	for matchNum, match in enumerate(matches, start=1):
		return match.group()
	return ''


if __name__ == '__main__':
	application = ApplicationBuilder() \
		.token(c.TOKEN) \
		.application_class(BotApp) \
		.post_init(post_init) \
		.post_shutdown(post_shutdown) \
		.rate_limiter(AIORateLimiter(max_retries=c.AIO_RATE_LIMITER_MAX_RETRIES)) \
		.http_version(c.HTTP_VERSION) \
		.get_updates_http_version(c.HTTP_VERSION) \
		.build()
	application.add_handler(CommandHandler('version', send_version))
	application.add_handler(CommandHandler('download', download))
	application.add_handler(MessageHandler(filters.COMMAND, unknown_command))
	application.add_handler(CallbackQueryHandler(keyboard_callback))
	application.add_error_handler(error_handler)
	application.run_polling(allowed_updates=Update.ALL_TYPES)

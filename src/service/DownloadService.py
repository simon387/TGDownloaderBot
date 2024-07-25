import base64
import logging as log

from telegram import Update
from telegram.ext import CallbackContext
# noinspection PyProtectedMember
from yt_dlp import DownloadError

from src.service.JDownloaderService import download_with_jdownloader
from src.service.LinkService import is_from_yt
from src.service.LogService import log_bot_event
from src.service.TelegramService import send_media
from src.service.YouGetService import download_with_you_get
from src.service.YoutubeDLService import download_with_yt_dlp, get_ydl_opts
from src.util import Constants as C


# this is the core of the business logic
async def download_clicked(update: Update, context: CallbackContext):
	log.info("==================================================================== \n\n")
	log_bot_event(update, 'download_clicked')
	query = update.callback_query
	mode = query.data
	url = str(base64.urlsafe_b64decode(query.message.entities[0].url[11:]))[2:-1]
	await query.answer(f'selected: download from {url}')
	ydl_opts = get_ydl_opts(mode)
	if is_from_yt(url):  # if is from YouTube, attemp login
		ydl_opts['username'] = C.YOUTUBE_USER
		ydl_opts['password'] = C.YOUTUBE_PASS
		if C.COOKIES_PATH != C.EMPTY:
			ydl_opts['cookiesfrombrowser'] = C.COOKIES_PATH
	try:
		await context.bot.send_message(chat_id=update.effective_chat.id, text=C.WAIT_MESSAGE)
		file_path = download_with_yt_dlp(ydl_opts, url)  # this is the first download try, using yt_dlp
	except DownloadError:
		log.error(C.ERROR_DOWNLOAD)
		ydl_opts['format'] = "18"
		file_path = download_with_yt_dlp(ydl_opts, url)  # if it fails with a DownloadError, use yt_dlp with another format, second try
	except Exception as e:
		file_path = await download_with_you_get(e, url)  # if the error is another one, the 2# try is with you_get
	if file_path is not None:
		await context.bot.send_message(chat_id=update.effective_chat.id, text=C.DOWNLOAD_COMPLETE_MESSAGE)
		await send_media(mode, file_path, context, update)
	else:
		file_path = download_with_jdownloader(url, mode)  # if something fails again, the 3# try is with the jDownloader2 integration
		if file_path is not None:
			await context.bot.send_message(chat_id=update.effective_chat.id, text=C.DOWNLOAD_COMPLETE_MESSAGE)
			await send_media(mode, file_path, context, update)
		else:
			await context.bot.send_message(chat_id=update.effective_chat.id, text=C.DOWNLOAD_JSON_ERROR)
			await context.bot.send_message(chat_id=update.effective_chat.id, text="Contacting the dev...")
			await context.bot.send_message(chat_id=C.TELEGRAM_DEVELOPER_CHAT_ID, text="Someone got a problem with downloading a video.")

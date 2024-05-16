import logging as log

from telegram import Update
from telegram.ext import CallbackContext

from src.service.JDownloaderService import download_with_jdownloader
from src.util import Constants as C


async def test(update: Update, context: CallbackContext):
	log.info(f"Entering test function")
	url = C.SPACE.join(context.args).strip()
	if C.EMPTY == url:
		return await context.bot.send_message(chat_id=update.effective_chat.id, text=C.ERROR_PARAMETER_NEEDED_MESSAGE)
	file_path = download_with_jdownloader(url, C.MP4)
	log.info(f"file_path={file_path}")

import ftplib
import os
import logging as log
from telegram import Update
from telegram.ext import CallbackContext
from src.util import Constants as C


async def upload_to_ftp(update: Update, context: CallbackContext, local_file_path):
	log.info(f"{C.FTP_MESSAGE_START} local_file_path={local_file_path}")
	await context.bot.send_message(chat_id=update.effective_chat.id, text=C.FTP_MESSAGE_START)
	ftp = C.EMPTY
	try:
		ftp = ftplib.FTP(C.FTP_HOST)
		ftp.login(C.FTP_USER, C.FTP_PASS)
		ftp.cwd(C.FTP_REMOTE_FOLDER)
		with open(local_file_path, 'rb') as file:
			remote_file = os.path.basename(local_file_path)
			ftp.storbinary('STOR ' + remote_file, file)
		log.info('Upload OK')
		await context.bot.send_message(chat_id=update.effective_chat.id, text=C.FTP_MESSAGE_OK + C.FTP_URL + remote_file)
	except ftplib.all_errors as e:
		log.info('Upload KO:', str(e))
		await context.bot.send_message(chat_id=update.effective_chat.id, text=C.ERROR_UPLOAD + str(e))
	finally:
		ftp.quit()

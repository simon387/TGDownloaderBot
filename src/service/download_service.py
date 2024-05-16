import base64
import logging as log
import os
import random
import string
import subprocess
import time

import myjdapi
import yt_dlp
from telegram import Update
from telegram.ext import CallbackContext
# noinspection PyProtectedMember
from yt_dlp import DownloadError

from src.service.link_service import is_from_yt
from src.service.log_service import log_bot_event
from src.service.telegram_service import send_media
from src.util import Constants as C


# this is the core of the business logic
async def download_clicked(update: Update, context: CallbackContext):
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


# download method #1
# @return file_path
def download_with_yt_dlp(ydl_opts, url):
	log.info(f"Using download method #1 url={url} ydl_opts={ydl_opts}")
	with yt_dlp.YoutubeDL(ydl_opts) as ydl:
		info = ydl.extract_info(url, download=False)
		file_path = ydl.prepare_filename(info)
		log.info(f"Downloaded file into {file_path}")
		ydl.process_info(info)
	return file_path


# download method #2
# @return file_path
async def download_with_you_get(e, url):
	log.info(f"Using download method #2 url={url}")
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


# download method #3
# @return file_path
def download_with_jdownloader(url, mode):
	log.info(f"Using download method #3 url={url} mode={mode}")
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
			"destinationFolder": C.JDOWNLOADER_DOWNLOAD_PATH,  # TODO For accuracy, it's better to dynamically change this line for concurrence
			"overwritePackagizerRules": True  # was False
		}])
	#
	# wait_for_file
	wait_for_file(C.JDOWNLOADER_DOWNLOAD_PATH, mode, 1)
	#
	if mode == C.MP3:
		return get_first_file_by_extension(C.JDOWNLOADER_DOWNLOAD_PATH, C.MP3_EXTENSION)
	else:
		return get_first_file_by_extension(C.JDOWNLOADER_DOWNLOAD_PATH, C.MP4_EXTENSION)


def get_ydl_opts(mode):  # return just the configuration json for ydl application
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


def generate_random_string(length):
	return C.EMPTY.join(random.choice(string.ascii_letters) for _ in range(length))


def find_file_with_prefix(path):
	for file in os.listdir(path):
		if file.startswith(C.VIDEO_FILE_NAME + C.POINT):
			return file
	return None


def delete_files_in_directory(directory):
	for file_name in os.listdir(directory):
		file_path = os.path.join(directory, file_name)
		try:
			if os.path.isfile(file_path):
				os.remove(file_path)
				log.info(f"Deleted {file_path}")
		except Exception as e:
			log.error(f"Error deleting {file_path}: {e}")


def wait_for_file(directory, mode, secs):
	extension = C.MP4_EXTENSION
	if mode == C.MP3:
		extension = C.MP3_EXTENSION
	while True:
		files = [file for file in os.listdir(directory) if file.endswith(C.POINT + extension)]
		if files:
			log.info(f"Files detected in directory {directory}:")
			for file in files:
				log.info(file)
			return files
		else:
			log.info(f"No {extension.upper()} files detected in directory {directory}")
		time.sleep(secs)


def get_first_file_by_extension(directory, extension):
	for file_name in os.listdir(directory):
		if file_name.endswith(extension):
			return os.path.join(directory, file_name)
	return None  # Return None if no file with the specified extension is found

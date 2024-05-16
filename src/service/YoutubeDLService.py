import logging as log

import yt_dlp

from src.util import Constants as C


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

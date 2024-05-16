import logging as log
import os
import time

import myjdapi

from src.util import Constants as C


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

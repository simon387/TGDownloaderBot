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
	jd.set_app_key("EXAMPLE")  # doesn't matter
	jd.connect(C.JDOWNLOADER_USER, C.JDOWNLOADER_PASS)
	jd.update_devices()
	device = jd.get_device(C.JDOWNLOADER_DEVICE_NAME)
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
			"overwritePackagizerRules": True  # was False
		}])
	#
	links = wait_for_links(device, 2)  # wait for jDownloader link interceptor
	#
	extension = get_extension(mode)
	#
	filename = get_filename(extension, links, url)
	#
	if filename == C.EMPTY:
		log.error("Something went wrong! No filename found")
		return None
	#
	wait_for_file_being_downloaded(C.JDOWNLOADER_DOWNLOAD_PATH, filename, extension, 1)
	#
	return os.path.join(C.JDOWNLOADER_DOWNLOAD_PATH, filename)


def wait_for_links(device, secs):
	links = device.downloads.query_links()
	while not links:
		links = device.downloads.query_links()
		log.info("Waiting for links...")
		time.sleep(secs)
	return links


def get_extension(mode):
	extension = C.MP4_EXTENSION
	if mode == C.MP3:
		extension = C.MP3_EXTENSION
	return extension


def get_filename(extension, links, url):
	filename = C.EMPTY
	for link in links:
		if link['url'] == url and link['name'][-3:] == extension:
			filename = link['name']
			log.info("Filename found!")
			break
	return filename


def wait_for_file_being_downloaded(directory, filename, extension, secs):
	log.info(f"wait_for_file :: directory={directory} filename={filename} extension={extension} secs={secs})")
	while True:
		files = [file for file in os.listdir(directory) if file.endswith(C.POINT + extension)]
		if files:
			log.info(f"Files detected in directory {directory}:")
			for file in files:
				log.info(file)
				if filename in file:
					return
		else:
			log.info(f"No {extension.upper()} files detected in directory {directory}")
		time.sleep(secs)

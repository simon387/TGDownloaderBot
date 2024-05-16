import logging as log
import os
import random
import string
import subprocess

from src.util import Constants as C


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


def find_file_with_prefix(path):
	for file in os.listdir(path):
		if file.startswith(C.VIDEO_FILE_NAME + C.POINT):
			return file
	return None


def generate_random_string(length):
	return C.EMPTY.join(random.choice(string.ascii_letters) for _ in range(length))

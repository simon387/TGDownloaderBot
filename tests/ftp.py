import os

from src.util import Constants as C
import ftplib
import re

ftp = C.EMPTY
local_file_path = 'C:\\dev\\TGDownloaderBot\\tests\\ftp.py'

try:
	ftp = ftplib.FTP(C.FTP_HOST)
	ftp.login(C.FTP_USER, C.FTP_PASS)
	ftp.cwd(C.FTP_REMOTE_FOLDER)
	with open(local_file_path, 'rb') as file:
		remote_file = re.sub(r"\s+", "_", local_file_path.replace('download\\', C.EMPTY).replace('download/', C.EMPTY))

		remote_file = os.path.basename(local_file_path)

		ftp.storbinary('STOR ' + remote_file, file)
except ftplib.all_errors as e:
	print("error")
finally:
	ftp.quit()

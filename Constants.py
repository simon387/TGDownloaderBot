import configparser
import logging

config = configparser.RawConfigParser()
config.read("config.properties")
# application's secrets
SECRETS = "secrets"
TOKEN = config.get(SECRETS, "telegram.token")
TELEGRAM_GROUP_ID = config.get(SECRETS, "telegram.group.id")
TELEGRAM_DEVELOPER_CHAT_ID = config.get(SECRETS, "telegram.developer.chat.id")
# application's settings
APPLICATION = "application"
SEND_START_AND_STOP_MESSAGE = config.get(APPLICATION, "send.start.and.stop.message")
HTTP_VERSION = config.get(APPLICATION, "http.version")
AIO_RATE_LIMITER_MAX_RETRIES = 10
case = config.get(APPLICATION, "log.level")
if case == "info":
	LOG_LEVEL = logging.INFO
elif case == "debug":
	LOG_LEVEL = logging.DEBUG
elif case == "error":
	LOG_LEVEL = logging.ERROR
else:
	LOG_LEVEL = logging.DEBUG
# ftp
FTP_URL = config.get(APPLICATION, "ftp.url")
FTP_HOST = config.get(APPLICATION, "ftp.host")
FTP_USER = config.get(APPLICATION, "ftp.user")
FTP_PASS = config.get(APPLICATION, "ftp.pass")
FTP_REMOTE_FOLDER = config.get(APPLICATION, "ftp.remote.folder")
# messages
STARTUP_MESSAGE = "TGDownloaderBot started! "
STOP_MESSAGE = "TGDownloaderBot stopped!"
VERSION_MESSAGE = " - more info on https://github.com/simon387/TGDownloaderBot/blob/master/changelog.txt"
VALID_LINK_MESSAGE = "This is a valid page link! What do you want to do?"
ERROR_NO_GRANT_SHUTDOWN = "You can't shutdown the bot!"
ERROR_CANT_DOWNLOAD = "I can't download this!"
ERROR_NOT_VALID_URL = "This is not a valid url!"
ERROR_UPLOAD = "Error on ftp upload: "
FTP_MESSAGE_OK = "Video loaded here: "
FTP_MESSAGE_START = "Loading file to ftp server because is too big for Telegram"
# urls

# var
SPACE = " "
EMPTY = ""
MP3 = "MP3"
MP4 = "MP4"
TRUE = "true"
UTF8 = "utf-8"

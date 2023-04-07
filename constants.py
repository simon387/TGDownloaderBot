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
# messages
STARTUP_MESSAGE = "TGDownloaderBot started! "
STOP_MESSAGE = "TGDownloaderBot stopped!"
VERSION_MESSAGE = " - more info on https://github.com/simon387/TGDownloaderBot/blob/master/changelog.txt"
ERROR_UNKNOWN_COMMAND_MESSAGE = "This command doesn't exist!"
YT_OK_MESSAGE = "This is a valid page link! What do you want to do?"
ERROR_NO_GRANT_SHUTDOWN = "You can't shutdown the bot!"
# urls

# var
SPACE = " "
EMPTY = ""
MP3 = "MP3"
MP4 = "MP4"
TRUE = "true"

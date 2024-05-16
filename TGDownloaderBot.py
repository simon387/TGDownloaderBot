import logging as log
from logging.handlers import RotatingFileHandler

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, AIORateLimiter, CallbackQueryHandler, MessageHandler, filters

from src.override.BotApp import BotApp
from src.service.download_service import download_clicked
from src.service.error_service import error_handler
from src.service.log_service import post_init, post_shutdown, send_version
from src.service.shutdown_service import send_shutdown
from src.service.telegram_service import show_download_buttons, chat_check
from src.util import Constants as C

log.basicConfig(
	handlers=[
		RotatingFileHandler(
			'_TGDownloaderBot.log',
			maxBytes=10240000,
			backupCount=5
		),
		log.StreamHandler()
	],
	format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
	level=C.LOG_LEVEL
)

if C.LOG_LEVEL <= log.INFO:
	log.getLogger('httpx').setLevel(log.WARNING)

# application's setup
if __name__ == '__main__':
	application = ApplicationBuilder() \
		.token(C.TOKEN) \
		.application_class(BotApp) \
		.post_init(post_init) \
		.post_shutdown(post_shutdown) \
		.rate_limiter(AIORateLimiter(max_retries=C.AIO_RATE_LIMITER_MAX_RETRIES)) \
		.http_version(C.HTTP_VERSION) \
		.get_updates_http_version(C.HTTP_VERSION) \
		.build()
	application.add_handler(CommandHandler('version', send_version))
	application.add_handler(CommandHandler('shutdown', send_shutdown))
	application.add_handler(CommandHandler('download', show_download_buttons))
	application.add_handler(CallbackQueryHandler(download_clicked))
	application.add_handler(MessageHandler(filters.TEXT, chat_check))
	application.add_error_handler(error_handler)
	application.run_polling(allowed_updates=Update.ALL_TYPES)

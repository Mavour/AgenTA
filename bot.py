import asyncio
import logging
from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from telegram.request import HTTPXRequest
from config import TELEGRAM_TOKEN
from handlers import (
    start,
    show_menu,
    help_command,
    journal_command,
    weekly_report_command,
    news_command,
    prices_command,
    predict_command,
    twitter_status_command,
    set_twitter_command,
    handle_photo,
    handle_text,
    button_handler,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


async def run_bot():
    request = HTTPXRequest(connection_pool_size=8, read_timeout=30, connect_timeout=30, write_timeout=30)
    app = Application.builder().token(TELEGRAM_TOKEN).request(request).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", show_menu))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("journal", journal_command))
    app.add_handler(CommandHandler("report", weekly_report_command))
    app.add_handler(CommandHandler("news", news_command))
    app.add_handler(CommandHandler("price", prices_command))
    app.add_handler(CommandHandler("predict", predict_command))
    app.add_handler(CommandHandler("twitterstatus", twitter_status_command))
    app.add_handler(CommandHandler("settwitter", set_twitter_command))

    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    app.add_handler(CallbackQueryHandler(button_handler))

    logger.info("Bot berjalan. Tekan Ctrl+C untuk menghentikan.")
    await app.initialize()
    await app.bot.set_my_commands([
        BotCommand("start", "Mulai bot"),
        BotCommand("menu", "Menu utama"),
        BotCommand("help", "Panduan lengkap"),
        BotCommand("journal", "Riwayat analisis"),
        BotCommand("report", "Weekly report"),
        BotCommand("news", "Crypto news"),
        BotCommand("price", "Harga crypto"),
        BotCommand("predict", "Market prediction"),
        BotCommand("twitterstatus", "Status Twitter cookie"),
        BotCommand("settwitter", "Set Twitter cookie"),
    ])
    await app.start()
    await app.updater.start_polling(allowed_updates=Update.ALL_TYPES)

    try:
        while True:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, SystemExit, asyncio.CancelledError):
        pass
    finally:
        logger.info("Menghentikan bot...")
        try:
            await app.updater.stop()
            await app.stop()
            await app.shutdown()
        except Exception:
            pass


def main():
    logger.info("Memulai Crypto TA Bot...")
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        logger.info("Bot dihentikan.")


if __name__ == "__main__":
    main()

import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

import config
import database as db
from handlers.admin import router as admin_router
from handlers.operator import router as operator_router
from handlers.client import router as client_router
from handlers.relay import router as relay_router

# Loglarni sozlash
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


async def main():
    if not config.BOT_TOKEN or config.BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
        logger.error(
            "BOT_TOKEN belgilanmagan! Iltimos, .env faylini oching va Telegram @BotFather dan olgan tokeningizni kiriting."
        )
        sys.exit(1)

    # 1. Bazani tayyorlash
    logger.info("Ma'lumotlar bazasi initsializatsiya qilinmoqda...")
    await db.init_db()
    logger.info("Ma'lumotlar bazasi tayyor.")

    # 2. Bot va Dispatcher
    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()

    # 3. Routerlarni ulash (tartib juda muhim!)
    dp.include_router(admin_router)
    dp.include_router(operator_router)
    dp.include_router(client_router)
    dp.include_router(relay_router)

    logger.info(f"«{config.COMPANY_NAME}» Call Center Bot ishga tushmoqda...")
    
    # Eski o'qilmagan xabarlarni o'tkazib yuborish
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot to'xtatildi.")

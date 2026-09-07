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


async def auto_close_sessions_loop(bot: Bot):
    """
    Har 60 soniyada 1 soatdan oshgan faol suhbatlarni tekshirish va avtomatik yopish.
    Operator va mijozga bildirishnoma yuboriladi, operator holati yana 'available' qilinadi.
    """
    while True:
        try:
            await asyncio.sleep(60)
            expired = await db.get_expired_active_sessions(timeout_hours=1.0)
            for sess in expired:
                ticket_id = sess["ticket_id"]
                op_id = sess["operator_id"]
                cust_id = sess["customer_id"]
                cust_name = sess["customer_name"]

                logger.info(f"Ticket #{ticket_id} 1 soatdan oshganligi sababli avtomatik yakunlanmoqda...")
                await db.close_session_by_ticket_id(ticket_id)

                # Operatorga bildirishnoma va xabarlarni tozalash
                try:
                    from handlers.common import clean_up_operator_session_messages
                    await clean_up_operator_session_messages(bot, sess["id"], op_id)
                    from keyboards import get_operator_idle_keyboard
                    await bot.send_message(
                        chat_id=op_id,
                        text=(
                            f"⏱ <b>Mijoz #{ticket_id} ({cust_name}) bilan muloqot vaqti (1 soat) to'ldi va tizim tomonidan yakunlandi.</b>\n\n"
                            "🧹 <i>Suhbat xabarlari chatdan tozalandi.</i>\n"
                            "📜 <i>Yozishmalar tarixini <b>«📋 Mening suhbatlarim»</b> bo'limida ko'rishingiz mumkin.</i>"
                        ),
                        reply_markup=get_operator_idle_keyboard(is_available=True, is_admin=(op_id in config.ADMIN_IDS)),
                        parse_mode="HTML"
                    )
                except Exception:
                    pass

                # Mijozga bildirishnoma va baholash
                try:
                    from keyboards import get_customer_rating_keyboard
                    await bot.send_message(
                        chat_id=cust_id,
                        text=(
                            f"⏱ <b>Muloqot vaqti (1 soat) yakunlandi.</b>\n\n"
                            f"«{config.COMPANY_NAME}» xizmatlaridan foydalanganingiz uchun tashakkur!\n"
                            f"{config.RATING_PROMPT}"
                        ),
                        reply_markup=get_customer_rating_keyboard(ticket_id),
                        parse_mode="HTML"
                    )
                except Exception:
                    pass
        except Exception as e:
            logger.error(f"Auto close loop error: {e}")


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

    # 4. Avtomatik 1 soatlik taymer vazifasini ishga tushirish
    asyncio.create_task(auto_close_sessions_loop(bot))

    logger.info(f"«{config.COMPANY_NAME}» Call Center Bot ishga tushmoqda...")
    
    # Eski o'qilmagan xabarlarni o'tkazib yuborish
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)



if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot to'xtatildi.")

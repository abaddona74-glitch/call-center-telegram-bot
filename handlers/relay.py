from aiogram import Router, Bot
from aiogram.types import Message
from aiogram.exceptions import TelegramAPIError
import database as db

router = Router()


@router.message()
async def relay_messages(message: Message, bot: Bot):
    """
    Barcha boshqa xabarlar (matn, rasm, voice, video, hujjat)ni
    faol sessiya ishtirokchilariga uzatuvchi asosiy relay xizmati.
    """
    user_id = message.from_user.id

    # 1. Xabar OPERATOR tomonidan yozildimi?
    active_op_sess = await db.get_active_session_by_operator(user_id)
    if active_op_sess:
        customer_id = active_op_sess["customer_id"]
        try:
            # Xabarni mijozga aynan qanday bo'lsa shunday nusxalab yuboramiz
            await message.copy_to(chat_id=customer_id)
        except TelegramAPIError as e:
            await message.answer(f"⚠️ Xabarni mijozga yetkazishda xatolik yuz berdi: {e}")
        return

    # 2. Xabar MIJOZ tomonidan yozildimi?
    active_cust_sess = await db.get_active_session_by_customer(user_id)
    if active_cust_sess:
        operator_id = active_cust_sess["operator_id"]
        try:
            # Xabarni operatorga nusxalaymiz
            await message.copy_to(chat_id=operator_id)
        except TelegramAPIError as e:
            await message.answer(f"⚠️ Xabarni operatorga yetkazishda xatolik: {e}")
        return

    # 3. Agar mijoz navbatda kutayotgan bo'lsa
    pos = await db.get_queue_position(user_id)
    if pos is not None:
        await message.answer(
            f"📨 Xabaringiz qabul qilindi. Operator ulangan zahoti xabarlaringizni ko'radi.\n"
            f"Siz navbatda <b>{pos}-o'rinda</b> turibsiz.",
            parse_mode="HTML"
        )
        return

    # 4. Agar umumiy begona foydalanuvchi bo'lsa (na navbatda, na suhbatda, na operator)
    await message.answer(
        "Operator bilan bog'lanish uchun /start buyrug'ini bosing.",
        parse_mode="HTML"
    )

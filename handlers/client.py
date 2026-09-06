from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.filters import CommandStart, Command
import database as db
import config
from keyboards import (
    get_customer_queue_keyboard,
    get_customer_rating_keyboard,
    get_operator_idle_keyboard
)
from handlers.common import broadcast_new_ticket_to_operators

router = Router()


from aiogram.fsm.context import FSMContext


@router.message(CommandStart())
async def cmd_start(message: Message, bot: Bot, state: FSMContext):
    user_id = message.from_user.id
    user_name = message.from_user.full_name or "Mijoz"

    # 0. Agar operator ulanish uchun havola orqali kirgan bo'lsa: /start op yoki /start operator
    start_args = message.text.split()
    if len(start_args) > 1 and start_args[1].lower() in ["operator", "op", "admin"]:
        from handlers.operator import start_operator_registration_flow
        await start_operator_registration_flow(message, state)
        return

    # 1. Agar foydalanuvchi Admin bo'lsa
    if user_id in config.ADMIN_IDS:
        from keyboards import get_admin_main_keyboard
        op = await db.get_operator(user_id)
        role_info = " (va Operator)" if op else ""
        await message.answer(
            f"👑 <b>Assalomu alaykum, Hurmatli Admin{role_info}!</b>\n\n"
            f"«{config.COMPANY_NAME}» call center boshqaruv panelidasiz.\n"
            "Kerakli bo'limni tanlang:",
            reply_markup=get_admin_main_keyboard(),
            parse_mode="HTML"
        )
        return

    # 2. Agar foydalanuvchi allaqachon operator bo'lsa
    op = await db.get_operator(user_id)
    if op:
        is_avail = (op["status"] != "offline")
        code_badge = f" [#{op['operator_code']}]" if op.get("operator_code") else ""
        await message.answer(
            f"Assalomu alaykum, operator <b>{op['full_name']}{code_badge}</b>!\n"
            "Siz boshqaruv panelidasiz.",
            reply_markup=get_operator_idle_keyboard(is_avail),
            parse_mode="HTML"
        )
        return

    # 2. Agar foydalanuvchi hozir faol suhbatda bo'lsa
    active_sess = await db.get_active_session_by_customer(user_id)
    if active_sess:
        await message.answer(
            f"Siz hozirda operator <b>{active_sess['operator_name']}</b> bilan muloqotdasiz.\n"
            "Savollaringizni to'g'ridan-to'g'ri yozishingiz mumkin.",
            parse_mode="HTML"
        )
        return

    # 3. Agar foydalanuvchi navbatda kutayotgan bo'lsa
    pos = await db.get_queue_position(user_id)
    if pos is not None:
        await message.answer(
            f"Siz allaqachon navbatdasiz!\n"
            f"Navbatdagi o'rningiz: <b>#{pos}</b>\n"
            "Iltimos, operator bog'lanishini kuting.",
            reply_markup=get_customer_queue_keyboard(),
            parse_mode="HTML"
        )
        return

    # 4. Yangi mijozni navbatga qo'shish
    ticket_id, pos = await db.add_to_queue(user_id, user_name)

    welcome_text = config.QUEUE_WELCOME_TEMPLATE.format(
        customer_name=user_name,
        company_name=config.COMPANY_NAME,
        ticket_id=ticket_id,
        position=pos
    )

    await message.answer(
        welcome_text,
        reply_markup=get_customer_queue_keyboard(),
        parse_mode="HTML"
    )

    # Operatorlarga xabarnoma tarqatish
    await broadcast_new_ticket_to_operators(bot, ticket_id, user_name, "")


@router.message(F.text == "ℹ️ Navbatimni tekshirish")
async def check_queue_position(message: Message):
    pos = await db.get_queue_position(message.from_user.id)
    if pos is not None:
        await message.answer(
            f"📍 Siz navbatda <b>{pos}-o'rinda</b> turibsiz.\n"
            f"Operator bo'shashi bilan sizga xabar beramiz.",
            parse_mode="HTML"
        )
    else:
        await message.answer("Siz hozirda navbatda emassiz. Yangi murojaat boshlash uchun /start bosing.")


@router.message(F.text == "❌ Navbatdan chiqish")
async def cancel_queue(message: Message):
    # Navbatdan o'chirish
    pos = await db.get_queue_position(message.from_user.id)
    if pos is not None:
        await db.close_session_by_customer(message.from_user.id)
        # Bazasidan queue ni ham closed qilish
        import aiosqlite
        async with aiosqlite.connect(config.DB_PATH) as conn:
            await conn.execute(
                "UPDATE queue SET status = 'closed' WHERE customer_id = ? AND status = 'waiting'",
                (message.from_user.id,)
            )
            await conn.commit()

        await message.answer(
            "Siz navbatdan chiqdingiz. Qaytadan bog'lanish uchun /start bosing.",
            reply_markup=ReplyKeyboardRemove()
        )
    else:
        await message.answer("Siz hozirda navbatda emassiz.")


@router.message(F.text == "❌ Suhbatni yakunlash")
async def customer_end_chat(message: Message, bot: Bot):
    session = await db.close_session_by_customer(message.from_user.id)
    if not session:
        await message.answer(
            "Hozir faol suhbat mavjud emas. Yangi murojaat uchun /start bosing.",
            reply_markup=ReplyKeyboardRemove()
        )
        return

    operator_id = session["operator_id"]
    ticket_id = session["ticket_id"]

    farewell_text = (
        f"{config.FAREWELL_TEMPLATE.format(company_name=config.COMPANY_NAME)}\n\n"
        f"{config.RATING_PROMPT}"
    )

    # Mijozga xayrlashuv va yulduzli baholash tugmalari
    await message.answer(
        farewell_text,
        reply_markup=get_customer_rating_keyboard(ticket_id),
        parse_mode="HTML"
    )

    # Operatorga xabar
    try:
        await bot.send_message(
            chat_id=operator_id,
            text=f"ℹ️ Mijoz #{ticket_id} suhbatni yakunladi.",
            reply_markup=get_operator_idle_keyboard(is_available=True)
        )
    except Exception:
        pass


@router.callback_query(F.data.startswith("rate:"))
async def cb_rate_service(callback: CallbackQuery):
    parts = callback.data.split(":")
    ticket_id = int(parts[1])
    stars = int(parts[2])
    
    await db.save_session_rating(ticket_id, stars)
    await callback.answer(f"Rahmat! {stars} ⭐ bilan baholadingiz.", show_alert=True)
    try:
        await callback.message.edit_text(
            f"✅ <b>Katta rahmat!</b>\n"
            f"Siz ko'rsatilgan xizmat sifatini <b>{stars} ⭐</b> bilan baholadingiz.\n\n"
            "<i>«{company}» xizmatlaridan foydalanganingiz uchun tashakkur! Yangi murojaat uchun /start bosing.</i>".format(company=config.COMPANY_NAME),
            parse_mode="HTML"
        )
    except Exception:
        pass

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
import aiosqlite

import database as db
import config
from regions import CONTRACT_REGIONS
from keyboards import (
    get_customer_main_menu_keyboard,
    get_regions_keyboard,
    get_region_details_keyboard,
    get_customer_queue_keyboard,
    get_customer_rating_keyboard,
    get_operator_idle_keyboard
)
from handlers.common import broadcast_new_ticket_to_operators

router = Router()


def _format_eta_text(eta: dict, subject: str = "") -> str:
    ticket_id = eta["ticket_id"]
    ahead = eta["ahead_count"]
    online = eta["online_operators"]
    avail = eta["available_operators"]
    est_min = eta["est_minutes"]
    est_max = eta["est_max"]

    subj_str = f"<b>{subject}</b> bo'yicha " if subject else ""
    text = f"⏳ Sizning {subj_str}murojaatingiz qabul qilindi (Ticket #{ticket_id}).\n\n"

    if online == 0:
        text += (
            "🔴 <b>Hozirda barcha operatorlarimiz tanaffusda.</b>\n"
            "Murojaatingiz navbatga yozildi. Operatorlarimiz ishga qaytishi bilanoq sizga ulanamiz.\n\n"
            "<i>Iltimos, kuting...</i>"
        )
    elif ahead == 0 and avail > 0:
        text += (
            "🟢 <b>Bo'sh operatorimiz hozir sizga ulanmoqda!</b>\n"
            "<i>Iltimos, bir necha soniya kuting...</i>"
        )
    else:
        ahead_text = f"👥 <b>Sizdan oldingi murojaatlar:</b> {ahead} ta\n" if ahead > 0 else ""
        text += (
            "🟡 <b>Hozirda barcha operatorlarimiz mijozlar bilan muloqotda.</b>\n"
            f"⏱ <b>Taxminiy kutish vaqti:</b> ~{est_min}–{est_max} daqiqa\n"
            f"{ahead_text}\n"
            "<i>Operatorimiz bo'shashi bilan darhol sizga ulanadi, iltimos kuting...</i>"
        )
    return text


# ================= ASOSIY /start BUYRUG'I =================

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
            reply_markup=get_operator_idle_keyboard(is_avail, is_admin=(user_id in config.ADMIN_IDS)),
            parse_mode="HTML"
        )
        return

    # 3. Agar foydalanuvchi hozir faol suhbatda bo'lsa
    active_sess = await db.get_active_session_by_customer(user_id)
    if active_sess:
        await message.answer(
            f"Siz hozirda operator <b>{active_sess['operator_name']}</b> bilan muloqotdasiz.\n"
            "Savollaringizni to'g'ridan-to'g'ri yozishingiz mumkin.",
            parse_mode="HTML"
        )
        return

    # 4. Agar foydalanuvchi navbatda kutayotgan bo'lsa
    eta = await db.get_queue_eta_info(user_id)
    if eta:
        ahead = eta["ahead_count"]
        online = eta["online_operators"]
        avail = eta["available_operators"]
        est_min = eta["est_minutes"]
        est_max = eta["est_max"]
        if online == 0:
            status_desc = "🔴 Hozirda operatorlar tanaffusda, tez orada ulanamiz."
        elif ahead == 0 and avail > 0:
            status_desc = "🟢 Bo'sh operator hozir sizga ulanmoqda!"
        else:
            ahead_text = f"\n👥 <b>Sizdan oldingi murojaatlar:</b> {ahead} ta" if ahead > 0 else ""
            status_desc = (
                "🟡 <b>Hozirda barcha operatorlarimiz mijozlar bilan muloqotda.</b>\n"
                f"⏱ <b>Taxminiy kutish vaqti:</b> ~{est_min}–{est_max} daqiqa{ahead_text}"
            )

        await message.answer(
            f"📍 <b>Murojaatingiz holati (Ticket #{eta['ticket_id']}):</b>\n\n"
            f"{status_desc}\n\n"
            "<i>Iltimos, operator bog'lanishini kuting.</i>",
            reply_markup=get_customer_queue_keyboard(),
            parse_mode="HTML"
        )
        return

    # 5. Yangi mijozga asosiy xizmatlar menyusini ko'rsatish
    welcome_text = (
        f"👋 <b>Assalomu alaykum, {user_name}!</b>\n\n"
        f"«{config.COMPANY_NAME}» yagona aloqa markaziga xush kelibsiz.\n\n"
        "Sizga qanday yordam bera olamiz? Iltimos, kerakli bo'limni tanlang:"
    )

    await message.answer(
        welcome_text,
        reply_markup=get_customer_main_menu_keyboard(),
        parse_mode="HTML"
    )


# ================= NAVBATGA ULASH YORDAMCHI FUNKSIYASI =================

async def _connect_customer_to_queue(message: Message, bot: Bot, subject: str):
    """Mijozni ma'lum bir mavzu bo'yicha operator navbatiga qo'shish"""
    user_id = message.from_user.id
    user_name = message.from_user.full_name or "Mijoz"

    # Faol suhbatda bo'lsa
    active_sess = await db.get_active_session_by_customer(user_id)
    if active_sess:
        await message.answer(
            f"Siz hozirda operator <b>{active_sess['operator_name']}</b> bilan muloqotdasiz.\n"
            "Savollaringizni to'g'ridan-to'g'ri yozishingiz mumkin.",
            parse_mode="HTML"
        )
        return

    # Allaqachon navbatda bo'lsa
    eta = await db.get_queue_eta_info(user_id)
    if eta:
        ahead = eta["ahead_count"]
        est_min = eta["est_minutes"]
        est_max = eta["est_max"]
        await message.answer(
            f"📍 Siz allaqachon navbatdasiz (Ticket #{eta['ticket_id']}).\n"
            f"⏱ <b>Taxminiy kutish vaqti:</b> ~{est_min}–{est_max} daqiqa (oldinda {ahead} ta murojaat).\n\n"
            "Iltimos, operator bog'lanishini kuting.",
            reply_markup=get_customer_queue_keyboard(),
            parse_mode="HTML"
        )
        return

    # Navbatga qo'shish
    first_msg = f"[Yo'nalish: {subject}]"
    customer_username = message.from_user.username or ""
    ticket_id, pos = await db.add_to_queue(
        user_id, 
        user_name, 
        first_message=first_msg, 
        customer_username=customer_username
    )
    eta = await db.get_queue_eta_info(user_id)
    welcome_text = _format_eta_text(eta, subject)

    await message.answer(
        welcome_text,
        reply_markup=get_customer_queue_keyboard(),
        parse_mode="HTML"
    )

    # Operatorlarga mavzu bilan bildirishnoma tarqatish
    await broadcast_new_ticket_to_operators(
        bot, 
        ticket_id, 
        user_name, 
        first_msg, 
        customer_id=user_id, 
        customer_username=customer_username
    )



# ================= YO'NALISHLAR (BUTTON HANDLERS) =================

@router.message(F.text == "⚖️ e-Huquqshunos")
async def handle_e_huquqshunos(message: Message, bot: Bot):
    await _connect_customer_to_queue(message, bot, "⚖️ e-Huquqshunos")


@router.message(F.text == "📄 edo.ijro.uz")
async def handle_edo_ijro(message: Message, bot: Bot):
    await _connect_customer_to_queue(message, bot, "📄 edo.ijro.uz")


@router.message(F.text == "📝 Shartnoma masalasida")
async def handle_contract_issues(message: Message):
    text = (
        "📝 <b>Shartnoma masalasida</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "Iltimos, shartnoma bo'yicha bog'lanmoqchi bo'lgan <b>hududingizni (viloyat yoki shahar)</b> tanlang:\n\n"
        "<i>Tegishli mutaxassislar bilan to'g'ridan-to'g'ri aloqa ma'lumotlari beriladi.</i>"
    )
    await message.answer(text, reply_markup=get_regions_keyboard(), parse_mode="HTML")


# ================= VILOYATLAR VA SHARTNOMA INLINE CALLBACKLARI =================

@router.callback_query(F.data.startswith("region:"))
async def cb_region_selected(callback: CallbackQuery):
    region_key = callback.data.split(":")[1]
    reg = CONTRACT_REGIONS.get(region_key)
    if not reg:
        await callback.answer("Hudud ma'lumotlari topilmadi!", show_alert=True)
        return

    text = (
        f"📝 <b>Shartnoma masalasida — {reg['name']}</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "Tegishli mas'ul mutaxassislar bilan bog'lanish uchun:\n\n"
        "📞 <b>Aloqa telefonlari:</b>\n"
    )
    for p in reg["phones"]:
        text += f"• <code>{p}</code>\n"

    if reg.get("telegram"):
        text += f"\n💬 <b>Telegram:</b> {reg['telegram']}\n"

    text += (
        "\n──────────────────────\n"
        "<i>💡 Shuningdek, kerak bo'lsa operator bilan ham bog'lanishingiz mumkin.</i>"
    )

    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_region_details_keyboard(region_key),
            parse_mode="HTML"
        )
        await callback.answer()
    except Exception:
        await callback.answer()


@router.callback_query(F.data == "regions_list")
async def cb_regions_list(callback: CallbackQuery):
    text = (
        "📝 <b>Shartnoma masalasida</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "Iltimos, shartnoma bo'yicha bog'lanmoqchi bo'lgan <b>hududingizni (viloyat yoki shahar)</b> tanlang:"
    )
    try:
        await callback.message.edit_text(text, reply_markup=get_regions_keyboard(), parse_mode="HTML")
        await callback.answer()
    except Exception:
        await callback.answer()


@router.callback_query(F.data == "back_to_main_menu")
async def cb_back_to_main_menu(callback: CallbackQuery):
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.message.answer(
        "Asosiy menyudasiz. Kerakli bo'limni tanlang:",
        reply_markup=get_customer_main_menu_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("queue_from_region:"))
async def cb_queue_from_region(callback: CallbackQuery, bot: Bot):
    region_key = callback.data.split(":")[1]
    reg = CONTRACT_REGIONS.get(region_key, {})
    reg_name = reg.get("name", "Hudud")

    subject = f"📝 Shartnoma ({reg_name})"
    await callback.answer("Operator navbatiga ulanmoqdasiz...")
    await _connect_customer_to_queue(callback.message, bot, subject)


# ================= NAVBAT VA SUHBATNI BOSHQARISH =================

@router.message(F.text == "ℹ️ Navbatimni tekshirish")
async def check_queue_position(message: Message):
    # Agar foydalanuvchi allaqachon suhbatda bo'lsa
    active_sess = await db.get_active_session_by_customer(message.from_user.id)
    if active_sess:
        await message.answer(
            f"💬 Siz hozirda operator <b>{active_sess['operator_name']}</b> bilan muloqotdasiz.\n\n"
            "Savollaringizni to'g'ridan-to'g'ri yozishingiz mumkin.",
            reply_markup=get_customer_active_keyboard(),
            parse_mode="HTML"
        )
        return

    eta = await db.get_queue_eta_info(message.from_user.id)
    if eta:
        ahead = eta["ahead_count"]
        online = eta["online_operators"]
        avail = eta["available_operators"]
        est_min = eta["est_minutes"]
        est_max = eta["est_max"]
        if online == 0:
            status_desc = "🔴 Barcha operatorlar tanaffusda, tez orada sizga ulanamiz."
        elif ahead == 0 and avail > 0:
            status_desc = "🟢 Navbatingiz yetib keldi, operator ulanmoqda!"
        else:
            ahead_text = f"\n👥 <b>Sizdan oldin:</b> {ahead} ta murojaat bor" if ahead > 0 else ""
            status_desc = (
                "🟡 <b>Hozirda barcha operatorlarimiz mijozlar bilan muloqotda.</b>\n"
                f"⏱ <b>Taxminiy kutish vaqti:</b> ~{est_min}–{est_max} daqiqa{ahead_text}"
            )

        await message.answer(
            f"📍 <b>Murojaatingiz holati (Ticket #{eta['ticket_id']}):</b>\n\n"
            f"{status_desc}\n\n"
            "<i>Iltimos, operator bog'lanishini kuting.</i>",
            parse_mode="HTML"
        )
    else:
        await message.answer(
            "Siz hozirda navbatda emassiz. Yangi murojaat boshlash uchun bo'limni tanlang:",
            reply_markup=get_customer_main_menu_keyboard()
        )


@router.message(F.text == "❌ Navbatdan chiqish")
async def cancel_queue(message: Message):
    active_sess = await db.get_active_session_by_customer(message.from_user.id)
    if active_sess:
        await message.answer(
            f"⚠️ Siz hozirda operator <b>{active_sess['operator_name']}</b> bilan jonli muloqotdasiz.\n\n"
            "Suhbatni yakunlash uchun pastdagi <b>«❌ Suhbatni yakunlash»</b> tugmasini bosing:",
            reply_markup=get_customer_active_keyboard(),
            parse_mode="HTML"
        )
        return

    pos = await db.get_queue_position(message.from_user.id)
    if pos is not None:
        await db.close_session_by_customer(message.from_user.id)
        async with aiosqlite.connect(config.DB_PATH) as conn:
            await conn.execute(
                "UPDATE queue SET status = 'closed' WHERE customer_id = ? AND status = 'waiting'",
                (message.from_user.id,)
            )
            await conn.commit()

        await message.answer(
            "Siz navbatdan chiqdingiz. Kerakli bo'limni tanlang:",
            reply_markup=get_customer_main_menu_keyboard()
        )
    else:
        await message.answer(
            "Siz hozirda navbatda emassiz.",
            reply_markup=get_customer_main_menu_keyboard()
        )


@router.message(F.text == "❌ Suhbatni yakunlash")
async def customer_end_chat(message: Message, bot: Bot):
    session = await db.close_session_by_customer(message.from_user.id)
    if not session:
        await message.answer(
            "Hozir faol suhbat mavjud emas. Yangi murojaat uchun bo'limni tanlang:",
            reply_markup=get_customer_main_menu_keyboard()
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

    # Operator chatidagi xabarlarni tozalash
    from handlers.common import clean_up_operator_session_messages
    await clean_up_operator_session_messages(bot, session["id"], operator_id)

    # Operatorga xabar
    try:
        await bot.send_message(
            chat_id=operator_id,
            text=(
                f"ℹ️ <b>Mijoz #{ticket_id} suhbatni yakunladi.</b>\n\n"
                "🧹 <i>Suhbat xabarlari chatdan tozalandi.</i>\n"
                "📜 <i>Yozishmalarni istalgan payt <b>«📋 Mening suhbatlarim»</b> bo'limida ko'rishingiz mumkin.</i>"
            ),
            reply_markup=get_operator_idle_keyboard(is_available=True, is_admin=(operator_id in config.ADMIN_IDS)),
            parse_mode="HTML"
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

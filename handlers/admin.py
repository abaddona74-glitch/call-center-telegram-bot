from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
import config
import database as db
from keyboards import (
    get_admin_main_keyboard, 
    get_admin_refresh_inline,
    get_admin_operators_kick_keyboard
)

router = Router()


def is_admin(user_id: int) -> bool:
    """Foydalanuvchi admin ekanligini tekshirish"""
    return user_id in config.ADMIN_IDS


# ================= ADMIN ASOSIY MENYUSI =================

@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ <b>Kechirasiz, sizda admin huquqi yo'q!</b>", parse_mode="HTML")
        return

    await message.answer(
        f"👑 <b>Call Center Boshqaruv Paneliga xush kelibsiz!</b>\n\n"
        f"Korxona: <b>«{config.COMPANY_NAME}»</b>\n"
        f"Kerakli bo'limni tanlang:",
        reply_markup=get_admin_main_keyboard(),
        parse_mode="HTML"
    )


# ================= 1. JONLI MONITORING (DASHBOARD) =================

async def build_dashboard_text() -> str:
    data = await db.get_live_dashboard()
    rating_str = f"{data['avg_rating']} ⭐" if data['avg_rating'] else "Mavjud emas"

    text = (
        "📊 <b>JONLI MONITORING (REAL-TIME)</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⏳ <b>Navbatda kutayotganlar:</b> {data['waiting_count']} ta mijoz\n"
        f"📞 <b>Hozir muloqotda:</b> {data['active_dialogs_count']} ta juftlik\n\n"
        "👨‍💼 <b>Operatorlar holati:</b>\n"
        f"  🟢 Onlayn (Bo'sh): {data['available_ops']} ta\n"
        f"  🟡 Band (Muloqotda): {data['busy_ops']} ta\n"
        f"  🔴 Oflayn (Tanaffus): {data['offline_ops']} ta\n\n"
        "📈 <b>Bugungi natijalar:</b>\n"
        f"  ✅ Yakunlangan murojaatlar: {data['today_closed']} ta\n"
        f"  ⭐ O'rtacha xizmat bahosi: {rating_str}\n"
        "━━━━━━━━━━━━━━━━━━━━━━"
    )
    return text


@router.message(F.text == "📊 Jonli monitoring (Live)")
async def admin_live_monitoring(message: Message):
    if not is_admin(message.from_user.id):
        return

    text = await build_dashboard_text()
    await message.answer(
        text,
        reply_markup=get_admin_refresh_inline("live"),
        parse_mode="HTML"
    )


# ================= 2. FAOL MULOQOTLAR (KIM KIM BILAN) =================

async def build_active_dialogs_text() -> str:
    dialogs = await db.get_active_dialogs_list()
    if not dialogs:
        return "📞 <b>Ayni damda hech qanday faol muloqot mavjud emas.</b>"

    text = f"📞 <b>Hozirda faol muloqotlar ({len(dialogs)} ta):</b>\n━━━━━━━━━━━━━━━━━━━━━━\n"
    for i, d in enumerate(dialogs, 1):
        started = d["started_at"].split()[1] if " " in d["started_at"] else d["started_at"]
        text += (
            f"<b>{i}. Ticket #{d['ticket_id']}</b>\n"
            f"  👨‍💼 Operator: <b>{d['operator_name']}</b>\n"
            f"  👤 Mijoz: <b>{d['customer_name']}</b>\n"
            f"  ⏱ Boshlangan vaqti: {started}\n"
            "──────────────────────\n"
        )
    return text


@router.message(F.text == "📞 Faol muloqotlar")
async def admin_active_dialogs(message: Message):
    if not is_admin(message.from_user.id):
        return

    text = await build_active_dialogs_text()
    await message.answer(
        text,
        reply_markup=get_admin_refresh_inline("dialogs"),
        parse_mode="HTML"
    )


# ================= 3. NAVBATDAGILAR RO'YXATI =================

async def build_queue_list_text() -> str:
    customers = await db.get_waiting_customers_list()
    if not customers:
        return "👥 <b>Hozirda navbat bo'sh! Hech kim kutmayapti.</b>"

    text = f"👥 <b>Navbatda kutayotgan mijozlar ({len(customers)} ta):</b>\n━━━━━━━━━━━━━━━━━━━━━━\n"
    for i, c in enumerate(customers, 1):
        msg_preview = f"<i>«{c['first_message'][:35]}...»</i>" if c.get("first_message") else "<i>Xabarsiz</i>"
        created = c["created_at"].split()[1] if " " in c["created_at"] else c["created_at"]
        text += (
            f"<b>#{i} (Ticket #{c['id']})</b>\n"
            f"  👤 Mijoz: <b>{c['customer_name']}</b>\n"
            f"  💬 Dastlabki xabar: {msg_preview}\n"
            f"  🕒 Kirgan vaqti: {created}\n"
            "──────────────────────\n"
        )
    return text


@router.message(F.text == "👥 Navbatdagilar ro'yxati")
async def admin_queue_list(message: Message):
    if not is_admin(message.from_user.id):
        return

    text = await build_queue_list_text()
    await message.answer(
        text,
        reply_markup=get_admin_refresh_inline("queue"),
        parse_mode="HTML"
    )


# ================= 4. OPERATORLAR HOLATI VA NATIJALARI =================

async def build_operators_text() -> str:
    ops = await db.get_operators_performance()
    if not ops:
        return "👨‍💼 <b>Hozircha tizimda birorta ham operator ro'yxatdan o'tmagan.</b>"

    status_icons = {
        "available": "🟢 Onlayn",
        "busy": "🟡 Band",
        "offline": "🔴 Oflayn"
    }

    text = f"👨‍💼 <b>Operatorlar faoliyati ({len(ops)} ta):</b>\n━━━━━━━━━━━━━━━━━━━━━━\n"
    for i, op in enumerate(ops, 1):
        status_text = status_icons.get(op["status"], op["status"])
        avg_rate = f"{round(op['avg_rating'], 1)} ⭐" if op["avg_rating"] else "Yo'q"
        code_badge = f" [#{op['operator_code']}]" if op.get("operator_code") else ""
        text += (
            f"<b>{i}. {op['full_name']}{code_badge}</b> ({status_text})\n"
            f"  🆔 Telegram ID: <code>{op['telegram_id']}</code>\n"
            f"  👥 Xizmat ko'rsatgan: <b>{op['total_served']}</b> ta mijoz\n"
            f"  ⭐ O'rtacha reytingi: <b>{avg_rate}</b>\n"
            "──────────────────────\n"
        )
    return text


@router.message(F.text.in_(["👨‍💼 Operatorlar holati", "❌ Operatorni chiqarish"]))
async def admin_operators_list(message: Message):
    if not is_admin(message.from_user.id):
        return

    text = await build_operators_text()
    ops = await db.get_operators_performance()
    kb = get_admin_operators_kick_keyboard(ops) if ops else get_admin_refresh_inline("operators")
    await message.answer(
        text,
        reply_markup=kb,
        parse_mode="HTML"
    )


# ================= 5. OPERATOR TAKLIF QILISH (INVITE LINK) =================

@router.message(F.text.startswith("➕ Operator taklif qilish"))
async def admin_invite_operator(message: Message, bot: Bot):
    if not is_admin(message.from_user.id):
        return

    bot_info = await bot.get_me()
    bot_username = bot_info.username
    invite_link = f"https://t.me/{bot_username}?start=op"

    share_text = (
        f"👋 Assalomu alaykum!\n"
        f"Siz «{config.COMPANY_NAME}» call center operatori sifatida taklif qilindingiz.\n\n"
        f"Tizimga ulanish havolasi:\n{invite_link}\n\n"
        f"Ulanish paroli: {config.OPERATOR_SECRET_KEY}"
    )
    import urllib.parse
    share_url = f"https://t.me/share/url?url={urllib.parse.quote(invite_link)}&text={urllib.parse.quote(share_text)}"

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="↗️ Xodimga yuborish (Ulashish)", url=share_url)
            ]
        ]
    )

    text = (
        "➕ <b>YANGI OPERATORNI TAKLIF QILISH</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "Yangi operator uchun maxsus havola tayyor!\n\n"
        f"🔗 <b>Taklif havolasi:</b>\n<code>{invite_link}</code>\n\n"
        f"🔑 <b>Korxona paroli:</b> <code>{config.OPERATOR_SECRET_KEY}</code>\n\n"
        "────────(Xodimga yuborish uchun matn)────────\n"
        f"<code>{share_text}</code>\n"
        "─────────────────────────────────────────────\n\n"
        "<i>💡 Xodim ushbu havolani bosganda bot avtomatik tarzda uning parolini, ismini va operator ID raqamini so'rab tizimga ulaydi.</i>"
    )

    await message.answer(text, reply_markup=kb, parse_mode="HTML")


# ================= 6. OPERATORNI CHIQARISH (KICK CONFIRMATION) =================

@router.callback_query(F.data.startswith("admin_ask_kick:"))
async def cb_admin_ask_kick(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo'q!", show_alert=True)
        return

    op_id = int(callback.data.split(":")[1])
    op = await db.get_operator(op_id)
    if not op:
        await callback.answer("Ushbu operator topilmadi yoki allaqachon chiqarilgan.", show_alert=True)
        return

    code_badge = f" [#{op['operator_code']}]" if op.get("operator_code") else ""
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🗑 Ha, tizimdan chiqarish", callback_data=f"admin_confirm_kick:{op_id}")
            ],
            [
                InlineKeyboardButton(text="⬅️ Bekor qilish", callback_data="admin_cancel_kick")
            ]
        ]
    )
    await callback.message.edit_text(
        f"⚠️ <b>Haqiqatan ham operatorni chiqarmoqchimisiz?</b>\n\n"
        f"👤 <b>Operator:</b> {op['full_name']}{code_badge}\n"
        f"🆔 <b>Telegram ID:</b> <code>{op_id}</code>\n\n"
        "<i>Agar chiqarsangiz, uning barcha faol suhbatlari yopiladi va u oddiy foydalanuvchiga aylanadi.</i>",
        reply_markup=kb,
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("admin_confirm_kick:"))
async def cb_admin_confirm_kick(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo'q!", show_alert=True)
        return

    op_id = int(callback.data.split(":")[1])
    op = await db.get_operator(op_id)
    op_name = op["full_name"] if op else "Operator"

    # Bazadan o'chirish
    await db.remove_operator(op_id)

    # Operatorning o'ziga bildirishnoma yuborish va klaviaturasini tozalash
    try:
        from aiogram.types import ReplyKeyboardRemove
        await bot.send_message(
            chat_id=op_id,
            text=f"⚠️ <b>Hurmatli {op_name}!</b>\n"
                 f"Siz «{config.COMPANY_NAME}» call center operatorlari safidan admin tomonidan chiqarildingiz.",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode="HTML"
        )
    except Exception:
        pass

    await callback.answer(f"✅ {op_name} tizimdan chiqarildi!", show_alert=True)

    # Yangilangan ro'yxatni ko'rsatish
    text = await build_operators_text()
    ops = await db.get_operators_performance()
    kb = get_admin_operators_kick_keyboard(ops) if ops else get_admin_refresh_inline("operators")
    await callback.message.edit_text(
        f"✅ <b>{op_name} muvaffaqiyatli chiqarildi.</b>\n\n" + text,
        reply_markup=kb,
        parse_mode="HTML"
    )


@router.callback_query(F.data == "admin_cancel_kick")
async def cb_admin_cancel_kick(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return

    text = await build_operators_text()
    ops = await db.get_operators_performance()
    kb = get_admin_operators_kick_keyboard(ops) if ops else get_admin_refresh_inline("operators")
    await callback.message.edit_text(
        text,
        reply_markup=kb,
        parse_mode="HTML"
    )


# ================= INLINE YANGILASH (REFRESH CALLBACK) =================

@router.callback_query(F.data.startswith("admin_refresh:"))
async def cb_admin_refresh(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo'q!", show_alert=True)
        return

    action = callback.data.split(":")[1]
    text = ""
    kb = get_admin_refresh_inline(action)

    if action == "live":
        text = await build_dashboard_text()
    elif action == "dialogs":
        text = await build_active_dialogs_text()
    elif action == "queue":
        text = await build_queue_list_text()
    elif action == "operators":
        text = await build_operators_text()
        ops = await db.get_operators_performance()
        if ops:
            kb = get_admin_operators_kick_keyboard(ops)

    if text:
        try:
            await callback.message.edit_text(
                text,
                reply_markup=kb,
                parse_mode="HTML"
            )
            await callback.answer("Yangilandi 🔄")
        except Exception:
            await callback.answer("Ma'lumotlar o'zgarmagan.")


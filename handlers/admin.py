from typing import Tuple, Optional, Dict, Any
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
import config
import database as db
from keyboards import (
    get_admin_main_keyboard, 
    get_admin_refresh_inline,
    get_admin_active_dialogs_keyboard,
    get_admin_operators_manage_keyboard,
    get_admin_operator_card_keyboard,
    get_admin_operators_kick_keyboard,
    get_history_sessions_keyboard,
    get_history_back_keyboard,
    get_admin_history_operators_keyboard
)

router = Router()

HISTORY_PER_PAGE = 10


class AdminEditOperatorState(StatesGroup):
    waiting_for_name = State()
    waiting_for_code = State()


class AdminHistorySearchState(StatesGroup):
    waiting_for_query = State()


def is_admin(user_id: int) -> bool:
    """Foydalanuvchi admin ekanligini tekshirish"""
    return user_id in config.ADMIN_IDS


# ================= ADMIN ASOSIY MENYUSI =================

@router.message(Command("admin"))
@router.message(F.text == "👑 Admin paneliga qaytish")
async def cmd_admin(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ <b>Kechirasiz, sizda admin huquqi yo'q!</b>", parse_mode="HTML")
        return

    await message.answer(
        f"👑 <b>Call Center Boshqaruv Paneliga xush kelibsiz!</b>\n\n"
        f"Korxona: <b>«{config.COMPANY_NAME}»</b>\n"
        "Kerakli bo'limni tanlang:\n"
        "<i>(Operator rejimiga o'tish uchun: /operator)</i>",
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
        cust_id = d.get("customer_id")
        cust_name = d.get("customer_name") or "Mijoz"
        cust_user = d.get("customer_username") or ""
        user_link = f'<a href="tg://user?id={cust_id}">{cust_name}</a>' if cust_id else cust_name
        user_badge = f" (@{cust_user})" if cust_user else ""
        text += (
            f"<b>{i}. Ticket #{d['ticket_id']}</b>\n"
            f"  👨‍💼 Operator: <b>{d['operator_name']}</b>\n"
            f"  👤 Mijoz: <b>{user_link}</b>{user_badge} [<code>{cust_id}</code>]\n"
            f"  ⏱ Boshlangan vaqti: {started}\n"
            "──────────────────────\n"
        )
    return text


@router.message(F.text == "📞 Faol muloqotlar")
async def admin_active_dialogs(message: Message):
    if not is_admin(message.from_user.id):
        return

    text = await build_active_dialogs_text()
    dialogs = await db.get_active_dialogs_list()
    kb = get_admin_active_dialogs_keyboard(dialogs) if dialogs else get_admin_refresh_inline("dialogs")
    await message.answer(
        text,
        reply_markup=kb,
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("admin_force_close:"))
async def cb_admin_force_close(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo'q!", show_alert=True)
        return

    ticket_id = int(callback.data.split(":")[1])
    session = await db.close_session_by_ticket_id(ticket_id)
    if not session:
        await callback.answer("Bu muloqot allaqachon yakunlangan!", show_alert=True)
        return

    op_id = session["operator_id"]
    cust_id = session["customer_id"]
    sess_id = session["id"]

    try:
        from handlers.common import clean_up_operator_session_messages
        await clean_up_operator_session_messages(bot, sess_id, op_id)
        from keyboards import get_operator_idle_keyboard
        await bot.send_message(
            chat_id=op_id,
            text=(
                f"🛑 <b>Mijoz #{ticket_id} bilan suhbat admin tomonidan yakunlandi.</b>\n\n"
                "🧹 <i>Suhbat xabarlari chatdan tozalandi.</i>\n"
                "📜 <i>Yozishmalar tarixini <b>«📋 Mening suhbatlarim»</b> bo'limida ko'rishingiz mumkin.</i>"
            ),
            reply_markup=get_operator_idle_keyboard(is_available=True, is_admin=(op_id in config.ADMIN_IDS)),
            parse_mode="HTML"
        )
    except Exception:
        pass

    try:
        from keyboards import get_customer_rating_keyboard
        await bot.send_message(
            chat_id=cust_id,
            text=f"Suhbat yakunlandi.\n\n{config.RATING_PROMPT}",
            reply_markup=get_customer_rating_keyboard(ticket_id),
            parse_mode="HTML"
        )
    except Exception:
        pass

    await callback.answer(f"✅ Ticket #{ticket_id} suhbati muvaffaqiyatli yakunlandi!", show_alert=True)

    text = await build_active_dialogs_text()
    dialogs = await db.get_active_dialogs_list()
    kb = get_admin_active_dialogs_keyboard(dialogs) if dialogs else get_admin_refresh_inline("dialogs")
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        pass



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


async def build_single_operator_card_text(op_id: int) -> Tuple[str, Optional[Dict[str, Any]]]:
    """Bitta operator haqida to'liq ma'lumot matni"""
    op = await db.get_operator(op_id)
    if not op:
        return "⚠️ Operator topilmadi.", None

    ops = await db.get_operators_performance()
    perf = next((x for x in ops if x["telegram_id"] == op_id), {})

    status_icons = {
        "available": "🟢 Onlayn",
        "busy": "🟡 Band",
        "offline": "🔴 Oflayn"
    }
    status_text = status_icons.get(op["status"], op["status"])
    code_badge = f"#{op.get('operator_code')}" if op.get("operator_code") else "Belgilanmagan"
    avg_rate = f"{round(perf.get('avg_rating', 0), 1)} ⭐" if perf.get('avg_rating') else "Baholanmagan"
    total_served = perf.get("total_served", 0)

    text = (
        "👨‍💼 <b>Operator ma'lumotlari:</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>Ism:</b> {op['full_name']}\n"
        f"🔢 <b>Operator kodi:</b> {code_badge}\n"
        f"🆔 <b>Telegram ID:</b> <code>{op['telegram_id']}</code>\n"
        f"📌 <b>Holat:</b> {status_text}\n"
        f"👥 <b>Xizmat ko'rsatgan:</b> {total_served} ta mijoz\n"
        f"⭐ <b>O'rtacha bahosi:</b> {avg_rate}\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "<i>Quyidagi tugmalar orqali operator ma'lumotlarini o'zgartirishingiz mumkin:</i>"
    )
    return text, op


@router.message(F.text == "👨‍💼 Operatorlar holati")
async def admin_operators_list(message: Message):
    if not is_admin(message.from_user.id):
        return

    text = await build_operators_text()
    text += "\n<i>💡 Operatorni tahrirlash yoki chiqarish uchun pastdagi ro'yxatdan tanlang:</i>"
    ops = await db.get_operators_performance()
    kb = get_admin_operators_manage_keyboard(ops) if ops else get_admin_refresh_inline("operators")
    await message.answer(
        text,
        reply_markup=kb,
        parse_mode="HTML"
    )


@router.message(F.text == "❌ Operatorni chiqarish")
async def admin_operators_kick_list(message: Message):
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
    kb = get_admin_operators_manage_keyboard(ops) if ops else get_admin_refresh_inline("operators")
    await callback.message.edit_text(
        text,
        reply_markup=kb,
        parse_mode="HTML"
    )


# ================= OPERATORNI BOSHQARISH VA TAHRIRLASH =================

@router.callback_query(F.data.startswith("admin_manage_op:"))
async def cb_admin_manage_op(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo'q!", show_alert=True)
        return

    op_id = int(callback.data.split(":")[1])
    text, op = await build_single_operator_card_text(op_id)
    if not op:
        await callback.answer("Operator topilmadi!", show_alert=True)
        return

    await callback.message.edit_text(
        text,
        reply_markup=get_admin_operator_card_keyboard(op_id),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_edit_name:"))
async def cb_admin_edit_name(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo'q!", show_alert=True)
        return

    op_id = int(callback.data.split(":")[1])
    op = await db.get_operator(op_id)
    if not op:
        await callback.answer("Operator topilmadi!", show_alert=True)
        return

    await state.set_state(AdminEditOperatorState.waiting_for_name)
    await state.update_data(edit_op_id=op_id)
    await callback.message.answer(
        f"✏️ <b>Operator ({op['full_name']}) uchun yangi ism kiriting:</b>\n\n"
        "<i>(Bekor qilish uchun: /cancel)</i>",
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_edit_code:"))
async def cb_admin_edit_code(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo'q!", show_alert=True)
        return

    op_id = int(callback.data.split(":")[1])
    op = await db.get_operator(op_id)
    if not op:
        await callback.answer("Operator topilmadi!", show_alert=True)
        return

    await state.set_state(AdminEditOperatorState.waiting_for_code)
    await state.update_data(edit_op_id=op_id)
    await callback.message.answer(
        f"🔢 <b>Operator ({op['full_name']}) uchun yangi operator kodini kiriting:</b>\n\n"
        "<i>Masalan: 101 yoki 105 (Bekor qilish uchun: /cancel)</i>",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(AdminEditOperatorState.waiting_for_name)
async def process_admin_edit_name(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    new_name = (message.text or "").strip()
    if new_name == "/cancel":
        await state.clear()
        await message.answer("❌ Tahrirlash bekor qilindi.")
        return

    if len(new_name) < 2:
        await message.answer("Iltimos, ismni to'liqroq kiriting (kamida 2 ta harf):")
        return

    data = await state.get_data()
    op_id = data.get("edit_op_id")
    await db.update_operator_name(op_id, new_name)
    await state.clear()

    text, _ = await build_single_operator_card_text(op_id)
    await message.answer(
        f"✅ Operator ismi muvaffaqiyatli <b>{new_name}</b> ga o'zgartirildi!\n\n" + text,
        reply_markup=get_admin_operator_card_keyboard(op_id),
        parse_mode="HTML"
    )


@router.message(AdminEditOperatorState.waiting_for_code)
async def process_admin_edit_code(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    new_code = (message.text or "").strip().lstrip("#")
    if new_code == "/cancel":
        await state.clear()
        await message.answer("❌ Tahrirlash bekor qilindi.")
        return

    if not new_code:
        await message.answer("Iltimos, to'g'ri kod kiriting:")
        return

    data = await state.get_data()
    op_id = data.get("edit_op_id")
    await db.update_operator_code(op_id, new_code)
    await state.clear()

    text, _ = await build_single_operator_card_text(op_id)
    await message.answer(
        f"✅ Operator kodi muvaffaqiyatli <b>#{new_code}</b> ga o'zgartirildi!\n\n" + text,
        reply_markup=get_admin_operator_card_keyboard(op_id),
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
        dialogs = await db.get_active_dialogs_list()
        if dialogs:
            kb = get_admin_active_dialogs_keyboard(dialogs)
    elif action == "queue":
        text = await build_queue_list_text()
    elif action == "operators":
        text = await build_operators_text()
        text += "\n<i>💡 Operatorni tahrirlash yoki chiqarish uchun pastdagi ro'yxatdan tanlang:</i>"
        ops = await db.get_operators_performance()
        if ops:
            kb = get_admin_operators_manage_keyboard(ops)

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


# ================= 7. SUHBATLAR TARIXI (CHAT HISTORY) =================

async def build_history_list_text(
    sessions: list, total: int, page: int, operator_info: Optional[Dict[str, Any]] = None
) -> str:
    op_header = ""
    if operator_info:
        code_str = f" [#{operator_info['operator_code']}]" if operator_info.get("operator_code") else ""
        op_header = f"👨‍💼 <b>Operator:</b> {operator_info['full_name']}{code_str}\n"

    if not sessions:
        if operator_info:
            return (
                f"📜 <b>Suhbatlar tarixi</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                f"{op_header}"
                "<i>Ushbu operator tomonidan hozircha yakunlangan suhbatlar mavjud emas.</i>"
            )
        return "📜 <b>Hozircha hech qanday yakunlangan suhbat mavjud emas.</b>"

    start_num = page * HISTORY_PER_PAGE + 1
    title = f"📜 <b>Suhbatlar tarixi ({total} ta)</b>\n"
    text = (
        f"{title}"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{op_header}"
        "<i>Suhbat tarixini ko'rish uchun quyidagi tugmalardan birini tanlang:</i>\n\n"
    )
    for i, s in enumerate(sessions, start_num):
        rating_str = f"{s['rating']} ⭐" if s.get("rating") else "Baholanmagan"
        op_name = s.get("operator_name", "Noma'lum")
        op_code = f" [#{s['operator_code']}]" if s.get("operator_code") else ""
        date_str = s["closed_at"].split()[0] if s.get("closed_at") and " " in s["closed_at"] else (s.get("closed_at") or "")
        reason_info = f"\n  💬 <b>Fikr:</b> <i>{s['feedback_reason']}</i>" if s.get("feedback_reason") else ""
        text += (
            f"<b>{i}. Ticket #{s['ticket_id']}</b>\n"
            f"  👤 Mijoz: {s['customer_name']}\n"
            f"  👨‍💼 Operator: {op_name}{op_code}\n"
            f"  📅 Sana: {date_str} | ⭐ {rating_str}{reason_info}\n"
            "──────────────────────\n"
        )
    return text


@router.message(F.text == "📜 Suhbatlar tarixi")
async def admin_chat_history(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.clear()

    sessions, total = await db.get_closed_sessions_list(limit=HISTORY_PER_PAGE, offset=0, operator_id=None)
    text = await build_history_list_text(sessions, total, 0)
    kb = get_history_sessions_keyboard(sessions, 0, total, HISTORY_PER_PAGE, "admin", operator_id=0)
    await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("admin_history_page:"))
async def cb_admin_history_page(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo'q!", show_alert=True)
        return

    parts = callback.data.split(":")
    page = int(parts[1]) if len(parts) > 1 else 0
    operator_id = int(parts[2]) if len(parts) > 2 else 0
    offset = page * HISTORY_PER_PAGE

    operator_info = None
    if operator_id > 0:
        operator_info = await db.get_operator(operator_id)
        sessions, total = await db.get_closed_sessions_list(limit=HISTORY_PER_PAGE, offset=offset, operator_id=operator_id)
    else:
        sessions, total = await db.get_closed_sessions_list(limit=HISTORY_PER_PAGE, offset=offset, operator_id=None)

    text = await build_history_list_text(sessions, total, page, operator_info=operator_info)
    kb = get_history_sessions_keyboard(sessions, page, total, HISTORY_PER_PAGE, "admin", operator_id=operator_id)

    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        await callback.answer()
    except Exception:
        await callback.answer("Ma'lumotlar o'zgarmagan.")


@router.callback_query(F.data == "admin_history_ops")
async def cb_admin_history_ops(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo'q!", show_alert=True)
        return

    ops = await db.get_operators_history_stats()
    if not ops:
        await callback.answer("Operatorlar mavjud emas!", show_alert=True)
        return

    text = (
        "👨‍💼 <b>Suhbatlar tarixini ko'rish uchun operatorni tanlang:</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "<i>Har bir operator yonida u yakunlagan jami suhbatlar soni ko'rsatilgan:</i>"
    )
    kb = get_admin_history_operators_keyboard(ops)
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        await callback.answer()
    except Exception:
        await callback.answer()


@router.callback_query(F.data == "admin_history_search")
async def cb_admin_history_search(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo'q!", show_alert=True)
        return

    await state.set_state(AdminHistorySearchState.waiting_for_query)
    await callback.message.answer(
        "🔍 Qidirmoqchi bo'lgan operatorning <b>ismi</b> yoki <b>ID raqami</b>ni kiriting:\n"
        "<i>(Masalan: Mahmudbek yoki 101)</i>",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(AdminHistorySearchState.waiting_for_query)
async def process_admin_history_search(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    query = (message.text or "").strip()
    await state.clear()

    if not query:
        await message.answer("Qidiruv bekor qilindi.")
        return

    results = await db.search_operators(query)
    if not results:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔍 Qayta qidirish", callback_data="admin_history_search")],
            [InlineKeyboardButton(text="👥 Barcha operatorlar", callback_data="admin_history_ops")],
            [InlineKeyboardButton(text="📜 Barcha suhbatlar", callback_data="admin_history_page:0:0")]
        ])
        await message.answer(
            f"🔍 «<b>{query}</b>» bo'yicha hech qanday operator topilmadi.",
            reply_markup=kb,
            parse_mode="HTML"
        )
        return

    text = (
        f"🔍 «<b>{query}</b>» bo'yicha topilgan operatorlar:\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "<i>Suhbatlarini ko'rish uchun kerakli operatorni tanlang:</i>"
    )
    kb = get_admin_history_operators_keyboard(results)
    await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("admin_history_view:"))
async def cb_admin_history_view(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo'q!", show_alert=True)
        return

    parts = callback.data.split(":")
    session_id = int(parts[1])
    page = int(parts[2]) if len(parts) > 2 else 0
    operator_id = int(parts[3]) if len(parts) > 3 else 0

    session = await db.get_session_by_id(session_id)
    if not session:
        await callback.answer("Suhbat topilmadi!", show_alert=True)
        return

    messages = await db.get_session_messages(session_id)

    # Suhbat ma'lumotlari
    rating_str = f"{session['rating']} ⭐" if session.get("rating") else "Baholanmagan"
    if session.get("feedback_reason"):
        rating_str += f" (E'tiroz: <i>{session['feedback_reason']}</i>)"
    op_name = session.get("operator_name") or "Noma'lum"
    op_code = f" [#{session['operator_code']}]" if session.get("operator_code") else ""
    started = session.get("started_at", "")
    closed = session.get("closed_at", "")

    cust_id = session.get("customer_id")
    cust_name = session.get("customer_name") or "Mijoz"
    cust_user = session.get("customer_username") or ""
    user_link = f'<a href="tg://user?id={cust_id}">{cust_name}</a>' if cust_id else cust_name
    username_info = f" (@{cust_user})" if cust_user else ""
    id_info = f" [<code>{cust_id}</code>]" if cust_id else ""

    text = (
        f"📜 <b>Suhbat tarixi: Ticket #{session['ticket_id']}</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>Mijoz:</b> {user_link}{username_info}{id_info}\n"
        f"👨‍💼 <b>Operator:</b> {op_name}{op_code}\n"
        f"📅 <b>Sana:</b> {started} — {closed}\n"
        f"⭐ <b>Baho:</b> {rating_str}\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
    )

    if not messages:
        text += "<i>Bu suhbatda saqlangan xabarlar mavjud emas.</i>\n"
        text += "<i>(Tarix faqat shu funksiya qo'shilgandan keyingi suhbatlarda ishlaydi)</i>"
    else:
        for msg in messages:
            time_str = msg["created_at"].split()[1][:5] if " " in msg["created_at"] else msg["created_at"]
            if msg["sender_type"] == "customer":
                sender_icon = "👤 Mijoz"
            else:
                sender_icon = "👨‍💼 Operator"
            content = msg["text_content"] or ""
            # Xabar matnini qisqartirish (juda uzun bo'lsa)
            if len(content) > 200:
                content = content[:200] + "..."
            text += f"<b>{sender_icon}</b> [{time_str}]: {content}\n"

    text += "\n━━━━━━━━━━━━━━━━━━━━━━"

    # Matn uzunligini tekshirish (Telegram limiti 4096)
    if len(text) > 4000:
        text = text[:3950] + "\n\n<i>... (xabarlar juda ko'p, qisqartirildi)</i>"

    media_files = await db.get_session_media_messages(session_id)
    kb = get_history_back_keyboard(page, "admin", session_id=session_id, media_count=len(media_files), operator_id=operator_id)
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        await callback.answer()
    except Exception:
        await callback.answer("Xatolik yuz berdi.")


@router.callback_query(F.data.startswith("admin_history_media:"))
async def cb_admin_history_media(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo'q!", show_alert=True)
        return

    session_id = int(callback.data.split(":")[1])
    media_files = await db.get_session_media_messages(session_id)
    if not media_files:
        await callback.answer("Bu suhbatda yuklangan media fayllar yo'q.", show_alert=True)
        return

    await callback.answer(f"{len(media_files)} ta fayl yuborilmoqda...")

    for item in media_files:
        c_type = item["content_type"]
        f_id = item["file_id"]
        sender = "👤 Mijoz" if item["sender_type"] == "customer" else "👨‍💼 Operator"
        time_str = item["created_at"].split()[1][:5] if " " in item["created_at"] else ""
        cap = f"{sender} [{time_str}]"

        try:
            if c_type == "audio":
                await bot.send_audio(chat_id=callback.from_user.id, audio=f_id, caption=cap)
            elif c_type == "voice":
                await bot.send_voice(chat_id=callback.from_user.id, voice=f_id, caption=cap)
            elif c_type == "photo":
                await bot.send_photo(chat_id=callback.from_user.id, photo=f_id, caption=cap)
            elif c_type == "video":
                await bot.send_video(chat_id=callback.from_user.id, video=f_id, caption=cap)
            elif c_type == "video_note":
                await bot.send_video_note(chat_id=callback.from_user.id, video_note=f_id)
            elif c_type == "document":
                await bot.send_document(chat_id=callback.from_user.id, document=f_id, caption=cap)
            elif c_type == "sticker":
                await bot.send_sticker(chat_id=callback.from_user.id, sticker=f_id)
        except Exception:
            pass


@router.callback_query(F.data == "noop")
async def cb_noop(callback: CallbackQuery):
    await callback.answer()

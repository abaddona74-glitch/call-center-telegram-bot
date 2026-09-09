from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
import database as db
import config
from keyboards import (
    get_operator_idle_keyboard,
    get_operator_active_keyboard,
    get_customer_active_keyboard,
    get_customer_rating_keyboard,
    get_ticket_claimed_keyboard,
    get_history_sessions_keyboard,
    get_history_back_keyboard
)
from handlers.common import (
    update_ticket_notifications_as_claimed, 
    broadcast_new_ticket_to_operators,
    clean_up_operator_session_messages,
    format_topic_line
)

router = Router()

OP_HISTORY_PER_PAGE = 10


# ================= FSM HOLATLARI =================

class OperatorRegState(StatesGroup):
    waiting_for_password = State()
    waiting_for_name = State()
    waiting_for_code = State()


async def start_operator_registration_flow(message: Message, state: FSMContext):
    """Operator ro'yxatdan o'tish interaktiv suhbatini boshlash"""
    op = await db.get_operator(message.from_user.id)
    if op:
        code_str = f" [#{op['operator_code']}]" if op.get("operator_code") else ""
        await message.answer(
            f"ℹ️ Siz allaqachon operator sifatida ro'yxatdan o'tgansiz: <b>{op['full_name']}{code_str}</b>.\n"
            "Qaytadan ro'yxatdan o'tish uchun avval /unbind deb yozing.",
            reply_markup=get_operator_idle_keyboard(op["status"] != "offline"),
            parse_mode="HTML"
        )
        return

    await state.set_state(OperatorRegState.waiting_for_password)
    await message.answer(
        "👨‍💼 <b>«{company}» Operator Ro'yxatdan O'tish</b>\n\n"
        "1️⃣-qadam: Iltimos, korxona tomonidan berilgan <b>maxfiy parol</b>ni kiriting:\n\n"
        "<i>(Bekor qilish uchun: /cancel)</i>".format(company=config.COMPANY_NAME),
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="HTML"
    )


# ================= BEKOR QILISH (/cancel) =================

@router.message(Command("cancel"))
async def cmd_cancel_registration(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        await message.answer("Bekor qilinadigan faol jarayon yo'q.")
        return

    await state.clear()
    await message.answer(
        "❌ Ro'yxatdan o'tish bekor qilindi. Bosh menyuga qaytish uchun /start bosing.",
        reply_markup=ReplyKeyboardRemove()
    )


# ================= INTERAKTIV RO'YXATDAN O'TISH QADAMLARI =================

@router.message(OperatorRegState.waiting_for_password)
async def process_op_password(message: Message, state: FSMContext):
    pwd = (message.text or "").strip()
    if pwd != config.OPERATOR_SECRET_KEY:
        await message.answer(
            "⛔ <b>Maxfiy parol noto'g'ri!</b>\n\n"
            "Iltimos, to'g'ri parolni kiriting yoki bekor qilish uchun /cancel deb yozing:",
            parse_mode="HTML"
        )
        return

    await state.set_state(OperatorRegState.waiting_for_name)
    await message.answer(
        "✅ <b>Parol to'g'ri tasdiqlandi!</b>\n\n"
        "2️⃣-qadam: Endi <b>ism va familiyangizni</b> kiriting:\n"
        "<i>(Masalan: Mahmudbek yoki Mahmudbek Ergashev)</i>",
        parse_mode="HTML"
    )


@router.message(OperatorRegState.waiting_for_name)
async def process_op_name(message: Message, state: FSMContext):
    name = (message.text or "").strip()
    if not name or len(name) < 2:
        await message.answer("Iltimos, ismingizni to'liq kiriting:")
        return

    await state.update_data(name=name)
    await state.set_state(OperatorRegState.waiting_for_code)
    await message.answer(
        f"👤 Qabul qilindi: <b>{name}</b>\n\n"
        "3️⃣-qadam: Korxonangizdagi <b>Operator raqamingiz (ID / kodi)</b>ni kiriting:\n"
        "<i>(Masalan: 101, 102 yoki OP-05)</i>",
        parse_mode="HTML"
    )


@router.message(OperatorRegState.waiting_for_code)
async def process_op_code(message: Message, state: FSMContext, bot: Bot):
    code = (message.text or "").strip().replace("#", "")
    if not code:
        await message.answer("Iltimos, operator raqamingizni (ID) kiriting:")
        return

    data = await state.get_data()
    operator_name = data.get("name", "Operator")

    await state.clear()
    await db.register_or_update_operator(message.from_user.id, operator_name, code)

    is_user_admin = (message.from_user.id in config.ADMIN_IDS)
    await message.answer(
        f"🎉 <b>Tabriklaymiz, siz muvaffaqiyatli ro'yxatdan o'tdingiz!</b>\n\n"
        f"👤 <b>Operator:</b> {operator_name}\n"
        f"🔢 <b>Operator ID:</b> #{code}\n"
        f"🏢 <b>Korxona:</b> «{config.COMPANY_NAME}»\n"
        f"📌 <b>Holatingiz:</b> 🟢 Onlayn (Mijoz kutish)\n\n"
        "<i>Yangi mijozlar murojaat qilganda sizga darhol qo'ng'iroq/qabul qilish xabari yuboriladi.</i>",
        reply_markup=get_operator_idle_keyboard(is_available=True, is_admin=is_user_admin),
        parse_mode="HTML"
    )

    # Agar allaqachon navbatda kutayotgan mijoz bo'lsa, xabarnoma jo'natish
    next_ticket = await db.get_next_waiting_ticket()
    if next_ticket:
        await broadcast_new_ticket_to_operators(
            bot,
            next_ticket["id"],
            next_ticket["customer_name"],
            next_ticket.get("first_message", "")
        )


# ================= TEZKOR RO'YXATDAN O'TISH VA OPERATOR REJIMIGA O'TISH =================

@router.message(Command("operator", "op", "bind", "register"))
@router.message(F.text == "🎧 Operator rejimiga o'tish")
async def cmd_register_operator(message: Message, state: FSMContext, bot: Bot):
    """
    Operator rejimiga o'tish yoki ro'yxatdan o'tish:
    1. Admin bo'lsa -> to'g'ridan-to'g'ri Operator rejimiga o'tkaziladi (onlayn qilinadi).
    2. Allaqachon operator bo'lsa -> operator panelini chiqaradi.
    3. Yangi bo'lsa -> interaktiv ro'yxatdan o'tishni boshlaydi.
    Format: /operator [parol] [Ism] [ID]
    """
    user_id = message.from_user.id
    is_user_admin = (user_id in config.ADMIN_IDS)
    text = (message.text or "").strip()
    args = text.split(maxsplit=3)

    # Parametrlar berilmagan yoki tugma bosilgan holat
    if len(args) == 1 or text == "🎧 Operator rejimiga o'tish":
        if is_user_admin:
            # Adminni tekshiramiz va avtomatik operator sifatida saqlaymiz/yangilaymiz
            op = await db.get_operator(user_id)
            if not op:
                await db.register_or_update_operator(
                    user_id, 
                    message.from_user.full_name or "Admin", 
                    "001"
                )
                op = await db.get_operator(user_id)
            
            # Agar oflayn bo'lsa, avtomatik ravishda onlaynga o'tkazamiz
            if op["status"] == "offline":
                await db.set_operator_status(user_id, "available")
                op["status"] = "available"

            code_badge = f" [#{op['operator_code']}]" if op.get("operator_code") else ""
            active_sess = await db.get_active_session_by_operator(user_id)

            if active_sess:
                await message.answer(
                    f"🎧 <b>Siz operator rejimidasiz!</b>\n\n"
                    f"👤 Operator: <b>{op['full_name']}{code_badge}</b>\n"
                    f"💬 Hozirda faol muloqotdasiz (Ticket #{active_sess['ticket_id']}).",
                    reply_markup=get_operator_active_keyboard(),
                    parse_mode="HTML"
                )
            else:
                await message.answer(
                    f"🎧 <b>Operator rejimiga o'tdingiz!</b>\n\n"
                    f"👤 Operator: <b>{op['full_name']}{code_badge}</b>\n"
                    f"📌 Holat: <b>🟢 Onlayn (Mijoz kutish)</b>\n\n"
                    "Yangi murojaat kelishi bilan sizga <b>[📞 Qabul qilish]</b> tugmasi yuboriladi.\n\n"
                    "<i>(Admin paneliga qaytish uchun: <b>/admin</b> yoki pastdagi <b>«👑 Admin paneliga qaytish»</b> tugmasini bosing)</i>",
                    reply_markup=get_operator_idle_keyboard(is_available=True, is_admin=True),
                    parse_mode="HTML"
                )

                # Agar navbatda kutayotgan mijoz bo'lsa darhol operatorga jo'natish
                next_ticket = await db.get_next_waiting_ticket()
                if next_ticket:
                    await broadcast_new_ticket_to_operators(
                        bot,
                        next_ticket["id"],
                        next_ticket["customer_name"],
                        next_ticket.get("first_message", "")
                    )
            return

        # Oddiy foydalanuvchi tekshiruvi
        op = await db.get_operator(user_id)
        if op:
            code_str = f" [#{op['operator_code']}]" if op.get("operator_code") else ""
            is_avail = (op["status"] != "offline")
            active_sess = await db.get_active_session_by_operator(user_id)
            if active_sess:
                await message.answer(
                    f"🎧 <b>Siz hozirda muloqotdasiz!</b> (Ticket #{active_sess['ticket_id']})",
                    reply_markup=get_operator_active_keyboard(),
                    parse_mode="HTML"
                )
            else:
                await message.answer(
                    f"🎧 <b>Operator paneli</b>\n\n"
                    f"👤 Operator: <b>{op['full_name']}{code_str}</b>\n"
                    f"📌 Holat: <b>{'🟢 Onlayn' if is_avail else '🔴 Oflayn'}</b>",
                    reply_markup=get_operator_idle_keyboard(is_avail, is_admin=False),
                    parse_mode="HTML"
                )
            return

        # Ro'yxatdan o'tmagan bo'lsa -> interaktiv so'rovnoma
        await start_operator_registration_flow(message, state)
        return

    elif len(args) < 3:
        await message.answer(
            "❌ <b>Noto'g'ri format!</b>\n\n"
            "Interaktiv ro'yxatdan o'tish uchun shunchaki <code>/operator</code> deb yozing,\n"
            "yoki bir satrda: <code>/operator [parol] [Ismingiz] [OperatorID]</code>\n\n"
            "<i>Masalan:</i> <code>/operator {pwd} Mahmudbek 101</code>".format(pwd=config.OPERATOR_SECRET_KEY),
            parse_mode="HTML"
        )
        return

    secret_key = args[1]
    operator_name = args[2].strip()
    operator_code = args[3].strip().replace("#", "") if len(args) > 3 else ""

    if secret_key != config.OPERATOR_SECRET_KEY:
        await message.answer("⛔ <b>Maxfiy parol noto'g'ri!</b>", parse_mode="HTML")
        return

    await db.register_or_update_operator(message.from_user.id, operator_name, operator_code)
    code_badge = f" [#{operator_code}]" if operator_code else ""
    await message.answer(
        f"✅ <b>Tabriklaymiz, {operator_name}{code_badge}!</b>\n"
        f"Siz «{config.COMPANY_NAME}» call center operatori sifatida muvaffaqiyatli ro'yxatdan o'tdingiz.\n\n"
        f"Holatingiz: <b>🟢 Onlayn (Mijoz kutish)</b>\n"
        "Yangi mijozlar kelganda sizga xabar yuboriladi.",
        reply_markup=get_operator_idle_keyboard(is_available=True, is_admin=is_user_admin),
        parse_mode="HTML"
    )

    # Agar allaqachon navbatda kutayotgan mijoz bo'lsa, xabarnoma jo'natish
    next_ticket = await db.get_next_waiting_ticket()
    if next_ticket:
        await broadcast_new_ticket_to_operators(
            bot,
            next_ticket["id"],
            next_ticket["customer_name"],
            next_ticket.get("first_message", "")
        )


@router.message(Command("unbind", "unregister", "logout"))
async def cmd_unbind_operator(message: Message):
    """
    Operatorlikdan chiqish:
    /unbind yoki /logout
    """
    user_id = message.from_user.id
    op = await db.get_operator(user_id)
    if not op:
        await message.answer("Siz operator sifatida ro'yxatdan o'tmagansiz.")
        return

    from aiogram.types import ReplyKeyboardRemove
    await db.remove_operator(user_id)
    await message.answer(
        f"✅ <b>{op['full_name']}</b>, siz operatorlik tizimidan muvaffaqiyatli chiqarildingiz (unbind bo'ldingiz).\n\n"
        "Endi ushbu akkaunt oddiy foydalanuvchi hisoblanadi. Mijoz sifatida kirish uchun /start bosing.",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="HTML"
    )


# ================= HOLATNI BOSHQARISH (ONLAYN / OFLAYN) =================

@router.message(F.text == "🔴 Oflayn (Tanaffus)")
async def op_go_offline(message: Message):
    op = await db.get_operator(message.from_user.id)
    if not op:
        return

    active_sess = await db.get_active_session_by_operator(message.from_user.id)
    if active_sess:
        await message.answer(
            f"⚠️ Hozir mijoz bilan muloqotdasiz (Ticket #{active_sess['ticket_id']})!\n\n"
            "Suhbatni yakunlash uchun pastdagi <b>«🛑 Suhbatni yakunlash»</b> tugmasini bosing:",
            reply_markup=get_operator_active_keyboard(),
            parse_mode="HTML"
        )
        return

    is_user_admin = (message.from_user.id in config.ADMIN_IDS)
    await db.set_operator_status(message.from_user.id, "offline")
    await message.answer(
        "🔴 <b>Siz oflayn rejimdasiz (Tanaffus).</b>\n"
        "Sizga yangi mijozlar bildirishnomalari yuborilmaydi.",
        reply_markup=get_operator_idle_keyboard(is_available=False, is_admin=is_user_admin),
        parse_mode="HTML"
    )


@router.message(F.text == "🟢 Onlayn (Mijoz kutish)")
async def op_go_online(message: Message, bot: Bot):
    op = await db.get_operator(message.from_user.id)
    if not op:
        return

    active_sess = await db.get_active_session_by_operator(message.from_user.id)
    if active_sess:
        await message.answer(
            f"⚠️ Hozir mijoz bilan muloqotdasiz (Ticket #{active_sess['ticket_id']})!",
            reply_markup=get_operator_active_keyboard(),
            parse_mode="HTML"
        )
        return

    is_user_admin = (message.from_user.id in config.ADMIN_IDS)
    await db.set_operator_status(message.from_user.id, "available")
    await message.answer(
        "🟢 <b>Siz onlayn rejimdasiz!</b>\n"
        "Yangi murojaatlar kelishi bilan sizga bildirishnoma yuboriladi.",
        reply_markup=get_operator_idle_keyboard(is_available=True, is_admin=is_user_admin),
        parse_mode="HTML"
    )

    # Agar navbatda kutayotgan mijoz bo'lsa, xabar beramiz
    next_ticket = await db.get_next_waiting_ticket()
    if next_ticket:
        await broadcast_new_ticket_to_operators(
            bot,
            next_ticket["id"],
            next_ticket["customer_name"],
            next_ticket.get("first_message", "")
        )


@router.message(F.text == "📊 Holatim")
async def op_status_info(message: Message):
    op = await db.get_operator(message.from_user.id)
    if not op:
        return

    active_sess = await db.get_active_session_by_operator(message.from_user.id)
    session_text = f"Mijoz bilan bog'langan (Ticket #{active_sess['ticket_id']})" if active_sess else "Bo'sh"

    status_labels = {
        "available": "🟢 Onlayn (Mijoz qabul qilishga tayyor)",
        "busy": "🟡 Band (Muloqotda)",
        "offline": "🔴 Oflayn (Tanaffus)"
    }

    code_str = f" [#{op['operator_code']}]" if op.get("operator_code") else ""
    is_user_admin = (message.from_user.id in config.ADMIN_IDS)
    reply_kb = get_operator_active_keyboard() if active_sess else get_operator_idle_keyboard(op["status"] != "offline", is_admin=is_user_admin)

    await message.answer(
        f"👤 <b>Operator:</b> {op['full_name']}{code_str}\n"
        f"📌 <b>Holat:</b> {status_labels.get(op['status'], op['status'])}\n"
        f"💬 <b>Faol muloqot:</b> {session_text}",
        reply_markup=reply_kb,
        parse_mode="HTML"
    )


@router.message(F.text == "👥 Kutayotganlar soni")
async def op_queue_count(message: Message, bot: Bot):
    op = await db.get_operator(message.from_user.id)
    if not op:
        return

    next_ticket = await db.get_next_waiting_ticket()
    if next_ticket:
        active_sess = await db.get_active_session_by_operator(message.from_user.id)
        if not active_sess and op["status"] != "offline":
            from keyboards import get_accept_ticket_keyboard
            await message.answer(
                f"🔔 <b>Mijoz #{next_ticket['id']}</b> ({next_ticket['customer_name']}) navbatda kutmoqda!\nQabul qilasizmi?",
                reply_markup=get_accept_ticket_keyboard(next_ticket["id"]),
                parse_mode="HTML"
            )
        else:
            await message.answer(
                f"👥 Navbatda kutayotganlar bor! Eng birinchi murojaat: <b>Mijoz #{next_ticket['id']}</b> ({next_ticket['customer_name']})", 
                parse_mode="HTML"
            )
    else:
        await message.answer("✅ Hozirda navbatda kutayotgan mijozlar yo'q.")


# ================= MIJOZNI QABUL QILISH (ACCEPT CALLBACK) =================

@router.callback_query(F.data.startswith("accept_ticket:"))
async def op_accept_ticket(callback: CallbackQuery, bot: Bot):
    operator_id = callback.from_user.id
    op = await db.get_operator(operator_id)
    if not op:
        await callback.answer("Siz operator emassiz!", show_alert=True)
        return

    ticket_id = int(callback.data.split(":")[1])

    # Operator allaqachon boshqa mijoz bilan suhbatda emasmi?
    active_sess = await db.get_active_session_by_operator(operator_id)
    if active_sess:
        await callback.answer("Siz allaqachon boshqa mijoz bilan suhbatdasiz!", show_alert=True)
        return

    # Atomic holda ticketni qabul qilish (Race-condition xavfsiz)
    success, ticket = await db.claim_ticket(ticket_id, operator_id)
    if not success:
        await callback.answer("Kechirasiz, bu mijoz allaqachon boshqa operator tomonidan qabul qilindi!", show_alert=True)
        try:
            await callback.message.edit_reply_markup(
                reply_markup=get_ticket_claimed_keyboard("Boshqa operator")
            )
        except Exception:
            pass
        return

    customer_id = ticket["customer_id"]
    customer_name = ticket["customer_name"]
    customer_username = ticket.get("customer_username") or ""
    op_name = op["full_name"]
    if op.get("operator_code"):
        op_name += f" (#{op['operator_code']})"

    user_link = f'<a href="tg://user?id={customer_id}">{customer_name}</a>'
    username_text = f"@{customer_username}" if customer_username else "<i>(Mavjud emas)</i>"

    await callback.answer("Mijoz qabul qilindi!")

    first_msg = ticket.get("first_message", "")
    topic_line = format_topic_line(first_msg)

    customer_lang = await db.get_user_language(customer_id)
    lang_badge = "🇷🇺 Ruscha" if customer_lang == "ru" else "🇺🇿 O'zbekcha"

    # 1. Boshqa operatorlardagi tugmani yangilash
    await update_ticket_notifications_as_claimed(bot, ticket_id, op_name, operator_id)

    # 2. Ushbu operatorga tasdiq va profil ma'lumotlarini berish
    try:
        await callback.message.edit_text(
            f"✅ <b>Mijoz #{ticket_id} qabul qilindi!</b>\n\n"
            f"👤 <b>Mijoz:</b> {user_link}\n"
            f"📱 <b>Telegram:</b> {username_text}\n"
            f"🆔 <b>Telegram ID:</b> <code>{customer_id}</code>\n"
            f"🌐 <b>Muloqot tili:</b> {lang_badge}\n"
            f"{topic_line}\n"
            f"<i>Endi siz yozgan barcha xabarlar to'g'ridan-to'g'ri mijozga yetkaziladi.</i>",
            parse_mode="HTML"
        )
    except Exception:
        pass

    # Operatorga profil tugmasi (agar username bo'lsa)
    inline_kb = None
    if customer_username:
        clean_user = customer_username.replace("@", "").strip()
        if clean_user:
            inline_kb = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text=f"👤 Mijoz profilini ochish (@{clean_user})", url=f"https://t.me/{clean_user}")
            ]])

    active_sess = await db.get_active_session_by_operator(operator_id)
    sess_id = active_sess["id"] if active_sess else None
    if sess_id and callback.message:
        await db.track_session_message(sess_id, operator_id, callback.message.message_id)

    info_msg = await bot.send_message(
        chat_id=operator_id,
        text=(
            f"💬 <b>{user_link} bilan muloqot boshlandi!</b>\n\n"
            f"👤 <b>Ism:</b> {customer_name}\n"
            f"📱 <b>Username:</b> {username_text}\n"
            f"🆔 <b>Telegram ID:</b> <code>{customer_id}</code>\n"
            f"🌐 <b>Muloqot tili:</b> {lang_badge}\n"
            f"{topic_line}\n"
            f"<i>(Suhbatni yakunlash uchun pastdagi <b>«🛑 Suhbatni yakunlash»</b> tugmasini bosing)</i>"
        ),
        reply_markup=get_operator_active_keyboard(),
        parse_mode="HTML"
    )
    if sess_id and info_msg:
        await db.track_session_message(sess_id, operator_id, info_msg.message_id)

    if inline_kb:
        try:
            link_msg = await bot.send_message(
                chat_id=operator_id,
                text=f"🔗 <b>{customer_name}</b> profiliga to'g'ridan-to'g'ri havola:",
                reply_markup=inline_kb,
                parse_mode="HTML"
            )
            if sess_id and link_msg:
                await db.track_session_message(sess_id, operator_id, link_msg.message_id)
        except Exception:
            pass

    # Bot tomonidan operatorga yo'nalish eslatmasi (Mijoz xabari emasligini alohida ta'kidlash)
    clean_topic = "Umumiy murojaat"
    if first_msg:
        if first_msg.startswith("[Yo'nalish:"):
            clean_topic = first_msg.replace("[Yo'nalish:", "").rstrip("]").strip()
        else:
            clean_topic = first_msg

    bot_reminder_text = (
        "🤖 <b>[BOT ESLATMASI]:</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 <b>Mijoz murojaat qilgan masala:</b>\n"
        f"👉 <b>{clean_topic}</b>\n\n"
        f"🌐 <b>Muloqot tili:</b> {lang_badge}\n\n"
        "💡 <i>(Diqqat: Bu xabar bot tomonidan avtomatik yuborildi. Bu mijozning shaxsiy xabari emas, mijoz aynan shu bo'lim/masala bo'yicha operatorga ulangan)</i>"
    )

    reminder_msg = await bot.send_message(
        chat_id=operator_id,
        text=bot_reminder_text,
        parse_mode="HTML"
    )
    if sess_id and reminder_msg:
        await db.track_session_message(sess_id, operator_id, reminder_msg.message_id)

    # 3. Mijozga salomlashuv shabloni va faol klaviatura yuborish
    if customer_lang == "ru":
        greeting_text = (
            f"✅ Оператор <b>{op_name}</b> подключился к диалогу!\n\n"
            "Вы можете написать свой вопрос, оператор сейчас ответит вам."
        )
    else:
        greeting_text = config.GREETING_TEMPLATE.format(
            company_name=config.COMPANY_NAME,
            operator_name=op_name
        )

    await bot.send_message(
        chat_id=customer_id,
        text=greeting_text,
        reply_markup=get_customer_active_keyboard(customer_lang),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "claimed_info")
async def cb_claimed_info(callback: CallbackQuery):
    await callback.answer("Ushbu murojaat boshqa operator tomonidan qabul qilingan.", show_alert=False)


# ================= SUHBATNI YAKUNLASH (END CHAT) =================

@router.message(F.text == "🛑 Suhbatni yakunlash")
@router.message(Command("end"))
async def op_end_chat(message: Message, bot: Bot):
    operator_id = message.from_user.id
    op = await db.get_operator(operator_id)
    if not op:
        return

    is_user_admin = (operator_id in config.ADMIN_IDS)
    session = await db.close_session_by_operator(operator_id)
    if not session:
        await message.answer(
            "⚠️ Hozirda faol suhbat mavjud emas.",
            reply_markup=get_operator_idle_keyboard(is_available=True, is_admin=is_user_admin)
        )
        return

    customer_id = session["customer_id"]
    ticket_id = session["ticket_id"]
    sess_id = session["id"]

    # "Suhbatni yakunlash" tugmasi xabarini ham o'chirish ro'yxatiga qo'shamiz
    await db.track_session_message(sess_id, operator_id, message.message_id)

    # Operator chatidagi barcha yozishmalarni tozalash (chat toza turishi uchun)
    await clean_up_operator_session_messages(bot, sess_id, operator_id)

    # Operatorga toza xabar
    await message.answer(
        f"✅ <b>Mijoz #{ticket_id} bilan suhbat yakunlandi.</b>\n\n"
        "🧹 <i>Suhbat xabarlari chatdan tozalandi.</i>\n"
        "📜 <i>Yozishmalar tarixini istalgan payt <b>«📋 Mening suhbatlarim»</b> bo'limida ko'rishingiz mumkin.</i>",
        reply_markup=get_operator_idle_keyboard(is_available=True, is_admin=is_user_admin),
        parse_mode="HTML"
    )

    # Mijozga xayrlashuv va yulduzli baholash tugmalari
    customer_lang = await db.get_user_language(customer_id)
    if customer_lang == "ru":
        farewell_text = (
            "ℹ️ <b>Оператор завершил диалог.</b> Спасибо за обращение!\n\n"
            "Пожалуйста, оцените качество обслуживания:"
        )
    else:
        farewell_text = (
            f"{config.FAREWELL_TEMPLATE.format(company_name=config.COMPANY_NAME)}\n\n"
            f"{config.RATING_PROMPT}"
        )

    try:
        await bot.send_message(
            chat_id=customer_id,
            text=farewell_text,
            reply_markup=get_customer_rating_keyboard(ticket_id),
            parse_mode="HTML"
        )
    except Exception:
        pass

    # Navbatda boshqa kutayotgan mijoz bormi tekshiramiz
    next_ticket = await db.get_next_waiting_ticket()
    if next_ticket:
        await message.answer(
            f"🔔 <b>Navbatda kutayotgan mijoz bor!</b>\n"
            f"Mijoz #{next_ticket['id']} ({next_ticket['customer_name']})"
        )
        await broadcast_new_ticket_to_operators(
            bot,
            next_ticket["id"],
            next_ticket["customer_name"],
            next_ticket.get("first_message", "")
        )


# ================= OPERATOR SUHBATLAR TARIXI =================

async def build_op_history_list_text(sessions: list, total: int, page: int, op_name: str) -> str:
    if not sessions:
        return "📋 <b>Hozircha hech qanday yakunlangan suhbat mavjud emas.</b>"

    start_num = page * OP_HISTORY_PER_PAGE + 1
    text = (
        f"📋 <b>{op_name} — suhbatlar tarixi ({total} ta)</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "<i>Suhbat tarixini ko'rish uchun tanlang:</i>\n\n"
    )
    for i, s in enumerate(sessions, start_num):
        rating_str = f"{s['rating']} ⭐" if s.get("rating") else "—"
        date_str = s["closed_at"].split()[0] if s.get("closed_at") and " " in s["closed_at"] else (s.get("closed_at") or "")
        reason_info = f"\n  💬 <b>Fikr:</b> <i>{s['feedback_reason']}</i>" if s.get("feedback_reason") else ""
        text += (
            f"<b>{i}. Ticket #{s['ticket_id']}</b>\n"
            f"  👤 Mijoz: {s['customer_name']}\n"
            f"  📅 {date_str} | ⭐ {rating_str}{reason_info}\n"
            "──────────────────────\n"
        )
    return text


@router.message(F.text == "📋 Mening suhbatlarim")
async def op_my_history(message: Message):
    op = await db.get_operator(message.from_user.id)
    if not op:
        return

    sessions, total = await db.get_operator_sessions(
        message.from_user.id, limit=OP_HISTORY_PER_PAGE, offset=0
    )
    text = await build_op_history_list_text(sessions, total, 0, op["full_name"])
    kb = get_history_sessions_keyboard(sessions, 0, total, OP_HISTORY_PER_PAGE, "op")
    await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("op_history_page:"))
async def cb_op_history_page(callback: CallbackQuery):
    op = await db.get_operator(callback.from_user.id)
    if not op:
        await callback.answer("Siz operator emassiz!", show_alert=True)
        return

    page = int(callback.data.split(":")[1])
    offset = page * OP_HISTORY_PER_PAGE
    sessions, total = await db.get_operator_sessions(
        callback.from_user.id, limit=OP_HISTORY_PER_PAGE, offset=offset
    )
    text = await build_op_history_list_text(sessions, total, page, op["full_name"])
    kb = get_history_sessions_keyboard(sessions, page, total, OP_HISTORY_PER_PAGE, "op")

    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        await callback.answer()
    except Exception:
        await callback.answer("Ma'lumotlar o'zgarmagan.")


@router.callback_query(F.data.startswith("op_history_view:"))
async def cb_op_history_view(callback: CallbackQuery):
    op = await db.get_operator(callback.from_user.id)
    if not op:
        await callback.answer("Siz operator emassiz!", show_alert=True)
        return

    session_id = int(callback.data.split(":")[1])
    session = await db.get_session_by_id(session_id)
    if not session:
        await callback.answer("Suhbat topilmadi!", show_alert=True)
        return

    # Faqat o'z suhbatlarini ko'rishi mumkin
    if session["operator_id"] != callback.from_user.id:
        await callback.answer("Bu sizning suhbatingiz emas!", show_alert=True)
        return

    messages = await db.get_session_messages(session_id)

    rating_str = f"{session['rating']} ⭐" if session.get("rating") else "Baholanmagan"
    if session.get("feedback_reason"):
        rating_str += f" (E'tiroz: <i>{session['feedback_reason']}</i>)"
    started = session.get("started_at", "")
    closed = session.get("closed_at", "")

    cust_id = session.get("customer_id")
    cust_name = session.get("customer_name") or "Mijoz"
    cust_user = session.get("customer_username") or ""
    user_link = f'<a href="tg://user?id={cust_id}">{cust_name}</a>' if cust_id else cust_name
    username_info = f" (@{cust_user})" if cust_user else ""
    id_info = f" [<code>{cust_id}</code>]" if cust_id else ""

    text = (
        f"📋 <b>Suhbat tarixi: Ticket #{session['ticket_id']}</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>Mijoz:</b> {user_link}{username_info}{id_info}\n"
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
                sender_icon = "👨‍💼 Men"
            content = msg["text_content"] or ""
            if len(content) > 200:
                content = content[:200] + "..."
            text += f"<b>{sender_icon}</b> [{time_str}]: {content}\n"

    text += "\n━━━━━━━━━━━━━━━━━━━━━━"

    if len(text) > 4000:
        text = text[:3950] + "\n\n<i>... (xabarlar juda ko'p, qisqartirildi)</i>"

    media_files = await db.get_session_media_messages(session_id)
    kb = get_history_back_keyboard(0, "op", session_id=session_id, media_count=len(media_files))
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        await callback.answer()
    except Exception:
        await callback.answer("Xatolik yuz berdi.")


@router.callback_query(F.data.startswith("op_history_media:"))
async def cb_op_history_media(callback: CallbackQuery, bot: Bot):
    op = await db.get_operator(callback.from_user.id)
    if not op:
        await callback.answer("Siz operator emassiz!", show_alert=True)
        return

    session_id = int(callback.data.split(":")[1])
    session = await db.get_session_by_id(session_id)
    if not session or session["operator_id"] != callback.from_user.id:
        await callback.answer("Ruxsat yo'q!", show_alert=True)
        return

    media_files = await db.get_session_media_messages(session_id)
    if not media_files:
        await callback.answer("Bu suhbatda yuklangan media fayllar yo'q.", show_alert=True)
        return

    await callback.answer(f"{len(media_files)} ta fayl yuborilmoqda...")

    for item in media_files:
        c_type = item["content_type"]
        f_id = item["file_id"]
        sender = "👤 Mijoz" if item["sender_type"] == "customer" else "👨‍💼 Men"
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

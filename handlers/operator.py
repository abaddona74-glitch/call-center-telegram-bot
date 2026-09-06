from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
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
    get_ticket_claimed_keyboard
)
from handlers.common import update_ticket_notifications_as_claimed, broadcast_new_ticket_to_operators

router = Router()


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

    await message.answer(
        f"🎉 <b>Tabriklaymiz, siz muvaffaqiyatli ro'yxatdan o'tdingiz!</b>\n\n"
        f"👤 <b>Operator:</b> {operator_name}\n"
        f"🔢 <b>Operator ID:</b> #{code}\n"
        f"🏢 <b>Korxona:</b> «{config.COMPANY_NAME}»\n"
        f"📌 <b>Holatingiz:</b> 🟢 Onlayn (Mijoz kutish)\n\n"
        "<i>Yangi mijozlar murojaat qilganda sizga darhol qo'ng'iroq/qabul qilish xabari yuboriladi.</i>",
        reply_markup=get_operator_idle_keyboard(is_available=True),
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


# ================= TEZKOR RO'YXATDAN O'TISH BUYRUG'I =================

@router.message(Command("operator", "bind", "register"))
async def cmd_register_operator(message: Message, state: FSMContext, bot: Bot):
    """
    Operator ulanishi:
    Agar parametr berilmasa -> interaktiv so'rovnoma boshlanadi.
    Format: /operator [parol] [Ism] [ID]
    """
    args = message.text.split(maxsplit=3)
    if len(args) == 1:
        # Interaktiv rejim
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
        reply_markup=get_operator_idle_keyboard(is_available=True),
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
        await message.answer("⚠️ Hozir suhbatdasiz! Avval suhbatni yakunlang.")
        return

    await db.set_operator_status(message.from_user.id, "offline")
    await message.answer(
        "🔴 <b>Siz oflayn rejimdasiz (Tanaffus).</b>\n"
        "Sizga yangi mijozlar bildirishnomalari yuborilmaydi.",
        reply_markup=get_operator_idle_keyboard(is_available=False),
        parse_mode="HTML"
    )


@router.message(F.text == "🟢 Onlayn (Mijoz kutish)")
async def op_go_online(message: Message, bot: Bot):
    op = await db.get_operator(message.from_user.id)
    if not op:
        return

    await db.set_operator_status(message.from_user.id, "available")
    await message.answer(
        "🟢 <b>Siz onlayn rejimdasiz!</b>\n"
        "Yangi murojaatlar kelishi bilan sizga bildirishnoma yuboriladi.",
        reply_markup=get_operator_idle_keyboard(is_available=True),
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
    await message.answer(
        f"👤 <b>Operator:</b> {op['full_name']}{code_str}\n"
        f"📌 <b>Holat:</b> {status_labels.get(op['status'], op['status'])}\n"
        f"💬 <b>Faol muloqot:</b> {session_text}",
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
    op_name = op["full_name"]
    if op.get("operator_code"):
        op_name += f" (#{op['operator_code']})"

    await callback.answer("Mijoz qabul qilindi!")

    # 1. Boshqa operatorlardagi tugmani yangilash
    await update_ticket_notifications_as_claimed(bot, ticket_id, op_name, operator_id)

    # 2. Ushbu operatorga tasdiq va aktiv klaviatura berish
    try:
        await callback.message.edit_text(
            f"✅ <b>Mijoz #{ticket_id} qabul qilindi!</b>\n"
            f"👤 <b>Mijoz:</b> {customer_name}\n\n"
            f"<i>Endi siz yozgan barcha xabarlar mijozga boradi. Suhbatni yakunlash uchun pastdagi tugmani bosing.</i>",
            parse_mode="HTML"
        )
    except Exception:
        pass

    await bot.send_message(
        chat_id=operator_id,
        text=f"💬 <b>{customer_name}</b> bilan muloqot boshlandi.",
        reply_markup=get_operator_active_keyboard(),
        parse_mode="HTML"
    )

    # 3. Mijozga salomlashuv shabloni va faol klaviatura yuborish
    greeting_text = config.GREETING_TEMPLATE.format(
        company_name=config.COMPANY_NAME,
        operator_name=op_name
    )

    await bot.send_message(
        chat_id=customer_id,
        text=greeting_text,
        reply_markup=get_customer_active_keyboard(),
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

    session = await db.close_session_by_operator(operator_id)
    if not session:
        await message.answer(
            "⚠️ Hozirda faol suhbat mavjud emas.",
            reply_markup=get_operator_idle_keyboard(is_available=True)
        )
        return

    customer_id = session["customer_id"]
    ticket_id = session["ticket_id"]

    # Operatorga xabar
    await message.answer(
        f"✅ <b>Mijoz #{ticket_id} bilan suhbat yakunlandi.</b>\n"
        "Siz yana yangi mijozlarni qabul qilishga tayyorsiz.",
        reply_markup=get_operator_idle_keyboard(is_available=True),
        parse_mode="HTML"
    )

    # Mijozga xayrlashuv va yulduzli baholash tugmalari
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

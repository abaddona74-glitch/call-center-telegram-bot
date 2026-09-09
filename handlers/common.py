from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
import database as db
from keyboards import get_accept_ticket_keyboard, get_ticket_claimed_keyboard


def format_topic_line(first_msg: str) -> str:
    """Mijoz tanlagan bo'lim/yo'nalish yoki dastlabki xabarni chiroyli formatlash"""
    if not first_msg:
        return ""
    if first_msg.startswith("[Yo'nalish:"):
        clean_topic = first_msg.replace("[Yo'nalish:", "").rstrip("]").strip()
        return f"📂 <b>Tanlangan bo'lim:</b> <b>{clean_topic}</b>\n"
    return f"💬 <b>Dastlabki xabar:</b> <i>{first_msg}</i>\n"


async def broadcast_new_ticket_to_operators(
    bot: Bot, 
    ticket_id: int, 
    customer_name: str = "", 
    first_message: str = "",
    customer_id: int = 0,
    customer_username: str = ""
):
    """Barcha onlayn va bo'sh operatorlarga yangi mijoz haqida ochiq profil ma'lumotlari bilan xabarnoma jo'natadi"""
    available_ops = await db.get_available_operators()
    if not available_ops:
        return

    # Agar parametrlar to'liq berilmagan bo'lsa, bazadan to'ldiramiz
    ticket = await db.get_ticket_by_id(ticket_id)
    if ticket:
        customer_name = customer_name or ticket.get("customer_name") or "Mijoz"
        customer_id = customer_id or ticket.get("customer_id") or 0
        customer_username = customer_username or ticket.get("customer_username") or ""
        first_message = first_message or ticket.get("first_message") or ""

    user_link = f'<a href="tg://user?id={customer_id}">{customer_name}</a>' if customer_id else customer_name
    username_text = f"@{customer_username}" if customer_username else "<i>(Mavjud emas)</i>"
    topic_line = format_topic_line(first_message)
    customer_lang = await db.get_user_language(customer_id)
    lang_badge = "🇷🇺 Ruscha" if customer_lang == "ru" else "🇺🇿 O'zbekcha"

    text = (
        f"🔔 <b>Yangi murojaat: Mijoz #{ticket_id}</b>\n\n"
        f"👤 <b>Mijoz:</b> {user_link}\n"
        f"📱 <b>Telegram:</b> {username_text}\n"
        f"🆔 <b>Telegram ID:</b> <code>{customer_id}</code>\n"
        f"🌐 <b>Muloqot tili:</b> {lang_badge}\n"
        f"{topic_line}"
    )

    kb = get_accept_ticket_keyboard(ticket_id, customer_username=customer_username)

    for op in available_ops:
        try:
            msg = await bot.send_message(
                chat_id=op["telegram_id"],
                text=text,
                reply_markup=kb,
                parse_mode="HTML"
            )
            await db.save_notification(ticket_id, op["telegram_id"], msg.message_id)
        except TelegramAPIError:
            pass


async def update_ticket_notifications_as_claimed(
    bot: Bot, 
    ticket_id: int, 
    operator_name: str, 
    claimed_operator_id: int
):
    """
    Birinchi operator qabul qilgach, qolgan barcha operatorlardagi 
    tugma olib tashlanadi va xabar '✅ [Ism] qabul qildi' ga o'zgartiriladi
    """
    ticket = await db.get_ticket_by_id(ticket_id)
    customer_id = ticket.get("customer_id") if ticket else 0
    customer_name = ticket.get("customer_name") if ticket else "Mijoz"
    customer_username = ticket.get("customer_username") if ticket else ""
    first_msg = ticket.get("first_message", "") if ticket else ""

    user_link = f'<a href="tg://user?id={customer_id}">{customer_name}</a>' if customer_id else customer_name
    username_text = f" (@{customer_username})" if customer_username else ""
    topic_line = format_topic_line(first_msg)

    text = (
        f"🔔 <b>Murojaat: Mijoz #{ticket_id}</b>\n\n"
        f"👤 <b>Mijoz:</b> {user_link}{username_text}\n"
        f"🆔 <b>Telegram ID:</b> <code>{customer_id}</code>\n"
        f"{topic_line}\n"
        f"✅ <b>{operator_name} qabul qildi</b>"
    )

    notifications = await db.get_notifications(ticket_id)
    for notif in notifications:
        op_id = notif["operator_id"]
        msg_id = notif["message_id"]

        # Qabul qilgan operatorga alohida xabar boradi, qolganlariga esa tugma olib tashlanadi
        if op_id != claimed_operator_id:
            try:
                await bot.edit_message_text(
                    chat_id=op_id,
                    message_id=msg_id,
                    text=text,
                    reply_markup=None,
                    parse_mode="HTML"
                )
            except TelegramAPIError:
                pass


async def clean_up_operator_session_messages(bot: Bot, session_id: int, operator_id: int) -> None:
    """
    Operator chatidan suhbat davomidagi yozishmalar va kartochkalarni o'chirish.
    Chat toza turishi uchun barcha xabarlar botdan tozalanadi, 
    lekin yozishmalar tarixi bazada qoladi va 'Mening suhbatlarim'da ko'rinadi.
    """
    try:
        msg_ids = await db.get_session_message_ids_for_chat(session_id, operator_id)
        if not msg_ids:
            return

        # Aiogram delete_messages (100 tadan qilib o'chirish)
        for i in range(0, len(msg_ids), 100):
            batch = msg_ids[i:i + 100]
            try:
                await bot.delete_messages(chat_id=operator_id, message_ids=batch)
            except Exception:
                # Agar bir vaqtda o'chirishda xatolik bo'lsa bittalab urinib ko'ramiz
                for m_id in batch:
                    try:
                        await bot.delete_message(chat_id=operator_id, message_id=m_id)
                    except Exception:
                        pass
        await db.clear_session_chat_messages(session_id)
    except Exception:
        pass


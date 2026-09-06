from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
import database as db
from keyboards import get_accept_ticket_keyboard, get_ticket_claimed_keyboard


async def broadcast_new_ticket_to_operators(
    bot: Bot, 
    ticket_id: int, 
    customer_name: str, 
    first_message: str = ""
):
    """Barcha onlayn va bo'sh operatorlarga yangi mijoz haqida xabarnoma jo'natadi"""
    available_ops = await db.get_available_operators()
    if not available_ops:
        return

    text = (
        f"🔔 <b>Yangi murojaat: Mijoz #{ticket_id}</b>\n"
        f"👤 <b>Mijoz:</b> {customer_name}\n"
    )
    if first_message:
        text += f"💬 <b>Dastlabki xabar:</b> <i>{first_message}</i>\n"

    kb = get_accept_ticket_keyboard(ticket_id)

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
    tugmani '✅ Operator [Ism] qabul qildi' ga yangilaydi
    """
    notifications = await db.get_notifications(ticket_id)
    for notif in notifications:
        op_id = notif["operator_id"]
        msg_id = notif["message_id"]

        # Qabul qilgan operatorga alohida xabar boradi, qolganlariga esa tugma yangilanadi
        if op_id != claimed_operator_id:
            try:
                await bot.edit_message_reply_markup(
                    chat_id=op_id,
                    message_id=msg_id,
                    reply_markup=get_ticket_claimed_keyboard(operator_name)
                )
            except TelegramAPIError:
                pass

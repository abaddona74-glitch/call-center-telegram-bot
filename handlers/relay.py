from aiogram import Router, Bot
from aiogram.types import Message
from aiogram.exceptions import TelegramAPIError
import database as db

router = Router()


def _detect_content(message: Message):
    """Xabar turini, matn tarkibini va file_id ni aniqlash"""
    if message.photo:
        return "photo", message.caption or "[📷 Rasm]", message.photo[-1].file_id
    elif message.voice:
        return "voice", "[🎤 Ovozli xabar]", message.voice.file_id
    elif message.video:
        return "video", message.caption or "[📹 Video]", message.video.file_id
    elif message.video_note:
        return "video_note", "[📹 Video xabar]", message.video_note.file_id
    elif message.document:
        doc_name = message.document.file_name or "fayl"
        return "document", message.caption or f"[📎 Hujjat: {doc_name}]", message.document.file_id
    elif message.sticker:
        return "sticker", f"[😀 Stiker: {message.sticker.emoji or ''}]", message.sticker.file_id
    elif message.animation:
        return "animation", message.caption or "[🎞 GIF]", message.animation.file_id
    elif message.audio:
        title = message.audio.title or message.audio.file_name or "Audio"
        return "audio", message.caption or f"[🎵 Audio: {title}]", message.audio.file_id
    elif message.location:
        return "location", "[📍 Joylashuv]", ""
    elif message.contact:
        return "contact", f"[👤 Kontakt: {message.contact.phone_number}]", ""
    else:
        return "text", message.text or "", ""


@router.message()
async def relay_messages(message: Message, bot: Bot):
    """
    Barcha boshqa xabarlar (matn, rasm, voice, video, hujjat)ni
    faol sessiya ishtirokchilariga uzatuvchi asosiy relay xizmati.
    Har bir xabar bazaga ham saqlanadi (tarix uchun).
    """
    user_id = message.from_user.id
    content_type, text_content, file_id = _detect_content(message)

    # 1. Xabar OPERATOR tomonidan yozildimi?
    active_op_sess = await db.get_active_session_by_operator(user_id)
    if active_op_sess:
        customer_id = active_op_sess["customer_id"]
        sess_id = active_op_sess["id"]
        # Operatorning xabarini tozalash uchun kuzatamiz
        await db.track_session_message(sess_id, user_id, message.message_id)
        # Xabarni bazaga saqlash
        try:
            await db.save_message(
                session_id=sess_id,
                sender_type="operator",
                sender_id=user_id,
                content_type=content_type,
                text_content=text_content,
                file_id=file_id
            )
        except Exception:
            pass
        try:
            # Xabarni mijozga aynan qanday bo'lsa shunday nusxalab yuboramiz
            sent_cust_msg = await message.copy_to(chat_id=customer_id)
            if sent_cust_msg:
                await db.save_relayed_message(
                    session_id=sess_id,
                    source_chat_id=user_id,
                    source_message_id=message.message_id,
                    target_chat_id=customer_id,
                    target_message_id=sent_cust_msg.message_id
                )
        except TelegramAPIError as e:
            await message.answer(f"⚠️ Xabarni mijozga yetkazishda xatolik yuz berdi: {e}")
        return

    # 2. Xabar MIJOZ tomonidan yozildimi?
    active_cust_sess = await db.get_active_session_by_customer(user_id)
    if active_cust_sess:
        operator_id = active_cust_sess["operator_id"]
        sess_id = active_cust_sess["id"]
        # Xabarni bazaga saqlash
        try:
            await db.save_message(
                session_id=sess_id,
                sender_type="customer",
                sender_id=user_id,
                content_type=content_type,
                text_content=text_content,
                file_id=file_id
            )
        except Exception:
            pass
        try:
            # Xabarni operatorga copy_to orqali yetkazamiz (shunda bot tomonidan yuborilib, edit qilinganda o'zgaradi)
            sent_op_msg = await message.copy_to(chat_id=operator_id)
            
            if sent_op_msg:
                # Operator chatidan o'chirish uchun xabarni saqlaymiz
                await db.track_session_message(sess_id, operator_id, sent_op_msg.message_id)
                # Tahrirlash (edited_message) uchun bog'lanishni saqlaymiz
                await db.save_relayed_message(
                    session_id=sess_id,
                    source_chat_id=user_id,
                    source_message_id=message.message_id,
                    target_chat_id=operator_id,
                    target_message_id=sent_op_msg.message_id
                )
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


# ================= TAHRIRLANGAN XABARLARNI SINXRONLASHTIRISH =================

@router.edited_message()
async def handle_edited_messages(message: Message, bot: Bot):
    """
    Operator yoki mijoz o'z xabarini tahrirlaganda (edit qilganda),
    ikkinchi tomonga yetkazilgan xabarni ham avtomatik tarzda real vaqtda tahrirlash.
    """
    user_id = message.from_user.id
    relayed = await db.get_relayed_message(user_id, message.message_id)
    if not relayed:
        return

    sess_id = relayed["session_id"]
    target_chat_id = relayed["target_chat_id"]
    target_message_id = relayed["target_message_id"]

    # Sessiya faol ekanligini tekshiramiz
    sess = await db.get_session_by_id(sess_id)
    if not sess or sess.get("status") != "active":
        return

    try:
        if message.text:
            await bot.edit_message_text(
                chat_id=target_chat_id,
                message_id=target_message_id,
                text=message.text,
                entities=message.entities
            )
        elif message.caption is not None:
            await bot.edit_message_caption(
                chat_id=target_chat_id,
                message_id=target_message_id,
                caption=message.caption,
                caption_entities=message.caption_entities
            )
    except TelegramAPIError:
        pass

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import aiosqlite
import re
import os

import database as db
import config
from regions import CONTRACT_REGIONS
from locales import t, get_reason_text

BANNER_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "banner.jpg")
from keyboards import (
    get_language_selection_keyboard,
    get_customer_main_menu_keyboard,
    get_regions_keyboard,
    get_region_details_keyboard,
    get_customer_queue_keyboard,
    get_customer_active_keyboard,
    get_customer_rating_keyboard,
    get_negative_feedback_keyboard,
    get_operator_idle_keyboard
)
from handlers.common import broadcast_new_ticket_to_operators, clean_up_operator_session_messages

router = Router()


class CustomerFeedbackState(StatesGroup):
    waiting_for_reason = State()


def _format_eta_text(eta: dict, subject: str = "", lang: str = "uz") -> str:
    ticket_id = eta["ticket_id"]
    ahead = eta["ahead_count"]
    online = eta["online_operators"]
    avail = eta["available_operators"]
    est_min = eta["est_minutes"]
    est_max = eta["est_max"]

    if lang == "ru":
        subj_str = f" по <b>{subject}</b>" if subject else ""
    else:
        subj_str = f"<b>{subject}</b> bo'yicha " if subject else ""

    text = t("queue_accepted", lang, subj=subj_str)

    if online == 0:
        text += t("queue_all_offline", lang)
    elif ahead == 0 and avail > 0:
        text += t("queue_routed", lang)
    else:
        ahead_text = (t("queue_ahead_count", lang, ahead=ahead) + "\n") if ahead > 0 else ""
        text += t("queue_busy", lang, est_min=est_min, est_max=est_max, ahead_text=ahead_text)
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

    lang = await db.get_user_language(user_id)

    # 3. Agar foydalanuvchi hozir faol suhbatda bo'lsa
    active_sess = await db.get_active_session_by_customer(user_id)
    if active_sess:
        await message.answer(
            t("in_active_chat", lang, operator_name=active_sess['operator_name']),
            reply_markup=get_customer_active_keyboard(lang),
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
            status_desc = t("queue_all_offline", lang)
        elif ahead == 0 and avail > 0:
            status_desc = t("queue_routed", lang)
        else:
            ahead_text = (t("queue_ahead_count", lang, ahead=ahead) + "\n") if ahead > 0 else ""
            status_desc = t("queue_busy", lang, est_min=est_min, est_max=est_max, ahead_text=ahead_text)

        await message.answer(
            t("queue_status_title", lang, status_desc=status_desc),
            reply_markup=get_customer_queue_keyboard(lang),
            parse_mode="HTML"
        )
        return

    # 5. Har qanday mijoz uchun /start bosilganda birinchi navbatda til tanlashni ko'rsatamiz:
    await message.answer(
        t("choose_lang"),
        reply_markup=get_language_selection_keyboard()
    )


# ================= TIL TANLASH (LANGUAGE SELECTION) =================

@router.callback_query(F.data.startswith("set_lang:"))
async def cb_set_language(callback: CallbackQuery):
    lang = callback.data.split(":")[1]
    user_id = callback.from_user.id
    user_name = callback.from_user.full_name or "Mijoz"

    await db.set_user_language(user_id, lang)
    await callback.answer(t("lang_selected", lang))

    try:
        await callback.message.delete()
    except Exception:
        pass

    welcome_text = t("welcome_caption", lang, name=user_name, company=config.COMPANY_NAME)

    if os.path.exists(BANNER_PATH):
        try:
            banner_file = FSInputFile(BANNER_PATH)
            await callback.message.answer_photo(
                photo=banner_file,
                caption=welcome_text,
                reply_markup=get_customer_main_menu_keyboard(lang),
                parse_mode="HTML"
            )
            return
        except Exception:
            pass

    await callback.message.answer(
        welcome_text,
        reply_markup=get_customer_main_menu_keyboard(lang),
        parse_mode="HTML"
    )


@router.message(F.text.in_({"🌐 Tilni o'zgartirish", "🌐 Сменить язык", "🌐 Tilni tanlash"}))
@router.message(Command("lang"))
@router.message(Command("language"))
async def cmd_change_language(message: Message):
    await message.answer(
        t("choose_lang"),
        reply_markup=get_language_selection_keyboard()
    )


# ================= NAVBATGA ULASH YORDAMCHI FUNKSIYASI =================

async def _connect_customer_to_queue(message: Message, bot: Bot, subject: str):
    """Mijozni ma'lum bir mavzu bo'yicha operator navbatiga qo'shish"""
    user_id = message.from_user.id
    user_name = message.from_user.full_name or "Mijoz"
    lang = await db.get_user_language(user_id)

    # Faol suhbatda bo'lsa
    active_sess = await db.get_active_session_by_customer(user_id)
    if active_sess:
        await message.answer(
            t("in_active_chat", lang, operator_name=active_sess['operator_name']),
            reply_markup=get_customer_active_keyboard(lang),
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
            t("queue_already_waiting", lang, est_min=est_min, est_max=est_max, ahead=ahead),
            reply_markup=get_customer_queue_keyboard(lang),
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
    welcome_text = _format_eta_text(eta, subject, lang=lang)

    await message.answer(
        welcome_text,
        reply_markup=get_customer_queue_keyboard(lang),
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

@router.message(F.text.in_({"e-huquqshunos", "⚖️ e-huquqshunos", "⚖️ e-Huquqshunos"}))
async def handle_e_huquqshunos(message: Message, bot: Bot):
    await _connect_customer_to_queue(message, bot, "e-huquqshunos")


@router.message(F.text.in_({"edo.ijro.uz", "📄 edo.ijro.uz"}))
async def handle_edo_ijro(message: Message, bot: Bot):
    await _connect_customer_to_queue(message, bot, "edo.ijro.uz")


@router.message(F.text.in_({"Shartnoma masalasida", "📝 Shartnoma masalasida", "По вопросам договоров", "📝 По вопросам договоров"}))
async def handle_contract_issues(message: Message):
    lang = await db.get_user_language(message.from_user.id)
    text = t("regions_title", lang)
    await message.answer(text, reply_markup=get_regions_keyboard(lang), parse_mode="HTML")


# ================= VILOYATLAR VA SHARTNOMA INLINE CALLBACKLARI =================

@router.callback_query(F.data.startswith("region:"))
async def cb_region_selected(callback: CallbackQuery):
    region_key = callback.data.split(":")[1]
    reg = CONTRACT_REGIONS.get(region_key)
    lang = await db.get_user_language(callback.from_user.id)

    if not reg:
        alert_msg = "Регион не найден!" if lang == "ru" else "Hudud ma'lumotlari topilmadi!"
        await callback.answer(alert_msg, show_alert=True)
        return

    region_name = reg.get("name_ru") if lang == "ru" else reg.get("name")

    phones_text = ""
    for p in reg["phones"]:
        clean_p = re.sub(r"[^\d+]", "", p)
        phones_text += f'• 📞 <a href="tel:{clean_p}"><b>{p}</b></a>\n'

    tg_text = ""
    if reg.get("telegram"):
        tg_text = t("tg_label", lang, tg=reg['telegram'])

    card_text = t(
        "region_card",
        lang,
        region_name=region_name,
        phones=phones_text.strip(),
        tg_text=tg_text
    )

    try:
        await callback.message.edit_text(
            card_text,
            reply_markup=get_region_details_keyboard(region_key, lang=lang),
            parse_mode="HTML"
        )
        await callback.answer()
    except Exception:
        await callback.answer()


@router.callback_query(F.data == "regions_list")
async def cb_regions_list(callback: CallbackQuery):
    lang = await db.get_user_language(callback.from_user.id)
    text = t("regions_title", lang)
    try:
        await callback.message.edit_text(text, reply_markup=get_regions_keyboard(lang), parse_mode="HTML")
        await callback.answer()
    except Exception:
        await callback.answer()


@router.callback_query(F.data == "back_to_main_menu")
async def cb_back_to_main_menu(callback: CallbackQuery):
    lang = await db.get_user_language(callback.from_user.id)
    user_name = callback.from_user.full_name or "Mijoz"

    try:
        await callback.message.delete()
    except Exception:
        pass

    welcome_text = t("welcome_caption", lang, name=user_name, company=config.COMPANY_NAME)
    if os.path.exists(BANNER_PATH):
        try:
            banner_file = FSInputFile(BANNER_PATH)
            await callback.message.answer_photo(
                photo=banner_file,
                caption=welcome_text,
                reply_markup=get_customer_main_menu_keyboard(lang),
                parse_mode="HTML"
            )
            await callback.answer()
            return
        except Exception:
            pass

    await callback.message.answer(
        welcome_text,
        reply_markup=get_customer_main_menu_keyboard(lang),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("queue_from_region:"))
async def cb_queue_from_region(callback: CallbackQuery, bot: Bot):
    region_key = callback.data.split(":")[1]
    reg = CONTRACT_REGIONS.get(region_key, {})
    lang = await db.get_user_language(callback.from_user.id)
    reg_name = reg.get("name_ru" if lang == "ru" else "name", "Hudud")

    if lang == "ru":
        subject = f"По вопросам договоров — {reg_name}"
        ans_toast = "Подключение к очереди операторов..."
    else:
        subject = f"Shartnoma masalasida — {reg_name}"
        ans_toast = "Operator navbatiga ulanmoqdasiz..."

    await callback.answer(ans_toast)
    await _connect_customer_to_queue(callback.message, bot, subject)


# ================= NAVBAT VA SUHBATNI BOSHQARISH =================

@router.message(F.text.in_({"ℹ️ Navbatimni tekshirish", "ℹ️ Проверить очередь"}))
async def check_queue_position(message: Message):
    lang = await db.get_user_language(message.from_user.id)

    # Agar foydalanuvchi allaqachon suhbatda bo'lsa
    active_sess = await db.get_active_session_by_customer(message.from_user.id)
    if active_sess:
        await message.answer(
            t("in_active_chat", lang, operator_name=active_sess['operator_name']),
            reply_markup=get_customer_active_keyboard(lang),
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
            status_desc = t("queue_all_offline", lang)
        elif ahead == 0 and avail > 0:
            status_desc = t("queue_routed", lang)
        else:
            ahead_text = (t("queue_ahead_count", lang, ahead=ahead) + "\n") if ahead > 0 else ""
            status_desc = t("queue_busy", lang, est_min=est_min, est_max=est_max, ahead_text=ahead_text)

        await message.answer(
            t("queue_status_title", lang, status_desc=status_desc),
            reply_markup=get_customer_queue_keyboard(lang),
            parse_mode="HTML"
        )
    else:
        await message.answer(
            t("not_in_queue", lang),
            reply_markup=get_customer_main_menu_keyboard(lang)
        )


@router.message(F.text.in_({"❌ Navbatdan chiqish", "❌ Выйти из очереди"}))
async def cancel_queue(message: Message):
    lang = await db.get_user_language(message.from_user.id)
    active_sess = await db.get_active_session_by_customer(message.from_user.id)
    if active_sess:
        await message.answer(
            t("in_active_chat", lang, operator_name=active_sess['operator_name']),
            reply_markup=get_customer_active_keyboard(lang),
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
            t("queue_cancelled", lang),
            reply_markup=get_customer_main_menu_keyboard(lang)
        )
    else:
        await message.answer(
            t("not_in_queue", lang),
            reply_markup=get_customer_main_menu_keyboard(lang)
        )


@router.message(F.text.in_({"❌ Suhbatni yakunlash", "❌ Завершить диалог"}))
async def customer_end_chat(message: Message, bot: Bot):
    lang = await db.get_user_language(message.from_user.id)
    session = await db.close_session_by_customer(message.from_user.id)
    if not session:
        await message.answer(
            t("not_in_queue", lang),
            reply_markup=get_customer_main_menu_keyboard(lang)
        )
        return

    operator_id = session["operator_id"]
    ticket_id = session["ticket_id"]

    farewell_text = t("chat_ended_by_user", lang)

    # Mijozga xayrlashuv va yulduzli baholash tugmalari
    await message.answer(
        farewell_text,
        reply_markup=get_customer_rating_keyboard(ticket_id),
        parse_mode="HTML"
    )

    # Operator chatidagi xabarlarni tozalash
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


# ================= BAHOLASH VA FIKR-MULOHAZALAR (FEEDBACK) =================

@router.callback_query(F.data.startswith("rate:"))
async def cb_rate_service(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    ticket_id = int(parts[1])
    stars = int(parts[2])
    lang = await db.get_user_language(callback.from_user.id)

    await db.save_session_rating(ticket_id, stars)

    if stars <= 3:
        # Past baho qo'yilganda sababini so'raymiz
        ans_toast = f"Оценка {stars} ⭐ принята." if lang == "ru" else f"Bahoyingiz ({stars} ⭐) qabul qilindi."
        await callback.answer(ans_toast)
        try:
            await callback.message.edit_text(
                t("rating_low_ask", lang),
                reply_markup=get_negative_feedback_keyboard(ticket_id, lang=lang),
                parse_mode="HTML"
            )
        except Exception:
            pass
    else:
        # Yuqori baho (4 yoki 5 ⭐)
        stars_str = f"{stars} ⭐"
        thanks_toast = f"Спасибо за оценку {stars_str}!" if lang == "ru" else f"Rahmat! {stars_str} bilan baholadingiz."
        await callback.answer(thanks_toast, show_alert=True)
        try:
            await callback.message.edit_text(
                t("rating_thanks", lang, stars=stars_str),
                parse_mode="HTML"
            )
        except Exception:
            pass


@router.callback_query(F.data.startswith("reason:"))
async def cb_feedback_reason(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    ticket_id = int(parts[1])
    code = parts[2]
    lang = await db.get_user_language(callback.from_user.id)

    if code == "skip":
        skip_toast = "Пропущено." if lang == "ru" else "O'tkazib yuborildi."
        await callback.answer(skip_toast)
        try:
            await callback.message.edit_text(
                t("feedback_skipped", lang),
                parse_mode="HTML"
            )
        except Exception:
            pass
        return

    if code == "custom":
        await state.set_state(CustomerFeedbackState.waiting_for_reason)
        await state.update_data(ticket_id=ticket_id, lang=lang)
        await callback.answer()
        try:
            await callback.message.edit_text(
                t("custom_reason_prompt", lang),
                reply_markup=None,
                parse_mode="HTML"
            )
        except Exception:
            pass
        return

    reason_text = get_reason_text(code, lang)
    await db.save_session_feedback(ticket_id, reason_text)
    saved_toast = "Отзыв принят!" if lang == "ru" else "Fikringiz qabul qilindi!"
    await callback.answer(saved_toast, show_alert=True)
    try:
        await callback.message.edit_text(
            f"✅ {t('feedback_saved', lang)}\n\n"
            f"<i>({reason_text})</i>",
            parse_mode="HTML"
        )
    except Exception:
        pass


@router.message(CustomerFeedbackState.waiting_for_reason)
async def process_custom_feedback_reason(message: Message, state: FSMContext):
    data = await state.get_data()
    ticket_id = data.get("ticket_id")
    lang = data.get("lang") or await db.get_user_language(message.from_user.id)
    custom_text = (message.text or "").strip()
    await state.clear()

    if ticket_id and custom_text:
        await db.save_session_feedback(ticket_id, custom_text[:500])

    await message.answer(
        t("feedback_saved", lang),
        reply_markup=get_customer_main_menu_keyboard(lang),
        parse_mode="HTML"
    )

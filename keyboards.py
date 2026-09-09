from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)


# ================= OPERATOR KLAVIATURALARI =================

def get_operator_idle_keyboard(is_available: bool = True, is_admin: bool = False) -> ReplyKeyboardMarkup:
    """Operator suhbatda bo'lmagan paytdagi menyusi"""
    status_btn = (
        KeyboardButton(text="🔴 Oflayn (Tanaffus)") 
        if is_available else 
        KeyboardButton(text="🟢 Onlayn (Mijoz kutish)")
    )
    rows = [
        [status_btn],
        [KeyboardButton(text="📊 Holatim"), KeyboardButton(text="👥 Kutayotganlar soni")],
        [KeyboardButton(text="📋 Mening suhbatlarim")]
    ]
    if is_admin:
        rows.append([KeyboardButton(text="👑 Admin paneliga qaytish")])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)



def get_operator_active_keyboard() -> ReplyKeyboardMarkup:
    """Operator mijoz bilan faol suhbatda bo'lgan paytdagi klaviatura"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🛑 Suhbatni yakunlash")]
        ],
        resize_keyboard=True
    )


def get_accept_ticket_keyboard(ticket_id: int, customer_username: str = "") -> InlineKeyboardMarkup:
    """Mijoz kelganda operatorlarga chiquvchi qabul qilish tugmasi"""
    rows = [
        [
            InlineKeyboardButton(
                text="📞 Qabul qilish (Accept)", 
                callback_data=f"accept_ticket:{ticket_id}"
            )
        ]
    ]
    if customer_username:
        clean_user = customer_username.replace("@", "").strip()
        if clean_user:
            rows.append([
                InlineKeyboardButton(
                    text=f"👤 Profilni ochish (@{clean_user})", 
                    url=f"https://t.me/{clean_user}"
                )
            ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_ticket_claimed_keyboard(operator_name: str) -> InlineKeyboardMarkup:
    """Ticket kimdir tomonidan qabul qilinganda ko'rinadigan tugma"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"✅ {operator_name} qabul qildi", 
                    callback_data="claimed_info"
                )
            ]
        ]
    )


# ================= MIJOZ KLAVIATURALARI =================

def get_language_selection_keyboard() -> InlineKeyboardMarkup:
    """Tilni tanlash inline tugmalari"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="set_lang:uz"),
                InlineKeyboardButton(text="🇷🇺 Русский", callback_data="set_lang:ru")
            ]
        ]
    )


def get_customer_main_menu_keyboard(lang: str = "uz") -> ReplyKeyboardMarkup:
    """Mijoz uchun asosiy xizmatlar menyusi"""
    from locales import t
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=t("btn_e_huquqshunos", lang)),
                KeyboardButton(text=t("btn_edo", lang))
            ],
            [
                KeyboardButton(text=t("btn_contracts", lang))
            ]
        ],
        resize_keyboard=True
    )


def get_regions_keyboard(lang: str = "uz") -> InlineKeyboardMarkup:
    """Shartnoma bo'yicha viloyatlar ro'yxati (inline)"""
    from regions import CONTRACT_REGIONS
    from locales import t
    buttons = []
    items = list(CONTRACT_REGIONS.items())
    
    for i in range(0, len(items), 2):
        row = []
        k1, v1 = items[i]
        icon1 = "🏙" if k1 == "tashkent_city" else "📍"
        name1 = v1.get("name_ru") if lang == "ru" else v1.get("name")
        row.append(InlineKeyboardButton(text=f"{icon1} {name1}", callback_data=f"region:{k1}"))
        
        if i + 1 < len(items):
            k2, v2 = items[i+1]
            icon2 = "🏙" if k2 == "tashkent_city" else "📍"
            name2 = v2.get("name_ru") if lang == "ru" else v2.get("name")
            row.append(InlineKeyboardButton(text=f"{icon2} {name2}", callback_data=f"region:{k2}"))
        buttons.append(row)
        
    buttons.append([
        InlineKeyboardButton(text=t("btn_back_main", lang), callback_data="back_to_main_menu")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_region_details_keyboard(region_key: str, lang: str = "uz") -> InlineKeyboardMarkup:
    """Tanlangan viloyat kontaktlari tagidagi tugmalar"""
    from regions import CONTRACT_REGIONS
    from locales import t
    reg = CONTRACT_REGIONS.get(region_key, {})
    buttons = []
    
    if reg.get("telegram"):
        tg_clean = reg["telegram"].replace("@", "")
        buttons.append([
            InlineKeyboardButton(text=t("btn_tg_contact", lang, tg=reg["telegram"]), url=f"https://t.me/{tg_clean}")
        ])
        
    buttons.append([
        InlineKeyboardButton(text=t("btn_connect_operator", lang), callback_data=f"queue_from_region:{region_key}")
    ])
    buttons.append([
        InlineKeyboardButton(text=t("btn_other_region", lang), callback_data="regions_list"),
        InlineKeyboardButton(text=t("btn_back_main", lang), callback_data="back_to_main_menu")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_customer_queue_keyboard(lang: str = "uz") -> ReplyKeyboardMarkup:
    """Mijoz navbatda kutayotgan paytdagi menyu"""
    from locales import t
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t("btn_check_queue", lang))],
            [KeyboardButton(text=t("btn_leave_queue", lang))]
        ],
        resize_keyboard=True
    )


def get_customer_active_keyboard(lang: str = "uz") -> ReplyKeyboardMarkup:
    """Mijoz operator bilan suhbatda bo'lganda"""
    from locales import t
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t("btn_end_chat", lang))]
        ],
        resize_keyboard=True
    )


def get_customer_rating_keyboard(ticket_id: int) -> InlineKeyboardMarkup:
    """Suhbat yakunlangach xizmat sifatini baholash"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⭐ 1", callback_data=f"rate:{ticket_id}:1"),
                InlineKeyboardButton(text="⭐ 2", callback_data=f"rate:{ticket_id}:2"),
                InlineKeyboardButton(text="⭐ 3", callback_data=f"rate:{ticket_id}:3"),
                InlineKeyboardButton(text="⭐ 4", callback_data=f"rate:{ticket_id}:4"),
                InlineKeyboardButton(text="⭐ 5", callback_data=f"rate:{ticket_id}:5"),
            ]
        ]
    )


def get_negative_feedback_keyboard(ticket_id: int, lang: str = "uz") -> InlineKeyboardMarkup:
    """Salbiy baho berilganda sababini tanlash klaviaturasi"""
    from locales import get_reason_text
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=get_reason_text("wait", lang), callback_data=f"reason:{ticket_id}:wait"),
                InlineKeyboardButton(text=get_reason_text("no_solution", lang), callback_data=f"reason:{ticket_id}:no_solution")
            ],
            [
                InlineKeyboardButton(text=get_reason_text("bad_attitude", lang), callback_data=f"reason:{ticket_id}:bad_attitude"),
                InlineKeyboardButton(text=get_reason_text("technical", lang), callback_data=f"reason:{ticket_id}:technical")
            ],
            [
                InlineKeyboardButton(text=get_reason_text("custom", lang), callback_data=f"reason:{ticket_id}:custom")
            ],
            [
                InlineKeyboardButton(text=get_reason_text("skip", lang), callback_data=f"reason:{ticket_id}:skip")
            ]
        ]
    )


# ================= ADMIN KLAVIATURALARI =================

def get_admin_main_keyboard() -> ReplyKeyboardMarkup:
    """Admin boshqaruv paneli menyusi"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📊 Jonli monitoring (Live)"),
                KeyboardButton(text="📞 Faol muloqotlar")
            ],
            [
                KeyboardButton(text="👥 Navbatdagilar ro'yxati"),
                KeyboardButton(text="👨‍💼 Operatorlar holati")
            ],
            [
                KeyboardButton(text="📜 Suhbatlar tarixi"),
                KeyboardButton(text="➕ Operator taklif qilish (Invite)")
            ],
            [
                KeyboardButton(text="🎧 Operator rejimiga o'tish"),
                KeyboardButton(text="❌ Operatorni chiqarish")
            ]
        ],
        resize_keyboard=True
    )


def get_admin_refresh_inline(action: str) -> InlineKeyboardMarkup:
    """Ma'lumotlarni yangilash uchun inline tugma"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔄 Yangilash", callback_data=f"admin_refresh:{action}")
            ]
        ]
    )


def get_admin_active_dialogs_keyboard(dialogs: list) -> InlineKeyboardMarkup:
    """Faol muloqotlarni majburiy yakunlash tugmalari bilan chiqarish"""
    buttons = []
    for d in dialogs:
        buttons.append([
            InlineKeyboardButton(
                text=f"🛑 Yakunlash: Ticket #{d['ticket_id']} ({d['operator_name']})",
                callback_data=f"admin_force_close:{d['ticket_id']}"
            )
        ])
    buttons.append([InlineKeyboardButton(text="🔄 Yangilash", callback_data="admin_refresh:dialogs")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)



def get_admin_operators_manage_keyboard(ops: list) -> InlineKeyboardMarkup:
    """Operatorlarni tanlash va boshqarish uchun inline klaviatura"""
    buttons = []
    for op in ops:
        code_badge = f" [#{op['operator_code']}]" if op.get("operator_code") else ""
        btn_text = f"⚙️ {op['full_name']}{code_badge}"
        buttons.append([InlineKeyboardButton(text=btn_text, callback_data=f"admin_manage_op:{op['telegram_id']}")])
    buttons.append([InlineKeyboardButton(text="🔄 Yangilash", callback_data="admin_refresh:operators")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_admin_operator_card_keyboard(op_id: int) -> InlineKeyboardMarkup:
    """Bitta operatorni boshqarish (tahrirlash/chiqarish) klaviaturasi"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✏️ Ismni o'zgartirish", callback_data=f"admin_edit_name:{op_id}"),
                InlineKeyboardButton(text="🔢 Kodni (#ID) o'zgartirish", callback_data=f"admin_edit_code:{op_id}")
            ],
            [
                InlineKeyboardButton(text="🗑 Tizimdan chiqarish", callback_data=f"admin_ask_kick:{op_id}")
            ],
            [
                InlineKeyboardButton(text="⬅️ Operatorlar ro'yxatiga qaytish", callback_data="admin_refresh:operators")
            ]
        ]
    )


def get_admin_operators_kick_keyboard(ops: list) -> InlineKeyboardMarkup:
    """Operatorlarni chiqarish uchun inline klaviatura"""
    buttons = []
    for op in ops:
        code_badge = f" [#{op['operator_code']}]" if op.get("operator_code") else ""
        btn_text = f"❌ Chiqarish: {op['full_name']}{code_badge}"
        buttons.append([InlineKeyboardButton(text=btn_text, callback_data=f"admin_ask_kick:{op['telegram_id']}")])
    buttons.append([InlineKeyboardButton(text="🔄 Yangilash", callback_data="admin_refresh:operators")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)



def get_history_sessions_keyboard(
    sessions: list, page: int, total: int, per_page: int, prefix: str = "admin", operator_id: int = 0
) -> InlineKeyboardMarkup:
    """Suhbatlar ro'yxati inline tugmalar (sahifalash va operator filtri bilan)"""
    buttons = []
    for s in sessions:
        rating_icon = f" {'⭐' * s['rating']}" if s.get("rating") else ""
        date_str = s["closed_at"].split()[0] if s.get("closed_at") and " " in s["closed_at"] else (s.get("closed_at") or "")
        btn_text = f"#{s['ticket_id']} {s['customer_name'][:15]} | {date_str}{rating_icon}"
        cb_data = f"{prefix}_history_view:{s['session_id']}:{page}:{operator_id}" if prefix == "admin" else f"{prefix}_history_view:{s['session_id']}"
        buttons.append([
            InlineKeyboardButton(
                text=btn_text,
                callback_data=cb_data
            )
        ])

    # Sahifalash (pagination) tugmalari
    total_pages = max(1, (total + per_page - 1) // per_page)
    nav_row = []
    if page > 0:
        prev_target = f"{prefix}_history_page:{page - 1}:{operator_id}" if prefix == "admin" else f"{prefix}_history_page:{page - 1}"
        nav_row.append(
            InlineKeyboardButton(text="⬅️ Oldingi", callback_data=prev_target)
        )
    nav_row.append(
        InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="noop")
    )
    if (page + 1) * per_page < total:
        next_target = f"{prefix}_history_page:{page + 1}:{operator_id}" if prefix == "admin" else f"{prefix}_history_page:{page + 1}"
        nav_row.append(
            InlineKeyboardButton(text="Keyingi ➡️", callback_data=next_target)
        )
    if nav_row:
        buttons.append(nav_row)

    # Admin uchun operator bo'yicha filtrlash va qidirish tugmalari
    if prefix == "admin":
        if operator_id > 0:
            buttons.append([
                InlineKeyboardButton(text="👨‍💼 Boshqa operatorni tanlash", callback_data="admin_history_ops"),
                InlineKeyboardButton(text="👥 Barcha suhbatlar", callback_data="admin_history_page:0:0")
            ])
        else:
            buttons.append([
                InlineKeyboardButton(text="👨‍💼 Operatorni tanlash", callback_data="admin_history_ops"),
                InlineKeyboardButton(text="🔍 Operator qidirish", callback_data="admin_history_search")
            ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_admin_history_operators_keyboard(ops: list) -> InlineKeyboardMarkup:
    """Admin uchun operatorlar bo'yicha suhbatlar tarixini tanlash klaviaturasi"""
    buttons = []
    for op in ops:
        code_badge = f" [#{op['operator_code']}]" if op.get("operator_code") else ""
        cnt = op.get("closed_count", 0)
        btn_text = f"👨‍💼 {op['full_name']}{code_badge} ({cnt} ta)"
        buttons.append([
            InlineKeyboardButton(
                text=btn_text,
                callback_data=f"admin_history_page:0:{op['telegram_id']}"
            )
        ])
    buttons.append([
        InlineKeyboardButton(text="🔍 Operator qidirish", callback_data="admin_history_search")
    ])
    buttons.append([
        InlineKeyboardButton(text="⬅️ Barcha suhbatlar ro'yxatiga qaytish", callback_data="admin_history_page:0:0")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_history_back_keyboard(
    page: int, prefix: str = "admin", session_id: int = 0, media_count: int = 0, operator_id: int = 0
) -> InlineKeyboardMarkup:
    """Suhbat tarixidan orqaga qaytish va medialarni yuklab olish tugmasi"""
    buttons = []
    if media_count > 0 and session_id > 0:
        buttons.append([
            InlineKeyboardButton(
                text=f"🎵 Fayl va audiolarni olish ({media_count} ta)",
                callback_data=f"{prefix}_history_media:{session_id}"
            )
        ])
    back_target = f"{prefix}_history_page:{page}:{operator_id}" if prefix == "admin" else f"{prefix}_history_page:{page}"
    buttons.append([
        InlineKeyboardButton(
            text="⬅️ Ro'yxatga qaytish",
            callback_data=back_target
        )
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

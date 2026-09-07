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

def get_customer_main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Mijoz uchun asosiy xizmatlar menyusi"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="⚖️ e-Huquqshunos"),
                KeyboardButton(text="📄 edo.ijro.uz")
            ],
            [
                KeyboardButton(text="📝 Shartnoma masalasida")
            ]
        ],
        resize_keyboard=True
    )


def get_regions_keyboard() -> InlineKeyboardMarkup:
    """Shartnoma bo'yicha viloyatlar ro'yxati (inline)"""
    from regions import CONTRACT_REGIONS
    buttons = []
    items = list(CONTRACT_REGIONS.items())
    
    for i in range(0, len(items), 2):
        row = []
        k1, v1 = items[i]
        icon1 = "🏙" if k1 == "tashkent_city" else "📍"
        row.append(InlineKeyboardButton(text=f"{icon1} {v1['name']}", callback_data=f"region:{k1}"))
        
        if i + 1 < len(items):
            k2, v2 = items[i+1]
            icon2 = "🏙" if k2 == "tashkent_city" else "📍"
            row.append(InlineKeyboardButton(text=f"{icon2} {v2['name']}", callback_data=f"region:{k2}"))
        buttons.append(row)
        
    buttons.append([
        InlineKeyboardButton(text="🔙 Asosiy menyu", callback_data="back_to_main_menu")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_region_details_keyboard(region_key: str) -> InlineKeyboardMarkup:
    """Tanlangan viloyat kontaktlari tagidagi tugmalar"""
    from regions import CONTRACT_REGIONS
    reg = CONTRACT_REGIONS.get(region_key, {})
    buttons = []
    
    if reg.get("telegram"):
        tg_clean = reg["telegram"].replace("@", "")
        buttons.append([
            InlineKeyboardButton(text=f"💬 Telegram orqali bog'lanish ({reg['telegram']})", url=f"https://t.me/{tg_clean}")
        ])
        
    buttons.append([
        InlineKeyboardButton(text="👨‍💼 Operator bilan bog'lanish", callback_data=f"queue_from_region:{region_key}")
    ])
    buttons.append([
        InlineKeyboardButton(text="⬅️ Boshqa hududni tanlash", callback_data="regions_list"),
        InlineKeyboardButton(text="🔙 Asosiy menyu", callback_data="back_to_main_menu")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_customer_queue_keyboard() -> ReplyKeyboardMarkup:
    """Mijoz navbatda kutayotgan paytdagi menyu"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="ℹ️ Navbatimni tekshirish")],
            [KeyboardButton(text="❌ Navbatdan chiqish")]
        ],
        resize_keyboard=True
    )


def get_customer_active_keyboard() -> ReplyKeyboardMarkup:
    """Mijoz operator bilan suhbatda bo'lganda"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="❌ Suhbatni yakunlash")]
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
    sessions: list, page: int, total: int, per_page: int, prefix: str = "admin"
) -> InlineKeyboardMarkup:
    """Suhbatlar ro'yxati inline tugmalar (sahifalash bilan)"""
    buttons = []
    for s in sessions:
        rating_icon = f" {'⭐' * s['rating']}" if s.get("rating") else ""
        date_str = s["closed_at"].split()[0] if s.get("closed_at") and " " in s["closed_at"] else (s.get("closed_at") or "")
        btn_text = f"#{s['ticket_id']} {s['customer_name'][:15]} | {date_str}{rating_icon}"
        buttons.append([
            InlineKeyboardButton(
                text=btn_text,
                callback_data=f"{prefix}_history_view:{s['session_id']}"
            )
        ])

    # Sahifalash (pagination) tugmalari
    total_pages = max(1, (total + per_page - 1) // per_page)
    nav_row = []
    if page > 0:
        nav_row.append(
            InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"{prefix}_history_page:{page - 1}")
        )
    nav_row.append(
        InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="noop")
    )
    if (page + 1) * per_page < total:
        nav_row.append(
            InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"{prefix}_history_page:{page + 1}")
        )
    if nav_row:
        buttons.append(nav_row)

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_history_back_keyboard(page: int, prefix: str = "admin", session_id: int = 0, media_count: int = 0) -> InlineKeyboardMarkup:
    """Suhbat tarixidan orqaga qaytish va medialarni yuklab olish tugmasi"""
    buttons = []
    if media_count > 0 and session_id > 0:
        buttons.append([
            InlineKeyboardButton(
                text=f"🎵 Fayl va audiolarni olish ({media_count} ta)",
                callback_data=f"{prefix}_history_media:{session_id}"
            )
        ])
    buttons.append([
        InlineKeyboardButton(
            text="⬅️ Ro'yxatga qaytish",
            callback_data=f"{prefix}_history_page:{page}"
        )
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)


# ================= OPERATOR KLAVIATURALARI =================

def get_operator_idle_keyboard(is_available: bool = True) -> ReplyKeyboardMarkup:
    """Operator suhbatda bo'lmagan paytdagi menyusi"""
    status_btn = (
        KeyboardButton(text="🔴 Oflayn (Tanaffus)") 
        if is_available else 
        KeyboardButton(text="🟢 Onlayn (Mijoz kutish)")
    )
    return ReplyKeyboardMarkup(
        keyboard=[
            [status_btn],
            [KeyboardButton(text="📊 Holatim"), KeyboardButton(text="👥 Kutayotganlar soni")]
        ],
        resize_keyboard=True
    )


def get_operator_active_keyboard() -> ReplyKeyboardMarkup:
    """Operator mijoz bilan faol suhbatda bo'lgan paytdagi klaviatura"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🛑 Suhbatni yakunlash")]
        ],
        resize_keyboard=True
    )


def get_accept_ticket_keyboard(ticket_id: int) -> InlineKeyboardMarkup:
    """Mijoz kelganda operatorlarga chiquvchi qabul qilish tugmasi"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📞 Qabul qilish (Accept)", 
                    callback_data=f"accept_ticket:{ticket_id}"
                )
            ]
        ]
    )


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
                KeyboardButton(text="➕ Operator taklif qilish (Invite)"),
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


def get_admin_operators_kick_keyboard(ops: list) -> InlineKeyboardMarkup:
    """Operatorlarni chiqarish uchun inline klaviatura"""
    buttons = []
    for op in ops:
        code_badge = f" [#{op['operator_code']}]" if op.get("operator_code") else ""
        btn_text = f"❌ Chiqarish: {op['full_name']}{code_badge}"
        buttons.append([InlineKeyboardButton(text=btn_text, callback_data=f"admin_ask_kick:{op['telegram_id']}")])
    buttons.append([InlineKeyboardButton(text="🔄 Yangilash", callback_data="admin_refresh:operators")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


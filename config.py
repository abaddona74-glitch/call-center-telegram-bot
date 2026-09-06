import os
from pathlib import Path
from dotenv import load_dotenv

# .env yuklash
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
COMPANY_NAME = os.getenv("COMPANY_NAME", "Call Center")
OPERATOR_SECRET_KEY = os.getenv("OPERATOR_SECRET_KEY", "operator123")
# Admin Telegram ID(lar)i - vergul bilan bir nechta kiritish mumkin (masalan: 123456,789012)
ADMIN_IDS_RAW = os.getenv("ADMIN_ID", "0")
ADMIN_IDS = [int(i.strip()) for i in ADMIN_IDS_RAW.split(",") if i.strip().isdigit()]

# Ma'lumotlar bazasi fayli
DB_PATH = BASE_DIR / "call_center.db"

# ================= SHABLON MATNLAR (TEMPLATES) =================

# 1. Mijoz navbatga kirgandagi xabar
QUEUE_WELCOME_TEMPLATE = (
    "Assalomu alaykum, <b>{customer_name}</b>!\n"
    "«{company_name}» call center xizmatiga xush kelibsiz.\n\n"
    "Sizga berilgan raqam: <b>Mijoz #{ticket_id}</b>\n"
    "Navbatdagi o'rningiz: <b>#{position}</b>\n\n"
    "Operatorlarimizdan biri tez orada siz bilan bog'lanadi. "
    "Murojaatingiz matnini shu yerga yozib qoldirishingiz mumkin."
)

# 2. Operator qabul qilgandagi salomlashuv shabloni
GREETING_TEMPLATE = (
    "Assalomu alaykum! Men «{company_name}» korxonasining operatori "
    "<b>{operator_name}</b> bo'laman. Sizga qanday yordam bera olaman?"
)

# 3. Suhbat yakunlangandagi xayrlashuv shabloni
FAREWELL_TEMPLATE = (
    "Xizmatingizdan mamnunmiz! Salomat bo'ling, kuniz xayrli o'tsin!\n"
    "«{company_name}» xizmatlaridan foydalanganingiz uchun rahmat."
)

# 4. Baholash taklifi
RATING_PROMPT = (
    "Iltimos, ko'rsatilgan xizmat sifatini <b>1 dan 5 gacha</b> bo'lgan shkala bo'yicha baholang:"
)


import aiosqlite
from typing import Optional, List, Dict, Any, Tuple
from config import DB_PATH


async def init_db():
    """Ma'lumotlar bazasini initsializatsiya qilish"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON;")
        
        # 1. Operatorlar jadvali
        await db.execute("""
            CREATE TABLE IF NOT EXISTS operators (
                telegram_id INTEGER PRIMARY KEY,
                full_name TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'offline', -- 'offline', 'available', 'busy'
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 2. Mijozlar navbati (Queue)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL,
                customer_name TEXT,
                status TEXT NOT NULL DEFAULT 'waiting', -- 'waiting', 'connected', 'closed'
                first_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 3. Faol muloqot sessiyalari (Sessions)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id INTEGER NOT NULL,
                customer_id INTEGER NOT NULL,
                operator_id INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'active', -- 'active', 'closed'
                rating INTEGER,                        -- 1 dan 5 gacha baho
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                closed_at TIMESTAMP,
                FOREIGN KEY (ticket_id) REFERENCES queue(id),
                FOREIGN KEY (operator_id) REFERENCES operators(telegram_id)
            )
        """)

        # 4. Operatorlarga yuborilgan bildirishnomalar (tugmani o'chirish/tahrirlash uchun)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS operator_notifications (
                ticket_id INTEGER NOT NULL,
                operator_id INTEGER NOT NULL,
                message_id INTEGER NOT NULL,
                PRIMARY KEY (ticket_id, operator_id)
            )
        """)

        # 5. Xabarlar tarixi (Chat History)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                sender_type TEXT NOT NULL,
                sender_id INTEGER NOT NULL,
                content_type TEXT DEFAULT 'text',
                text_content TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            )
        """)

        # operator_code ustuni mavjudligini ta'minlash
        try:
            await db.execute("ALTER TABLE operators ADD COLUMN operator_code TEXT DEFAULT '';")
        except Exception:
            pass

        # customer_username ustuni mavjudligini ta'minlash
        try:
            await db.execute("ALTER TABLE queue ADD COLUMN customer_username TEXT DEFAULT '';")
        except Exception:
            pass

        # file_id ustuni mavjudligini ta'minlash (audio, rasm, ovozli xabarlarni saqlash uchun)
        try:
            await db.execute("ALTER TABLE messages ADD COLUMN file_id TEXT DEFAULT '';")
        except Exception:
            pass

        # feedback_reason ustuni mavjudligini ta'minlash (salbiy baho sababini saqlash)
        try:
            await db.execute("ALTER TABLE sessions ADD COLUMN feedback_reason TEXT DEFAULT '';")
        except Exception:
            pass

        # 6. Sessiyadagi xabarlarni kuzatish (yakunlanganda tozalash uchun)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS session_chat_messages (
                session_id INTEGER NOT NULL,
                chat_id INTEGER NOT NULL,
                message_id INTEGER NOT NULL,
                PRIMARY KEY (session_id, chat_id, message_id)
            )
        """)

        # 7. Foydalanuvchi sozlamalari (tanlangan til)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_settings (
                user_id INTEGER PRIMARY KEY,
                language TEXT NOT NULL DEFAULT 'uz',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 8. Tahrirlangan (edited) xabarlarni sinxronlashtirish uchun bog'langan xabarlar jadvali
        await db.execute("""
            CREATE TABLE IF NOT EXISTS relayed_messages (
                session_id INTEGER NOT NULL,
                source_chat_id INTEGER NOT NULL,
                source_message_id INTEGER NOT NULL,
                target_chat_id INTEGER NOT NULL,
                target_message_id INTEGER NOT NULL,
                PRIMARY KEY (source_chat_id, source_message_id)
            )
        """)

        await db.commit()


# ================= OPERATOR FUNKSIYALARI =================

async def register_or_update_operator(telegram_id: int, full_name: str, operator_code: str = "") -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO operators (telegram_id, full_name, operator_code, status)
            VALUES (?, ?, ?, 'available')
            ON CONFLICT(telegram_id) DO UPDATE SET
                full_name = excluded.full_name,
                operator_code = CASE WHEN excluded.operator_code != '' THEN excluded.operator_code ELSE operators.operator_code END,
                status = 'available'
        """, (telegram_id, full_name, operator_code))
        # Agar bu foydalanuvchi avval mijoz sifatida navbatga kirgan bo'lsa, o'z navbatini yopamiz
        await db.execute("""
            UPDATE queue SET status = 'closed'
            WHERE customer_id = ? AND status = 'waiting'
        """, (telegram_id,))
        await db.commit()


async def get_operator(telegram_id: int) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM operators WHERE telegram_id = ?", (telegram_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def get_available_operators() -> List[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM operators WHERE status = 'available'") as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def set_operator_status(telegram_id: int, status: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE operators SET status = ? WHERE telegram_id = ?", (status, telegram_id))
        await db.commit()


async def remove_operator(telegram_id: int) -> bool:
    """Operatorni tizimdan o'chirish (unbind)"""
    async with aiosqlite.connect(DB_PATH) as db:
        # Agar faol sessiyasi bo'lsa, uni ham yopamiz
        await db.execute("""
            UPDATE sessions SET status = 'closed', closed_at = CURRENT_TIMESTAMP
            WHERE operator_id = ? AND status = 'active'
        """, (telegram_id,))
        cursor = await db.execute("DELETE FROM operators WHERE telegram_id = ?", (telegram_id,))
        await db.commit()
        return cursor.rowcount > 0


async def update_operator_name(telegram_id: int, full_name: str) -> None:
    """Operator ismini yangilash"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE operators SET full_name = ? WHERE telegram_id = ?", (full_name, telegram_id))
        await db.commit()


async def update_operator_code(telegram_id: int, operator_code: str) -> None:
    """Operator kodini yangilash"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE operators SET operator_code = ? WHERE telegram_id = ?", (operator_code, telegram_id))
        await db.commit()


# ================= NAVBAT (QUEUE) FUNKSIYALARI =================

async def add_to_queue(
    customer_id: int, 
    customer_name: str, 
    first_message: str = "", 
    customer_username: str = ""
) -> Tuple[int, int]:
    """
    Mijozni navbatga qo'shadi yoki mavjud navbatini qaytaradi.
    Qaytaradi: (ticket_id, queue_position)
    """
    clean_user = (customer_username or "").strip().replace("@", "")
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        # Avval kutayotgan navbati bormi tekshiramiz
        async with db.execute(
            "SELECT id FROM queue WHERE customer_id = ? AND status = 'waiting' ORDER BY id ASC LIMIT 1",
            (customer_id,)
        ) as cursor:
            existing = await cursor.fetchone()
            if existing:
                ticket_id = existing["id"]
                await db.execute(
                    "UPDATE queue SET customer_name = ?, customer_username = ? WHERE id = ?",
                    (customer_name, clean_user, ticket_id)
                )
                await db.commit()
            else:
                cursor_ins = await db.execute(
                    "INSERT INTO queue (customer_id, customer_name, customer_username, first_message) VALUES (?, ?, ?, ?)",
                    (customer_id, customer_name, clean_user, first_message)
                )
                await db.commit()
                ticket_id = cursor_ins.lastrowid

        # Navbatdagi o'rnini hisoblash
        async with db.execute(
            "SELECT COUNT(*) as pos FROM queue WHERE status = 'waiting' AND id <= ?",
            (ticket_id,)
        ) as cursor:
            pos_row = await cursor.fetchone()
            position = pos_row["pos"] if pos_row else 1

        return ticket_id, position


async def get_queue_position(customer_id: int) -> Optional[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id FROM queue WHERE customer_id = ? AND status = 'waiting' LIMIT 1",
            (customer_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None
            ticket_id = row["id"]

        async with db.execute(
            "SELECT COUNT(*) as pos FROM queue WHERE status = 'waiting' AND id <= ?",
            (ticket_id,)
        ) as cursor:
            pos_row = await cursor.fetchone()
            return pos_row["pos"] if pos_row else 1


async def get_queue_eta_info(customer_id: int) -> Optional[Dict[str, Any]]:
    """
    Mijoz uchun navbatdagi o'rni va taxminiy kutish vaqtini (ETA) hisoblash.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        # 1. Mijozning navbatdagi ticketini topish
        async with db.execute(
            "SELECT id FROM queue WHERE customer_id = ? AND status = 'waiting' LIMIT 1",
            (customer_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None
            ticket_id = row["id"]

        # 2. O'rni va oldingi odamlar soni
        async with db.execute(
            "SELECT COUNT(*) as pos FROM queue WHERE status = 'waiting' AND id <= ?",
            (ticket_id,)
        ) as cursor:
            pos_row = await cursor.fetchone()
            position = pos_row["pos"] if pos_row else 1

        ahead_count = max(0, position - 1)

        # 3. Onlayn va bo'sh operatorlar soni
        async with db.execute(
            "SELECT COUNT(*) as c FROM operators WHERE status IN ('available', 'busy')"
        ) as cursor:
            online_ops = (await cursor.fetchone())["c"]

        async with db.execute(
            "SELECT COUNT(*) as c FROM operators WHERE status = 'available'"
        ) as cursor:
            available_ops = (await cursor.fetchone())["c"]

        # 4. Taxminiy vaqtni (daqiqa) hisoblash
        # O'rtacha 1 ta suhbat: ~3-4 daqiqa
        if online_ops > 0:
            est_minutes = max(1, int(round((ahead_count / online_ops) * 3)))
            est_max = est_minutes + 2
        else:
            est_minutes = 0
            est_max = 0

        return {
            "ticket_id": ticket_id,
            "position": position,
            "ahead_count": ahead_count,
            "online_operators": online_ops,
            "available_operators": available_ops,
            "est_minutes": est_minutes,
            "est_max": est_max
        }


async def get_next_waiting_ticket() -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM queue WHERE status = 'waiting' ORDER BY id ASC LIMIT 1"
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def get_ticket_by_id(ticket_id: int) -> Optional[Dict[str, Any]]:
    """Ticket ma'lumotlarini id bo'yicha olish"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM queue WHERE id = ?", (ticket_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


# ================= SESSIYA VA CLAIM (RACE-CONDITION XAVFSIZLIGI) =================

async def claim_ticket(ticket_id: int, operator_id: int) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Operator ticketni qabul qiladi.
    Atomic operatsiya: agar ticket hali ham 'waiting' bo'lsa, 'connected' qilinadi
    va sessiya yaratiladi. Aks holda False qaytadi.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("BEGIN IMMEDIATE;")
        
        # 1. Ticketni tekshirish
        async with db.execute(
            "SELECT * FROM queue WHERE id = ? AND status = 'waiting'",
            (ticket_id,)
        ) as cursor:
            ticket = await cursor.fetchone()
            if not ticket:
                await db.rollback()
                return False, None

        # 2. Operator o'z-o'zini qabul qila olmaydi
        if ticket["customer_id"] == operator_id:
            await db.rollback()
            return False, None

        # 3. Operator boshqa aktiv sessiyada emasmi?
        async with db.execute(
            "SELECT id FROM sessions WHERE operator_id = ? AND status = 'active'",
            (operator_id,)
        ) as cursor:
            active_op = await cursor.fetchone()
            if active_op:
                await db.rollback()
                return False, None

        # 3. Statuslarni o'zgartirish
        await db.execute("UPDATE queue SET status = 'connected' WHERE id = ?", (ticket_id,))
        await db.execute("UPDATE operators SET status = 'busy' WHERE telegram_id = ?", (operator_id,))
        
        # 4. Yangi sessiya ochish
        cur = await db.execute(
            "INSERT INTO sessions (ticket_id, customer_id, operator_id, status) VALUES (?, ?, ?, 'active')",
            (ticket_id, ticket["customer_id"], operator_id)
        )
        session_id = cur.lastrowid
        if ticket["first_message"]:
            await db.execute("""
                INSERT INTO messages (session_id, sender_type, sender_id, content_type, text_content)
                VALUES (?, 'customer', ?, 'text', ?)
            """, (session_id, ticket["customer_id"], ticket["first_message"]))
        await db.commit()
        return True, dict(ticket)


async def get_active_session_by_operator(operator_id: int) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT s.*, q.customer_name, q.customer_username 
            FROM sessions s
            JOIN queue q ON s.ticket_id = q.id
            WHERE s.operator_id = ? AND s.status = 'active'
            LIMIT 1
        """, (operator_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def get_active_session_by_customer(customer_id: int) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT s.*, o.full_name as operator_name 
            FROM sessions s
            JOIN operators o ON s.operator_id = o.telegram_id
            WHERE s.customer_id = ? AND s.status = 'active'
            LIMIT 1
        """, (customer_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def close_session_by_operator(operator_id: int) -> Optional[Dict[str, Any]]:
    """
    Operator tomonidan sessiyani yakunlash.
    Operator holatini 'available' ga qaytaradi.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM sessions WHERE operator_id = ? AND status = 'active' LIMIT 1",
            (operator_id,)
        ) as cursor:
            session = await cursor.fetchone()
            if not session:
                return None
            session_dict = dict(session)

        # Sessiyani va navbatni yopish
        await db.execute(
            "UPDATE sessions SET status = 'closed', closed_at = CURRENT_TIMESTAMP WHERE id = ?",
            (session_dict["id"],)
        )
        await db.execute(
            "UPDATE queue SET status = 'closed' WHERE id = ?",
            (session_dict["ticket_id"],)
        )
        # Operatorni yana bo'shatish
        await db.execute(
            "UPDATE operators SET status = 'available' WHERE telegram_id = ?",
            (operator_id,)
        )
        await db.commit()
        return session_dict


async def close_session_by_customer(customer_id: int) -> Optional[Dict[str, Any]]:
    """Mijoz tomonidan sessiyani yakunlash (agar kerak bo'lsa)"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM sessions WHERE customer_id = ? AND status = 'active' LIMIT 1",
            (customer_id,)
        ) as cursor:
            session = await cursor.fetchone()
            if not session:
                return None
            session_dict = dict(session)

        await db.execute(
            "UPDATE sessions SET status = 'closed', closed_at = CURRENT_TIMESTAMP WHERE id = ?",
            (session_dict["id"],)
        )
        await db.execute(
            "UPDATE queue SET status = 'closed' WHERE id = ?",
            (session_dict["ticket_id"],)
        )
        await db.execute(
            "UPDATE operators SET status = 'available' WHERE telegram_id = ?",
            (session_dict["operator_id"],)
        )
        await db.commit()
        return session_dict


async def close_session_by_ticket_id(ticket_id: int) -> Optional[Dict[str, Any]]:
    """Admin tomonidan ticket bo'yicha sessiyani majburiy yakunlash"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM sessions WHERE ticket_id = ? AND status = 'active' LIMIT 1",
            (ticket_id,)
        ) as cursor:
            session = await cursor.fetchone()
            if not session:
                return None
            session_dict = dict(session)

        await db.execute(
            "UPDATE sessions SET status = 'closed', closed_at = CURRENT_TIMESTAMP WHERE id = ?",
            (session_dict["id"],)
        )
        await db.execute(
            "UPDATE queue SET status = 'closed' WHERE id = ?",
            (ticket_id,)
        )
        await db.execute(
            "UPDATE operators SET status = 'available' WHERE telegram_id = ?",
            (session_dict["operator_id"],)
        )
        await db.commit()
        return session_dict


async def get_expired_active_sessions(timeout_hours: float = 1.0) -> List[Dict[str, Any]]:
    """Maksimal vaqtidan (masalan, 1 soat) oshib ketgan faol sessiyalarni topish"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT s.*, q.customer_name, o.full_name as operator_name
            FROM sessions s
            JOIN queue q ON s.ticket_id = q.id
            JOIN operators o ON s.operator_id = o.telegram_id
            WHERE s.status = 'active'
              AND (julianday('now') - julianday(s.started_at)) * 24 >= ?
        """, (timeout_hours,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]




# ================= BILDIRISHNOMALAR (NOTIFICATIONS) =================

async def save_notification(ticket_id: int, operator_id: int, message_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT OR REPLACE INTO operator_notifications (ticket_id, operator_id, message_id)
            VALUES (?, ?, ?)
        """, (ticket_id, operator_id, message_id))
        await db.commit()


async def get_notifications(ticket_id: int) -> List[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM operator_notifications WHERE ticket_id = ?",
            (ticket_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


# ================= ADMIN VA MONITORING FUNKSIYALARI =================

async def save_session_rating(ticket_id: int, rating: int):
    """Mijoz bergan bahoni sessiyaga saqlash"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE sessions SET rating = ? WHERE ticket_id = ?",
            (rating, ticket_id)
        )
        await db.commit()


async def save_session_feedback(ticket_id: int, reason: str):
    """Mijoz bergan salbiy baho sababini saqlash"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE sessions SET feedback_reason = ? WHERE ticket_id = ?",
            (reason, ticket_id)
        )
        await db.commit()


async def get_live_dashboard() -> Dict[str, Any]:
    """Jonli admin monitoringi: navbat, faol muloqotlar, operatorlar holati"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        # 1. Navbatda kutayotganlar soni
        async with db.execute("SELECT COUNT(*) as c FROM queue WHERE status = 'waiting'") as cur:
            waiting_count = (await cur.fetchone())["c"]

        # 2. Faol muloqotlar soni
        async with db.execute("SELECT COUNT(*) as c FROM sessions WHERE status = 'active'") as cur:
            active_dialogs_count = (await cur.fetchone())["c"]

        # 3. Operatorlar statistikasi holat bo'yicha
        async with db.execute("SELECT status, COUNT(*) as c FROM operators GROUP BY status") as cur:
            rows = await cur.fetchall()
            op_stats = {r["status"]: r["c"] for r in rows}

        # 4. Bugun yopilgan jami murojaatlar soni va o'rtacha baho
        async with db.execute("""
            SELECT COUNT(*) as closed_count, AVG(rating) as avg_rate 
            FROM sessions 
            WHERE status = 'closed' AND date(closed_at) = date('now')
        """) as cur:
            today_row = await cur.fetchone()
            today_closed = today_row["closed_count"] or 0
            avg_rating = round(today_row["avg_rate"], 1) if today_row["avg_rate"] else None

        return {
            "waiting_count": waiting_count,
            "active_dialogs_count": active_dialogs_count,
            "available_ops": op_stats.get("available", 0),
            "busy_ops": op_stats.get("busy", 0),
            "offline_ops": op_stats.get("offline", 0),
            "today_closed": today_closed,
            "avg_rating": avg_rating
        }


async def get_waiting_customers_list() -> List[Dict[str, Any]]:
    """Hozir navbatda kutayotgan barcha mijozlar ro'yxati"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT id, customer_id, customer_name, first_message, created_at 
            FROM queue 
            WHERE status = 'waiting' 
            ORDER BY id ASC
        """) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def get_active_dialogs_list() -> List[Dict[str, Any]]:
    """Hozir qaysi operator qaysi mijoz bilan gaplashmoqda"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT 
                s.id as session_id,
                s.ticket_id,
                s.started_at,
                q.customer_name,
                q.customer_username,
                q.customer_id,
                o.full_name as operator_name,
                o.telegram_id as operator_id
            FROM sessions s
            JOIN queue q ON s.ticket_id = q.id
            JOIN operators o ON s.operator_id = o.telegram_id
            WHERE s.status = 'active'
            ORDER BY s.started_at ASC
        """) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def get_operators_performance() -> List[Dict[str, Any]]:
    """Har bir operatorning umumiy va bugungi faoliyati"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT 
                o.telegram_id,
                o.full_name,
                o.operator_code,
                o.status,
                COUNT(s.id) as total_served,
                AVG(s.rating) as avg_rating
            FROM operators o
            LEFT JOIN sessions s ON o.telegram_id = s.operator_id AND s.status = 'closed'
            GROUP BY o.telegram_id, o.full_name, o.operator_code, o.status
            ORDER BY total_served DESC
        """) as cur:
            return [dict(r) for r in await cur.fetchall()]


# ================= SUHBAT TARIXI (CHAT HISTORY) FUNKSIYALARI =================

async def save_message(
    session_id: int,
    sender_type: str,
    sender_id: int,
    content_type: str = "text",
    text_content: str = "",
    file_id: str = ""
) -> None:
    """Suhbat xabarini (matn va fayl ID si bilan) bazaga saqlash"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO messages (session_id, sender_type, sender_id, content_type, text_content, file_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (session_id, sender_type, sender_id, content_type, text_content, file_id))
        await db.commit()


async def get_session_media_messages(session_id: int) -> List[Dict[str, Any]]:
    """Sessiyadagi barcha yuklangan media (audio, ovoz, rasm, video, hujjat) xabarlarini olish"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT * FROM messages
            WHERE session_id = ? AND file_id != '' AND file_id IS NOT NULL
            ORDER BY created_at ASC
        """, (session_id,)) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def track_session_message(session_id: int, chat_id: int, message_id: int) -> None:
    """Sessiyaga tegishli xabar ID sini saqlash (suhbat yakunlanganda tozalash uchun)"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT OR IGNORE INTO session_chat_messages (session_id, chat_id, message_id)
            VALUES (?, ?, ?)
        """, (session_id, chat_id, message_id))
        await db.commit()


async def get_session_message_ids_for_chat(session_id: int, chat_id: int) -> List[int]:
    """Sessiya tugaganda o'chirish uchun xabar ID larini olish"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("""
            SELECT message_id FROM session_chat_messages
            WHERE session_id = ? AND chat_id = ?
            ORDER BY message_id ASC
        """, (session_id, chat_id)) as cur:
            rows = await cur.fetchall()
            return [r[0] for r in rows]


async def clear_session_chat_messages(session_id: int) -> None:
    """Sessiya tozalanib bo'lingach yozuvlarni o'chirish"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM session_chat_messages WHERE session_id = ?", (session_id,))
        await db.commit()


async def get_session_messages(session_id: int) -> List[Dict[str, Any]]:
    """Bitta suhbatdagi barcha xabarlarni olish"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT * FROM messages
            WHERE session_id = ?
            ORDER BY created_at ASC
        """, (session_id,)) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def get_session_by_id(session_id: int) -> Optional[Dict[str, Any]]:
    """Sessiya ma'lumotlarini olish (operator va mijoz nomlari bilan)"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT 
                s.id as session_id,
                s.ticket_id,
                s.customer_id,
                s.operator_id,
                s.status,
                s.rating,
                s.feedback_reason,
                s.started_at,
                s.closed_at,
                q.customer_name,
                q.customer_username,
                o.full_name as operator_name,
                o.operator_code
            FROM sessions s
            JOIN queue q ON s.ticket_id = q.id
            LEFT JOIN operators o ON s.operator_id = o.telegram_id
            WHERE s.id = ?
        """, (session_id,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def get_closed_sessions_list(
    limit: int = 20, offset: int = 0, operator_id: Optional[int] = None
) -> Tuple[List[Dict[str, Any]], int]:
    """Admin uchun barcha (yoki tanlangan operator bo'yicha) yopilgan suhbatlar ro'yxati (paginated)"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        if operator_id:
            # Muayyan operator bo'yicha
            async with db.execute(
                "SELECT COUNT(*) as c FROM sessions WHERE status = 'closed' AND operator_id = ?",
                (operator_id,)
            ) as cur:
                total = (await cur.fetchone())["c"]

            async with db.execute("""
                SELECT 
                    s.id as session_id,
                    s.ticket_id,
                    s.customer_id,
                    s.rating,
                    s.feedback_reason,
                    s.started_at,
                    s.closed_at,
                    q.customer_name,
                    q.customer_username,
                    o.full_name as operator_name,
                    o.operator_code
                FROM sessions s
                JOIN queue q ON s.ticket_id = q.id
                LEFT JOIN operators o ON s.operator_id = o.telegram_id
                WHERE s.status = 'closed' AND s.operator_id = ?
                ORDER BY s.closed_at DESC
                LIMIT ? OFFSET ?
            """, (operator_id, limit, offset)) as cur:
                rows = [dict(r) for r in await cur.fetchall()]
        else:
            # Barcha operatorlar bo'yicha
            async with db.execute("SELECT COUNT(*) as c FROM sessions WHERE status = 'closed'") as cur:
                total = (await cur.fetchone())["c"]

            async with db.execute("""
                SELECT 
                    s.id as session_id,
                    s.ticket_id,
                    s.customer_id,
                    s.rating,
                    s.feedback_reason,
                    s.started_at,
                    s.closed_at,
                    q.customer_name,
                    q.customer_username,
                    o.full_name as operator_name,
                    o.operator_code
                FROM sessions s
                JOIN queue q ON s.ticket_id = q.id
                LEFT JOIN operators o ON s.operator_id = o.telegram_id
                WHERE s.status = 'closed'
                ORDER BY s.closed_at DESC
                LIMIT ? OFFSET ?
            """, (limit, offset)) as cur:
                rows = [dict(r) for r in await cur.fetchall()]

        return rows, total


async def get_operators_history_stats() -> List[Dict[str, Any]]:
    """Admin uchun barcha operatorlar va ularning yopilgan suhbatlar soni"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT 
                o.telegram_id,
                o.full_name,
                o.operator_code,
                COUNT(s.id) as closed_count
            FROM operators o
            LEFT JOIN sessions s ON o.telegram_id = s.operator_id AND s.status = 'closed'
            GROUP BY o.telegram_id, o.full_name, o.operator_code
            ORDER BY closed_count DESC, o.full_name ASC
        """) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def search_operators(query: str) -> List[Dict[str, Any]]:
    """Ism yoki kod bo'yicha operatorlarni qidirish (suhbatlar soni bilan)"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        clean_q = f"%{query.strip().lower()}%"
        async with db.execute("""
            SELECT 
                o.telegram_id,
                o.full_name,
                o.operator_code,
                COUNT(s.id) as closed_count
            FROM operators o
            LEFT JOIN sessions s ON o.telegram_id = s.operator_id AND s.status = 'closed'
            WHERE LOWER(o.full_name) LIKE ? OR LOWER(o.operator_code) LIKE ?
            GROUP BY o.telegram_id, o.full_name, o.operator_code
            ORDER BY closed_count DESC, o.full_name ASC
        """, (clean_q, clean_q)) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def get_operator_sessions(
    operator_id: int, limit: int = 20, offset: int = 0
) -> Tuple[List[Dict[str, Any]], int]:
    """Operator uchun o'z suhbatlari ro'yxati (paginated)"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        # Jami sonini olish
        async with db.execute(
            "SELECT COUNT(*) as c FROM sessions WHERE operator_id = ? AND status = 'closed'",
            (operator_id,)
        ) as cur:
            total = (await cur.fetchone())["c"]

        async with db.execute("""
            SELECT 
                s.id as session_id,
                s.ticket_id,
                s.customer_id,
                s.rating,
                s.feedback_reason,
                s.started_at,
                s.closed_at,
                q.customer_name,
                q.customer_username
            FROM sessions s
            JOIN queue q ON s.ticket_id = q.id
            WHERE s.operator_id = ? AND s.status = 'closed'
            ORDER BY s.closed_at DESC
            LIMIT ? OFFSET ?
        """, (operator_id, limit, offset)) as cur:
            rows = [dict(r) for r in await cur.fetchall()]

        return rows, total


# ================= FOYDALANUVCHI SOZLAMALARI (TIL) =================

async def get_user_language(user_id: int) -> str:
    """Foydalanuvchi tanlagan tilni olish (sukut bo'yicha 'uz')"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT language FROM user_settings WHERE user_id = ?", (user_id,)) as cur:
            row = await cur.fetchone()
            if row and row["language"]:
                return row["language"]
            return "uz"


async def set_user_language(user_id: int, language: str) -> None:
    """Foydalanuvchi tilini saqlash yoki yangilash"""
    lang = language.lower().strip()
    if lang not in ["uz", "ru"]:
        lang = "uz"
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO user_settings (user_id, language, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                language = excluded.language,
                updated_at = CURRENT_TIMESTAMP
        """, (user_id, lang))
        await db.commit()


async def has_user_selected_language(user_id: int) -> bool:
    """Foydalanuvchi avval til tanlagan yoki yo'qligini tekshirish"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT 1 FROM user_settings WHERE user_id = ?", (user_id,)) as cur:
            return (await cur.fetchone()) is not None


# ================= BOG'LANGAN XABARLAR (TAHRIRLASH UCHUN) =================

async def save_relayed_message(
    session_id: int, 
    source_chat_id: int, 
    source_message_id: int, 
    target_chat_id: int, 
    target_message_id: int
) -> None:
    """Yuborilgan xabarni va uning ikkinchi tomonga yetkazilgan nusxasi ID sini saqlash"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO relayed_messages (session_id, source_chat_id, source_message_id, target_chat_id, target_message_id)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(source_chat_id, source_message_id) DO UPDATE SET
                target_chat_id = excluded.target_chat_id,
                target_message_id = excluded.target_message_id
        """, (session_id, source_chat_id, source_message_id, target_chat_id, target_message_id))
        await db.commit()


async def get_relayed_message(source_chat_id: int, source_message_id: int) -> Optional[Dict[str, Any]]:
    """Tahrirlanayotgan xabarga mos ikkinchi tomondagi xabarni topish"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT session_id, target_chat_id, target_message_id
            FROM relayed_messages
            WHERE source_chat_id = ? AND source_message_id = ?
        """, (source_chat_id, source_message_id)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


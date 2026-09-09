"""
Ko'p tillilik (Lokalizatsiya) moduli: O'zbek va Rus tillari
"""

TEXTS = {
    "uz": {
        "choose_lang": "🇺🇿 Iltimos, muloqot tilini tanlang:\n🇷🇺 Пожалуйста, выберите язык обслуживания:",
        "lang_selected": "🇺🇿 O'zbek tili tanlandi.",
        "welcome_caption": (
            "👋 <b>Assalomu alaykum, {name}!</b>\n\n"
            "«{company}» yagona aloqa markaziga xush kelibsiz.\n\n"
            "📌 <b>Quyidagi tizimlar bo'yicha texnik yordam ko'rsatamiz:</b>\n"
            "• <b>e-huquqshunos</b> — yuridik xizmat tizimi\n"
            "• <b>edo.ijro.uz</b> — elektron hujjat aylanish tizimi\n"
            "• <b>Shartnoma masalalari</b> — hududlar bo'yicha kontaktlar\n\n"
            "Sizga qanday yordam bera olamiz? Iltimos, kerakli bo'limni tanlang:"
        ),
        "btn_e_huquqshunos": "e-huquqshunos",
        "btn_edo": "edo.ijro.uz",
        "btn_contracts": "Shartnoma masalasida",
        "btn_change_lang": "🌐 Tilni o'zgartirish",
        "btn_check_queue": "ℹ️ Navbatimni tekshirish",
        "btn_leave_queue": "❌ Navbatdan chiqish",
        "btn_end_chat": "❌ Suhbatni yakunlash",
        "btn_back_main": "🔙 Asosiy menyu",
        "btn_other_region": "⬅️ Boshqa hududni tanlash",
        "btn_connect_operator": "👨‍💼 Operator bilan bog'lanish",
        "btn_tg_contact": "💬 Telegram orqali bog'lanish ({tg})",
        "queue_accepted": "⏳ Sizning {subj}murojaatingiz qabul qilindi.\n\n",
        "queue_all_offline": (
            "🔴 <b>Hozirda barcha operatorlarimiz tanaffusda.</b>\n"
            "Murojaatingiz navbatga yozildi. Operatorlarimiz ishga qaytishi bilanoq sizga ulanamiz.\n\n"
            "<i>Iltimos, kuting...</i>"
        ),
        "queue_routed": (
            "🟢 <b>Murojaatingiz operatorga yo'naltirildi.</b>\n"
            "<i>Iltimos, aloqada qoling, operatorlarimiz tez orada siz bilan bog'lanishadi.</i>"
        ),
        "queue_busy": (
            "🟡 <b>Hozirda operatorlarimiz mijozlar bilan muloqotda.</b>\n"
            "⏱ <b>Taxminiy kutish vaqti:</b> ~{est_min}–{est_max} daqiqa\n"
            "{ahead_text}\n"
            "<i>Iltimos, aloqada qoling, bo'shagan operatorimiz tez orada sizga ulanadi.</i>"
        ),
        "queue_ahead_count": "👥 <b>Sizdan oldingi murojaatlar:</b> {ahead} ta",
        "queue_status_title": "📍 <b>Murojaatingiz holati:</b>\n\n{status_desc}\n\n<i>Iltimos, operator bog'lanishini kuting.</i>",
        "queue_already_waiting": (
            "📍 Siz allaqachon navbatdasiz.\n"
            "⏱ <b>Taxminiy kutish vaqti:</b> ~{est_min}–{est_max} daqiqa (oldinda {ahead} ta murojaat).\n\n"
            "Iltimos, operator bog'lanishini kuting."
        ),
        "queue_cancelled": "✅ Siz navbatdan muvaffaqiyatli chiqdingiz.\n\nYangi murojaat uchun bo'limni tanlang:",
        "not_in_queue": "Siz hozirda navbatda emassiz. Yangi murojaat boshlash uchun bo'limni tanlang:",
        "in_active_chat": "⚠️ Siz hozirda operator <b>{operator_name}</b> bilan jonli muloqotdasiz.\n\nSuhbatni yakunlash uchun pastdagi <b>«❌ Suhbatni yakunlash»</b> tugmasini bosing:",
        "chat_connected": "✅ Operator <b>{operator_name}</b> suhbatga ulandi!\nSavollaringizni to'g'ridan-to'g'ri yozishingiz mumkin.",
        "chat_ended_by_user": "✅ Suhbat yakunlandi. Xizmatimizdan foydalanganingiz uchun rahmat!\n\nIltimos, ko'rsatilgan xizmat sifatini baholang:",
        "chat_ended_by_op": "ℹ️ Operator suhbatni yakunladi. Xizmatimizdan foydalanganingiz uchun rahmat!\n\nIltimos, operator xizmatini baholang:",
        "rating_thanks": "Rahmat! Sizning bahongiz qabul qilindi: {stars}",
        "rating_low_ask": "Keltirilgan noqulaylik uchun uzr so'raymiz! 🙏\nXizmatimizni yaxshilashimiz uchun nima sababdan past baho qo'yganingizni belgilab bera olasizmi?",
        "feedback_reasons": {
            "wait": "⏱ Uzoq kutdim",
            "no_solution": "🤷‍♂️ Yechim berilmadi",
            "bad_attitude": "😠 Operator muomalasi",
            "technical": "📉 Texnik nosozlik",
            "custom": "✍️ Boshqa sabab (matn yozish)",
            "skip": "➡️ O'tkazib yuborish"
        },
        "custom_reason_prompt": "Iltimos, nima sizga ma'qul kelmaganini yozib qoldiring:",
        "feedback_saved": "Fikringiz uchun katta rahmat! Biz xizmat sifatini albatta yaxshilaymiz. 🤝",
        "feedback_skipped": "Tushundik. Murojaatingiz uchun rahmat!",
        "regions_title": "📋 <b>Shartnoma masalasida hududiy mas'ullar kontaktlari:</b>\n\nO'zingizga tegishli viloyat yoki shaharni tanlang:",
        "region_card": (
            "📝 Shartnoma masalasida — {region_name}\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "Tegishli mas'ul mutaxassislar bilan bog'lanish uchun:\n\n"
            "📞 Aloqa telefonlari:\n{phones}\n\n"
            "{tg_text}\n"
            "──────────────────────\n"
            "💡 Shuningdek, kerak bo'lsa operator bilan ham bog'lanishingiz mumkin."
        ),
        "tg_label": "💬 Telegram: {tg}",
    },
    "ru": {
        "choose_lang": "🇺🇿 Iltimos, muloqot tilini tanlang:\n🇷🇺 Пожалуйста, выберите язык обслуживания:",
        "lang_selected": "🇷🇺 Выбран русский язык.",
        "welcome_caption": (
            "👋 <b>Здравствуйте, {name}!</b>\n\n"
            "Добро пожаловать в единый контакт-центр «{company}».\n\n"
            "📌 <b>Мы оказываем техническую поддержку по следующим системам:</b>\n"
            "• <b>e-huquqshunos</b> — система юридических услуг\n"
            "• <b>edo.ijro.uz</b> — система электронного документооборота\n"
            "• <b>Вопросы по договорам</b> — контакты по регионам\n\n"
            "Чем мы можем вам помочь? Пожалуйста, выберите нужный раздел:"
        ),
        "btn_e_huquqshunos": "e-huquqshunos",
        "btn_edo": "edo.ijro.uz",
        "btn_contracts": "По вопросам договоров",
        "btn_change_lang": "🌐 Сменить язык",
        "btn_check_queue": "ℹ️ Проверить очередь",
        "btn_leave_queue": "❌ Выйти из очереди",
        "btn_end_chat": "❌ Завершить диалог",
        "btn_back_main": "🔙 Главное меню",
        "btn_other_region": "⬅️ Выбрать другой регион",
        "btn_connect_operator": "👨‍💼 Связаться с оператором",
        "btn_tg_contact": "💬 Связаться через Telegram ({tg})",
        "queue_accepted": "⏳ Ваше обращение{subj} принято.\n\n",
        "queue_all_offline": (
            "🔴 <b>В настоящее время все операторы на перерыве.</b>\n"
            "Ваше обращение добавлено в очередь. Как только операторы вернутся, мы сразу свяжемся с вами.\n\n"
            "<i>Пожалуйста, подождите...</i>"
        ),
        "queue_routed": (
            "🟢 <b>Ваше обращение направлено оператору.</b>\n"
            "<i>Пожалуйста, оставайтесь на связи, наши операторы скоро свяжутся с вами.</i>"
        ),
        "queue_busy": (
            "🟡 <b>Сейчас операторы ведут диалог с другими клиентами.</b>\n"
            "⏱ <b>Примерное время ожидания:</b> ~{est_min}–{est_max} мин.\n"
            "{ahead_text}\n"
            "<i>Пожалуйста, оставайтесь на связи, освободившийся оператор скоро подключится.</i>"
        ),
        "queue_ahead_count": "👥 <b>Перед вами обращений:</b> {ahead} шт.",
        "queue_status_title": "📍 <b>Статус вашего обращения:</b>\n\n{status_desc}\n\n<i>Пожалуйста, ожидайте ответа оператора.</i>",
        "queue_already_waiting": (
            "📍 Вы уже находитесь в очереди.\n"
            "⏱ <b>Примерное время ожидания:</b> ~{est_min}–{est_max} мин. (перед вами {ahead} обращений).\n\n"
            "Пожалуйста, ожидайте ответа оператора."
        ),
        "queue_cancelled": "✅ Вы успешно вышли из очереди.\n\nДля нового обращения выберите раздел:",
        "not_in_queue": "Сейчас вы не находитесь в очереди. Для нового обращения выберите раздел:",
        "in_active_chat": "⚠️ Сейчас вы находитесь в активном диалоге с оператором <b>{operator_name}</b>.\n\nЧтобы завершить диалог, нажмите <b>«❌ Завершить диалог»</b> ниже:",
        "chat_connected": "✅ Оператор <b>{operator_name}</b> подключился к диалогу!\nВы можете написать ваш вопрос.",
        "chat_ended_by_user": "✅ Диалог завершен. Спасибо за обращение!\n\nПожалуйста, оцените качество обслуживания:",
        "chat_ended_by_op": "ℹ️ Оператор завершил диалог. Спасибо за обращение!\n\nПожалуйста, оцените работу оператора:",
        "rating_thanks": "Спасибо! Ваша оценка принята: {stars}",
        "rating_low_ask": "Приносим извинения за неудобства! 🙏\nПожалуйста, укажите причину низкой оценки, чтобы мы могли улучшить наш сервис:",
        "feedback_reasons": {
            "wait": "⏱ Долго ждал(а)",
            "no_solution": "🤷‍♂️ Вопрос не решен",
            "bad_attitude": "😠 Грубость оператора",
            "technical": "📉 Технический сбой",
            "custom": "✍️ Другая причина (текст)",
            "skip": "➡️ Пропустить"
        },
        "custom_reason_prompt": "Пожалуйста, напишите, что именно вам не понравилось:",
        "feedback_saved": "Большое спасибо за ваш отзыв! Мы обязательно улучшим качество обслуживания. 🤝",
        "feedback_skipped": "Понятно. Спасибо за обращение!",
        "regions_title": "📋 <b>Контакты региональных специалистов по договорам:</b>\n\nВыберите ваш регион или город:",
        "region_card": (
            "📝 По вопросам договоров — {region_name}\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "Для связи с ответственным специалистом:\n\n"
            "📞 Контактные телефоны:\n{phones}\n\n"
            "{tg_text}\n"
            "──────────────────────\n"
            "💡 Вы также можете связаться с нашим оператором поддержки."
        ),
        "tg_label": "💬 Telegram: {tg}",
    }
}


def t(key: str, lang: str = "uz", **kwargs) -> str:
    """Berilgan kalit va til bo'yicha matnni olish"""
    current_lang = "ru" if lang == "ru" else "uz"
    text_val = TEXTS.get(current_lang, {}).get(key)
    if text_val is None:
        text_val = TEXTS.get("uz", {}).get(key, key)
    if isinstance(text_val, str) and kwargs:
        return text_val.format(**kwargs)
    return text_val


def get_reason_text(reason_key: str, lang: str = "uz") -> str:
    """Baho sababi matnini olish"""
    current_lang = "ru" if lang == "ru" else "uz"
    reasons = TEXTS.get(current_lang, {}).get("feedback_reasons", {})
    return reasons.get(reason_key, TEXTS["uz"]["feedback_reasons"].get(reason_key, reason_key))

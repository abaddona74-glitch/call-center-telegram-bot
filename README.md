# Call Center Operator Relay Telegram Bot

Mijozlar va Call Center operatorlari o'rtasida Telegram orqali jonli, navbatli (FIFO queue) va shaxsiy shablon asosidagi muloqotni tashkil qiluvchi bot.

---

## 🌟 Asosiy Xususiyatlar

1. **Operatorlarni ulash (Binding)**:
   - Operator o'z Telegram akkauntidan: `/operator <parol> <Ism>` deb yozadi.
   - Masalan: `/operator operator123 Azizbek`
   - Shu tariqa bot operatorni taniydi va unga boshqaruv menyusini beradi.

2. **Mijozlar Navbati (Queue)**:
   - Mijoz `/start` bosganda unga navbat raqami beriladi: `Mijoz #1`, `Mijoz #2`...
   - Mijoz o'zining navbatdagi o'rnini bilib turadi.

3. **Birinchi bosgan qabul qiladi (Accept / Race-condition himoyasi)**:
   - Yangi mijoz kelganda barcha bo'sh operatorlarga `[ 📞 Qabul qilish (Accept) ]` tugmasi chiqadi.
   - Birinchi bosgan operator mijoz bilan ulanadi.
   - Qolgan barcha operatorlarda tugma darhol `✅ Operator [Ism] qabul qildi` ga o'zgaradi.

4. **Shablon asosida tanishtiruv**:
   - Operator mijozni qabul qilishi bilan mijozga avtomatik salomlashuv yuboriladi:
     > *"Assalomu alaykum! Men «Biznes Xizmat» korxonasining operatori <b>Azizbek</b> bo'laman. Sizga qanday yordam bera olaman?"*

5. **P2P Relay (Ikki tomonlama jonli chat)**:
   - Operator yozgan xabarlar mijozga boradi.
   - Mijoz yozgan barcha xabarlar (matn, ovozli xabar (voice), rasm, video, fayl) operatorga yetkaziladi.

6. **Suhbatni yakunlash (End Chat)**:
   - Operator `[ 🛑 Suhbatni yakunlash ]` tugmasini yoki `/end` komandasini bosadi.
   - Sessiya yopiladi, mijozga baholash tugmalari yuboriladi, operator yana navbatdagi mijozni qabul qilishga tayyor bo'ladi.

---

## 🚀 O'rnatish va Ishga tushirish

### 1. Bog'liqliklarni o'rnatish
```bash
pip install -r requirements.txt
```

### 2. Sozlamalarni kiritish (.env)
`.env` faylini oching va quyidagi parametrlarni o'zingizga moslang:
```env
BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRstuVWxYz
COMPANY_NAME=Biznes Xizmat
OPERATOR_SECRET_KEY=operator123
```
- `BOT_TOKEN`: [@BotFather](https://t.me/BotFather) dan olingan token.
- `COMPANY_NAME`: Kompaniyangiz yoki xizmatingiz nomi.
- `OPERATOR_SECRET_KEY`: Operatorlar ulanishi uchun maxfiy parol.

### 3. Botni ishga tushirish
```bash
python main.py
```

---

## 📋 Operatorlar uchun qo'llanma

1. Botga kiring va `/operator operator123 SizningIsmingiz` deb yozing.
2. Bot sizni operator sifatida qabul qiladi.
3. Yangi mijoz kelganda `📞 Qabul qilish` tugmasi chiqadi.
4. Suhbat yakunlangach `🛑 Suhbatni yakunlash` tugmasini bosing.
5. Tanaffusga chiqmoqchi bo'lsangiz `🔴 Oflayn (Tanaffus)` tugmasini bosing.

---

## 👑 Admin Boshqaruv Paneli (Supervisor)

Admin Telegram ID egasi botda `/admin` komandasini yuborganda to'liq boshqaruv paneli ochiladi:

1. **📊 Jonli monitoring (Live Dashboard)**:
   - Hozir navbatda nechta mijoz kutmoqda
   - Ayni paytda nechta faol muloqot davom etyapti
   - Onlayn, band va oflayn operatorlar soni
   - Bugun yopilgan jami murojaatlar va o'rtacha xizmat reytingi (⭐ 1-5).
2. **📞 Faol muloqotlar**:
   - Ayni paytda qaysi operator qaysi mijoz bilan gaplashayotgani (boshlangan vaqti bilan).
3. **👥 Navbatdagilar ro'yxati**:
   - Navbatda kutayotgan barcha mijozlar (Ismi, dastlabki savoli, kirgan vaqti).
4. **👨‍💼 Operatorlar holati va natijalari**:
   - Har bir operatorning statusi, jami xizmat ko'rsatgan mijozlari soni va shaxsiy o'rtacha reytingi.


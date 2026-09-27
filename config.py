"""
Kartinka Home bot — sozlamalar.
Narx, matn, avans — hammasini shu fayldan o'zgartirasiz. Kodga tegmang.
"""
import os

# ---------- Maxfiy ma'lumotlar (Railway → Variables bo'limida kiritiladi) ----------
BOT_TOKEN = os.getenv("BOT_TOKEN", "")                  # @BotFather bergan token
# Buyurtmalar keladigan joy(lar): shaxsiy chat ID va/yoki guruh ID, vergul bilan. Masalan: "123456789,987654321"
# ID ni bilish uchun botga /id deb yozing.
MANAGER_IDS = [int(x) for x in os.getenv("MANAGER_CHAT_ID", "").replace(" ", "").split(",") if x]
CARD_NUMBER = os.getenv("CARD_NUMBER", "9860 1601 0505 9747")
CARD_OWNER = os.getenv("CARD_OWNER", "Bekzodjon Ramazanov")
SHEET_WEBHOOK_URL = os.getenv("SHEET_WEBHOOK_URL", "")  # Google Apps Script havolasi (Sarhisob'ga yozish)

# ---------- Biznes sozlamalari ----------
AVANS = 100_000  # so'm, qat'iy

# O'lcham → narx (so'm)
PRICES = {
    "120x80": 690_000,
    "150x90": 990_000,
}

FON_RANGLARI = ["Qora", "Oq"]

# Katalog: mavzu nomi → rasmlar (media/ papkadagi fayl nomlari). Rasm bo'lmasa — shunchaki o'tkazib yuboriladi.
# Bitta mavzu bo'lsa — bot mavzu so'ramasdan to'g'ridan-to'g'ri rasmlarni ko'rsatadi.
CATALOG = {
    "🕌 Islomiy kartina (3 qismli komplekt)": ["islomiy_qora.jpg", "islomiy_oq.jpg"],
}

TAYYOR_BOLISH_MUDDATI = "3–5 ish kuni"

VILOYATLAR = [
    "Toshkent sh.", "Toshkent vil.", "Samarqand", "Farg'ona", "Andijon", "Namangan",
    "Buxoro", "Navoiy", "Qashqadaryo", "Surxondaryo", "Jizzax", "Sirdaryo",
    "Xorazm", "Qoraqalpog'iston",
]

# Eslatmalar: mijoz jarayonni tashlab ketsa (soat, matn)
ESLATMALAR = [
    (1, "Assalomu alaykum 😊 Kartinangiz tanlovini yakunlamadingiz. Davom ettiramizmi? Savol bo'lsa — menejer yordam beradi."),
    (24, "Kecha ko'rgan kartinangiz hali ham sizni kutyapti 🖼 Buyurtmani 2 daqiqada yakunlash mumkin — pastdagi tugmani bosing."),
]

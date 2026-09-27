"""
Kartinka Home — Telegram avto-voronka.
Yo'l: salom → katalog → mavzu → fon → o'lcham → narx → ism/telefon/manzil →
avans (kartaga o'tkazma + chek) → menejer tasdiqlaydi → Sarhisob'ga yoziladi.
"""
import asyncio
import json
import logging
import os
import sqlite3
import time
from datetime import datetime, timedelta, timezone

import aiohttp
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (CallbackQuery, FSInputFile, InlineKeyboardButton,
                           InlineKeyboardMarkup, InputMediaPhoto, KeyboardButton,
                           Message, ReplyKeyboardMarkup, ReplyKeyboardRemove)

import config as C

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("kartinka")
router = Router()
TZ = timezone(timedelta(hours=5))  # Toshkent
MEDIA = os.path.join(os.path.dirname(__file__), "media")


def som(x: int) -> str:
    return f"{x:,}".replace(",", " ") + " so'm"


# ------------------------------------------------------------------ DB
db = sqlite3.connect(os.getenv("DB_PATH", "bot.db"))
db.execute("""CREATE TABLE IF NOT EXISTS leads(
    user_id INTEGER PRIMARY KEY, username TEXT, source TEXT, step TEXT,
    last_ts REAL, reminded INTEGER DEFAULT 0, done INTEGER DEFAULT 0)""")
db.execute("""CREATE TABLE IF NOT EXISTS orders(
    id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, data TEXT,
    status TEXT, created REAL)""")
db.commit()


def touch(user_id, step, username=None, source=None, done=0):
    row = db.execute("SELECT source FROM leads WHERE user_id=?", (user_id,)).fetchone()
    if row is None:
        db.execute("INSERT INTO leads(user_id,username,source,step,last_ts,done) VALUES(?,?,?,?,?,?)",
                   (user_id, username, source or "", step, time.time(), done))
    else:
        db.execute("UPDATE leads SET step=?, last_ts=?, reminded=0, done=?"
                   + (", source=?" if source else "") + " WHERE user_id=?",
                   (step, time.time(), done, *( [source] if source else [] ), user_id))
    db.commit()


# ------------------------------------------------------------------ States
class S(StatesGroup):
    mavzu = State()
    fon = State()
    olcham = State()
    tasdiq = State()
    ism = State()
    telefon = State()
    viloyat = State()
    manzil = State()
    chek = State()


def kb(rows):
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=t, callback_data=d) for t, d in r] for r in rows])


MENEJER_BTN = ("💬 Menejer bilan gaplashish", "menejer")


# ------------------------------------------------------------------ Start
@router.message(CommandStart())
async def start(m: Message, state: FSMContext, command: CommandObject):
    await state.clear()
    source = command.args or "organic"  # reklama havolasi: t.me/BOT?start=fb_video2
    await state.update_data(source=source)
    touch(m.from_user.id, "start", m.from_user.username, source)
    await m.answer(
        f"Assalomu alaykum, {m.from_user.first_name}! 👋\n\n"
        "<b>Kartinka Home</b> — uyingiz uchun metall devor kartinalari.\n"
        "✅ O'zbekiston bo'ylab yetkazib beramiz\n"
        f"✅ Tayyor bo'lish muddati: {C.TAYYOR_BOLISH_MUDDATI}\n"
        f"✅ Oldindan atigi {som(C.AVANS)}, qolgani — qabul qilganda\n\n"
        + ("Qaysi mavzudagi kartinani ko'rmoqchisiz? 👇" if len(C.CATALOG) > 1 else "Mana bizning kartinalarimiz 👇"),
        reply_markup=kb([[(name, f"mavzu:{i}")] for i, name in enumerate(C.CATALOG)] + [[MENEJER_BTN]]) if len(C.CATALOG) > 1 else None,
    )
    if len(C.CATALOG) == 1:
        await show_mavzu(m, state, list(C.CATALOG)[0], m.from_user.id)
    else:
        await state.set_state(S.mavzu)


@router.callback_query(F.data.startswith("mavzu:"))
async def mavzu(c: CallbackQuery, state: FSMContext):
    await show_mavzu(c.message, state, list(C.CATALOG)[int(c.data.split(":")[1])], c.from_user.id)
    await c.answer()


async def show_mavzu(msg: Message, state: FSMContext, name: str, user_id: int):
    await state.update_data(mavzu=name)
    touch(user_id, "mavzu")
    photos = [p for p in C.CATALOG[name] if os.path.exists(os.path.join(MEDIA, p))]
    if len(photos) == 1:
        await msg.answer_photo(FSInputFile(os.path.join(MEDIA, photos[0])))
    elif photos:
        await msg.answer_media_group([InputMediaPhoto(media=FSInputFile(os.path.join(MEDIA, p))) for p in photos[:10]])
    await msg.answer("Qaysi fon rangi yoqdi? 👇",
                     reply_markup=kb([[(f"{'⚫' if f == 'Qora' else '⚪'} {f} fon", f"fon:{f}") for f in C.FON_RANGLARI], [MENEJER_BTN]]))
    await state.set_state(S.fon)


@router.callback_query(F.data.startswith("fon:"))
async def fon(c: CallbackQuery, state: FSMContext):
    await state.update_data(fon=c.data.split(":", 1)[1])
    touch(c.from_user.id, "fon")
    rows = [[(f"{s} sm — {som(p)}", f"size:{s}")] for s, p in C.PRICES.items()]
    rows.append([("📐 Boshqa o'lcham kerak", "menejer")])
    await c.message.answer("O'lchamni tanlang (eni x bo'yi):", reply_markup=kb(rows))
    await state.set_state(S.olcham)
    await c.answer()


@router.callback_query(F.data.startswith("size:"))
async def olcham(c: CallbackQuery, state: FSMContext):
    size = c.data.split(":", 1)[1]
    price = C.PRICES[size]
    await state.update_data(size=size, price=price)
    d = await state.get_data()
    touch(c.from_user.id, "narx")
    await c.message.answer(
        f"Ajoyib tanlov! 🔥\n\n"
        f"🖼 {d['mavzu']}\n🎨 Fon: {d['fon']}\n📐 O'lcham: {size} sm\n"
        f"💰 Narxi: <b>{som(price)}</b>\n\n"
        f"Oldindan to'lov: <b>{som(C.AVANS)}</b>\nQolgani ({som(price - C.AVANS)}) — kartinani qabul qilganda.\n\n"
        "Buyurtma beramizmi?",
        reply_markup=kb([[("✅ Ha, buyurtma beraman", "order")], [MENEJER_BTN]]),
    )
    await state.set_state(S.tasdiq)
    await c.answer()


@router.callback_query(F.data == "order")
async def order(c: CallbackQuery, state: FSMContext):
    touch(c.from_user.id, "ism")
    await c.message.answer("Ismingizni yozing:")
    await state.set_state(S.ism)
    await c.answer()


@router.message(S.ism, F.text)
async def ism(m: Message, state: FSMContext):
    await state.update_data(ism=m.text.strip()[:60])
    touch(m.from_user.id, "telefon")
    await m.answer("Telefon raqamingizni yuboring 👇",
                   reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="📱 Raqamni yuborish", request_contact=True)]],
                                                    resize_keyboard=True, one_time_keyboard=True))
    await state.set_state(S.telefon)


@router.message(S.telefon)
async def telefon(m: Message, state: FSMContext):
    phone = m.contact.phone_number if m.contact else (m.text or "").strip()
    if len("".join(ch for ch in phone if ch.isdigit())) < 9:
        return await m.answer("Iltimos, to'g'ri raqam yuboring (masalan: 90 123 45 67).")
    await state.update_data(telefon=phone)
    touch(m.from_user.id, "viloyat")
    await m.answer("Rahmat! ✅", reply_markup=ReplyKeyboardRemove())
    rows, row = [], []
    for i, v in enumerate(C.VILOYATLAR):
        row.append((v, f"vil:{i}"))
        if len(row) == 2:
            rows.append(row); row = []
    if row:
        rows.append(row)
    await m.answer("Qaysi viloyatga yetkazib beramiz?", reply_markup=kb(rows))
    await state.set_state(S.viloyat)


@router.callback_query(F.data.startswith("vil:"))
async def viloyat(c: CallbackQuery, state: FSMContext):
    await state.update_data(viloyat=C.VILOYATLAR[int(c.data.split(":")[1])])
    touch(c.from_user.id, "manzil")
    await c.message.answer("Tuman / shahar va aniq manzil (yoki BTS pochta filiali) ni yozing:")
    await state.set_state(S.manzil)
    await c.answer()


@router.message(S.manzil, F.text)
async def manzil(m: Message, state: FSMContext):
    await state.update_data(manzil=m.text.strip()[:200])
    d = await state.get_data()
    touch(m.from_user.id, "chek")
    await m.answer(
        "📋 <b>Buyurtmangiz:</b>\n"
        f"👤 {d['ism']}, {d['telefon']}\n📍 {d['viloyat']}, {d['manzil']}\n"
        f"🖼 {d['mavzu']} · {d['fon']} fon · {d['size']} sm\n"
        f"💰 Jami: {som(d['price'])}\n\n"
        f"Buyurtmani tasdiqlash uchun <b>{som(C.AVANS)}</b> oldindan to'lov qiling:\n\n"
        f"💳 <code>{C.CARD_NUMBER}</code>\n👤 {C.CARD_OWNER}\n\n"
        "To'lovdan so'ng <b>chek rasmini (skrinshot)</b> shu yerga yuboring 👇",
        reply_markup=kb([[MENEJER_BTN]]),
    )
    await state.set_state(S.chek)


@router.message(S.chek, F.photo | F.document)
async def chek(m: Message, state: FSMContext, bot: Bot):
    d = await state.get_data()
    cur = db.execute("INSERT INTO orders(user_id,data,status,created) VALUES(?,?,?,?)",
                     (m.from_user.id, json.dumps(d, ensure_ascii=False), "kutilmoqda", time.time()))
    db.commit()
    oid = cur.lastrowid
    touch(m.from_user.id, "chek_yuborildi", done=1)
    await m.answer("Rahmat! 🙏 Chekingiz tekshirilmoqda. Tez orada tasdiqlaymiz.")
    await state.clear()
    if C.MANAGER_IDS:
        uname = f"@{m.from_user.username}" if m.from_user.username else f"id {m.from_user.id}"
        caption = (f"🆕 <b>Buyurtma #{oid}</b> (avans cheki)\n"
                   f"👤 {d['ism']} · {d['telefon']} · {uname}\n📍 {d['viloyat']}, {d['manzil']}\n"
                   f"🖼 {d['mavzu']} · {d['fon']} · {d['size']}\n💰 {som(d['price'])} · avans {som(C.AVANS)}\n"
                   f"📣 Manba: {d.get('source', '')}")
        markup = kb([[("✅ Tasdiqlash", f"ok:{oid}"), ("❌ Rad etish", f"no:{oid}")]])
        for mid in C.MANAGER_IDS:
            try:
                if m.photo:
                    await bot.send_photo(mid, m.photo[-1].file_id, caption=caption, reply_markup=markup)
                else:
                    await bot.send_document(mid, m.document.file_id, caption=caption, reply_markup=markup)
            except Exception as e:
                log.warning("manager %s: %s", mid, e)


@router.message(S.chek)
async def chek_wrong(m: Message):
    await m.answer("Iltimos, to'lov chekini <b>rasm</b> ko'rinishida yuboring 📸")


# ------------------------------------------------------------------ Menejer
@router.callback_query(F.data == "menejer")
async def menejer(c: CallbackQuery, state: FSMContext, bot: Bot):
    d = await state.get_data()
    touch(c.from_user.id, "menejer", done=1)
    await c.message.answer("Menejerimiz tez orada sizga yozadi 😊\nSavolingizni shu yerga yozib qoldirishingiz mumkin.")
    u = c.from_user
    for mid in C.MANAGER_IDS:
        try:
            await bot.send_message(mid,
                               f"🙋 <b>Mijoz menejer so'radi</b>\n{u.full_name} · "
                               f"{'@' + u.username if u.username else 'id ' + str(u.id)}\n"
                               f"Bosqich: {d.get('mavzu', '-')} / {d.get('fon', '-')} / {d.get('size', '-')}\n"
                               f"Manba: {d.get('source', '')}\n"
                               f"<a href='tg://user?id={u.id}'>Profilni ochish</a>")
        except Exception as e:
            log.warning("manager %s: %s", mid, e)
    await c.answer()


@router.callback_query(F.data.regexp(r"^(ok|no):\d+$"))
async def manager_decision(c: CallbackQuery, bot: Bot):
    act, oid = c.data.split(":")
    row = db.execute("SELECT user_id,data,status FROM orders WHERE id=?", (int(oid),)).fetchone()
    if not row:
        return await c.answer("Buyurtma topilmadi", show_alert=True)
    if row[2] != "kutilmoqda":
        return await c.answer(f"Allaqachon: {row[2]}", show_alert=True)
    user_id, d = row[0], json.loads(row[1])
    who = c.from_user.first_name
    if act == "ok":
        db.execute("UPDATE orders SET status='tasdiqlandi' WHERE id=?", (int(oid),)); db.commit()
        await bot.send_message(user_id,
                               f"✅ To'lov qabul qilindi! Buyurtmangiz #{oid} ishlab chiqarishga berildi.\n"
                               f"Tayyor bo'lish muddati: {C.TAYYOR_BOLISH_MUDDATI}. Jo'natganimizda xabar beramiz 🚚")
        ok = await write_sheet(d)
        note = "📄 Sarhisob'ga yozildi" if ok else "⚠️ Sarhisob'ga yozilmadi — qo'lda kiriting"
        await c.message.edit_caption(caption=(c.message.caption or "") + f"\n\n✅ Tasdiqladi: {who}\n{note}")
    else:
        db.execute("UPDATE orders SET status='rad etildi' WHERE id=?", (int(oid),)); db.commit()
        await bot.send_message(user_id, "❗ To'lov tasdiqlanmadi. Iltimos, chekni qayta tekshiring yoki menejer bilan bog'laning.",
                               reply_markup=kb([[MENEJER_BTN]]))
        await c.message.edit_caption(caption=(c.message.caption or "") + f"\n\n❌ Rad etdi: {who}")
    await c.answer()


async def write_sheet(d) -> bool:
    if not C.SHEET_WEBHOOK_URL:
        return False
    payload = {
        "ism": d["ism"], "telefon": d["telefon"],
        "sana": datetime.now(TZ).strftime("%Y-%m-%d"),
        "manager": "Bot", "fon": d["fon"], "razmer": d["size"],
        "jami": d["price"], "tolangan": C.AVANS, "qoldiq": d["price"] - C.AVANS,
        "manzil": f"{d['viloyat']}, {d['manzil']}",
        "izoh": f"Telegram bot · {d['mavzu']} · manba: {d.get('source', '')}",
    }
    try:
        async with aiohttp.ClientSession() as s:
            async with s.post(C.SHEET_WEBHOOK_URL, json=payload, timeout=aiohttp.ClientTimeout(total=20)) as r:
                return r.status == 200 and "ok" in (await r.text())
    except Exception as e:
        log.warning("sheet error: %s", e)
        return False


@router.message(Command("id"))
async def chat_id(m: Message):
    await m.answer(f"Chat ID: <code>{m.chat.id}</code>")


@router.message(Command("stat"))
async def stat(m: Message):
    if m.chat.id not in C.MANAGER_IDS:
        return
    since = time.time() - 86400
    q = lambda sql: db.execute(sql, (since,)).fetchone()[0]
    kirdi = q("SELECT COUNT(*) FROM leads WHERE last_ts>?")
    chek_n = q("SELECT COUNT(*) FROM orders WHERE created>?")
    ok_n = q("SELECT COUNT(*) FROM orders WHERE created>? AND status='tasdiqlandi'")
    await m.answer(f"📊 Oxirgi 24 soat:\nBotga kirdi: {kirdi}\nChek yubordi: {chek_n}\nTasdiqlandi: {ok_n}")


@router.callback_query(F.data == "davom")
async def davom(c: CallbackQuery, state: FSMContext):
    if len(C.CATALOG) == 1:
        await show_mavzu(c.message, state, list(C.CATALOG)[0], c.from_user.id)
    else:
        await c.message.answer("Qaysi mavzudagi kartinani ko'rmoqchisiz? 👇",
                               reply_markup=kb([[(n, f"mavzu:{i}")] for i, n in enumerate(C.CATALOG)] + [[MENEJER_BTN]]))
        await state.set_state(S.mavzu)
    await c.answer()


# ------------------------------------------------------------------ Eslatmalar
async def reminder_loop(bot: Bot):
    while True:
        try:
            now = time.time()
            for idx, (hours, text) in enumerate(C.ESLATMALAR):
                rows = db.execute("SELECT user_id FROM leads WHERE done=0 AND reminded=? AND last_ts<?",
                                  (idx, now - hours * 3600)).fetchall()
                for (uid,) in rows:
                    try:
                        await bot.send_message(uid, text, reply_markup=kb([[("▶️ Davom etish", "davom")], [MENEJER_BTN]]))
                    except Exception:
                        pass
                    db.execute("UPDATE leads SET reminded=? WHERE user_id=?", (idx + 1, uid))
            db.commit()
        except Exception as e:
            log.warning("reminder error: %s", e)
        await asyncio.sleep(300)


async def main():
    from aiogram.client.default import DefaultBotProperties
    bot = Bot(C.BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    dp = Dispatcher()
    dp.include_router(router)
    asyncio.create_task(reminder_loop(bot))
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

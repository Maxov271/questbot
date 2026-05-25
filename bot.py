import telebot
from telebot import types
import sqlite3
import threading
import schedule
import time
import logging
from datetime import datetime, date

# ==================== SOZLAMALAR ====================
BOT_TOKEN = "8648316530:AAGpUDwPvSWNazeelITOg95gM3CPxFIlz7E"
LEADER_ID = 8623551943  # O'zingizning Telegram ID ingiz
BOT_USERNAME = "Abduaziz_offbot"
# ==================== LOGGING ====================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ==================== BOT ====================
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

# ==================== FSM (dict orqali) ====================
user_states = {}
user_data_store = {}

def set_state(user_id, state):
    user_states[user_id] = state

def get_state(user_id):
    return user_states.get(user_id)

def clear_state(user_id):
    user_states.pop(user_id, None)
    user_data_store.pop(user_id, None)

def update_data(user_id, key, value):
    if user_id not in user_data_store:
        user_data_store[user_id] = {}
    user_data_store[user_id][key] = value

def get_data(user_id):
    return user_data_store.get(user_id, {})
import sqlite3


# ==================== DATABASE ====================
def get_conn():
    return sqlite3.connect("bot.db", check_same_thread=False)

def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        telegram_id INTEGER UNIQUE,
        full_name TEXT,
        phone TEXT,
        score INTEGER DEFAULT 0,
        total_answers INTEGER DEFAULT 0,
        correct_answers INTEGER DEFAULT 0,
        registered_at TEXT,
        last_active TEXT,
        referal_code INTEGER
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS admins (
        id INTEGER PRIMARY KEY,
        telegram_id INTEGER UNIQUE,
        added_at TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS channels (
        id INTEGER PRIMARY KEY,
        channel_username TEXT UNIQUE,
        channel_title TEXT,
        added_at TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS questions (
        id INTEGER PRIMARY KEY,
        question_text TEXT,
        option_a TEXT,
        option_b TEXT,
        option_c TEXT,
        option_d TEXT,
        correct_answer TEXT,
        added_at TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS answers (
        id INTEGER PRIMARY KEY,
        user_id INTEGER,
        question_id INTEGER,
        is_correct INTEGER,
        answered_at TEXT,
        UNIQUE(user_id, question_id)
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS daily_stats (
        id INTEGER PRIMARY KEY,
        stat_date TEXT UNIQUE,
        sent_at TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS referal (
    user_id INTEGER,
    referal_id INTEGER)""")
    conn.commit()
    conn.close()
    logger.info("Database tayyor.")

# ==================== YORDAMCHI FUNKSIYALAR ====================
def is_leader(user_id):
    return int(user_id) == int(LEADER_ID)

def is_admin(user_id):
    if is_leader(user_id):
        return True
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT 1 FROM admins WHERE telegram_id=?", (user_id,))
    res = c.fetchone()
    conn.close()
    return res is not None

def is_registered(user_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT 1 FROM users WHERE telegram_id=?", (user_id,))
    res = c.fetchone()
    conn.close()
    return res is not None

def check_subscription(user_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT channel_username FROM channels")
    channels = c.fetchall()
    conn.close()
    not_sub = []
    for (ch,) in channels:
        try:
            member = bot.get_chat_member(ch, user_id)
            if member.status in ["left", "kicked"]:
                not_sub.append(ch)
        except Exception as e:
            logger.warning(f"Kanal xatosi {ch}: {e}")
            notify_channel_error(ch)
    return not_sub

def notify_channel_error(channel):
    msg = f"⚠️ <b>Diqqat!</b>\nBot <b>{channel}</b> kanalida admin emas yoki kanal topilmadi!\nBotni kanalga admin qiling."
    try:
        bot.send_message(LEADER_ID, msg)
    except:
        pass
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT telegram_id FROM admins")
    for (aid,) in c.fetchall():
        try:
            bot.send_message(aid, msg)
        except:
            pass
    conn.close()

def sub_keyboard(not_sub):
    kb = types.InlineKeyboardMarkup(row_width=1)
    for ch in not_sub:
        kb.add(types.InlineKeyboardButton(f"📢 {ch} — Obuna bo'lish", url=f"https://t.me/{ch.lstrip('@')}"))
    kb.add(types.InlineKeyboardButton("✅ Tekshirish", callback_data="check_sub"))
    return kb

def main_menu(user_id):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("🧠 Savol hal qilish", "🏆 Reyting")
    if is_admin(user_id):
        kb.row("📊 Statistika (Admin)", "⚙️ Boshqaruv")
    else:
        kb.row("📈 Mening natijam")
    return kb

def  referal(user_id,referal_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
    INSERT INTO referal (user_id, referal_id) VALUES (?,?)
    """, (user_id, referal_id))
    conn.commit()
    conn.close()
# ==================== /start ====================
@bot.message_handler(commands=['start'])
def cmd_start(message):
    args = message.text.split()

    if len(args) >1:
        referal_id = args[1]

        if referal_id != str(message.from_user.id):
            referal(message.from_user.id,referal_id)
    uid = message.from_user.id
    clear_state(uid)
    not_sub = check_subscription(uid)



    if not_sub:
        bot.send_message(uid, "📢 <b>Botdan foydalanish uchun kanallarga obuna bo'ling:</b>",
                         reply_markup=sub_keyboard(not_sub))
        return
    if is_registered(uid):
        bot.send_message(uid, f"👋 Xush kelibsiz, <b>{message.from_user.first_name}</b>!\n\nMenyu:",
                         reply_markup=main_menu(uid))
        return
    bot.send_message(uid, "👋 <b>Xush kelibsiz!</b>\n\n📝 Ism va familiyangizni kiriting:",
                     reply_markup=types.ReplyKeyboardRemove())
    set_state(uid, "reg_name")


@bot.message_handler(commands=['referal'])
def postreferal(message):


    markup = types.InlineKeyboardMarkup()

    btn = types.InlineKeyboardButton(
        text="📎 Referal linkimni olish",
        callback_data="get_ref"
    )

    markup.add(btn)

    bot.send_message(
        chat_id=message.chat.id,
        text="👇 Referal linkingizni olish uchun tugmani bosing:",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda c: c.data == "check_sub")
def cb_check_sub(call):
    uid = call.from_user.id
    not_sub = check_subscription(uid)
    if not_sub:
        bot.answer_callback_query(call.id, "❌ Hali obuna bo'lmadingiz!", show_alert=True)
        try:
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id,
                                          reply_markup=sub_keyboard(not_sub))
        except:
            pass
    else:
        bot.delete_message(call.message.chat.id, call.message.message_id)
        if is_registered(uid):
            bot.send_message(uid, "✅ Tasdiqlandi!", reply_markup=main_menu(uid))
        else:
            bot.send_message(uid, "✅ Tasdiqlandi!\n\n📝 Ism va familiyangizni kiriting:",
                             reply_markup=types.ReplyKeyboardRemove())
            set_state(uid, "reg_name")

# ==================== RO'YXATDAN O'TISH ====================
@bot.message_handler(func=lambda m: get_state(m.from_user.id) == "reg_name")
def reg_name(message):
    uid = message.from_user.id
    update_data(uid, "full_name", message.text)
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.add(types.KeyboardButton("📱 Raqamni ulashish", request_contact=True))
    bot.send_message(uid, "📱 Telefon raqamingizni yuboring:", reply_markup=kb)
    set_state(uid, "reg_phone")

@bot.message_handler(content_types=['contact'], func=lambda m: get_state(m.from_user.id) == "reg_phone")
def reg_phone(message):
    uid = message.from_user.id
    data = get_data(uid)
    phone = message.contact.phone_number
    name = data.get("full_name", message.from_user.first_name)
    now = datetime.now().isoformat()
    conn = get_conn()
    c = conn.cursor()

    c.execute("INSERT OR IGNORE INTO users (telegram_id, full_name, phone, registered_at, last_active) VALUES (?,?,?,?,?)",
              (uid, name, phone, now, now))
    c.execute("SELECT * FROM referal WHERE user_id = ?",(uid,))
    referaluid = c.fetchone()
    c.execute("SELECT referal_code FROM users WHERE telegram_id=?", (uid,))
    referalcode = c.fetchone()
    if referalcode:
        referalcode = referalcode[0]
    try:

        if referalcode==None:

            if referaluid !=None:
                c.execute("""UPDATE users SET referal_code = ? WHERE telegram_id = ?""",(referaluid[1],uid))
                c.execute("UPDATE users SET score=score+300 WHERE telegram_id=?", (referaluid[1],))
                c.execute("SELECT referal_code FROM users WHERE telegram_id=?", (referaluid[1],))

                referal_code = c.fetchone()
                if referal_code:
                    referal_code = referal_code[0]
                    if referal_code is not None:
                        c.execute("""
                                    UPDATE users 
                                    SET score = score + 30
                                    WHERE telegram_id = ?
                                """, (referal_code,))
                        c.execute("SELECT full_name FROM users WHERE telegram_id = ?", (referaluid[1],))
                        foolname = c.fetchone()
                        bot.send_message(referal_code,f"siz taklif qilgan {foolname[0].title()} foydalanuvchisi botga {name.title()} ni taklif qildi va sizga +30 bal olib keldi 🎉")
                        c.execute("SELECT referal_code FROM users WHERE telegram_id = ?",(referal_code,))
                        referal_3 = c.fetchone()
                        if referal_3 is not None:
                            referal_3 = referal_3[0]
                            c.execute("""
                                            UPDATE users 
                                            SET score = score + 10
                                            WHERE telegram_id = ?
                                        """, (referal_3,))
                            c.execute("SELECT full_name FROM users WHERE telegram_id = ?", (referal_code,))
                            foolname1 = c.fetchone()
                            bot.send_message(referal_3,
                                             f"siz taklif qilgan {foolname1[0].title()} taklif qilgan {foolname[0].title()} foydalanuvchisi botga {name.title()} ni taklif qildi va sizga +10 bal olib keldi 🎉")


                bot.send_message(referaluid[1],f"siz {name.title()} ni taklif qilganingiz uchun <b>+300 ball  bal qo'lga kiritgingiz va sizni taklif qilgan odam 30 balni qo'lga kiritdi</b> 🎉")

    except:
        bot.send_message(LEADER_ID, f"XATOLIK",)
    conn.commit()
    conn.close()
    clear_state(uid)
    bot.send_message(uid, f"✅ <b>Ro'yxatdan o'tdingiz!</b>\n\n👤 {name}\n📱 {phone}",
                     reply_markup=main_menu(uid))

@bot.message_handler(func=lambda m: get_state(m.from_user.id) == "reg_phone")
def reg_phone_text(message):
    bot.send_message(message.from_user.id, "📱 Tugmani bosib raqamni yuboring.")

# ==================== SAVOL HAL QILISH ====================
def send_question_to(uid, edit_msg=None):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""SELECT * FROM questions WHERE id NOT IN
                 (SELECT question_id FROM answers WHERE user_id=?)
                 ORDER BY RANDOM() LIMIT 1""", (uid,))
    q = c.fetchone()
    conn.close()
    if not q:
        text = "🎉 Barcha savollarni hal qildingiz! Yangi savollar qo'shilishini kuting."
        if edit_msg:
            try:
                bot.edit_message_text(text, edit_msg.chat.id, edit_msg.message_id)
            except:
                bot.send_message(uid, text)
        else:
            bot.send_message(uid, text)
        return
    q_id, q_text, a, b, c_opt, d, correct, _ = q
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(
        types.InlineKeyboardButton(f"A) {a}", callback_data=f"ans_{q_id}_A"),
        types.InlineKeyboardButton(f"B) {b}", callback_data=f"ans_{q_id}_B"),
        types.InlineKeyboardButton(f"C) {c_opt}", callback_data=f"ans_{q_id}_C"),
        types.InlineKeyboardButton(f"D) {d}", callback_data=f"ans_{q_id}_D"),
    )
    text = f"❓ <b>Savol #{q_id}:</b>\n\n{q_text}"
    if edit_msg:
        try:
            bot.edit_message_text(text, edit_msg.chat.id, edit_msg.message_id, reply_markup=kb)
        except:
            bot.send_message(uid, text, reply_markup=kb)
    else:
        bot.send_message(uid, text, reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == "🧠 Savol hal qilish")
def solve_question(message):
    uid = message.from_user.id
    if not is_registered(uid):
        bot.send_message(uid, "❌ Avval ro'yxatdan o'ting! /start")
        return
    send_question_to(uid)

@bot.callback_query_handler(func=lambda c: c.data.startswith("ans_"))
def handle_answer(call):
    uid = call.from_user.id
    _, q_id, chosen = call.data.split("_")
    q_id = int(q_id)
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT correct_answer, option_a, option_b, option_c, option_d  FROM questions WHERE id=?", (q_id,))#referal_code
    row = c.fetchone()
    c.execute("SELECT referal_code FROM users WHERE telegram_id=?",(uid,))
    referal_code = c.fetchone()[0]

    if not row:
        conn.close()
        bot.answer_callback_query(call.id, "Savol topilmadi!", show_alert=True)
        return
    correct, a, b, c_opt, d = row
    opts = {"A": a, "B": b, "C": c_opt, "D": d}
    is_correct = 1 if chosen == correct else 0
    now = datetime.now().isoformat()
    try:
        c.execute("""
            INSERT INTO answers (user_id, question_id, is_correct, answered_at)
            VALUES (?,?,?,?)
        """, (uid, q_id, is_correct, now))

        # users update har doim ishlashi kerak
        if is_correct:
            c.execute("""
                UPDATE users 
                SET score = score + 10,
                    correct_answers = correct_answers + 1,
                    total_answers = total_answers + 1,
                    last_active = ?
                WHERE telegram_id = ?
            """, (now, uid))
            if referal_code is not None:
                c.execute("""
                            UPDATE users 
                            SET score = score + 1
                            WHERE telegram_id = ?
                        """, (referal_code,))
        else:
            c.execute("""
                UPDATE users 
                SET total_answers = total_answers + 1,
                    last_active = ?
                WHERE telegram_id = ?
            """, (now, uid))

        conn.commit()

    except sqlite3.IntegrityError:
        conn.rollback()  # muhim!

        try:
            bot.answer_callback_query(
                call.id,
                "Bu savolga allaqachon javob berdingiz!",
                show_alert=True
            )
        except:
            pass

    finally:
        conn.close()
    conn.close()
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("➡️ Keyingi savol", callback_data="next_q"))
    if is_correct:
        text = "✅ <b>To'g'ri javob!</b> +10 ball 🎉"
    else:
        text = f"❌ <b>Noto'g'ri!</b>\nTo'g'ri javob: <b>{correct}) {opts[correct]}</b>"
    try:
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=kb)
    except:
        bot.send_message(uid, text, reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data == "next_q")
def next_q(call):
    send_question_to(call.from_user.id, edit_msg=call.message)


@bot.callback_query_handler(func=lambda call: call.data == "get_ref")
def get_ref(call):

    user_id = call.from_user.id

    ref_link = f"https://t.me/{BOT_USERNAME}?start={user_id}"

    bot.send_message(
        chat_id=call.message.chat.id,
        text=f"🔗 Sizning referal linkingiz:\n\n<code>{ref_link}</code>\n\n👆 Ustiga bosib nusxa oling",
        parse_mode="HTML"
    )

# ==================== REYTING ====================
@bot.message_handler(func=lambda m: m.text == "🏆 Reyting")
def show_rating(message):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT full_name, score, correct_answers, total_answers FROM users ORDER BY score DESC LIMIT 10")
    rows = c.fetchall()
    conn.close()
    if not rows:
        bot.send_message(message.chat.id, "Hozircha reyting yo'q.")
        return
    medals = ["🥇", "🥈", "🥉"]
    text = "🏆 <b>TOP 10 Reyting:</b>\n\n"
    for i, (name, score, correct, total) in enumerate(rows):
        medal = medals[i] if i < 3 else f"{i+1}."
        acc = round(correct / total * 100) if total > 0 else 0
        text += f"{medal} <b>{name}</b> — {score} ball | {acc}% aniqlik\n"
    bot.send_message(message.chat.id, text)

# ==================== MENING NATIJAM ====================
@bot.message_handler(func=lambda m: m.text == "📈 Mening natijam")
def my_stats(message):
    uid = message.from_user.id
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT full_name, score, correct_answers, total_answers, registered_at FROM users WHERE telegram_id=?", (uid,))
    row = c.fetchone()
    c.execute("SELECT COUNT(*) FROM users WHERE score > (SELECT COALESCE(score,0) FROM users WHERE telegram_id=?)", (uid,))
    rank = c.fetchone()[0] + 1
    c.execute("SELECT COUNT(*) FROM questions")
    total_q = c.fetchone()[0]
    conn.close()
    if not row:
        bot.send_message(uid, "Avval ro'yxatdan o'ting: /start")
        return
    name, score, correct, total, reg = row
    acc = round(correct / total * 100) if total > 0 else 0
    text = f"""📈 <b>Mening natijam:</b>

👤 {name}
🏆 O'rin: #{rank}
💯 Ball: {score}
✅ To'g'ri: {correct} / {total}
🎯 Aniqlik: {acc}%
📌 Qolgan savollar: {total_q - total}
📅 Ro'yxat: {reg[:10]}"""
    bot.send_message(uid, text)

# ==================== ADMIN PANEL ====================
@bot.message_handler(func=lambda m: m.text == "⚙️ Boshqaruv")
def admin_panel(message):
    uid = message.from_user.id
    if not is_admin(uid):
        bot.send_message(uid, "❌ Ruxsat yo'q!")
        return
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(
        types.InlineKeyboardButton("➕ Savol qo'shish", callback_data="add_q"),
        types.InlineKeyboardButton("📥 Ko'p savol qo'shish", callback_data="bulk_q"),
        types.InlineKeyboardButton("📋 Savollar ro'yxati", callback_data="list_q"),
        types.InlineKeyboardButton("📢 Broadcast", callback_data="broadcast"),
        types.InlineKeyboardButton("👥 Foydalanuvchilar", callback_data="list_users"),
        types.InlineKeyboardButton("📡 Kanallar boshqaruvi", callback_data="manage_ch"),
    )
    if is_leader(uid):
        kb.add(types.InlineKeyboardButton("👮 Adminlar boshqaruvi", callback_data="manage_admins"))
    bot.send_message(uid, "⚙️ <b>Boshqaruv paneli:</b>", reply_markup=kb)

# ==================== STATISTIKA ====================
@bot.message_handler(func=lambda m: m.text == "📊 Statistika (Admin)")
def admin_stats(message):
    uid = message.from_user.id
    if not is_admin(uid):
        bot.send_message(uid, "❌ Ruxsat yo'q!")
        return
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users"); total_u = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM questions"); total_q = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM answers WHERE answered_at >= date('now')"); today_a = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM users WHERE registered_at >= date('now')"); today_u = c.fetchone()[0]
    c.execute("SELECT full_name, score FROM users ORDER BY score DESC LIMIT 3"); top3 = c.fetchall()
    c.execute("""SELECT u.full_name, COUNT(a.id) cnt FROM answers a
                 JOIN users u ON u.telegram_id=a.user_id
                 WHERE a.answered_at >= date('now','-7 days')
                 GROUP BY a.user_id ORDER BY cnt DESC LIMIT 1""")
    weekly = c.fetchone()
    conn.close()
    top_text = "\n".join([f"  {i+1}. {n} — {s} ball" for i,(n,s) in enumerate(top3)]) or "  Mavjud emas"
    weekly_text = f"{weekly[0]} ({weekly[1]} javob)" if weekly else "Mavjud emas"
    text = f"""📊 <b>Bot statistikasi:</b>

👥 Jami foydalanuvchilar: <b>{total_u}</b>
🆕 Bugun ro'yxatdan: <b>{today_u}</b>
❓ Jami savollar: <b>{total_q}</b>
✏️ Bugungi javoblar: <b>{today_a}</b>

🏆 <b>Top 3:</b>
{top_text}

🔥 <b>Haftalik eng faol:</b> {weekly_text}"""
    bot.send_message(uid, text)

# ==================== SAVOL QO'SHISH ====================
@bot.callback_query_handler(func=lambda c: c.data == "add_q")
def cb_add_q(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ Ruxsat yo'q!", show_alert=True); return
    bot.send_message(call.from_user.id, "❓ Savol matnini kiriting:")
    set_state(call.from_user.id, "aq_text")

@bot.message_handler(func=lambda m: get_state(m.from_user.id) == "aq_text")
def aq_text(message):
    update_data(message.from_user.id, "q", message.text)
    bot.send_message(message.from_user.id, "A) variantini kiriting:")
    set_state(message.from_user.id, "aq_a")

@bot.message_handler(func=lambda m: get_state(m.from_user.id) == "aq_a")
def aq_a(message):
    update_data(message.from_user.id, "a", message.text)
    bot.send_message(message.from_user.id, "B) variantini kiriting:")
    set_state(message.from_user.id, "aq_b")

@bot.message_handler(func=lambda m: get_state(m.from_user.id) == "aq_b")
def aq_b(message):
    update_data(message.from_user.id, "b", message.text)
    bot.send_message(message.from_user.id, "C) variantini kiriting:")
    set_state(message.from_user.id, "aq_c")

@bot.message_handler(func=lambda m: get_state(m.from_user.id) == "aq_c")
def aq_c(message):
    update_data(message.from_user.id, "c", message.text)
    bot.send_message(message.from_user.id, "D) variantini kiriting:")
    set_state(message.from_user.id, "aq_d")

@bot.message_handler(func=lambda m: get_state(m.from_user.id) == "aq_d")
def aq_d(message):
    update_data(message.from_user.id, "d", message.text)
    kb = types.InlineKeyboardMarkup(row_width=4)
    kb.add(*[types.InlineKeyboardButton(x, callback_data=f"crt_{x}") for x in ["A","B","C","D"]])
    bot.send_message(message.from_user.id, "✅ To'g'ri javobni tanlang:", reply_markup=kb)
    set_state(message.from_user.id, "aq_correct")

@bot.callback_query_handler(func=lambda c: c.data.startswith("crt_") and get_state(c.from_user.id) == "aq_correct")
def aq_correct(call):
    uid = call.from_user.id
    chosen = call.data.split("_")[1]
    data = get_data(uid)
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT INTO questions (question_text,option_a,option_b,option_c,option_d,correct_answer,added_at) VALUES (?,?,?,?,?,?,?)",
              (data['q'], data['a'], data['b'], data['c'], data['d'], chosen, datetime.now().isoformat()))
    conn.commit()
    q_id = c.lastrowid
    conn.close()
    clear_state(uid)
    try:
        bot.edit_message_text(f"✅ Savol #{q_id} qo'shildi!", call.message.chat.id, call.message.message_id)
    except:
        bot.send_message(uid, f"✅ Savol #{q_id} qo'shildi!")

# ==================== KO'P SAVOL QO'SHISH (BULK) ====================
# Format:
# Savol matni
# A) variant
# B) variant
# C) variant
# D) variant
# To'g'ri: A
# ---
# Savol matni 2
# ...

BULK_EXAMPLE = """📥 <b>Ko'p savol qo'shish formati:</b>

Har bir savolni quyidagi tartibda yozing, savollar orasiga <code>---</code> qo'ying:

<code>Qaysi planet eng katta?
A) Yer
B) Mars
C) Yupiter
D) Saturn
To'g'ri: C
---
Suv formulasi nima?
A) CO2
B) H2O
C) O2
D) NaCl
To'g'ri: B</code>

Yuborishdan oldin to'g'ri formatda ekanligini tekshiring."""

@bot.callback_query_handler(func=lambda c: c.data == "bulk_q")
def cb_bulk_q(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ Ruxsat yo'q!", show_alert=True); return
    bot.send_message(call.from_user.id, BULK_EXAMPLE + "\n\n✏️ Endi savollaringizni yuboring:")
    set_state(call.from_user.id, "bulk_q")

@bot.message_handler(func=lambda m: get_state(m.from_user.id) == "bulk_q")
def do_bulk_q(message):
    uid = message.from_user.id
    clear_state(uid)
    text = message.text.strip()
    blocks = [b.strip() for b in text.split("---") if b.strip()]

    added = []
    errors = []

    for i, block in enumerate(blocks, 1):
        lines = [l.strip() for l in block.strip().splitlines() if l.strip()]
        try:
            # Savol matni (1-qator yoki A) gacha bo'lgan barcha qatorlar)
            q_lines = []
            rest = []
            for idx, line in enumerate(lines):
                if line.upper().startswith("A)") or line.upper().startswith("A )"):
                    rest = lines[idx:]
                    break
                q_lines.append(line)

            if not q_lines or len(rest) < 5:
                errors.append(f"#{i}: Format noto'g'ri")
                continue

            q_text = " ".join(q_lines)
            opt_a = rest[0][2:].strip() if rest[0].upper().startswith("A)") else rest[0][3:].strip()
            opt_b = rest[1][2:].strip() if rest[1].upper().startswith("B)") else rest[1][3:].strip()
            opt_c = rest[2][2:].strip() if rest[2].upper().startswith("C)") else rest[2][3:].strip()
            opt_d = rest[3][2:].strip() if rest[3].upper().startswith("D)") else rest[3][3:].strip()

            # To'g'ri javob qatori: "To'g'ri: A" yoki "Togri: B"
            correct_line = rest[4]
            correct = correct_line.split(":")[-1].strip().upper()
            if correct not in ["A", "B", "C", "D"]:
                errors.append(f"#{i}: To'g'ri javob noto'g'ri ({correct})")
                continue

            conn = get_conn()
            c = conn.cursor()
            c.execute(
                "INSERT INTO questions (question_text,option_a,option_b,option_c,option_d,correct_answer,added_at) VALUES (?,?,?,?,?,?,?)",
                (q_text, opt_a, opt_b, opt_c, opt_d, correct, datetime.now().isoformat())
            )
            conn.commit()
            added.append(c.lastrowid)
            conn.close()

        except Exception as e:
            errors.append(f"#{i}: {str(e)}")

    result = f"✅ <b>{len(added)} ta savol qo'shildi!</b>"
    if added:
        result += f"\nID lar: {', '.join(map(str, added))}"
    if errors:
        result += f"\n\n❌ <b>{len(errors)} ta xato:</b>\n" + "\n".join(errors)

    bot.send_message(uid, result)

# ==================== SAVOLLAR RO'YXATI ====================
@bot.callback_query_handler(func=lambda c: c.data == "list_q")
def cb_list_q(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ Ruxsat yo'q!", show_alert=True); return
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT id, question_text FROM questions ORDER BY id DESC LIMIT 20")
    rows = c.fetchall()
    conn.close()
    if not rows:
        bot.send_message(call.from_user.id, "Savollar yo'q."); return
    kb = types.InlineKeyboardMarkup(row_width=1)
    for qid, qtxt in rows:
        short = qtxt[:35] + "..." if len(qtxt) > 35 else qtxt
        kb.add(types.InlineKeyboardButton(f"🗑 #{qid} {short}", callback_data=f"delq_{qid}"))
    bot.send_message(call.from_user.id, "📋 <b>Savollar</b> (o'chirish uchun bosing):", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("delq_"))
def delq_ask(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ Ruxsat yo'q!", show_alert=True); return
    qid = call.data.split("_")[1]
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("✅ Ha", callback_data=f"cdelq_{qid}"),
           types.InlineKeyboardButton("❌ Yo'q", callback_data="cancel"))
    bot.send_message(call.from_user.id, f"Savol #{qid} ni o'chirasizmi?", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("cdelq_"))
def delq_confirm(call):
    qid = int(call.data.split("_")[1])
    conn = get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM questions WHERE id=?", (qid,))
    c.execute("DELETE FROM answers WHERE question_id=?", (qid,))
    conn.commit()
    conn.close()
    try:
        bot.edit_message_text(f"✅ Savol #{qid} o'chirildi.", call.message.chat.id, call.message.message_id)
    except:
        bot.send_message(call.from_user.id, f"✅ Savol #{qid} o'chirildi.")

@bot.callback_query_handler(func=lambda c: c.data == "cancel")
def cancel_cb(call):
    try:
        bot.edit_message_text("❌ Bekor qilindi.", call.message.chat.id, call.message.message_id)
    except:
        pass

# ==================== BROADCAST ====================
@bot.callback_query_handler(func=lambda c: c.data == "broadcast")
def cb_broadcast(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ Ruxsat yo'q!", show_alert=True); return
    bot.send_message(call.from_user.id, "📢 Xabarni yuboring (matn, rasm, video):\n<i>Bekor qilish: /cancel</i>")
    set_state(call.from_user.id, "broadcast")

@bot.message_handler(func=lambda m: get_state(m.from_user.id) == "broadcast",
                     content_types=['text','photo','video','document','audio','sticker'])
def do_broadcast(message):
    if message.text and message.text == "/cancel":
        clear_state(message.from_user.id)
        bot.send_message(message.from_user.id, "❌ Bekor qilindi.")
        return
    clear_state(message.from_user.id)
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT telegram_id FROM users")
    users = c.fetchall()
    conn.close()
    sent = failed = 0
    for (uid,) in users:
        try:
            bot.copy_message(uid, message.chat.id, message.message_id)
            sent += 1
            time.sleep(0.05)
        except:
            failed += 1
    bot.send_message(message.from_user.id, f"📢 <b>Broadcast tugadi!</b>\n✅ Yuborildi: {sent}\n❌ Xato: {failed}")

# ==================== FOYDALANUVCHILAR ====================
@bot.callback_query_handler(func=lambda c: c.data == "list_users")
def cb_list_users(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ Ruxsat yo'q!", show_alert=True); return
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT telegram_id, full_name, phone, score, registered_at FROM users ORDER BY registered_at DESC LIMIT 15")
    rows = c.fetchall()
    c.execute("SELECT COUNT(*) FROM users"); total = c.fetchone()[0]
    conn.close()
    text = f"👥 <b>Foydalanuvchilar (jami: {total}):</b>\n\n"
    for uid, name, phone, score, reg in rows:
        text += f"👤 <b>{name}</b>\n📱 {phone} | 💯 {score} ball | 🆔 <code>{uid}</code>\n📅 {reg[:10]}\n\n"
    if len(text) > 4000:
        text = text[:4000] + "\n...va boshqalar"
    bot.send_message(call.from_user.id, text)

# ==================== KANALLAR ====================
@bot.callback_query_handler(func=lambda c: c.data == "manage_ch")
def cb_manage_ch(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ Ruxsat yo'q!", show_alert=True); return
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT channel_username, channel_title FROM channels")
    channels = c.fetchall()
    conn.close()
    kb = types.InlineKeyboardMarkup(row_width=1)
    for ch, title in channels:
        kb.add(types.InlineKeyboardButton(f"🗑 {ch} ({title})", callback_data=f"delch_{ch.lstrip('@')}"))
    kb.add(types.InlineKeyboardButton("➕ Kanal qo'shish", callback_data="add_ch"))
    ch_list = "\n".join([f"• {ch} — {t}" for ch, t in channels]) or "Kanallar yo'q"
    bot.send_message(call.from_user.id, f"📡 <b>Obuna kanallari:</b>\n\n{ch_list}", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data == "add_ch")
def cb_add_ch(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ Ruxsat yo'q!", show_alert=True); return
    bot.send_message(call.from_user.id, "📡 Kanal username: (masalan @mening_kanal)")
    set_state(call.from_user.id, "add_ch")

@bot.message_handler(func=lambda m: get_state(m.from_user.id) == "add_ch")
def do_add_ch(message):
    ch = message.text.strip()
    if not ch.startswith("@"): ch = "@" + ch
    try:
        chat = bot.get_chat(ch)
        title = chat.title or ch
        conn = get_conn()
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO channels (channel_username, channel_title, added_at) VALUES (?,?,?)",
                  (ch, title, datetime.now().isoformat()))
        conn.commit()
        conn.close()
        bot.send_message(message.from_user.id, f"✅ Kanal qo'shildi: {ch} ({title})")
    except Exception as e:
        bot.send_message(message.from_user.id, f"❌ Xato: {e}\nBotni kanalga admin qiling.")
    clear_state(message.from_user.id)

@bot.callback_query_handler(func=lambda c: c.data.startswith("delch_"))
def delch(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ Ruxsat yo'q!", show_alert=True); return
    ch = "@" + call.data.split("_", 1)[1]
    conn = get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM channels WHERE channel_username=?", (ch,))
    conn.commit()
    conn.close()
    try:
        bot.edit_message_text(f"✅ {ch} o'chirildi.", call.message.chat.id, call.message.message_id)
    except:
        bot.send_message(call.from_user.id, f"✅ {ch} o'chirildi.")

# ==================== ADMINLAR (FAQAT LEADER) ====================
@bot.callback_query_handler(func=lambda c: c.data == "manage_admins")
def cb_manage_admins(call):
    if not is_leader(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ Faqat leader!", show_alert=True); return
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT telegram_id, added_at FROM admins")
    admins = c.fetchall()
    conn.close()
    kb = types.InlineKeyboardMarkup(row_width=1)
    for aid, added in admins:
        kb.add(types.InlineKeyboardButton(f"🗑 ID: {aid} ({added[:10]})", callback_data=f"deladmin_{aid}"))
    kb.add(types.InlineKeyboardButton("➕ Admin qo'shish", callback_data="add_admin"))
    adm_list = "\n".join([f"• {aid} ({a[:10]})" for aid, a in admins]) or "Adminlar yo'q"
    bot.send_message(call.from_user.id, f"👮 <b>Adminlar:</b>\n\n{adm_list}", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data == "add_admin")
def cb_add_admin(call):
    if not is_leader(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ Faqat leader!", show_alert=True); return
    bot.send_message(call.from_user.id, "👮 Yangi admin Telegram ID sini kiriting:")
    set_state(call.from_user.id, "add_admin")

@bot.message_handler(func=lambda m: get_state(m.from_user.id) == "add_admin")
def do_add_admin(message):
    if not is_leader(message.from_user.id):
        clear_state(message.from_user.id); return
    try:
        admin_id = int(message.text.strip())
        conn = get_conn()
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO admins (telegram_id, added_at) VALUES (?,?)",
                  (admin_id, datetime.now().isoformat()))
        conn.commit()
        conn.close()
        bot.send_message(message.from_user.id, f"✅ Admin qo'shildi: {admin_id}")
        try:
            bot.send_message(admin_id, "🎉 Siz bot admini etib tayinlandingiz!")
        except:
            pass
    except ValueError:
        bot.send_message(message.from_user.id, "❌ ID raqam bo'lishi kerak!")
    clear_state(message.from_user.id)

@bot.callback_query_handler(func=lambda c: c.data.startswith("deladmin_"))
def deladmin(call):
    if not is_leader(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ Faqat leader!", show_alert=True); return
    aid = int(call.data.split("_")[1])
    conn = get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM admins WHERE telegram_id=?", (aid,))
    conn.commit()
    conn.close()
    try:
        bot.edit_message_text(f"✅ Admin {aid} o'chirildi.", call.message.chat.id, call.message.message_id)
    except:
        bot.send_message(call.from_user.id, f"✅ Admin {aid} o'chirildi.")

# ==================== KUNLIK STATISTIKA ====================
def send_daily_stats():
    today = date.today().isoformat()
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT 1 FROM daily_stats WHERE stat_date=?", (today,))
    if c.fetchone():
        conn.close(); return
    c.execute("SELECT full_name, score FROM users ORDER BY score DESC LIMIT 1"); top = c.fetchone()
    c.execute("""SELECT u.full_name, COUNT(a.id) cnt FROM answers a
                 JOIN users u ON u.telegram_id=a.user_id
                 WHERE a.answered_at >= date('now','-7 days')
                 GROUP BY a.user_id ORDER BY cnt DESC LIMIT 1""")
    weekly = c.fetchone()
    c.execute("SELECT COUNT(*) FROM users"); total_u = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM answers WHERE answered_at >= date('now')"); today_a = c.fetchone()[0]
    c.execute("SELECT telegram_id FROM users"); all_users = c.fetchall()
    c.execute("SELECT telegram_id FROM admins"); admin_ids = set(r[0] for r in c.fetchall())
    admin_ids.add(LEADER_ID)
    c.execute("INSERT OR IGNORE INTO daily_stats (stat_date, sent_at) VALUES (?,?)",
              (today, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    top_text = f"🥇 {top[0]} — {top[1]} ball" if top else "Mavjud emas"
    weekly_text = f"🔥 {weekly[0]} ({weekly[1]} javob)" if weekly else "Mavjud emas"
    msg = f"""📅 <b>Kunlik statistika — {today}</b>

👥 Jami foydalanuvchilar: <b>{total_u}</b>
✏️ Bugungi javoblar: <b>{today_a}</b>

🏆 <b>1-o'rin:</b> {top_text}
⚡ <b>Haftalik eng faol:</b> {weekly_text}

💪 Davom eting, yangi savollar kutmoqda!"""
    for (uid,) in all_users:
        if uid not in admin_ids:
            try:
                bot.send_message(uid, msg)
                time.sleep(0.05)
            except:
                pass

def schedule_runner():
    schedule.every().day.at("20:00").do(send_daily_stats)
    while True:
        schedule.run_pending()
        time.sleep(30)

# ==================== MAIN ====================
if __name__ == "__main__":
    init_db()
    try:
        bot.send_message(LEADER_ID, f"🤖 <b>Bot ishga tushdi!</b>\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    except:
        pass
    threading.Thread(target=schedule_runner, daemon=True).start()
    logger.info("Bot polling boshlandi...")
    bot.infinity_polling(timeout=30, long_polling_timeout=20)

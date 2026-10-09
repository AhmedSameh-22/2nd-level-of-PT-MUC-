import sqlite3
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

# ==================== التعديلات المطلوبة ====================
TOKEN = "8741855221:AAG5KHT_WZXBk9RM-6UAyTNtovSBraBGpi8"      # استبدله بالتوكن الخاص بك من BotFather
ADMIN_ID = 5383693396          # استبدله برقم الـ ID الخاص بك من userinfobot
# ============================================================

bot = telebot.TeleBot(TOKEN)

# إعداد قاعدة البيانات بالهيكل الجديد (مواد -> تقسم لـ محاضرات وسكاشن -> ملفات)
def init_db():
    conn = sqlite3.connect('courses.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS subjects (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS items (id INTEGER PRIMARY KEY AUTOINCREMENT, subject_id INTEGER, type TEXT, name TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS files (id INTEGER PRIMARY KEY AUTOINCREMENT, item_id INTEGER, file_id TEXT, file_type TEXT)''')
    conn.commit()
    conn.close()

init_db()

user_states = {}

@bot.message_handler(commands=['start'])
def start(message):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("📚 عرض المواد"))
    
    if message.from_user.id == ADMIN_ID:
        markup.add(KeyboardButton("⚙️ لوحة التحكم"))
        
    bot.send_message(message.chat.id, "أهلاً بك في بوت الدفعة!", reply_markup=markup)

# --- تصفح المواد للطلاب ---
@bot.message_handler(func=lambda m: m.text == "📚 عرض المواد")
def show_subjects(message):
    conn = sqlite3.connect('courses.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM subjects")
    subjects = cursor.fetchall()
    conn.close()

    if not subjects:
        bot.send_message(message.chat.id, "لا توجد مواد مضافة حالياً.")
        return

    markup = InlineKeyboardMarkup()
    for sub_id, sub_name in subjects:
        markup.add(InlineKeyboardButton(sub_name, callback_data=f"get_sub_{sub_id}"))
    
    bot.send_message(message.chat.id, "اختر المادة:", reply_markup=markup)

# --- لوحة التحكم للأدمن ---
@bot.message_handler(func=lambda m: m.text == "⚙️ لوحة التحكم" and m.from_user.id == ADMIN_ID)
def admin_panel(message):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("➕ إضافة مادة جديدة", callback_data="admin_add_subject"))
    markup.add(InlineKeyboardButton("➕ إضافة (محاضرة / سكشن)", callback_data="admin_add_item"))
    markup.add(InlineKeyboardButton("📤 رفع ملفات", callback_data="admin_add_file"))
    
    bot.send_message(message.chat.id, "لوحة التحكم وإدارة المحتوى:", reply_markup=markup)

# --- التعامل مع الضغط على الأزرار ---
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    chat_id = call.message.chat.id
    data = call.data

    # 1. الطالب يختار مادة -> يظهر خيار (المحاضرات / السكاشن)
    if data.startswith("get_sub_"):
        sub_id = data.split("_")[2]
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("📚 المحاضرات", callback_data=f"show_type_{sub_id}_lec"))
        markup.add(InlineKeyboardButton("🔬 السكاشن", callback_data=f"show_type_{sub_id}_sec"))
        bot.send_message(chat_id, "اختر ما تريد عرضة:", reply_markup=markup)

    # 2. عرض المحاضرات أو السكاشن التابعة للمادة
    elif data.startswith("show_type_"):
        parts = data.split("_")
        sub_id = parts[2]
        item_type = parts[3]
        
        conn = sqlite3.connect('courses.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM items WHERE subject_id = ? AND type = ?", (sub_id, item_type))
        items = cursor.fetchall()
        conn.close()

        if not items:
            bot.send_message(chat_id, "لا يوجد محتوى مضاف في هذا القسم حالياً.")
            return

        type_title = "المحاضرات" if item_type == "lec" else "السكاشن"
        markup = InlineKeyboardMarkup()
        for item_id, item_name in items:
            markup.add(InlineKeyboardButton(item_name, callback_data=f"get_item_{item_id}"))
        
        bot.send_message(chat_id, f"قائمة {type_title}:", reply_markup=markup)

    # 3. إرسال الملفات عند اختيار المحاضرة أو السكشن
    elif data.startswith("get_item_"):
        item_id = data.split("_")[2]
        conn = sqlite3.connect('courses.db')
        cursor = conn.cursor()
        cursor.execute("SELECT file_id, file_type FROM files WHERE item_id = ?", (item_id,))
        files = cursor.fetchall()
        conn.close()

        if not files:
            bot.send_message(chat_id, "لا توجد ملفات مرفوعة هنا بعد.")
            return

        bot.send_message(chat_id, "جاري إرسال الملفات...")
        for f_id, f_type in files:
            if f_type == "document":
                bot.send_document(chat_id, f_id)
            elif f_type == "audio":
                bot.send_audio(chat_id, f_id)

    # --- أدمن: إضافة مادة ---
    elif data == "admin_add_subject" and call.from_user.id == ADMIN_ID:
        user_states[chat_id] = "WAITING_SUBJECT_NAME"
        bot.send_message(chat_id, "اكتب اسم المادة الجديدة الآن:")

    # --- أدمن: إضافة محاضرة أو سكشن ---
    elif data == "admin_add_item" and call.from_user.id == ADMIN_ID:
        conn = sqlite3.connect('courses.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM subjects")
        subjects = cursor.fetchall()
        conn.close()

        if not subjects:
            bot.send_message(chat_id, "قم بإضافة مادة أولاً.")
            return

        markup = InlineKeyboardMarkup()
        for sub_id, sub_name in subjects:
            markup.add(InlineKeyboardButton(sub_name, callback_data=f"adm_item_sub_{sub_id}"))
        bot.send_message(chat_id, "اختر المادة المراد الإضافة إليها:", reply_markup=markup)

    elif data.startswith("adm_item_sub_"):
        sub_id = data.split("_")[3]
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("📚 محاضرة", callback_data=f"adm_set_type_{sub_id}_lec"))
        markup.add(InlineKeyboardButton("🔬 سكشن", callback_data=f"adm_set_type_{sub_id}_sec"))
        bot.send_message(chat_id, "اختر نوع الإضافة:", reply_markup=markup)

    elif data.startswith("adm_set_type_"):
        parts = data.split("_")
        sub_id = parts[3]
        item_type = parts[4]
        user_states[chat_id] = f"WAITING_ITEM_NAME_{sub_id}_{item_type}"
        type_label = "المحاضرة" if item_type == "lec" else "السكشن"
        bot.send_message(chat_id, f"اكتب اسم {type_label} الآن (مثال: Lec 1 أو Sec 1):")

    # --- أدمن: اختيار المكان لرفع ملفات ---
    elif data == "admin_add_file" and call.from_user.id == ADMIN_ID:
        conn = sqlite3.connect('courses.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM subjects")
        subjects = cursor.fetchall()
        conn.close()

        markup = InlineKeyboardMarkup()
        for sub_id, sub_name in subjects:
            markup.add(InlineKeyboardButton(sub_name, callback_data=f"adm_file_sub_{sub_id}"))
        bot.send_message(chat_id, "اختر المادة لرفع الملف إليها:", reply_markup=markup)

    elif data.startswith("adm_file_sub_"):
        sub_id = data.split("_")[3]
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("📚 المحاضرات", callback_data=f"adm_file_type_{sub_id}_lec"))
        markup.add(InlineKeyboardButton("🔬 السكاشن", callback_data=f"adm_file_type_{sub_id}_sec"))
        bot.send_message(chat_id, "اختر القسم:", reply_markup=markup)

    elif data.startswith("adm_file_type_"):
        parts = data.split("_")
        sub_id = parts[3]
        item_type = parts[4]

        conn = sqlite3.connect('courses.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM items WHERE subject_id = ? AND type = ?", (sub_id, item_type))
        items = cursor.fetchall()
        conn.close()

        if not items:
            bot.send_message(chat_id, "لا يوجد محتوى في هذا القسم حتى الآن لإضافة ملفات له.")
            return

        markup = InlineKeyboardMarkup()
        for item_id, item_name in items:
            markup.add(InlineKeyboardButton(item_name, callback_data=f"adm_set_item_{item_id}"))
        bot.send_message(chat_id, "اختر المحاضرة/السكشن لرفع الملفات إليها:", reply_markup=markup)

    elif data.startswith("adm_set_item_"):
        item_id = data.split("_")[3]
        user_states[chat_id] = f"WAITING_FILE_{item_id}"
        bot.send_message(chat_id, "قم بإرسال الـ PDF أو الـ MP3 الآن مباشرة إلى الشات:")

# --- التعامل مع الإدخالات والملفات ---
@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID, content_types=['text', 'document', 'audio'])
def handle_admin_inputs(message):
    state = user_states.get(message.chat.id)
    if not state:
        return

    conn = sqlite3.connect('courses.db')
    cursor = conn.cursor()

    # حفظ اسم المادة
    if state == "WAITING_SUBJECT_NAME":
        cursor.execute("INSERT INTO subjects (name) VALUES (?)", (message.text,))
        conn.commit()
        bot.send_message(message.chat.id, f"✅ تم إضافة مادة: {message.text}")
        del user_states[message.chat.id]

    # حفظ اسم المحاضرة أو السكشن
    elif state.startswith("WAITING_ITEM_NAME_"):
        parts = state.split("_")
        sub_id = parts[3]
        item_type = parts[4]
        cursor.execute("INSERT INTO items (subject_id, type, name) VALUES (?, ?, ?)", (sub_id, item_type, message.text))
        conn.commit()
        type_label = "محاضرة" if item_type == "lec" else "سكشن"
        bot.send_message(message.chat.id, f"✅ تم إضافة {type_label}: {message.text}")
        del user_states[message.chat.id]

    # حفظ الملف المرفوع
    elif state.startswith("WAITING_FILE_"):
        item_id = state.split("_")[2]
        if message.document:
            file_id = message.document.file_id
            cursor.execute("INSERT INTO files (item_id, file_id, file_type) VALUES (?, ?, 'document')", (item_id, file_id))
            conn.commit()
            bot.send_message(message.chat.id, "✅ تم حفظ ملف الـ PDF بنجاح!")
        elif message.audio:
            file_id = message.audio.file_id
            cursor.execute("INSERT INTO files (item_id, file_id, file_type) VALUES (?, ?, 'audio')", (item_id, file_id))
            conn.commit()
            bot.send_message(message.chat.id, "✅ تم حفظ التسجيل الصوتي بنجاح!")
        del user_states[message.chat.id]

    conn.close()

bot.infinity_polling()

import os
import time
from datetime import datetime, timedelta
import pytz
from typing import Dict, Any
import sqlite3

import requests
from apscheduler.schedulers.background import BackgroundScheduler
from telebot import TeleBot, types
from telebot.util import quick_markup
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Boolean, Float
from sqlalchemy.orm import sessionmaker, relationship, declarative_base
from werkzeug.security import generate_password_hash, check_password_hash

# ----- Config -----
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '8039732483:AAELszNcgl0saq6LKVAT0Dr5rPZJEPEi2Q4')
DATABASE_URL = 'sqlite:///uptime.db'
MAX_PASSWORD_ATTEMPTS = 3
INDIAN_TIMEZONE = pytz.timezone('Asia/Kolkata')
LANGUAGE = 'en'  # 'en' or 'hi'

bot = TeleBot(TELEGRAM_BOT_TOKEN)

# ----- Database setup -----
Base = declarative_base()

def init_db():
    # Check if database exists and has the correct schema
    if os.path.exists('uptime.db'):
        conn = sqlite3.connect('uptime.db')
        cursor = conn.cursor()
        
        # Check if columns exist
        cursor.execute("PRAGMA table_info(user)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # If old schema exists, drop and recreate
        if 'language' not in columns or 'notifications' not in columns:
            print("Old database schema detected. Recreating database...")
            os.remove('uptime.db')
    
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return engine

engine = init_db()
Session = sessionmaker(bind=engine)
db_session = Session()

class User(Base):
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True)
    chat_id = Column(String, unique=True, nullable=False)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    language = Column(String, default='en')
    notifications = Column(Boolean, default=True)
    monitors = relationship("Monitor", back_populates="user")

class Monitor(Base):
    __tablename__ = 'monitor'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    url = Column(String, nullable=False)
    interval = Column(Integer, default=60)  # seconds
    user_id = Column(Integer, ForeignKey('user.id'))
    status = Column(String, default='unknown')
    last_checked = Column(DateTime)
    response_time = Column(Integer)
    uptime_percentage = Column(Float, default=100.0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="monitors")

class MonitorLog(Base):
    __tablename__ = 'monitor_log'
    id = Column(Integer, primary_key=True)
    monitor_id = Column(Integer, ForeignKey('monitor.id'))
    status = Column(String)
    response_time = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(engine)

# ----- Scheduler -----
scheduler = BackgroundScheduler()
scheduler.start()

# ----- User states -----
user_states: Dict[int, Dict[str, Any]] = {}

# ----- Localization -----
translations = {
    'en': {
        'welcome': "Welcome! Please choose to Register or Login.",
        'welcome_back': "Welcome back, {username}!",
        'register': "Register",
        'login': "Login",
        'enter_username': "Enter desired username:",
        'username_taken': "Username already exists. Enter another username:",
        'enter_password': "Enter a password:",
        'registration_success': "🎉 Registration successful! You are now logged in.",
        'login_success': "✅ Login successful! Welcome back, {username}.",
        'invalid_credentials': "❌ Invalid username or password. {attempts} attempts remaining.",
        'max_attempts': "❌ Maximum login attempts reached. Please try again later.",
        'main_menu': "🏠 Main Menu",
        'my_monitors': "📊 My Monitors",
        'add_monitor': "➕ Add Monitor",
        'settings': "⚙️ Settings",
        'logout': "❌ Logout",
        'no_monitors': "You have no monitors yet. Add one using '➕ Add Monitor'.",
        'monitor_details': "🔍 Monitor Details:\n\nName: {name}\nURL: {url}\nStatus: {status}\nLast checked: {last_checked}\nResponse time: {response_time}ms\nUptime: {uptime}%\nInterval: {interval}s",
        'enter_monitor_name': "Enter monitor name:",
        'enter_monitor_url': "Enter URL to monitor (must start with http:// or https://):",
        'invalid_url': "Invalid URL format. Enter a URL starting with http:// or https://:",
        'enter_monitor_interval': "Enter check interval in seconds (minimum 10):",
        'invalid_interval': "Invalid input. Enter a number (minimum 10 seconds):",
        'monitor_added': "✅ Monitor '{name}' added and will be checked every {interval} seconds.",
        'monitor_actions': "🛠️ Monitor Actions",
        'edit_monitor': "✏️ Edit",
        'delete_monitor': "🗑️ Delete",
        'pause_monitor': "⏸️ Pause",
        'resume_monitor': "▶️ Resume",
        'confirm_delete': "⚠️ Are you sure you want to delete this monitor?",
        'monitor_deleted': "🗑️ Monitor '{name}' has been deleted.",
        'monitor_paused': "⏸️ Monitor '{name}' has been paused.",
        'monitor_resumed': "▶️ Monitor '{name}' has been resumed.",
        'settings_menu': "⚙️ Settings",
        'language_settings': "🌐 Language",
        'notification_settings': "🔔 Notifications",
        'current_language': "Current language: English",
        'language_changed': "🌐 Language changed to English",
        'notifications_on': "🔔 Notifications: ON",
        'notifications_off': "🔔 Notifications: OFF",
        'notifications_toggled': "Notifications have been {status}.",
        'help': """
🤖 *Uptime Monitor Bot Help*

*Commands:*
/start - Start the bot
/help - Show this help message
/stats - Show your monitoring statistics

*Features:*
- Monitor website uptime
- Get instant downtime alerts
- Track response times
- View uptime statistics
- Pause/resume monitoring
- Custom check intervals

*How to use:*
1. Register or login
2. Add monitors with /add
3. View your monitors with /monitors
4. Configure settings with /settings
""",
        'stats': """
📈 *Your Monitoring Statistics*

Total monitors: {total_monitors}
Active monitors: {active_monitors}
Paused monitors: {paused_monitors}

Average uptime: {avg_uptime}%
Average response time: {avg_response_time}ms
"""
    },
    'hi': {
        'welcome': "स्वागत है! कृपया रजिस्टर या लॉगिन करें।",
        'welcome_back': "वापसी पर स्वागत है, {username}!",
        'register': "रजिस्टर",
        'login': "लॉगिन",
        'enter_username': "वांछित उपयोगकर्ता नाम दर्ज करें:",
        'username_taken': "उपयोगकर्ता नाम पहले से मौजूद है। कोई अन्य नाम दर्ज करें:",
        'enter_password': "एक पासवर्ड दर्ज करें:",
        'registration_success': "🎉 पंजीकरण सफल! अब आप लॉग इन हैं।",
        'login_success': "✅ लॉगिन सफल! वापसी पर स्वागत है, {username}।",
        'invalid_credentials': "❌ अमान्य उपयोगकर्ता नाम या पासवर्ड। {attempts} प्रयास शेष।",
        'max_attempts': "❌ अधिकतम लॉगिन प्रयास पूर्ण। कृपया बाद में पुनः प्रयास करें।",
        'main_menu': "🏠 मुख्य मेनू",
        'my_monitors': "📊 मेरे मॉनिटर्स",
        'add_monitor': "➕ मॉनिटर जोड़ें",
        'settings': "⚙️ सेटिंग्स",
        'logout': "❌ लॉगआउट",
        'no_monitors': "आपके पास अभी तक कोई मॉनिटर नहीं है। '➕ मॉनिटर जोड़ें' का उपयोग करके एक जोड़ें।",
        'monitor_details': "🔍 मॉनिटर विवरण:\n\nनाम: {name}\nURL: {url}\nस्थिति: {status}\nअंतिम जांच: {last_checked}\nप्रतिक्रिया समय: {response_time}ms\nअपटाइम: {uptime}%\nअंतराल: {interval}s",
        'enter_monitor_name': "मॉनिटर का नाम दर्ज करें:",
        'enter_monitor_url': "मॉनिटर करने के लिए URL दर्ज करें (http:// या https:// से शुरू होना चाहिए):",
        'invalid_url': "अमान्य URL प्रारूप। http:// या https:// से शुरू होने वाला URL दर्ज करें:",
        'enter_monitor_interval': "सेकंड में जांच अंतराल दर्ज करें (न्यूनतम 10):",
        'invalid_interval': "अमान्य इनपुट। एक संख्या दर्ज करें (न्यूनतम 10 सेकंड):",
        'monitor_added': "✅ मॉनिटर '{name}' जोड़ा गया और हर {interval} सेकंड में जांचा जाएगा।",
        'monitor_actions': "🛠️ मॉनिटर क्रियाएं",
        'edit_monitor': "✏️ संपादित करें",
        'delete_monitor': "🗑️ हटाएं",
        'pause_monitor': "⏸️ रोकें",
        'resume_monitor': "▶️ फिर से शुरू करें",
        'confirm_delete': "⚠️ क्या आप वाकई इस मॉनिटर को हटाना चाहते हैं?",
        'monitor_deleted': "🗑️ मॉनिटर '{name}' हटा दिया गया है।",
        'monitor_paused': "⏸️ मॉनिटर '{name}' रोक दिया गया है।",
        'monitor_resumed': "▶️ मॉनिटर '{name}' फिर से शुरू किया गया है।",
        'settings_menu': "⚙️ सेटिंग्स",
        'language_settings': "🌐 भाषा",
        'notification_settings': "🔔 सूचनाएं",
        'current_language': "वर्तमान भाषा: हिंदी",
        'language_changed': "🌐 भाषा हिंदी में बदल गई",
        'notifications_on': "🔔 सूचनाएं: चालू",
        'notifications_off': "🔔 सूचनाएं: बंद",
        'notifications_toggled': "सूचनाएं {status} कर दी गई हैं।",
        'help': """
🤖 *अपटाइम मॉनिटर बॉट सहायता*

*कमांड्स:*
/start - बॉट शुरू करें
/help - यह सहायता संदेश दिखाएं
/stats - अपने मॉनिटरिंग आंकड़े दिखाएं

*विशेषताएं:*
- वेबसाइट अपटाइम मॉनिटर करें
- तुरंत डाउनटाइम अलर्ट प्राप्त करें
- प्रतिक्रिया समय ट्रैक करें
- अपटाइम आंकड़े देखें
- मॉनिटरिंग रोकें/फिर से शुरू करें
- कस्टम जांच अंतराल

*उपयोग कैसे करें:*
1. रजिस्टर या लॉगिन करें
2. /add से मॉनिटर जोड़ें
3. /monitors से अपने मॉनिटर देखें
4. /settings से सेटिंग्स कॉन्फ़िगर करें
""",
        'stats': """
📈 *आपके मॉनिटरिंग आंकड़े*

कुल मॉनिटर्स: {total_monitors}
सक्रिय मॉनिटर्स: {active_monitors}
रुके हुए मॉनिटर्स: {paused_monitors}

औसत अपटाइम: {avg_uptime}%
औसत प्रतिक्रिया समय: {avg_response_time}ms
"""
    }
}

def t(key: str, **kwargs) -> str:
    """Get translated text"""
    lang = LANGUAGE
    if 'chat_id' in kwargs:
        user = get_user_by_chat(kwargs['chat_id'])
        if user and user.language:
            lang = user.language
    return translations[lang].get(key, key).format(**kwargs)

# ----- Helper functions -----

def schedule_monitor(monitor: Monitor) -> None:
    job_id = f"monitor_{monitor.id}"
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
    if monitor.is_active:
        scheduler.add_job(
            func=check_monitor,
            args=[monitor.id],
            trigger='interval',
            seconds=monitor.interval,
            id=job_id,
            replace_existing=True
        )

def check_monitor(monitor_id: int) -> None:
    session = Session()
    monitor = session.query(Monitor).get(monitor_id)
    if not monitor:
        session.close()
        return

    start = time.time()
    try:
        resp = requests.get(monitor.url, timeout=monitor.interval)
        response_time = int((time.time() - start) * 1000)
        status = 'up' if resp.status_code < 400 else 'down'
        message = f"{resp.status_code} {resp.reason}"
    except Exception as e:
        response_time = monitor.interval * 1000
        status = 'down'
        message = str(e)

    # Update monitor status
    monitor.status = status
    monitor.response_time = response_time
    monitor.last_checked = datetime.utcnow()
    
    # Calculate uptime percentage (simple moving average)
    if monitor.uptime_percentage == 100.0:  # First check
        monitor.uptime_percentage = 100.0 if status == 'up' else 0.0
    else:
        if status == 'up':
            monitor.uptime_percentage = (monitor.uptime_percentage * 0.9) + 10.0
        else:
            monitor.uptime_percentage = monitor.uptime_percentage * 0.9
    
    # Log this check
    log = MonitorLog(
        monitor_id=monitor.id,
        status=status,
        response_time=response_time
    )
    session.add(log)
    
    session.commit()

    # Send notification if status changed to down and notifications are enabled
    user = monitor.user
    if status == 'down' and user and user.notifications:
        try:
            bot.send_message(
                user.chat_id,
                f"⚠️ {t('monitor_down_alert', chat_id=user.chat_id)}\n"
                f"{t('name', chat_id=user.chat_id)}: {monitor.name}\n"
                f"URL: {monitor.url}\n"
                f"{t('error', chat_id=user.chat_id)}: {message}"
            )
        except Exception:
            pass
    
    session.close()

def get_user_by_chat(chat_id: int) -> User:
    return db_session.query(User).filter_by(chat_id=str(chat_id)).first()

def register_user(chat_id: int, username: str, password: str) -> tuple[bool, str]:
    if db_session.query(User).filter_by(username=username).first():
        return False, t('username_taken')
    user = User(
        chat_id=str(chat_id),
        username=username,
        password_hash=generate_password_hash(password)
    )
    db_session.add(user)
    db_session.commit()
    return True, t('registration_success')

def validate_login(username: str, password: str) -> User:
    user = db_session.query(User).filter_by(username=username).first()
    if user and check_password_hash(user.password_hash, password):
        return user
    return None

def format_datetime(dt: datetime) -> str:
    if dt is None:
        return t('never')
    return dt.astimezone(INDIAN_TIMEZONE).strftime("%Y-%m-%d %H:%M:%S")

def main_menu_markup(chat_id: int) -> types.ReplyKeyboardMarkup:
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(
        types.KeyboardButton(t('my_monitors', chat_id=chat_id)),
        types.KeyboardButton(t('add_monitor', chat_id=chat_id))
    )
    markup.row(
        types.KeyboardButton(t('settings', chat_id=chat_id)),
        types.KeyboardButton(t('logout', chat_id=chat_id))
    )
    return markup

def monitor_actions_markup(monitor_id: int, chat_id: int) -> types.InlineKeyboardMarkup:
    return quick_markup({
        t('edit_monitor', chat_id=chat_id): {'callback_data': f'edit_{monitor_id}'},
        t('delete_monitor', chat_id=chat_id): {'callback_data': f'delete_{monitor_id}'},
        t('pause_monitor', chat_id=chat_id): {'callback_data': f'toggle_{monitor_id}'}
    }, row_width=2)

def confirm_delete_markup(monitor_id: int, chat_id: int) -> types.InlineKeyboardMarkup:
    return quick_markup({
        t('yes', chat_id=chat_id): {'callback_data': f'confirm_delete_{monitor_id}'},
        t('no', chat_id=chat_id): {'callback_data': f'cancel_delete_{monitor_id}'}
    }, row_width=2)

def settings_markup(chat_id: int) -> types.InlineKeyboardMarkup:
    user = get_user_by_chat(chat_id)
    notification_text = t('notifications_off', chat_id=chat_id) if not user.notifications else t('notifications_on', chat_id=chat_id)
    return quick_markup({
        t('language_settings', chat_id=chat_id): {'callback_data': 'set_lang'},
        notification_text: {'callback_data': 'toggle_notifications'},
        t('back', chat_id=chat_id): {'callback_data': 'back_to_main'}
    }, row_width=1)

def language_markup(chat_id: int) -> types.InlineKeyboardMarkup:
    return quick_markup({
        "English 🇬🇧": {'callback_data': 'lang_en'},
        "हिंदी 🇮🇳": {'callback_data': 'lang_hi'},
        t('back', chat_id=chat_id): {'callback_data': 'back_to_settings'}
    }, row_width=2)

# ----- Telegram Handlers -----

@bot.message_handler(commands=['start', 'help', 'stats'])
def handle_commands(message: types.Message) -> None:
    chat_id = message.chat.id
    user = get_user_by_chat(chat_id)
    
    if message.text == '/start':
        if user:
            bot.send_message(chat_id, t('welcome_back', username=user.username, chat_id=chat_id), 
                           reply_markup=main_menu_markup(chat_id))
        else:
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            markup.row(
                types.KeyboardButton(t('register', chat_id=chat_id)),
                types.KeyboardButton(t('login', chat_id=chat_id))
            )
            bot.send_message(chat_id, t('welcome', chat_id=chat_id), reply_markup=markup)
    
    elif message.text == '/help':
        bot.send_message(chat_id, t('help', chat_id=chat_id), parse_mode='Markdown')
    
    elif message.text == '/stats' and user:
        monitors = db_session.query(Monitor).filter_by(user_id=user.id).all()
        active_monitors = [m for m in monitors if m.is_active]
        paused_monitors = [m for m in monitors if not m.is_active]
        
        avg_uptime = sum(m.uptime_percentage for m in monitors) / len(monitors) if monitors else 100.0
        avg_response = sum(m.response_time for m in monitors if m.response_time) / len([m for m in monitors if m.response_time]) if monitors else 0
        
        bot.send_message(
            chat_id,
            t('stats',
              total_monitors=len(monitors),
              active_monitors=len(active_monitors),
              paused_monitors=len(paused_monitors),
              avg_uptime=round(avg_uptime, 2),
              avg_response_time=round(avg_response, 2),
              chat_id=chat_id),
            parse_mode='Markdown'
        )

@bot.message_handler(func=lambda m: m.text in [t('register'), t('login')])
def auth_handler(message: types.Message) -> None:
    chat_id = message.chat.id
    user = get_user_by_chat(chat_id)
    
    if user:
        bot.send_message(chat_id, t('already_logged_in', chat_id=chat_id), 
                        reply_markup=main_menu_markup(chat_id))
        return
    
    if message.text == t('register', chat_id=chat_id):
        msg = bot.send_message(chat_id, t('enter_username', chat_id=chat_id))
        bot.register_next_step_handler(msg, process_registration_username)
    else:
        user_states[chat_id] = {'attempts': 0}
        msg = bot.send_message(chat_id, t('enter_username', chat_id=chat_id))
        bot.register_next_step_handler(msg, process_login_username)

def process_registration_username(message: types.Message) -> None:
    chat_id = message.chat.id
    username = message.text.strip()
    
    if get_user_by_chat(chat_id):
        bot.send_message(chat_id, t('already_registered', chat_id=chat_id), 
                         reply_markup=main_menu_markup(chat_id))
        return

    if db_session.query(User).filter_by(username=username).first():
        msg = bot.send_message(chat_id, t('username_taken', chat_id=chat_id))
        bot.register_next_step_handler(msg, process_registration_username)
        return

    user_states[chat_id] = {'username': username}
    msg = bot.send_message(chat_id, t('enter_password', chat_id=chat_id))
    bot.register_next_step_handler(msg, process_registration_password)

def process_registration_password(message: types.Message) -> None:
    chat_id = message.chat.id
    password = message.text.strip()
    username = user_states.get(chat_id, {}).get('username')
    
    if not username:
        bot.send_message(chat_id, t('restart_registration', chat_id=chat_id))
        return
    
    success, msg = register_user(chat_id, username, password)
    bot.send_message(chat_id, msg, reply_markup=main_menu_markup(chat_id))
    user_states.pop(chat_id, None)

def process_login_username(message: types.Message) -> None:
    chat_id = message.chat.id
    username = message.text.strip()
    
    user_states[chat_id] = {
        'username': username,
        'attempts': 0
    }
    
    msg = bot.send_message(chat_id, t('enter_password', chat_id=chat_id))
    bot.register_next_step_handler(msg, process_login_password)

def process_login_password(message: types.Message) -> None:
    chat_id = message.chat.id
    password = message.text.strip()
    state = user_states.get(chat_id, {})
    username = state.get('username')
    
    if not username:
        bot.send_message(chat_id, t('restart_login', chat_id=chat_id))
        user_states.pop(chat_id, None)
        return
    
    # Increment attempts
    attempts = state.get('attempts', 0) + 1
    user_states[chat_id]['attempts'] = attempts
    
    user = validate_login(username, password)
    if user:
        # Update chat_id in case user changed chat
        if user.chat_id != str(chat_id):
            user.chat_id = str(chat_id)
            db_session.commit()
        
        bot.send_message(chat_id, t('login_success', username=username, chat_id=chat_id), 
                        reply_markup=main_menu_markup(chat_id))
        user_states.pop(chat_id, None)
    else:
        if attempts >= MAX_PASSWORD_ATTEMPTS:
            bot.send_message(chat_id, t('max_attempts', chat_id=chat_id))
            user_states.pop(chat_id, None)
        else:
            remaining = MAX_PASSWORD_ATTEMPTS - attempts
            msg = bot.send_message(
                chat_id,
                t('invalid_credentials', attempts=remaining, chat_id=chat_id)
            )
            bot.register_next_step_handler(msg, process_login_password)

@bot.message_handler(func=lambda m: m.text == t('my_monitors', chat_id=m.chat.id))
def my_monitors(message: types.Message) -> None:
    chat_id = message.chat.id
    user = get_user_by_chat(chat_id)
    
    if not user:
        bot.send_message(chat_id, t('login_required', chat_id=chat_id))
        return

    monitors = db_session.query(Monitor).filter_by(user_id=user.id).order_by(Monitor.is_active.desc(), Monitor.name).all()
    
    if not monitors:
        bot.send_message(chat_id, t('no_monitors', chat_id=chat_id))
        return

    # Send monitors in chunks of 5 to avoid message flooding
    for i in range(0, len(monitors), 5):
        chunk = monitors[i:i+5]
        text = ""
        for monitor in chunk:
            status_emoji = "🟢" if monitor.status == 'up' else ("🔴" if monitor.status == 'down' else "⚪️")
            pause_emoji = " ⏸️" if not monitor.is_active else ""
            text += f"{status_emoji}{pause_emoji} {monitor.name}\n"
        
        markup = types.InlineKeyboardMarkup()
        for monitor in chunk:
            markup.add(types.InlineKeyboardButton(
                f"{'⏸️ ' if not monitor.is_active else ''}{monitor.name}",
                callback_data=f"details_{monitor.id}"
            ))
        
        bot.send_message(chat_id, text, reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == t('add_monitor', chat_id=m.chat.id))
def add_monitor_start(message: types.Message) -> None:
    chat_id = message.chat.id
    user = get_user_by_chat(chat_id)
    
    if not user:
        bot.send_message(chat_id, t('login_required', chat_id=chat_id))
        return

    msg = bot.send_message(chat_id, t('enter_monitor_name', chat_id=chat_id))
    bot.register_next_step_handler(msg, add_monitor_name)

def add_monitor_name(message: types.Message) -> None:
    chat_id = message.chat.id
    name = message.text.strip()
    
    if name.lower() == '❌ cancel':
        bot.send_message(chat_id, t('operation_cancelled', chat_id=chat_id), 
                         reply_markup=main_menu_markup(chat_id))
        return
    
    user_states[chat_id] = {'monitor_name': name}
    msg = bot.send_message(chat_id, t('enter_monitor_url', chat_id=chat_id))
    bot.register_next_step_handler(msg, add_monitor_url)

def add_monitor_url(message: types.Message) -> None:
    chat_id = message.chat.id
    url = message.text.strip()
    
    if url.lower() == '❌ cancel':
        bot.send_message(chat_id, t('operation_cancelled', chat_id=chat_id), 
                         reply_markup=main_menu_markup(chat_id))
        return
    
    if not url.startswith(('http://', 'https://')):
        msg = bot.send_message(chat_id, t('invalid_url', chat_id=chat_id))
        bot.register_next_step_handler(msg, add_monitor_url)
        return
    
    user_states[chat_id]['monitor_url'] = url
    msg = bot.send_message(chat_id, t('enter_monitor_interval', chat_id=chat_id))
    bot.register_next_step_handler(msg, add_monitor_interval)

def add_monitor_interval(message: types.Message) -> None:
    chat_id = message.chat.id
    try:
        interval = int(message.text.strip())
        if interval < 10:
            raise ValueError
    except ValueError:
        msg = bot.send_message(chat_id, t('invalid_interval', chat_id=chat_id))
        bot.register_next_step_handler(msg, add_monitor_interval)
        return

    data = user_states.get(chat_id)
    if not data:
        bot.send_message(chat_id, t('restart_monitor_creation', chat_id=chat_id))
        return

    user = get_user_by_chat(chat_id)
    monitor = Monitor(
        name=data['monitor_name'],
        url=data['monitor_url'],
        interval=interval,
        user_id=user.id
    )
    db_session.add(monitor)
    db_session.commit()
    schedule_monitor(monitor)

    bot.send_message(
        chat_id,
        t('monitor_added', name=monitor.name, interval=interval, chat_id=chat_id),
        reply_markup=main_menu_markup(chat_id)
    )
    user_states.pop(chat_id, None)

@bot.message_handler(func=lambda m: m.text == t('settings', chat_id=m.chat.id))
def settings_menu(message: types.Message) -> None:
    chat_id = message.chat.id
    user = get_user_by_chat(chat_id)
    
    if not user:
        bot.send_message(chat_id, t('login_required', chat_id=chat_id))
        return
    
    bot.send_message(
        chat_id,
        t('settings_menu', chat_id=chat_id),
        reply_markup=settings_markup(chat_id)
    )

@bot.message_handler(func=lambda m: m.text == t('logout', chat_id=m.chat.id))
def logout(message: types.Message) -> None:
    chat_id = message.chat.id
    user = get_user_by_chat(chat_id)
    
    if not user:
        bot.send_message(chat_id, t('not_logged_in', chat_id=chat_id), 
                         reply_markup=auth_menu_markup(chat_id))
        return
    
    # Clear any ongoing states
    user_states.pop(chat_id, None)
    
    # Remove user session
    db_session.delete(user)
    db_session.commit()
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.row(
        types.KeyboardButton(t('register', chat_id=chat_id)),
        types.KeyboardButton(t('login', chat_id=chat_id))
    )
    bot.send_message(chat_id, t('logged_out', chat_id=chat_id), reply_markup=markup)

# ----- Callback Handlers -----

@bot.callback_query_handler(func=lambda call: call.data.startswith('details_'))
def monitor_details(call: types.CallbackQuery) -> None:
    chat_id = call.message.chat.id
    monitor_id = int(call.data.split('_')[1])
    monitor = db_session.query(Monitor).get(monitor_id)
    
    if not monitor or monitor.user_id != get_user_by_chat(chat_id).id:
        bot.answer_callback_query(call.id, t('monitor_not_found', chat_id=chat_id))
        return
    
    status_text = {
        'up': t('status_up', chat_id=chat_id),
        'down': t('status_down', chat_id=chat_id),
        'unknown': t('status_unknown', chat_id=chat_id)
    }.get(monitor.status, monitor.status)
    
    text = t('monitor_details',
             name=monitor.name,
             url=monitor.url,
             status=status_text,
             last_checked=format_datetime(monitor.last_checked),
             response_time=monitor.response_time or t('na', chat_id=chat_id),
             uptime=round(monitor.uptime_percentage, 2),
             interval=monitor.interval,
             chat_id=chat_id)
    
    markup = monitor_actions_markup(monitor_id, chat_id)
    bot.edit_message_text(
        text,
        chat_id,
        call.message.message_id,
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('toggle_'))
def toggle_monitor(call: types.CallbackQuery) -> None:
    chat_id = call.message.chat.id
    monitor_id = int(call.data.split('_')[1])
    monitor = db_session.query(Monitor).get(monitor_id)
    
    if not monitor or monitor.user_id != get_user_by_chat(chat_id).id:
        bot.answer_callback_query(call.id, t('monitor_not_found', chat_id=chat_id))
        return
    
    monitor.is_active = not monitor.is_active
    db_session.commit()
    schedule_monitor(monitor)
    
    if monitor.is_active:
        bot.answer_callback_query(call.id, t('monitor_resumed', name=monitor.name, chat_id=chat_id))
    else:
        bot.answer_callback_query(call.id, t('monitor_paused', name=monitor.name, chat_id=chat_id))
    
    # Update the message to reflect changes
    monitor_details(call)

@bot.callback_query_handler(func=lambda call: call.data.startswith('delete_'))
def delete_monitor_prompt(call: types.CallbackQuery) -> None:
    chat_id = call.message.chat.id
    monitor_id = int(call.data.split('_')[1])
    monitor = db_session.query(Monitor).get(monitor_id)
    
    if not monitor or monitor.user_id != get_user_by_chat(chat_id).id:
        bot.answer_callback_query(call.id, t('monitor_not_found', chat_id=chat_id))
        return
    
    bot.edit_message_text(
        t('confirm_delete', chat_id=chat_id),
        chat_id,
        call.message.message_id,
        reply_markup=confirm_delete_markup(monitor_id, chat_id)
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('confirm_delete_'))
def confirm_delete_monitor(call: types.CallbackQuery) -> None:
    chat_id = call.message.chat.id
    monitor_id = int(call.data.split('_')[2])
    monitor = db_session.query(Monitor).get(monitor_id)
    
    if not monitor or monitor.user_id != get_user_by_chat(chat_id).id:
        bot.answer_callback_query(call.id, t('monitor_not_found', chat_id=chat_id))
        return
    
    name = monitor.name
    # Remove scheduler job
    job_id = f"monitor_{monitor.id}"
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
    
    db_session.delete(monitor)
    db_session.commit()
    
    bot.edit_message_text(
        t('monitor_deleted', name=name, chat_id=chat_id),
        chat_id,
        call.message.message_id
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('cancel_delete_'))
def cancel_delete_monitor(call: types.CallbackQuery) -> None:
    # Just show the monitor details again
    monitor_details(call)

@bot.callback_query_handler(func=lambda call: call.data == 'set_lang')
def set_language(call: types.CallbackQuery) -> None:
    chat_id = call.message.chat.id
    bot.edit_message_text(
        t('current_language', chat_id=chat_id),
        chat_id,
        call.message.message_id,
        reply_markup=language_markup(chat_id)
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('lang_'))
def change_language(call: types.CallbackQuery) -> None:
    chat_id = call.message.chat.id
    lang = call.data.split('_')[1]
    user = get_user_by_chat(chat_id)
    
    if user:
        user.language = lang
        db_session.commit()
    
    bot.edit_message_text(
        t('language_changed', chat_id=chat_id),
        chat_id,
        call.message.message_id
    )
    
    # Update the settings menu
    bot.send_message(
        chat_id,
        t('settings_menu', chat_id=chat_id),
        reply_markup=settings_markup(chat_id)
    )

@bot.callback_query_handler(func=lambda call: call.data == 'toggle_notifications')
def toggle_notifications(call: types.CallbackQuery) -> None:
    chat_id = call.message.chat.id
    user = get_user_by_chat(chat_id)
    
    if user:
        user.notifications = not user.notifications
        db_session.commit()
        
        status = t('on', chat_id=chat_id) if user.notifications else t('off', chat_id=chat_id)
        bot.answer_callback_query(
            call.id,
            t('notifications_toggled', status=status, chat_id=chat_id)
        )
        
        # Update the settings menu
        bot.edit_message_text(
            t('settings_menu', chat_id=chat_id),
            chat_id,
            call.message.message_id,
            reply_markup=settings_markup(chat_id)
        )

@bot.callback_query_handler(func=lambda call: call.data == 'back_to_main')
def back_to_main(call: types.CallbackQuery) -> None:
    chat_id = call.message.chat.id
    bot.edit_message_text(
        t('main_menu', chat_id=chat_id),
        chat_id,
        call.message.message_id,
        reply_markup=None
    )
    bot.send_message(
        chat_id,
        t('main_menu', chat_id=chat_id),
        reply_markup=main_menu_markup(chat_id)
    )

@bot.callback_query_handler(func=lambda call: call.data == 'back_to_settings')
def back_to_settings(call: types.CallbackQuery) -> None:
    chat_id = call.message.chat.id
    bot.edit_message_text(
        t('settings_menu', chat_id=chat_id),
        chat_id,
        call.message.message_id,
        reply_markup=settings_markup(chat_id)
    )

# ----- Start polling -----
if __name__ == '__main__':
    print("Initializing database...")
    init_db()
    print("Bot started...")
    try:
        bot.infinity_polling()
    except Exception as e:
        print(f"Error: {e}")
        db_session.close()

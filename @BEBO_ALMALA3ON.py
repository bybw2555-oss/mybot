# -*- coding: utf-8 -*-
"""
بوت الشد الداخلي المتطور - v12.0
المطور: @BEBO_ALMALA3ON
بلاغ قناة خاصة برابط دعوة + بدون مخزن كلايش
"""
import requests, json, os, re, base64, time, threading, asyncio, shutil, tempfile, atexit, zipfile
from pathlib import Path
from datetime import datetime, timedelta
from tinydb import TinyDB, Query

from pyrogram import Client
from pyrogram.errors import SessionPasswordNeeded, PhoneCodeExpired
from pyrogram.errors.exceptions.bad_request_400 import PasswordHashInvalid, PhoneCodeInvalid
from pyrogram.errors.exceptions.not_acceptable_406 import PhoneNumberInvalid
from pyrogram.raw.functions.messages import Report
from pyrogram.raw.functions.account import ReportPeer
from pyrogram.raw.types import (
    InputReportReasonChildAbuse, InputReportReasonCopyright,
    InputReportReasonIllegalDrugs, InputReportReasonOther,
    InputReportReasonPersonalDetails, InputReportReasonPornography,
    InputReportReasonSpam, InputReportReasonViolence, InputReportReasonFake,
)

try:
    from telethon import TelegramClient
    from telethon.sessions import StringSession
except ImportError:
    TelegramClient = None
    StringSession = None

# ============================== قفل الملف ==============================
_LOCK_FILE = "bot.lock"; _lock_fd = None

def _acquire_lock():
    global _lock_fd
    if (os.getenv('RAILWAY_ENVIRONMENT') or os.getenv('RAILWAY_PROJECT_ID')
            or os.getenv('REPL_ID') or os.getenv('DYNO')
            or os.getenv('HEROKU_APP_NAME') or os.getenv('RENDER')):
        return True
    try:
        import fcntl
        _lock_fd = open(_LOCK_FILE, 'w')
        fcntl.flock(_lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        _lock_fd.write(str(os.getpid())); _lock_fd.flush(); return True
    except ImportError: pass
    except (IOError, OSError):
        print("⚠️ تحذير: فيه نسخة تانية؟ هكمل...", flush=True)
        return True
    try:
        import msvcrt
        _lock_fd = open(_LOCK_FILE, 'w')
        msvcrt.locking(_lock_fd.fileno(), msvcrt.LK_NBLCK, 1)
        _lock_fd.write(str(os.getpid())); _lock_fd.flush(); return True
    except Exception:
        return True

def _release_lock():
    global _lock_fd
    try:
        if _lock_fd: _lock_fd.close(); _lock_fd = None
        if os.path.exists(_LOCK_FILE):
            try: os.remove(_LOCK_FILE)
            except Exception: pass
    except Exception: pass

BOT_VERSION = "v12.0"

# ============================== الإعدادات ==============================
TOKEN = "8608907903:AAHy3rXjNUK4xGgh8nAKRb1KrY77ECS7EtQ"
OWNER_ID = 8112061400
API_ID = 32449556
API_HASH = "f6aebfd52a5b5aebcfa75e50ee58ae2e"
API_URL = f"https://api.telegram.org/bot{TOKEN}"

OWNER_USERNAME = "BEBO_ALMALA3ON"
SECOND_DEV_USERNAME = "BEBO_ALMALA3ON"
CHANNEL_USERNAME = "Unkle_BEBO"
OWNER_LINK = f"https://t.me/{OWNER_USERNAME}"
SECOND_DEV_LINK = f"https://t.me/{SECOND_DEV_USERNAME}"
CHANNEL_LINK = f"https://t.me/{CHANNEL_USERNAME}"

# ============================== زخرفة ==============================
DECO_LINE = "━━━━━━━━━━━━━━━━━━━━"
DECO_LINE2 = "┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄"

def Zakhrafa(text):
    if not text: return text
    ar = set("ابتثجحخدذرزسشصضطظعغفقكلمنهويىةأإآئؤء")
    marks = ["ً", "ٍ", "ٌ", "ْ"]; out = []; cnt = 0
    for i, ch in enumerate(text):
        out.append(ch)
        if (ch in ar and 0 < i < len(text) - 1
                and text[i-1] in ar and text[i+1] in ar):
            if cnt % 2 == 0:
                out.append("ـ"); out.append(marks[cnt % len(marks)])
            cnt += 1
    return "".join(out)

def Z(text): return f"◈ ─── « {Zakhrafa(text)} » ─── ◈"
def decorate_title(title): return f"╭━━━❰ {Zakhrafa(title)} ❱━━━╮"

# ============================== الملفات ==============================
ADMINS_FILE = 'admins.json'; STATS_FILE = 'user_stats.json'
SUBS_FILE = 'subscriptions.json'; ACCOUNTS_FILE = 'user_accounts.json'
WELCOME_FILE = 'welcome_media.json'
WELCOME_FOLDER = 'welcome_media'; BACKUP_DIR = Path('backups')
os.makedirs(WELCOME_FOLDER, exist_ok=True); BACKUP_DIR.mkdir(exist_ok=True)

REPORT_MEDIA_FILE = 'report_media.json'

ADMIN_IDS = [OWNER_ID]
if os.path.exists(ADMINS_FILE):
    try:
        with open(ADMINS_FILE, 'r', encoding='utf-8') as f:
            for adm in json.load(f):
                if adm not in ADMIN_IDS: ADMIN_IDS.append(adm)
    except Exception: pass

def save_admins():
    with open(ADMINS_FILE, 'w', encoding='utf-8') as f:
        json.dump(ADMIN_IDS, f, ensure_ascii=False, indent=2)

db = TinyDB(SUBS_FILE); Subscription = Query()
accounts_db = TinyDB(ACCOUNTS_FILE)

if not os.path.exists(STATS_FILE):
    with open(STATS_FILE, 'w', encoding='utf-8') as f: json.dump({}, f)

user_data = {}; is_reporting = {}; report_delay = 1; last_update_id = 0
SESSION_CHECK_INTERVAL = 60 * 60

ALL_REPORT_TYPES = {
    "report_not_interested": "👎 لا يهمني",
    "report_child_abuse_sexual": "🔞 إساءة جنسية لأطفال",
    "report_child_abuse_physical": "💢 اعتداء جسدي على أطفال",
    "report_violence_physical": "💢 عنف جسدي",
    "report_violence_sexual": "🔞 عنف جنسي",
    "report_violence_psychological": "💢 عنف نفسي / تحرش",
    "report_violence_incitement": "💢 تحريض على عنف",
    "report_violence_other": "❓ عنف - أخرى",
    "report_illegal_goods_weapons": "🔫 أسلحة",
    "report_illegal_goods_drugs": "💊 مخدرات",
    "report_illegal_goods_fake_docs": "📄 وثائق مزيفة",
    "report_illegal_goods_fake_money": "💰 مال مزيف",
    "report_illegal_goods_hacking": "💻 أدوات اختراق",
    "report_illegal_goods_counterfeit": "🛍️ بضائع مزيفة",
    "report_illegal_goods_other": "❓ سلع أخرى",
    "report_adult_illegal_porn": "🔞 مواد إباحية",
    "report_adult_exploitation": "🔞 استغلال جنسي",
    "report_adult_child_porn": "🔞 مواد قاصرين",
    "report_adult_other": "❓ محتوى كبار آخر",
    "report_scam_impersonation": "🎭 انتحال شخصية",
    "report_scam_financial": "💰 مطالبات مالية",
    "report_scam_malware": "💻 برامج ضارة",
    "report_scam_fraudulent": "🛍️ بائع محتال",
    "report_spam_misleading": "📢 إهانات / مضللة",
    "report_spam_illegal_promo": "🚫 ترويج غير قانوني",
    "report_spam_promoting": "📢 ترويج آخر",
    "report_other_harassment": "💢 تحرش",
    "report_other_hate": "💢 كراهية",
    "report_other_misinformation": "📢 معلومات خاطئة",
    "report_other_generic": "❓ أخرى",
    "report_personal_details": "🔐 معلومات خاصة",
    "report_copyright": "©️ حقوق النشر",
    "report_not_violation": "⚠️ ليس مخالفاً",
}

WELCOME_MEDIA = {'file_id': None, 'url': None, 'path': None, 'type': None}
if os.path.exists(WELCOME_FILE):
    try:
        with open(WELCOME_FILE, 'r', encoding='utf-8') as f: WELCOME_MEDIA = json.load(f)
    except Exception: pass

def save_welcome_media():
    with open(WELCOME_FILE, 'w', encoding='utf-8') as f:
        json.dump(WELCOME_MEDIA, f, ensure_ascii=False, indent=2)

def set_welcome_media(file_id=None, url=None, path=None, media_type=None):
    WELCOME_MEDIA.update({'file_id': file_id, 'url': url, 'path': path, 'type': media_type})
    save_welcome_media()

def get_welcome_media_to_send():
    if WELCOME_MEDIA.get('path') and os.path.exists(WELCOME_MEDIA['path']):
        try: return open(WELCOME_MEDIA['path'], 'rb'), 'path'
        except Exception: pass
    if WELCOME_MEDIA.get('file_id'): return WELCOME_MEDIA['file_id'], 'file_id'
    if WELCOME_MEDIA.get('url'): return WELCOME_MEDIA['url'], 'url'
    return None, None

REPORT_MEDIA = {'start': None, 'flight': None}
if os.path.exists(REPORT_MEDIA_FILE):
    try:
        with open(REPORT_MEDIA_FILE, 'r', encoding='utf-8') as f:
            saved_report_media = json.load(f)
            if isinstance(saved_report_media, dict):
                REPORT_MEDIA.update(saved_report_media)
    except Exception:
        pass

def save_report_media():
    with open(REPORT_MEDIA_FILE, 'w', encoding='utf-8') as f:
        json.dump(REPORT_MEDIA, f, ensure_ascii=False, indent=2)

def set_report_media(kind, file_id=None):
    if kind in REPORT_MEDIA:
        REPORT_MEDIA[kind] = file_id
        save_report_media()

def send_report_media(chat_id, kind, caption=None):
    """إرسال فيديو حالة اختياري قبل رسالة التقرير، بدون تعطيل التقرير عند الفشل."""
    file_id = REPORT_MEDIA.get(kind)
    if not file_id or not chat_id:
        return {}
    try:
        data = {'chat_id': chat_id, 'video': file_id, 'supports_streaming': True}
        if caption:
            data['caption'] = caption
        return session.post(f"{API_URL}/sendVideo", data=data, timeout=60).json()
    except Exception as e:
        debug_log(f"report media err ({kind}): {e}")
        return {'ok': False}

def debug_log(text):
    try:
        with open("debug.log", "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {text}\n")
    except Exception: pass

# ============================== Event Loop ==============================
pyrogram_loop = None; pyrogram_thread = None; pyrogram_lock = threading.Lock()

def _run_pyrogram_loop():
    global pyrogram_loop
    pyrogram_loop = asyncio.new_event_loop(); asyncio.set_event_loop(pyrogram_loop)
    pyrogram_loop.run_forever()

def init_pyrogram_loop():
    global pyrogram_thread
    with pyrogram_lock:
        if pyrogram_thread is None or not pyrogram_thread.is_alive():
            pyrogram_thread = threading.Thread(target=_run_pyrogram_loop, daemon=True)
            pyrogram_thread.start()
            for _ in range(50):
                if pyrogram_loop is not None: break
                time.sleep(0.01)
    return pyrogram_loop

def run_async(coro_factory, timeout=60):
    loop = init_pyrogram_loop()
    async def wrapper(): return await coro_factory()
    future = asyncio.run_coroutine_threadsafe(wrapper(), loop)
    return future.result(timeout=timeout)

# ============================== حفظ الحسابات ==============================
def save_user_accounts(user_id):
    if user_id in user_data and "accounts" in user_data[user_id]:
        data = []
        for acc in user_data[user_id]["accounts"]:
            data.append({"first_name": acc.get("first_name", "بدون اسم"),
                "id": acc.get("id"), "number": acc.get("number", ""),
                "session_string": acc.get("session_string"),
                "session_type": acc.get("session_type", "pyrogram"),
                "session_file": acc.get("session_file"),
                "api_id": acc.get("api_id"), "api_hash": acc.get("api_hash")})
        accounts_db.upsert({"user_id": user_id, "accounts": data,
                            "updated_at": datetime.now().isoformat()},
                           Query().user_id == user_id)

def load_user_accounts(user_id):
    r = accounts_db.search(Query().user_id == user_id)
    return r[0].get("accounts", []) if r else []

def save_all_accounts():
    for uid in user_data: save_user_accounts(uid)

def _make_default_user():
    return {"accounts": [], "selected_posts": [], "report_type": None,
            "report_reason": None, "channel_invites": {}, "waiting_for": None,
            "temp_target_id": None, "message_count": 10, "target_users": [],
            "user_report_type": None, "report_delay": 1,
            "is_bot_report": False, "bot_target": None,
            "is_private_channel": False, "private_invite": None}

def _ensure_user(user_id):
    if user_id not in user_data:
        user_data[user_id] = _make_default_user()
        saved = load_user_accounts(user_id)
        if saved: user_data[user_id]["accounts"] = saved

def load_all_accounts():
    for entry in accounts_db.all():
        uid = entry["user_id"]
        if uid not in user_data: user_data[uid] = _make_default_user()
        for acc in entry.get("accounts", []):
            client = None; s_str = acc.get("session_string")
            s_type = acc.get("session_type", "pyrogram")
            if s_str:
                try:
                    if s_type == "telethon":
                        if TelegramClient and StringSession:
                            client = TelegramClient(StringSession(s_str),
                                                    int(acc.get("api_id") or API_ID),
                                                    str(acc.get("api_hash") or API_HASH))
                    else:
                        client = Client(f"session_{uid}_{acc.get('id', 0)}",
                                        API_ID, API_HASH, session_string=s_str,
                                        in_memory=True, no_updates=True)
                    if client: run_async(lambda c=client: c.connect(), timeout=20)
                except Exception as e:
                    debug_log(f"restore fail: {e.__class__.__name__}"); client = None
            user_data[uid]["accounts"].append({
                "first_name": acc.get("first_name", "بدون اسم"),
                "id": acc.get("id"), "number": acc.get("number", ""),
                "session_string": s_str, "session_type": s_type,
                "session_file": acc.get("session_file"),
                "api_id": acc.get("api_id"), "api_hash": acc.get("api_hash"),
                "client": client})

# ============================== فحص حالة الحسابات ==============================
def _check_pyrogram_account(account):
    client = account.get("client")
    if client is None: return "no_client", "الحساب مش متحمّل"
    async def verify():
        try:
            await client.get_me(); return "ok", "سليم"
        except Exception as e:
            name = e.__class__.__name__
            if "UserDeactivatedBan" in name: return "banned", "الحساب محظور أو متجمد"
            if "UserDeactivated" in name: return "deleted", "الحساب محذوف"
            if any(x in name for x in ("AuthKeyUnregistered", "SessionRevoked", "AuthKeyDuplicated")):
                return "revoked", "الجلسة اتلغت"
            if "Unauthorized" in name: return "unauthorized", "الجلسة منتهية"
            if "PeerFlood" in name: return "restricted", "الحساب مقيد من الإرسال"
            if "Flood" in name: return "flood", "مقيد مؤقتاً"
            if any(x in name for x in ("Timeout", "Connection", "Network", "ServiceUnavailable")):
                return "network", "خطأ شبكة"
            return "unknown", "خطأ"
    try: return run_async(verify, timeout=25)
    except Exception: return "error", "فشل"

def check_user_sessions(user_id, notify=True):
    accounts = user_data.get(user_id, {}).get("accounts", [])
    removed = []
    results = {"ok": [], "deleted": [], "banned": [], "revoked": [],
               "unauthorized": [], "restricted": [], "flood": [],
               "network": [], "unknown": [], "no_client": [], "error": []}
    for acc in list(accounts):
        status, reason = _check_pyrogram_account(acc)
        label = acc.get("number") or acc.get("first_name") or str(acc.get("id"))
        results.setdefault(status, []).append((label, reason))
        if status in ("deleted", "banned", "revoked", "unauthorized"):
            accounts.remove(acc); removed.append(label)
    if removed: save_user_accounts(user_id)
    if not notify: return removed
    total = len(accounts) + len(removed)
    if total == 0: send_message(user_id, f"{Z('لا توجد حسابات مضافة')}"); return removed
    lines = [f"{decorate_title('فحص حالة الحسابات')}\n", f"📊 {Zakhrafa('إجمالي')}: {total}"]
    if results["ok"]:
        lines.append(f"\n✅ {Zakhrafa('سليم')}: {len(results['ok'])}")
        for label, _ in results["ok"][:20]: lines.append(f"  • {label}")
    if results["deleted"]:
        lines.append(f"\n❌ {Zakhrafa('محذوف')}: {len(results['deleted'])}")
        for label, _ in results["deleted"][:20]: lines.append(f"  • {label} ← اتشال")
    if results["banned"]:
        lines.append(f"\n🧊 {Zakhrafa('محظور/متجمد')}: {len(results['banned'])}")
        for label, _ in results["banned"][:20]: lines.append(f"  • {label} ← اتشال")
    if results["revoked"]:
        lines.append(f"\n🚫 {Zakhrafa('جلسة ملغاة')}: {len(results['revoked'])}")
        for label, _ in results["revoked"][:20]: lines.append(f"  • {label} ← اتشال")
    if results["unauthorized"]:
        lines.append(f"\n🔓 {Zakhrafa('جلسة منتهية')}: {len(results['unauthorized'])}")
        for label, _ in results["unauthorized"][:20]: lines.append(f"  • {label} ← اتشال")
    if results["flood"]: lines.append(f"\n⏳ {Zakhrafa('مقيد مؤقت')}: {len(results['flood'])}")
    if results["restricted"]: lines.append(f"\n🔒 {Zakhrafa('مقيد من الإرسال')}: {len(results['restricted'])}")
    if results["network"]: lines.append(f"\n🌐 {Zakhrafa('خطأ شبكة')}: {len(results['network'])} (مؤقت)")
    if results["no_client"]: lines.append(f"\n⚠️ {Zakhrafa('مش محمّل')}: {len(results['no_client'])}")
    if results["unknown"]: lines.append(f"\n❔ {Zakhrafa('غير معروف')}: {len(results['unknown'])}")
    lines.append(f"\n{DECO_LINE}")
    if removed: lines.append(f"🗑️ {Zakhrafa('تم عزل')}: {len(removed)} حساب")
    else: lines.append(f"✅ {Zakhrafa('كل الحسابات سليمة')}")
    text = "\n".join(lines)
    if len(text) > 4000:
        for i in range(0, len(text), 4000): send_message(user_id, text[i:i+4000])
    else: send_message(user_id, text)
    return removed

def check_all_sessions_on_startup():
    while True:
        for uid in list(user_data):
            try: check_user_sessions(uid, notify=False)
            except Exception: pass
        time.sleep(SESSION_CHECK_INTERVAL)

# ============================== Telegram API ==============================
session = requests.Session()
session.headers.update({'User-Agent': 'Mozilla/5.0'})

def tg_request(method, data=None, retries=3):
    url = f"{API_URL}/{method}"
    for attempt in range(retries):
        try:
            r = session.post(url, json=data, timeout=30) if data else session.get(url, timeout=30)
            r.raise_for_status(); return r.json()
        except requests.exceptions.Timeout: time.sleep(min(2 ** attempt, 10))
        except Exception as e: print(f"req err: {e}", flush=True); return {"ok": False, "description": str(e)}
    return {"ok": False, "description": "retries failed"}

def send_message(chat_id, text, reply_markup=None, parse_mode=None):
    if not chat_id: return {}
    data = {"chat_id": chat_id, "text": text, "disable_web_page_preview": True}
    if parse_mode: data["parse_mode"] = parse_mode
    if reply_markup: data["reply_markup"] = json.dumps(horizontal_keyboard(reply_markup))
    return tg_request("sendMessage", data)

def send_document(chat_id, file_path, caption=None):
    try:
        with open(file_path, "rb") as doc:
            files = {"document": doc}; data = {"chat_id": chat_id}
            if caption: data["caption"] = caption
            return session.post(f"{API_URL}/sendDocument", data=data, files=files, timeout=120).json()
    except Exception as e: return {"ok": False, "description": str(e)}

def edit_message(chat_id, message_id, text, reply_markup=None):
    if not chat_id or not message_id: return {}
    data = {"chat_id": chat_id, "message_id": message_id, "text": text, "disable_web_page_preview": True}
    if reply_markup: data["reply_markup"] = json.dumps(horizontal_keyboard(reply_markup))
    return tg_request("editMessageText", data)

def safe_delete_message(chat_id, message_id):
    try:
        time.sleep(0.3); tg_request("deleteMessage", {"chat_id": chat_id, "message_id": message_id})
    except Exception: pass

def answer_callback(query_id, text=None):
    try:
        data = {"callback_query_id": query_id}
        if text: data["text"] = text; data["show_alert"] = True
        tg_request("answerCallbackQuery", data)
    except Exception: pass

# ============================== أزرار ==============================
def B(text, callback_data=None, url=None, style="primary"):
    if style == "danger": style = "primary"
    b = {"text": text, "style": style}
    if callback_data: b["callback_data"] = callback_data
    if url: b["url"] = url
    return b

def horizontal_keyboard(reply_markup, columns=3):
    if not isinstance(reply_markup, dict):
        return reply_markup
    rows = reply_markup.get("inline_keyboard")
    if not isinstance(rows, list):
        return reply_markup
    buttons = [button for row in rows if isinstance(row, list) for button in row]
    horizontal = [buttons[i:i + columns] for i in range(0, len(buttons), columns)]
    result = dict(reply_markup)
    result["inline_keyboard"] = horizontal
    return result

def get_main_keyboard(user_id):
    kb = {"inline_keyboard": [
        [B("⚡ تشغيل", "start_reporting", style="success"),
         B("🎯 استهداف", "report_on_user", style="primary")],
        [B("➕ إضافة حساب", "add_account", style="primary"),
         B("📊 حساباتي", "show_accounts", style="primary")],
        [B("📞 أرقامي", "show_numbers", style="primary"),
         B("🧪 فحص الجلسات", "check_sessions", style="primary")],
        [B("📌 الأهداف", "select_post", style="primary"),
         B("🤖 بلاغ بوت", "report_bot_menu", style="primary")],
        [B("🔒 قناة خاصة", "report_private_channel", style="primary"),
         B("⏱️ السرعة", "set_sleep", style="primary")],
        [B("⬇️ استخراج", "download_accounts", style="success"),
         B("📤 رفع ZIP/JSON", "upload_sessions_json", style="success")],
        [B("🔢 العدد", "set_count", style="primary"),
         B("🗑️ مسح الكل", "clear_all", style="primary")],
        [B("⏹ إيقاف", "stop_report", style="primary"),
         B("📢 القناة", url=CHANNEL_LINK, style="primary")],
        [B("👨‍💻 المطور", url=OWNER_LINK, style="primary"),
         B("👨‍💻 المطور الثاني", url=SECOND_DEV_LINK, style="primary")],
        ]}
    if is_admin_user(user_id):
        kb["inline_keyboard"].append([
            B("👑 غرفــة القيــادة", "admin_panel", style="primary")])
    return kb

def get_owner_panel_keyboard():
    return {"inline_keyboard": [
        [B("➕ إضــافة عضــو", "add_user", style="success"),
         B("➖ طــرد عضــو", "remove_user", style="danger")],
        [B("👥 ســجل الأعضــاء", "show_all_users", style="primary"),
         B("📢 إذاعــة عامــة", "broadcast", style="primary")],
        [B("📊 تقريــر الأرقــام", "show_stats", style="primary"),
         B("📜 أرشيف العمليــات", "show_logs", style="primary")],
        [B("💾 خزانــة الاحتيــاطي", "backup_menu", style="success"),
         B("🔔 قنــاة التقاريــر", "notify_channel_menu", style="success")],
        [B("🔒 بوابــة الاشتــراك", "force_sub_menu", style="primary"),
         B("👥 مجلــس الإدارة", "show_admins", style="primary")],
        [B("🖼️ واجهــة الترحيــب", "set_welcome_media", style="primary"),
         B("🗑️ حــذف الواجهــة", "delete_welcome_media", style="danger")],
        [B("🎬 فيديو بداية التبليغ", "set_report_start_media", style="primary"),
         B("✈️ فيديو التطيير", "set_report_flight_media", style="danger")],
        [B("➕ ترقيــة مشــرف", "add_admin", style="success"),
         B("➖ تنزيــل مشــرف", "remove_admin", style="danger")],
        [B("🔄 تفريــغ قاعــد البيانــات", "delete_all_users", style="primary")],
        [B("🔙 الرجــوع للرئيسيــة", "back_to_main", style="primary")]]}

def get_backup_menu_keyboard():
    return {"inline_keyboard": [
        [B("➕ توليــد نسخــة", "create_backup_file", style="success")],
        [B("📥 تنزيــل نسخــة", "download_backup_list", style="primary")],
        [B("🔄 تفعيــل نسخــة", "activate_backup_list", style="danger")],
        [B("📤 رفــع نسخــة", "upload_backup", style="danger")],
        [B("🔙 الرجــوع للرئيسيــة", "admin_panel")]]}

def get_report_types_keyboard():
    return {"inline_keyboard": [
        [B("👎 لا يهمنــي", "report_not_interested")],
        [B("🚸 انتهاكــات الأطفــال", "report_child_abuse_menu", style="danger")],
        [B("💥 العنــف والتهديــد", "report_violence_menu", style="danger")],
        [B("🛑 الســلع الممنوعــة", "report_illegal_goods_menu", style="danger")],
        [B("🔞 محتــوى البالغين", "report_illegal_adult_menu", style="danger")],
        [B("🔐 البيانــات الخاصــة", "report_personal_details")],
        [B("🎭 النصــب والاحتيــال", "report_scam_menu", style="danger")],
        [B("©️ حقــوق الملكيــة", "report_copyright")],
        [B("🚫 الإزعــاج والتكــرار", "report_spam_menu")],
        [B("❓ مخالفــات أخــرى", "report_other_menu")],
        [B("⚠️ مخالــف للإزالــة", "report_not_violation")],
        [B("🔙 الرجــوع للرئيسيــة", "back_to_main")]]}

def get_child_abuse_keyboard():
    return {"inline_keyboard": [
        [B("🔞 إساءة جنسية لأطفال", "report_child_abuse_sexual", style="danger")],
        [B("💢 اعتداء جسدي على أطفال", "report_child_abuse_physical", style="danger")],
        [B("🔙 رجــوع", "report_menu")]]}

def get_violence_keyboard():
    return {"inline_keyboard": [
        [B("💢 عنف جسدي", "report_violence_physical", style="danger")],
        [B("🔞 عنف جنسي", "report_violence_sexual", style="danger")],
        [B("💢 عنف نفسي / تحرش", "report_violence_psychological", style="danger")],
        [B("💢 تحريض على عنف", "report_violence_incitement", style="danger")],
        [B("❓ أخرى", "report_violence_other")],
        [B("🔙 رجــوع", "report_menu")]]}

def get_illegal_goods_keyboard():
    return {"inline_keyboard": [
        [B("🔫 أسلحة", "report_illegal_goods_weapons", style="danger")],
        [B("💊 مخدرات", "report_illegal_goods_drugs", style="danger")],
        [B("📄 وثائق مزيفة", "report_illegal_goods_fake_docs", style="danger")],
        [B("💰 مال مزيف", "report_illegal_goods_fake_money", style="danger")],
        [B("💻 أدوات اختراق", "report_illegal_goods_hacking", style="danger")],
        [B("🛍️ بضائع مزيفة", "report_illegal_goods_counterfeit", style="danger")],
        [B("❓ أخرى", "report_illegal_goods_other")],
        [B("🔙 رجــوع", "report_menu")]]}

def get_illegal_adult_keyboard():
    return {"inline_keyboard": [
        [B("🔞 مواد إباحية غير قانونية", "report_adult_illegal_porn", style="danger")],
        [B("🔞 استغلال جنسي", "report_adult_exploitation", style="danger")],
        [B("🔞 مواد إباحية قاصرين", "report_adult_child_porn", style="danger")],
        [B("❓ أخرى", "report_adult_other")],
        [B("🔙 رجــوع", "report_menu")]]}

def get_scam_keyboard():
    return {"inline_keyboard": [
        [B("🎭 انتحال شخصية", "report_scam_impersonation", style="danger")],
        [B("💰 مطالبات مالية خادعة", "report_scam_financial", style="danger")],
        [B("💻 برامج ضارة أو تصيد", "report_scam_malware", style="danger")],
        [B("🛍️ بائع محتال", "report_scam_fraudulent", style="danger")],
        [B("🔙 رجــوع", "report_menu")]]}

def get_spam_keyboard():
    return {"inline_keyboard": [
        [B("📢 إهانات / معلومات مضللة", "report_spam_misleading", style="danger")],
        [B("🚫 ترويج لمحتوى غير قانوني", "report_spam_illegal_promo", style="danger")],
        [B("📢 ترويج لمحتوى آخر", "report_spam_promoting")],
        [B("🔙 رجــوع", "report_menu")]]}

def get_other_keyboard():
    return {"inline_keyboard": [
        [B("💢 تعليقات مسيئة / تحرش", "report_other_harassment", style="danger")],
        [B("💢 محتوى كراهية", "report_other_hate", style="danger")],
        [B("📢 معلومات خاطئة", "report_other_misinformation", style="danger")],
        [B("❓ أخرى", "report_other_generic")],
        [B("🔙 رجــوع", "report_menu")]]}

def get_user_report_types_keyboard():
    return {"inline_keyboard": [
        [B("🚫 إزعــاج", "u_report_spam", style="danger")],
        [B("🎭 حســاب مزيــف", "u_report_fake", style="danger")],
        [B("💥 عنــف", "u_report_violence", style="danger")],
        [B("🔞 محتــوى للكبــار", "u_report_porn", style="danger")],
        [B("🚸 انتهاكــات الأطفــال", "u_report_child", style="danger")],
        [B("🔐 بيانــات خاصــة", "u_report_personal", style="danger")],
        [B("©️ حقــوق النشــر", "u_report_copyright", style="danger")],
        [B("💊 مخــدرات", "u_report_drugs", style="danger")],
        [B("❓ أخــرى", "u_report_other")],
        [B("🔙 الرجــوع للرئيسيــة", "back_to_main")]]}

def get_back_keyboard():
    return {"inline_keyboard": [[B("🔙 الرجــوع للرئيسيــة", "back_to_main")]]}

def get_stop_keyboard():
    return {"inline_keyboard": [[B("⏹ إيقــاف الحمــلة", "stop_report", style="danger")]]}

def get_clear_all_confirm_keyboard():
    return {"inline_keyboard": [
        [B("✅ نعــم، امســح الكــل", "confirm_clear_all", style="danger"),
         B("❌ لا، تراجــع", "cancel_clear_all", style="success")]]}

def get_phone_cancel_keyboard():
    return {"inline_keyboard": [[B("🔙 إلغــاء", "cancel_add_account")]]}

# ============================== إحصائيات ==============================
def load_stats():
    with open(STATS_FILE, 'r', encoding='utf-8') as f: return json.load(f)

def save_stats(stats):
    with open(STATS_FILE, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

def update_user_stats(user_id, reports_sent=0, accounts_added=0, successful=0, failed=0):
    stats = load_stats(); key = str(user_id)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if key not in stats:
        stats[key] = {"total_reports": 0, "total_accounts": 0,
                      "successful": 0, "failed": 0, "last_used": now}
    stats[key]["total_reports"] += reports_sent
    stats[key]["total_accounts"] += accounts_added
    stats[key]["successful"] = stats[key].get("successful", 0) + successful
    stats[key]["failed"] = stats[key].get("failed", 0) + failed
    stats[key]["last_used"] = now
    save_stats(stats)

def is_admin_user(user_id): return user_id == OWNER_ID or user_id in ADMIN_IDS

def delete_all_users():
    db.truncate(); save_stats({}); accounts_db.truncate()

def log_report(user_id, rtype, post, count, status=""):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open("report_log.txt", "a", encoding="utf-8") as f:
            f.write(f"[{now}] U:{user_id} T:{rtype} P:{post} C:{count} S:{status}\n")
    except Exception: pass

def notify_owner(text): send_message(OWNER_ID, f"🔔 إشعار:\n\n{text}")

def get_all_accounts_for_admin(admin_id):
    accounts = []
    for uid, udata in user_data.items():
        if uid == admin_id: continue
        for acc in udata.get("accounts", []):
            if acc.get("client") is not None:
                accounts.append(acc)
    return accounts

# ============================== النسخ الاحتياطي ==============================
def create_backup_file():
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    fn = BACKUP_DIR / f"backup_{stamp}.json"
    data = {"created_at": datetime.now().isoformat(),
            "admins": ADMIN_IDS, "stats": load_stats(),
            "subscriptions": db.all(), "accounts": accounts_db.all(),
            "welcome_media": WELCOME_MEDIA,
            "notify_channel": NOTIFY_CHANNEL, "force_sub": FORCE_SUB}
    with open(fn, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return fn

def list_backups(): return sorted(BACKUP_DIR.glob("backup_*.json"), reverse=True)

def activate_backup_data(data):
    global ADMIN_IDS
    if "admins" in data and data["admins"]:
        ADMIN_IDS = list(data["admins"])
        if OWNER_ID not in ADMIN_IDS: ADMIN_IDS.append(OWNER_ID)
        save_admins()
    if "stats" in data: save_stats(data["stats"])
    if "subscriptions" in data:
        db.truncate()
        for s in data["subscriptions"]: db.insert(s)
    if "accounts" in data:
        accounts_db.truncate()
        for a in data["accounts"]: accounts_db.insert(a)
    if "welcome_media" in data: WELCOME_MEDIA.update(data["welcome_media"]); save_welcome_media()
    if "notify_channel" in data and data["notify_channel"]:
        NOTIFY_CHANNEL.update(data["notify_channel"]); save_notify_channel()
    if "force_sub" in data and data["force_sub"]:
        FORCE_SUB.update(data["force_sub"]); save_force_sub()
    user_data.clear(); load_all_accounts()

def activate_backup_file(path):
    with open(path, "r", encoding="utf-8") as f: data = json.load(f)
    activate_backup_data(data)

def upload_backup_from_telegram(chat_id, document):
    tmp = Path(tempfile.mkdtemp(prefix="restore_"))
    try:
        info = tg_request("getFile", {"file_id": document.get("file_id")})
        if not info.get("ok"): raise RuntimeError("getFile failed")
        url = f"https://api.telegram.org/file/bot{TOKEN}/{info['result']['file_path']}"
        r = session.get(url, stream=True, timeout=120); r.raise_for_status()
        fn = (document.get("file_name") or "backup.json")
        local = tmp / fn
        with open(local, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024*1024):
                if chunk: f.write(chunk)
        saved = BACKUP_DIR / f"uploaded_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{fn}"
        shutil.copy2(local, saved)
        with open(local, "r", encoding="utf-8") as f: data = json.load(f)
        activate_backup_data(data)
        return True, saved.name
    finally: shutil.rmtree(tmp, ignore_errors=True)

# ============================== رفع جلسات JSON / ZIP ==============================
def upload_sessions_json(user_id, chat_id, document):
    fn = (document.get("file_name") or "").lower()
    if not (fn.endswith(".json") or fn.endswith(".zip")):
        send_message(chat_id, "❌ أرسل ملف JSON أو ZIP يحتوي على ملفات الجلسات.",
                     reply_markup=get_back_keyboard())
        return
    tmp = Path(tempfile.mkdtemp(prefix=f"session_json_{user_id}_"))
    try:
        send_message(chat_id, "📥 جاري تنزيل الملف...")
        info = tg_request("getFile", {"file_id": document.get("file_id")})
        if not info.get("ok"): raise RuntimeError("فشل الحصول على الملف")
        url = f"https://api.telegram.org/file/bot{TOKEN}/{info['result']['file_path']}"
        r = session.get(url, timeout=120); r.raise_for_status()

        json_files = []
        session_files = []
        if fn.endswith(".zip"):
            archive = tmp / "sessions.zip"
            archive.write_bytes(r.content)
            with zipfile.ZipFile(archive) as zf:
                for item in zf.infolist():
                    name = Path(item.filename)
                    if item.is_dir() or name.name.startswith('.'):
                        continue
                    safe_name = Path(*[p for p in name.parts if p not in ('', '.', '..')])
                    if not safe_name.name:
                        continue
                    dest = tmp / safe_name
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(item) as src, open(dest, 'wb') as out:
                        shutil.copyfileobj(src, out)
                    if dest.suffix.lower() == '.json': json_files.append(dest)
                    elif dest.suffix.lower() == '.session': session_files.append(dest)
        else:
            local = tmp / "sessions.json"
            local.write_text(r.text, encoding="utf-8")
            json_files.append(local)

        sessions = []
        for json_file in json_files:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if isinstance(data, dict):
                if "accounts" in data and isinstance(data["accounts"], list):
                    sessions.extend(data["accounts"])
                elif "session_string" in data:
                    sessions.append(data)
                else:
                    for v in data.values():
                        if isinstance(v, dict) and (v.get("session_string") or v.get("session")):
                            sessions.append(v)
            elif isinstance(data, list):
                sessions.extend(data)

        for session_file in session_files:
            sessions.append({"session_file": str(session_file), "session_type": "telethon"})

        if not sessions:
            send_message(chat_id, "❌ لم يتم العثور على جلسات JSON أو ملفات .session.",
                         reply_markup=get_back_keyboard()); return

        send_message(chat_id, f"⏳ جاري التحقق من {len(sessions)} جلسة...")
        added = 0; failed = 0
        for it in sessions:
            if not isinstance(it, dict): continue
            try:
                s_type = it.get("session_type", "pyrogram")
                if s_type == "telethon" and TelegramClient and StringSession:
                    source = it.get("session_file")
                    c = TelegramClient(source, int(it.get("api_id") or API_ID),
                                       str(it.get("api_hash") or API_HASH))
                    run_async(lambda cc=c: cc.connect(), timeout=30)
                    me = run_async(lambda cc=c: cc.get_me(), timeout=30)
                    ss = run_async(lambda cc=c: asyncio.sleep(0, result=cc.session.save()), timeout=10)
                    info_acc = {"first_name": me.first_name or "بدون اسم", "id": me.id,
                                "number": getattr(me, "phone", "") or "",
                                "session_string": ss, "session_type": "telethon",
                                "api_id": int(it.get("api_id") or API_ID),
                                "api_hash": str(it.get("api_hash") or API_HASH),
                                "client": c}
                    accounts = user_data[user_id].setdefault("accounts", [])
                    ex = next((a for a in accounts if a.get("id") == info_acc["id"]), None)
                    if ex: ex.update(info_acc)
                    else: accounts.append(info_acc)
                    added += 1
                    continue

                ss = it.get("session_string") or it.get("session")
                if not ss or not isinstance(ss, str): failed += 1; continue
                c = Client(f"tmp_{user_id}_{int(time.time()*1000)}", API_ID, API_HASH,
                           session_string=ss, in_memory=True, no_updates=True)
                run_async(lambda cc=c: cc.connect(), timeout=20)
                me = run_async(lambda cc=c: cc.get_me(), timeout=20)
                info_acc = {"first_name": me.first_name or "بدون اسم",
                            "id": me.id,
                            "number": getattr(me, "phone_number", "") or "",
                            "session_string": ss,
                            "session_type": "pyrogram",
                            "client": c}
                accounts = user_data[user_id].setdefault("accounts", [])
                ex = next((a for a in accounts
                           if a.get("id") == info_acc["id"] or
                           (info_acc["number"] and a.get("number") == info_acc["number"])), None)
                if ex: ex.update(info_acc)
                else: accounts.append(info_acc)
                added += 1
            except Exception as e:
                failed += 1
                debug_log(f"session json import fail: {e.__class__.__name__}")
        if added:
            save_user_accounts(user_id)
            update_user_stats(user_id, accounts_added=added)
        send_message(chat_id,
                     f"✅ تم الرفع\n\n🟢 أضيف: {added}\n⚠️ فشل: {failed}",
                     reply_markup=get_main_keyboard(user_id))
    except Exception as e:
        send_message(chat_id, f"❌ فشل: {e}", reply_markup=get_back_keyboard())
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

# ============================== انضمام قناة خاصة ==============================
def _join_private_channel(user_id, chat_id, invite):
    data = user_data.get(user_id, {})
    if is_admin_user(user_id):
        accounts = get_all_accounts_for_admin(user_id)
        if not accounts: accounts = data.get("accounts", [])
    else:
        accounts = data.get("accounts", [])
    if not accounts:
        send_message(chat_id, "❌ لا توجد حسابات.",
                     reply_markup=get_back_keyboard()); return
    joined = 0; failed = 0
    for acc in accounts:
        client = acc.get("client")
        if client is None: continue
        try:
            async def join():
                await client.join_chat(invite)
            run_async(join, timeout=30)
            joined += 1
        except Exception as e:
            err = str(e).lower()
            if "already" in err or "user_already_participant" in err:
                joined += 1
            else:
                failed += 1
                debug_log(f"join fail: {e.__class__.__name__}")
    user_data[user_id]["waiting_for"] = "private_msg_links"
    send_message(chat_id,
                 f"✅ تم الانضمام\n\n"
                 f"🟢 نجح: {joined}\n⚠️ فشل: {failed}\n\n"
                 f"📌 أرسل الآن **روابط الرسايل** من القناة الخاصة.\n\n"
                 f"**مثال:**\n`https://t.me/c/1234567890/123`\n"
                 f"`https://t.me/c/1234567890/456`\n\n"
                 f"⚠️ كل رابط في سطر لوحده.",
                 reply_markup=get_back_keyboard(),
                 parse_mode="Markdown")

# ============================== قناة الإشعارات ==============================
NOTIFY_CHANNEL_FILE = 'notify_channel.json'; SENT_NOTIF_FILE = 'sent_notifications.json'
NOTIFY_CHANNEL = {'id': None, 'username': None}
if os.path.exists(NOTIFY_CHANNEL_FILE):
    try:
        with open(NOTIFY_CHANNEL_FILE, 'r', encoding='utf-8') as f: NOTIFY_CHANNEL = json.load(f)
    except Exception: pass
if not os.path.exists(SENT_NOTIF_FILE):
    with open(SENT_NOTIF_FILE, 'w', encoding='utf-8') as f: json.dump([], f)

def save_notify_channel():
    with open(NOTIFY_CHANNEL_FILE, 'w', encoding='utf-8') as f:
        json.dump(NOTIFY_CHANNEL, f, ensure_ascii=False, indent=2)

def set_notify_channel(channel_id, username=None):
    NOTIFY_CHANNEL['id'] = channel_id; NOTIFY_CHANNEL['username'] = username
    save_notify_channel()

def _load_sent_notifs():
    try:
        with open(SENT_NOTIF_FILE, 'r', encoding='utf-8') as f: return json.load(f)
    except Exception: return []

def _save_sent_notifs(lst):
    try:
        with open(SENT_NOTIF_FILE, 'w', encoding='utf-8') as f: json.dump(lst[-1000:], f)
    except Exception: pass

def was_notification_sent(key): return key in _load_sent_notifs()

def mark_notification_sent(key):
    sent = _load_sent_notifs()
    if key not in sent: sent.append(key); _save_sent_notifs(sent)

def notify_channel_report(user_id, username, channel_link, report_type, success_count, flight_reasons=None):
    if not NOTIFY_CHANNEL.get('id'): return
    if not flight_reasons: return
    key = f"{user_id}|{channel_link}|{report_type}|{len(flight_reasons)}|{flight_reasons[0]}"
    if was_notification_sent(key): return
    ft = "\n┃ ✈️ " + Zakhrafa("سبب التطير") + ":\n"
    for r in list(set(flight_reasons))[:6]: ft += f"┃   • {r}\n"
    text = (f"╭━━━❰ 🎯 {Zakhrafa('تم التطير')} ❱━━━╮\n┃\n"
            f"┃ 👤 {Zakhrafa('المستخدم')}: {username or user_id}\n"
            f"┃ 🆔 {Zakhrafa('الآيدي')}: {user_id}\n"
            f"┃ 🔗 {Zakhrafa('الرابط')}: {channel_link}\n"
            f"┃ 🏷️ {Zakhrafa('النوع')}: {report_type}\n"
            f"┃ ✅ {Zakhrafa('نجح')}: {success_count}\n{ft}"
            f"┃ 🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n┃\n"
            f"╰━━━━━━━━━━━━━━━━━━━━━━━━╯")
    result = send_message(NOTIFY_CHANNEL['id'], text)
    if result.get('ok'): mark_notification_sent(key)

# ============================== الاشتراك الإجباري ==============================
FORCE_SUB_FILE = 'force_sub.json'
FORCE_SUB = {'channel': None, 'username': None, 'link': None}
if os.path.exists(FORCE_SUB_FILE):
    try:
        with open(FORCE_SUB_FILE, 'r', encoding='utf-8') as f: FORCE_SUB = json.load(f)
    except Exception: pass

def save_force_sub():
    with open(FORCE_SUB_FILE, 'w', encoding='utf-8') as f:
        json.dump(FORCE_SUB, f, ensure_ascii=False, indent=2)

def set_force_sub(channel, username=None, link=None):
    FORCE_SUB['channel'] = channel; FORCE_SUB['username'] = username; FORCE_SUB['link'] = link
    save_force_sub()

def remove_force_sub():
    FORCE_SUB['channel'] = None; FORCE_SUB['username'] = None; FORCE_SUB['link'] = None
    save_force_sub()

def check_user_joined(user_id):
    if not FORCE_SUB.get('channel'): return True
    try:
        r = tg_request("getChatMember", {"chat_id": FORCE_SUB['channel'], "user_id": user_id})
        if r.get('ok'):
            return r['result'].get('status', '') in ('creator', 'administrator', 'member', 'restricted')
        return False
    except Exception: return True

def send_force_sub_message(chat_id, user_id):
    channel_link = FORCE_SUB.get('link') or (
        f"https://t.me/{FORCE_SUB['username']}" if FORCE_SUB.get('username') else None)
    if not channel_link: return
    text = (f"╭━━━❰ 🔒 {Zakhrafa('اشتراك إجباري')} ❱━━━╮\n┃\n"
            f"┃ ⚠️ {Zakhrafa('لازم تشترك في القناة')}\n"
            f"┃ {Zakhrafa('قبل ما تستخدم البوت')}\n┃\n"
            f"┃ 👇 {Zakhrafa('اضغط على الزر تحت')}\n┃\n"
            f"╰━━━━━━━━━━━━━━━━━━━━━━╯")
    kb = {"inline_keyboard": [
        [B("📢 اشترك في القناة", url=channel_link, style="success")],
        [B("✅ تحققت من الاشتراك", "check_force_sub", style="primary")]]}
    send_message(chat_id, text, reply_markup=kb)

# ============================== تبليغات ==============================
def get_reporting_status_text(succ, fail, accs, elapsed):
    h = elapsed // 3600; m = (elapsed % 3600) // 60; s = elapsed % 60
    t = f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"
    return (f"⚡ {Z('جاري الإبلاغ')}\n\n✅ نجح: {succ}\n❌ فشل: {fail}\n"
            f"👤 حسابات: {accs}\n⏱ مضى: {t}\n🕐 {datetime.now().strftime('%H:%M:%S')}")

def get_report_reason_class(rtype, reason_text):
    if rtype.startswith("child_abuse"): return InputReportReasonChildAbuse()
    if rtype.startswith("violence"): return InputReportReasonViolence()
    if rtype.startswith("drugs"): return InputReportReasonIllegalDrugs()
    if rtype in ("illegal_goods_fake_docs", "illegal_goods_fake_money", "scam_impersonation"):
        return InputReportReasonFake()
    if rtype.startswith("illegal_goods"): return InputReportReasonOther(text=reason_text or "Illegal goods/services")
    if rtype.startswith("adult"): return InputReportReasonPornography()
    if rtype == "personal_details": return InputReportReasonPersonalDetails()
    if rtype.startswith("scam"): return InputReportReasonOther(text=reason_text or "Scam/Fraud")
    if rtype == "copyright": return InputReportReasonCopyright()
    if rtype.startswith("spam"): return InputReportReasonSpam()
    return InputReportReasonOther(text=reason_text or "Report")

def get_user_report_reason(rtype, reason_text=""):
    m = {"spam": InputReportReasonSpam, "fake": InputReportReasonFake,
         "violence": InputReportReasonViolence, "porn": InputReportReasonPornography,
         "child": InputReportReasonChildAbuse, "personal": InputReportReasonPersonalDetails,
         "copyright": InputReportReasonCopyright, "drugs": InputReportReasonIllegalDrugs}
    if rtype in m: return m[rtype]()
    return InputReportReasonOther(text=reason_text or "بلاغ تلقائي")

async def check_channel_alive(client, channel_id):
    try:
        chat = await client.get_chat(channel_id)
        if chat is None: return False, "✈️ الهدف مش موجود"
        return True, "alive"
    except Exception as e:
        name = e.__class__.__name__; err = str(e).lower()
        FLIGHT = {
            "ChannelPrivate": "🔐 القناة بقت خاصة",
            "UsernameNotOccupied": "❌ القناة اتحذفت",
            "UsernameInvalid": "❌ اليوزر غير صالح",
            "ChannelInvalid": "❌ القناة غير موجودة",
            "PeerIdInvalid": "❌ القناة اتحذفت",
            "ChannelBanned": "🔒 القناة اتحظرت",
            "ChatForbidden": "🚫 الوصول للقناة ممنوع",
            "ChatAdminRequired": "🚫 القناة اتشالت",
            "UserBannedInChannel": "🚫 القناة اتحظرت",
        }
        for k, msg in FLIGHT.items():
            if k in name or k.lower() in err: return False, f"✈️ {msg}"
        if any(x in name for x in ("Timeout", "Connection", "Network", "ServiceUnavailable")):
            return True, "network"
        return True, "unknown"

async def check_user_alive(client, target):
    try:
        users = await client.get_users(target)
        if users is None: return False, "✈️ الهدف مش موجود"
        return True, "alive"
    except Exception as e:
        name = e.__class__.__name__; err = str(e).lower()
        FLIGHT = {
            "UserDeactivatedBan": "🧊 الهدف اتجمد",
            "UserDeactivated": "❌ الهدف اتحذف",
            "AccountBanned": "⛔ الهدف محظور",
            "PeerIdInvalid": "❌ الهدف اتحذف",
            "UsernameNotOccupied": "❌ الهدف اتحذف",
            "UsernameInvalid": "❌ اليوزر غير صالح",
        }
        for k, msg in FLIGHT.items():
            if k in name or k.lower() in err: return False, f"✈️ {msg}"
        if any(x in name for x in ("Timeout", "Connection", "Network")):
            return True, "network"
        return True, "unknown"

async def send_real_report(client, channel_id, msg_id, rtype, reason):
    try:
        peer = await client.resolve_peer(channel_id)
        await client.invoke(Report(peer=peer, id=[msg_id],
                                   reason=get_report_reason_class(rtype, reason),
                                   message=reason))
        return True, "SUCCESS", False
    except Exception as e:
        name = e.__class__.__name__; err_text = str(e).lower()
        FLIGHT = {
            "ChannelPrivate": "🔐 القناة بقت خاصة",
            "ChannelInvalid": "❌ القناة اتحذفت",
            "UsernameNotOccupied": "❌ القناة اتحذفت",
            "ChannelBanned": "🔒 القناة اتحظرت",
            "ChatAdminRequired": "🚫 القناة اتشالت",
            "PeerIdInvalid": "❌ القناة اتحذفت",
        }
        for k, msg in FLIGHT.items():
            if k in name or k.lower() in err_text:
                return False, f"✈️ {msg}", True
        if any(x in name for x in ("PeerFlood", "ChatWriteForbidden",
                                    "UserBannedInChannel", "FloodWait",
                                    "SlowmodeWait", "AuthKeyUnregistered",
                                    "SessionRevoked", "UserDeactivatedBan")):
            return False, f"حساب: {name}", False
        return False, str(e), False

async def send_real_user_report(client, target, rtype, reason):
    try:
        peer = await client.resolve_peer(target)
        await client.invoke(ReportPeer(peer=peer,
                                       reason=get_user_report_reason(rtype, reason),
                                       message=reason or ""))
        return True, "SUCCESS", False
    except Exception as e:
        name = e.__class__.__name__; err_text = str(e).lower()
        FLIGHT = {
            "UserDeactivatedBan": "🧊 الهدف اتجمد",
            "UserDeactivated": "❌ الهدف اتحذف",
            "AccountBanned": "⛔ الهدف محظور",
            "PeerIdInvalid": "❌ الهدف اتحذف",
            "UsernameNotOccupied": "❌ الهدف اتحذف",
            "UsernameInvalid": "❌ اليوزر غير صالح",
        }
        for k, msg in FLIGHT.items():
            if k in name or k.lower() in err_text:
                return False, f"✈️ {msg}", True
        if any(x in name for x in ("PeerFlood", "ChatWriteForbidden",
                                    "FloodWait", "SlowmodeWait",
                                    "AuthKeyUnregistered", "SessionRevoked")):
            return False, f"حساب: {name}", False
        return False, str(e), False

async def join_channel(client, channel_id, invite_link=None):
    try:
        await client.join_chat(invite_link) if invite_link else await client.join_chat(channel_id)
        return True, "joined"
    except Exception as e:
        if "already" in str(e).lower(): return True, "already"
        return False, str(e)

# ============================== تشغيل كل الحسابات مرة واحدة ==============================
async def _report_all_at_once(clients, coro_factory):
    """
    تنفيذ البلاغ من كل الحسابات في نفس الوقت (بالتوازي).
    coro_factory(client) -> coroutine ترجع (ok, status, is_flight)
    ترجع: (نجح, فشل, أسباب التطير, هل طار)
    """
    async def one(c):
        try:
            return await coro_factory(c)
        except Exception as e:
            return (False, str(e), False)

    results = await asyncio.gather(*(one(c) for c in clients),
                                   return_exceptions=True)
    succ = fail = 0
    reasons = []
    flew = False
    for r in results:
        if isinstance(r, Exception):
            fail += 1
            continue
        ok, st, is_flight = r
        if ok:
            succ += 1
        elif is_flight:
            succ += 1
            reasons.append(st)
            flew = True
        else:
            fail += 1
    return succ, fail, reasons, flew

async def perform_real_reporting(user_id, chat_id, status_message_id):
    is_reporting[user_id] = True
    data = user_data.get(user_id, {})

    # ===== بلاغ على بوت =====
    if data.get("is_bot_report"):
        bot_target = data.get("bot_target", {})
        bot_user = bot_target.get("username")
        msg_ids = bot_target.get("msg_ids", [])
        reason = data.get("report_reason", "بلاغ تلقائي")
        count = data.get("message_count", 10)
        delay = data.get("report_delay", report_delay)
        if is_admin_user(user_id):
            accounts = get_all_accounts_for_admin(user_id)
            if not accounts: accounts = data.get("accounts", [])
        else:
            accounts = data.get("accounts", [])
        clients = [a["client"] for a in accounts if a.get("client")]
        succ = 0; fail = 0; start = time.time()
        flight_reasons = []; target_flowed = False
        edit_message(chat_id, status_message_id,
                     get_reporting_status_text(0, 0, len(accounts), 0),
                     reply_markup=get_stop_keyboard())
        for msg_id in msg_ids:
            if not is_reporting.get(user_id): break
            for i in range(count):
                if not is_reporting.get(user_id): break
                if clients:
                    s, f, rs, flew = await _report_all_at_once(
                        clients,
                        lambda c, mu=bot_user, r=reason:
                            send_real_user_report(c, mu, "other", r))
                    succ += s; fail += f; flight_reasons.extend(rs)
                    if flew:
                        target_flowed = True
                        is_reporting[user_id] = False
                try:
                    edit_message(chat_id, status_message_id,
                                 get_reporting_status_text(succ, fail, len(accounts),
                                                           int(time.time() - start)),
                                 reply_markup=get_stop_keyboard())
                except Exception: pass
                if target_flowed: break
                await asyncio.sleep(delay)
            if target_flowed: break
        is_reporting[user_id] = False
        elapsed = int(time.time() - start)
        update_user_stats(user_id, reports_sent=succ+fail, successful=succ, failed=fail)
        final = (f"╭━━━❰ 🎯 {Zakhrafa('انتهى البلاغ على البوت')} ❱━━━╮\n┃\n"
                 f"┃ 🤖 @{bot_user}\n┃ 📩 الرسائل: {len(msg_ids)}\n"
                 f"┃ ✅ نجح: {succ}\n┃ ❌ فشل: {fail}\n"
                 f"┃ ⏱ {elapsed} ثانية\n┃\n"
                 f"╰━━━━━━━━━━━━━━━━━━━━━━━━╯")
        edit_message(chat_id, status_message_id, final,
                     reply_markup=get_main_keyboard(user_id))
        for k in ("is_bot_report", "bot_target"):
            user_data[user_id].pop(k, None)
        return

    # ===== البلاغ العادي (قناة عامة/خاصة) =====
    posts = data.get("selected_posts", [])
    rtype = data.get("report_type", "other"); reason = data.get("report_reason", "")
    count = data.get("message_count", 10); delay = data.get("report_delay", report_delay)

    if is_admin_user(user_id):
        accounts = get_all_accounts_for_admin(user_id)
        if not accounts: accounts = data.get("accounts", [])
    else:
        accounts = data.get("accounts", [])

    clients = [a["client"] for a in accounts if a.get("client")]
    succ = 0; fail = 0; start = time.time()
    flight_reasons = []; target_flowed = False; flown_link = None

    send_report_media(chat_id, "start", "🚀 بدأ التبليغ")
    edit_message(chat_id, status_message_id, get_reporting_status_text(0, 0, len(accounts), 0),
                 reply_markup=get_stop_keyboard())

    for link in posts:
        if not is_reporting.get(user_id): break
        try:
            if "/c/" in link:
                parts = link.split("/"); raw_id = parts[-2].replace("c", "")
                ch_id = int(f"-100{abs(int(raw_id))}"); msg_id = int(parts[-1])
            else:
                parts = link.split("/"); ch_id = parts[-2]; msg_id = int(parts[-1])
        except Exception: continue

        # فحص الهدف بحساب واحد
        if clients:
            alive, why = await check_channel_alive(clients[0], ch_id)
            if not alive:
                target_flowed = True; flown_link = link; flight_reasons.append(why); break

        # كل الحسابات تنضم للقناة في نفس الوقت
        if clients:
            await asyncio.gather(
                *(join_channel(c, ch_id) for c in clients),
                return_exceptions=True)

        for i in range(count):
            if not is_reporting.get(user_id): break
            if i > 0 and i % 2 == 0 and clients:
                chk_client = clients[i % len(clients)]
                alive, why = await check_channel_alive(chk_client, ch_id)
                if not alive:
                    target_flowed = True; flown_link = link; flight_reasons.append(why)
                    is_reporting[user_id] = False; break
            if target_flowed: break

            # 🚀 كل الحسابات تبعت في نفس الوقت
            if clients:
                s, f, rs, flew = await _report_all_at_once(
                    clients,
                    lambda c, ci=ch_id, mi=msg_id, rt=rtype, rs_=reason:
                        send_real_report(c, ci, mi, rt, rs_))
                succ += s; fail += f; flight_reasons.extend(rs)
                if flew:
                    target_flowed = True; flown_link = link
                    is_reporting[user_id] = False
                    break

            try:
                edit_message(chat_id, status_message_id,
                             get_reporting_status_text(succ, fail, len(accounts), int(time.time() - start)),
                             reply_markup=get_stop_keyboard())
            except Exception: pass
            if target_flowed: break
            await asyncio.sleep(delay)
        if target_flowed: break

    is_reporting[user_id] = False
    elapsed = int(time.time() - start)
    update_user_stats(user_id, reports_sent=succ + fail, successful=succ, failed=fail)

    if target_flowed:
        final_text = (f"╭━━━❰ 🎯 {Zakhrafa('تم التطير')} ❱━━━╮\n┃\n"
                      f"┃ 🎉 {Zakhrafa('الهدف طار فعلاً')}\n┃ 🔗 {flown_link}\n"
                      f"┃ {flight_reasons[-1] if flight_reasons else 'تم'}\n┃\n"
                      f"┃ ✅ {Zakhrafa('نجح')}: {succ}\n┃ ❌ {Zakhrafa('فشل')}: {fail}\n"
                      f"┃ ⏱ {Zakhrafa('المدة')}: {elapsed} ثانية\n┃\n"
                      f"╰━━━━━━━━━━━━━━━━━━━━━━━━╯")
    else:
        final_text = (f"{Z('انتهى الإبلاغ')}\n\n✅ نجح: {succ}\n❌ فشل: {fail}\n"
                      f"👤 حسابات: {len(accounts)}\n⏱ {elapsed} ثانية")

    if target_flowed:
        send_report_media(chat_id, "flight", "✈️ تم التطيير")
    edit_message(chat_id, status_message_id, final_text, reply_markup=get_main_keyboard(user_id))
    if flight_reasons:
        try:
            username = user_data.get(user_id, {}).get("username")
            for link in (posts if not flown_link else [flown_link]):
                notify_channel_report(user_id, username, link, rtype, succ, flight_reasons)
        except Exception as e: debug_log(f"notify_channel err: {e}")
    if target_flowed:
        send_report_media(OWNER_ID, "flight", "✈️ تم التطيير")
    notify_owner(f"📊 تقرير تبليغ\n👤 {user_id}\n✅ {succ} | ❌ {fail}\n"
                 f"✈️ تطير: {'آه' if target_flowed else 'لأ'}")

    user_data[user_id].pop("is_private_channel", None)
    user_data[user_id].pop("private_invite", None)

async def perform_user_reporting(user_id, chat_id, status_message_id):
    is_reporting[user_id] = True
    data = user_data.get(user_id, {})
    targets = data.get("target_users", [])
    rtype = data.get("user_report_type", "other"); reason = data.get("report_reason", "")
    count = data.get("message_count", 10); delay = data.get("report_delay", report_delay)

    if is_admin_user(user_id):
        accounts = get_all_accounts_for_admin(user_id)
        if not accounts: accounts = data.get("accounts", [])
    else:
        accounts = data.get("accounts", [])

    clients = [a["client"] for a in accounts if a.get("client")]
    succ = 0; fail = 0; start = time.time()
    flight_reasons = []; target_flowed = False; flown_target = None

    send_report_media(chat_id, "start", "🚀 بدأ التبليغ")
    edit_message(chat_id, status_message_id, get_reporting_status_text(0, 0, len(accounts), 0),
                 reply_markup=get_stop_keyboard())

    for t in targets:
        if not is_reporting.get(user_id): break
        target = t.strip()
        if "t.me/" in target:
            target = target.split("t.me/")[-1].split("/")[0].split("?")[0]
        target = target.lstrip("@")

        if clients:
            alive, why = await check_user_alive(clients[0], target)
            if not alive:
                target_flowed = True; flown_target = target; flight_reasons.append(why); break

        for i in range(count):
            if not is_reporting.get(user_id): break
            if i > 0 and i % 2 == 0 and clients:
                chk_client = clients[i % len(clients)]
                alive, why = await check_user_alive(chk_client, target)
                if not alive:
                    target_flowed = True; flown_target = target; flight_reasons.append(why)
                    is_reporting[user_id] = False; break
            if target_flowed: break

            # 🚀 كل الحسابات تبعت البلاغ على المستخدم في نفس الوقت
            if clients:
                s, f, rs, flew = await _report_all_at_once(
                    clients,
                    lambda c, tg=target, rt=rtype, rs_=reason:
                        send_real_user_report(c, tg, rt, rs_))
                succ += s; fail += f; flight_reasons.extend(rs)
                if flew:
                    target_flowed = True; flown_target = target
                    is_reporting[user_id] = False
                    break

            try:
                edit_message(chat_id, status_message_id,
                             get_reporting_status_text(succ, fail, len(accounts), int(time.time() - start)),
                             reply_markup=get_stop_keyboard())
            except Exception: pass
            if target_flowed: break
            await asyncio.sleep(delay)
        if target_flowed: break

    is_reporting[user_id] = False
    elapsed = int(time.time() - start)
    update_user_stats(user_id, reports_sent=succ + fail, successful=succ, failed=fail)

    if target_flowed:
        final_text = (f"╭━━━❰ 🎯 {Zakhrafa('تم التطير')} ❱━━━╮\n┃\n"
                      f"┃ 🎉 {Zakhrafa('المستخدم طار')}\n┃ 👤 {flown_target}\n"
                      f"┃ {flight_reasons[-1] if flight_reasons else 'تم'}\n┃\n"
                      f"┃ ✅ {Zakhrafa('نجح')}: {succ}\n┃ ❌ {Zakhrafa('فشل')}: {fail}\n"
                      f"┃ ⏱ {Zakhrafa('المدة')}: {elapsed} ثانية\n┃\n"
                      f"╰━━━━━━━━━━━━━━━━━━━━━━━━╯")
    else:
        final_text = (f"{Z('انتهى الإبلاغ على المستخدمين')}\n\n✅ نجح: {succ}\n❌ فشل: {fail}\n"
                      f"👤 حسابات: {len(accounts)}\n🎯 أهداف: {len(targets)}\n⏱ {elapsed} ثانية")
    if target_flowed:
        send_report_media(chat_id, "flight", "✈️ تم التطيير")
    edit_message(chat_id, status_message_id, final_text, reply_markup=get_main_keyboard(user_id))
    if flight_reasons:
        try:
            username = user_data.get(user_id, {}).get("username")
            for target in (targets if not flown_target else [flown_target]):
                notify_channel_report(user_id, username, target, rtype, succ, flight_reasons)
        except Exception as e: debug_log(f"notify_channel err: {e}")
    if target_flowed:
        send_report_media(OWNER_ID, "flight", "✈️ تم التطيير")
    notify_owner(f"📊 تقرير مستخدمين\n👤 {user_id}\n✅ {succ} | ❌ {fail}\n"
                 f"✈️ تطير: {'آه' if target_flowed else 'لأ'}")

# ============================== البداية ==============================
def send_welcome(chat_id, first_name, user_id):
    stats = load_stats().get(str(user_id), {})
    accs = len(user_data.get(user_id, {}).get("accounts", []))
    caption = (f"{decorate_title('بوت الشد الداخلي المتطور')}\n"
               f"✨ {BOT_VERSION} ✨\n\n📱 أهلاً {first_name}\n"
               f"{DECO_LINE}\n📊 حساباتك: {accs}\n"
               f"📈 إجمالي بلاغاتك: {stats.get('total_reports', 0)}\n"
               f"✅ ناجح: {stats.get('successful', 0)}\n"
               f"❌ فاشل: {stats.get('failed', 0)}\n"
               f"{DECO_LINE}\n\n👋 اختر من الأزرار أدناه")
    media, mtype = get_welcome_media_to_send()
    if media:
        try:
            if mtype == 'video':
                r = session.post(f"{API_URL}/sendVideo",
                                 data={"chat_id": chat_id, "video": media,
                                       "caption": caption,
                                       "supports_streaming": True,
                                       "reply_markup": json.dumps(horizontal_keyboard(get_main_keyboard(user_id)))}, timeout=60)
                if r.json().get('ok'): return
            elif mtype == 'file_id' or (mtype == 'path' and
                                      str(WELCOME_MEDIA.get('path', '')).lower().endswith(('.gif', '.mp4'))):
                r = session.post(f"{API_URL}/sendAnimation",
                                 data={"chat_id": chat_id, "animation": media,
                                       "caption": caption,
                                       "reply_markup": json.dumps(horizontal_keyboard(get_main_keyboard(user_id)))}, timeout=30)
                if r.json().get("ok"): return
            if mtype == 'path':
                with open(WELCOME_MEDIA['path'], 'rb') as f:
                    r = session.post(f"{API_URL}/sendPhoto",
                                     data={"chat_id": chat_id, "caption": caption,
                                           "reply_markup": json.dumps(horizontal_keyboard(get_main_keyboard(user_id)))},
                                     files={"photo": f}, timeout=30)
                    if r.json().get("ok"): return
            elif mtype == 'url':
                r = session.post(f"{API_URL}/sendPhoto",
                                 data={"chat_id": chat_id, "photo": media, "caption": caption,
                                       "reply_markup": json.dumps(horizontal_keyboard(get_main_keyboard(user_id)))}, timeout=30)
                if r.json().get("ok"): return
            elif mtype == 'file_id':
                r = session.post(f"{API_URL}/sendPhoto",
                                 data={"chat_id": chat_id, "photo": media, "caption": caption,
                                       "reply_markup": json.dumps(horizontal_keyboard(get_main_keyboard(user_id)))}, timeout=30)
                if r.json().get("ok"): return
        except Exception as e: debug_log(f"welcome media err: {e}")
    send_message(chat_id, caption, reply_markup=get_main_keyboard(user_id))

def handle_start(user_id, chat_id, first_name):
    _ensure_user(user_id); send_welcome(chat_id, first_name, user_id)

# ============================== Callback ==============================
def handle_callback(query):
    try:
        user_id = query["from"]["id"]; data = query["data"]; qid = query["id"]
        chat_id = user_id; message_id = None
        if query.get("message"):
            chat_id = query["message"]["chat"]["id"]; message_id = query["message"]["message_id"]
        answer_callback(qid); _ensure_user(user_id)

        if not is_admin_user(user_id) and not check_user_joined(user_id):
            if data != "check_force_sub":
                send_force_sub_message(chat_id, user_id); return

        if data == "back_to_main":
            user_data[user_id]["waiting_for"] = None
            send_welcome(chat_id, query["from"].get("first_name", "User"), user_id)

        elif data == "admin_panel":
            if is_admin_user(user_id):
                send_message(chat_id, decorate_title("لوحة الأدمن"),
                             reply_markup=get_owner_panel_keyboard())

        elif data == "add_account":
            user_data[user_id]["waiting_for"] = "add_account_phone"
            user_data[user_id]["temp_client"] = None
            user_data[user_id]["temp_phone"] = None
            user_data[user_id]["temp_phone_hash"] = None
            send_message(chat_id,
                         f"{decorate_title('إضافة حساب جديد')}\n\n"
                         "📱 أرسل الآن **رقم الهاتف** بصيغة دولية.\n\n"
                         "مثال:\n`+201234567890`\n\n⚠️ يجب أن يحتوي على كود الدولة.",
                         reply_markup=get_phone_cancel_keyboard(), parse_mode="Markdown")

        elif data == "cancel_add_account":
            tmp_c = user_data[user_id].get("temp_client")
            if tmp_c:
                try: run_async(lambda c=tmp_c: c.disconnect(), timeout=10)
                except Exception: pass
            user_data[user_id]["temp_client"] = None
            user_data[user_id]["temp_phone"] = None
            user_data[user_id]["temp_phone_hash"] = None
            user_data[user_id]["waiting_for"] = None
            send_message(chat_id, "❌ تم إلغاء إضافة الحساب.",
                         reply_markup=get_main_keyboard(user_id))

        elif data == "show_numbers":
            accs = user_data.get(user_id, {}).get("accounts", [])
            nums = [a.get("number") or f"ID:{a.get('id')}" for a in accs]
            txt = f"{Z('أرقامك')}\n\n" + ("\n".join(f"{i}. {n}" for i, n in enumerate(nums, 1))
                                          if nums else "لا توجد أرقام.")
            send_message(chat_id, txt, reply_markup=get_back_keyboard())

        elif data == "show_accounts":
            accs = user_data.get(user_id, {}).get("accounts", [])
            if not accs:
                send_message(chat_id, "❌ لا توجد حسابات.", reply_markup=get_back_keyboard())
            else:
                kb = {"inline_keyboard": []}
                for a in accs:
                    name = a.get("first_name", "بدون اسم"); num = a.get("number", "")
                    dn = f"{name} ({num})" if num else name
                    kb["inline_keyboard"].append([B(f"🗑️ حذف {dn}", f"delete_account_{a.get('id', 0)}")])
                send_message(chat_id, f"{Z('حساباتك')}", reply_markup=kb)

        elif data.startswith("delete_account_"):
            aid = int(data.split("_")[-1])
            accs = user_data[user_id]["accounts"]
            for i, a in enumerate(accs):
                if a.get("id") == aid:
                    try:
                        if a.get("client"): run_async(lambda c=a["client"]: c.stop(), timeout=10)
                    except Exception: pass
                    del accs[i]; save_user_accounts(user_id); break
            send_message(chat_id, "✅ تم الحذف.", reply_markup=get_back_keyboard())

        elif data == "check_sessions":
            send_message(chat_id, "🧪 بدأ الفحص...")
            threading.Thread(target=check_user_sessions, args=(user_id,), daemon=True).start()

        elif data == "download_accounts":
            accs = user_data.get(user_id, {}).get("accounts", [])
            if not accs:
                send_message(chat_id, "❌ لا توجد حسابات لتحميلها.",
                             reply_markup=get_back_keyboard()); return
            lines = []
            for i, a in enumerate(accs, 1):
                lines.append(f"# {i}. {a.get('first_name', 'بدون اسم')}")
                lines.append(f"ID: {a.get('id')}")
                lines.append(f"Number: {a.get('number', '')}")
                lines.append(f"Session: {a.get('session_string', '')}")
                lines.append("")
            fn = f"accounts_{user_id}_{int(time.time())}.txt"
            try:
                with open(fn, "w", encoding="utf-8") as f: f.write("\n".join(lines))
                send_document(chat_id, fn, caption=f"⬇️ نسخة من {len(accs)} حساب")
                os.remove(fn)
            except Exception as e:
                send_message(chat_id, f"❌ فشل التحميل: {e}", reply_markup=get_back_keyboard())

        elif data == "upload_sessions_json":
            user_data[user_id]["waiting_for"] = "upload_sessions_json"
            send_message(chat_id,
                         f"{Z('رفع جلسات JSON أو ZIP')}\n\n"
                         "📤 أرسل ملف JSON فيه session_strings أو ملف ZIP للجلسات.\n"
                         "الصيغ المدعومة:\n"
                         "• `{\"accounts\": [{...}]}`\n"
                         "• `[{\"session_string\": \"...\"}]`\n"
                         "• `{\"session_string\": \"...\"}`\n"
                         "• ملفات `.session` داخل ZIP",
                         reply_markup=get_back_keyboard())

        elif data == "select_post":
            user_data[user_id]["waiting_for"] = "select_post"
            user_data[user_id]["is_private_channel"] = False
            send_message(chat_id, "📌 أرسل روابط المنشورات (سطر لكل رابط).",
                         reply_markup=get_back_keyboard())

        elif data == "report_bot_menu":
            user_data[user_id]["waiting_for"] = "bot_target_username"
            send_message(chat_id,
                         f"{decorate_title('بلاغ على بوت')}\n\n"
                         "1️⃣ أرسل **يوزر البوت** اللي عايز تبلّغ على رسايله.\n\n"
                         "مثال: `@SpamBot`\n"
                         "أو: `SpamBot`",
                         reply_markup=get_back_keyboard(),
                         parse_mode="Markdown")

        elif data == "report_private_channel":
            if not user_data.get(user_id, {}).get("accounts") and not is_admin_user(user_id):
                send_message(chat_id, "⚠️ أضف حساباً أولاً!",
                             reply_markup=get_back_keyboard()); return
            user_data[user_id]["waiting_for"] = "private_invite_link"
            user_data[user_id]["is_private_channel"] = True
            send_message(chat_id,
                         f"{decorate_title('بلاغ على قناة خاصة')}\n\n"
                         "1️⃣ أرسل **رابط الدعوة** للقناة الخاصة.\n\n"
                         "**أمثلة:**\n"
                         "`https://t.me/+AbCdEfGhIj`\n"
                         "`https://t.me/joinchat/AbCdEfGhIj`\n\n"
                         "⚠️ البوت هيخلي الحسابات تنضم للقناة تلقائياً.",
                         reply_markup=get_back_keyboard(),
                         parse_mode="Markdown")

        elif data == "report_menu":
            send_message(chat_id, "🏷️ اختر نوع البلاغ:", reply_markup=get_report_types_keyboard())

        elif data == "start_reporting":
            handle_start_reporting(user_id, chat_id)

        elif data == "stop_report":
            if is_reporting.get(user_id):
                is_reporting[user_id] = False
                send_message(chat_id, "⏹ تم الإيقاف.", reply_markup=get_main_keyboard(user_id))
            else:
                send_message(chat_id, "ℹ️ لا يوجد تبليغ جارٍ.", reply_markup=get_main_keyboard(user_id))

        elif data == "set_sleep":
            user_data[user_id]["waiting_for"] = "set_sleep"
            send_message(chat_id, "⏱️ أدخل عدد الثواني:", reply_markup=get_back_keyboard())

        elif data == "set_count":
            user_data[user_id]["waiting_for"] = "set_count"
            send_message(chat_id, "🔢 كم عدد البلاغات لكل منشور؟", reply_markup=get_back_keyboard())

        elif data == "clear_all":
            send_message(chat_id, f"{Z('تأكيد مسح الكل')}\n\n⚠️ لا يمكن التراجع!",
                         reply_markup=get_clear_all_confirm_keyboard())

        elif data == "confirm_clear_all":
            for a in user_data.get(user_id, {}).get("accounts", []):
                try:
                    if a.get("client"): run_async(lambda c=a["client"]: c.stop(), timeout=10)
                except Exception: pass
            user_data[user_id] = _make_default_user()
            accounts_db.remove(Query().user_id == user_id)
            send_message(chat_id, "✅ تم المسح.", reply_markup=get_main_keyboard(user_id))

        elif data == "cancel_clear_all":
            send_message(chat_id, "❌ تم الإلغاء.", reply_markup=get_main_keyboard(user_id))

        elif data == "report_child_abuse_menu":
            edit_message(chat_id, message_id, "🚸 إساءة للأطفال - اختر:", reply_markup=get_child_abuse_keyboard())
        elif data == "report_violence_menu":
            edit_message(chat_id, message_id, "💥 عنف - اختر:", reply_markup=get_violence_keyboard())
        elif data == "report_illegal_goods_menu":
            edit_message(chat_id, message_id, "🛑 سلع غير قانونية - اختر:", reply_markup=get_illegal_goods_keyboard())
        elif data == "report_illegal_adult_menu":
            edit_message(chat_id, message_id, "🔞 محتوى للكبار - اختر:", reply_markup=get_illegal_adult_keyboard())
        elif data == "report_scam_menu":
            edit_message(chat_id, message_id, "🎭 نصب - اختر:", reply_markup=get_scam_keyboard())
        elif data == "report_spam_menu":
            edit_message(chat_id, message_id, "🚫 إزعاج - اختر:", reply_markup=get_spam_keyboard())
        elif data == "report_other_menu":
            edit_message(chat_id, message_id, "❓ أخرى - اختر:", reply_markup=get_other_keyboard())

        elif data in ALL_REPORT_TYPES.keys():
            rtype = data.replace("report_", "")
            show_report_confirmation(user_id, chat_id, message_id, rtype, ALL_REPORT_TYPES[data])

        elif data == "report_on_user":
            if not user_data.get(user_id, {}).get("accounts") and not is_admin_user(user_id):
                send_message(chat_id, "⚠️ أضف حساباً أولاً!", reply_markup=get_back_keyboard()); return
            user_data[user_id]["waiting_for"] = "select_user_targets"
            send_message(chat_id, "👤 أرسل روابط/معرفات المستخدمين (سطر لكل واحد).",
                         reply_markup=get_back_keyboard())

        elif data.startswith("u_report_"):
            rtype = data.replace("u_report_", "")
            user_data[user_id]["user_report_type"] = rtype
            user_data[user_id]["waiting_for"] = "set_user_report_reason"
            send_message(chat_id, f"{Z('نوع البلاغ على المستخدم')}\n🏷️ {rtype}\n\n📝 أرسل الكليشة:",
                         reply_markup={"inline_keyboard": [[B("⏭️ تخطي", "u_skip_reason")]]})

        elif data == "u_skip_reason":
            user_data[user_id]["report_reason"] = "بلاغ تلقائي"
            user_data[user_id]["waiting_for"] = "set_report_count_user"
            send_message(chat_id, "🔢 كم عدد البلاغات لكل مستخدم؟", reply_markup=get_back_keyboard())

        elif data == "start_user_reporting":
            handle_start_user_reporting(user_id, chat_id)

        elif data == "notify_channel_menu" and is_admin_user(user_id):
            cur = NOTIFY_CHANNEL.get('username') or NOTIFY_CHANNEL.get('id') or "غير محدد"
            send_message(chat_id, f"{decorate_title('قناة الإشعارات')}\n\n📌 الحالي: `{cur}`\n\n"
                         "📤 أرسل الآن:\n• `@username` لقناة عامة\n• أو `-100xxxxxxxxxx` لقناة خاصة",
                         reply_markup={"inline_keyboard": [
                             [B("🗑️ حــذف القنــاة", "notify_channel_delete", style="danger")],
                             [B("🔙 الرجــوع للرئيسيــة", "admin_panel")]]}, parse_mode="Markdown")
            user_data[user_id]["waiting_for"] = "set_notify_channel"

        elif data == "notify_channel_delete" and is_admin_user(user_id):
            set_notify_channel(None, None)
            send_message(chat_id, "🗑️ تم حذف قناة الإشعارات.", reply_markup=get_owner_panel_keyboard())

        elif data == "force_sub_menu" and is_admin_user(user_id):
            cur = FORCE_SUB.get('username') or FORCE_SUB.get('channel') or "غير مفعّل"
            send_message(chat_id, f"{decorate_title('الاشتراك الإجباري')}\n\n📌 الحالي: `{cur}`\n\n"
                         "📤 أرسل الآن:\n• `@username`\n• أو `-100xxxxxxxxxx`",
                         reply_markup={"inline_keyboard": [
                             [B("🗑️ إلغــاء", "force_sub_remove", style="danger")],
                             [B("🔙 الرجــوع للرئيسيــة", "admin_panel")]]}, parse_mode="Markdown")
            user_data[user_id]["waiting_for"] = "set_force_sub"

        elif data == "force_sub_remove" and is_admin_user(user_id):
            remove_force_sub()
            send_message(chat_id, "🗑️ تم إلغاء الاشتراك الإجباري.", reply_markup=get_owner_panel_keyboard())

        elif data == "check_force_sub":
            if check_user_joined(user_id):
                send_message(chat_id, f"✅ {Zakhrafa('تم التحقق')}",
                             reply_markup=get_main_keyboard(user_id))
            else:
                send_message(chat_id, f"❌ {Zakhrafa('لسه مشتركتش')}")
                send_force_sub_message(chat_id, user_id)

        elif data == "backup_menu" and is_admin_user(user_id):
            send_message(chat_id, decorate_title("النسخ الاحتياطي"), reply_markup=get_backup_menu_keyboard())

        elif data == "create_backup_file" and is_admin_user(user_id):
            try:
                fn = create_backup_file()
                send_message(chat_id, f"✅ تم إنشاء النسخة: {fn.name}",
                             reply_markup=get_backup_menu_keyboard())
            except Exception as e:
                send_message(chat_id, f"❌ فشل: {e}", reply_markup=get_backup_menu_keyboard())

        elif data == "download_backup_list" and is_admin_user(user_id):
            files = list_backups()
            if not files:
                send_message(chat_id, "❌ لا توجد نسخ.", reply_markup=get_backup_menu_keyboard()); return
            kb = {"inline_keyboard": []}
            for f in files[:20]:
                kb["inline_keyboard"].append([B(f"📥 {f.name}", f"dl_backup_{f.name}")])
            kb["inline_keyboard"].append([B("🔙 الرجــوع للرئيسيــة", "backup_menu")])
            send_message(chat_id, "اختر نسخة للتنزيل:", reply_markup=kb)

        elif data.startswith("dl_backup_") and is_admin_user(user_id):
            name = data.replace("dl_backup_", "")
            path = BACKUP_DIR / name
            if path.exists(): send_document(chat_id, str(path), caption=f"📥 {name}")
            else: send_message(chat_id, "❌ غير موجود.", reply_markup=get_backup_menu_keyboard())

        elif data == "activate_backup_list" and is_admin_user(user_id):
            files = list_backups()
            if not files:
                send_message(chat_id, "❌ لا توجد نسخ.", reply_markup=get_backup_menu_keyboard()); return
            kb = {"inline_keyboard": []}
            for f in files[:20]:
                kb["inline_keyboard"].append([B(f"🔄 {f.name}", f"act_backup_{f.name}")])
            kb["inline_keyboard"].append([B("🔙 الرجــوع للرئيسيــة", "backup_menu")])
            send_message(chat_id, "⚠️ اختر نسخة:", reply_markup=kb)

        elif data.startswith("act_backup_") and is_admin_user(user_id):
            name = data.replace("act_backup_", "")
            path = BACKUP_DIR / name
            if path.exists():
                try:
                    activate_backup_file(path)
                    send_message(chat_id, f"✅ تم التفعيل: {name}", reply_markup=get_owner_panel_keyboard())
                except Exception as e:
                    send_message(chat_id, f"❌ فشل: {e}", reply_markup=get_backup_menu_keyboard())
            else: send_message(chat_id, "❌ غير موجود.", reply_markup=get_backup_menu_keyboard())

        elif data == "upload_backup" and is_admin_user(user_id):
            user_data[user_id]["waiting_for"] = "upload_backup"
            send_message(chat_id, f"{Z('رفع نسخة للتفعيل')}\n\n📤 أرسل ملف JSON.",
                         reply_markup={"inline_keyboard": [[B("🔙 الرجــوع للرئيسيــة", "backup_menu")]]})

        elif data == "add_user" and is_admin_user(user_id):
            user_data[user_id]["waiting_for"] = "owner_add_user"
            send_message(chat_id, "➕ أرسل معرف المستخدم:", reply_markup=get_back_keyboard())

        elif data == "remove_user" and is_admin_user(user_id):
            user_data[user_id]["waiting_for"] = "owner_remove_user"
            send_message(chat_id, "➖ أرسل معرف المستخدم:", reply_markup=get_back_keyboard())

        elif data == "show_all_users" and is_admin_user(user_id):
            stats = load_stats()
            if not stats:
                send_message(chat_id, "❌ لا يوجد مستخدمون.", reply_markup=get_back_keyboard()); return
            txt = f"{Z('قائمة المستخدمين')}\n\n"
            for uid, s in stats.items():
                txt += (f"🆔 {uid}\n📊 {s['total_reports']} | 👤 {s['total_accounts']}\n"
                        f"🕐 {s['last_used']}\n{DECO_LINE2}\n")
            if len(txt) > 4000:
                fn = "users.txt"
                with open(fn, "w", encoding="utf-8") as f: f.write(txt)
                send_document(chat_id, fn, caption="📊 قائمة المستخدمين"); os.remove(fn)
            else: send_message(chat_id, txt, reply_markup=get_back_keyboard())

        elif data == "broadcast" and is_admin_user(user_id):
            user_data[user_id]["waiting_for"] = "owner_broadcast"
            send_message(chat_id, "📢 أرسل الرسالة:", reply_markup=get_back_keyboard())

        elif data == "show_stats" and is_admin_user(user_id):
            stats = load_stats()
            total_r = sum(s['total_reports'] for s in stats.values())
            total_a = sum(s['total_accounts'] for s in stats.values())
            send_message(chat_id,
                         f"{Z('الإحصائيات')}\n\n👥 المستخدمين: {len(stats)}\n"
                         f"📊 إجمالي البلاغات: {total_r}\n👤 إجمالي الحسابات: {total_a}",
                         reply_markup=get_back_keyboard())

        elif data == "show_logs" and is_admin_user(user_id):
            if not os.path.exists("report_log.txt"):
                send_message(chat_id, "❌ لا يوجد سجل.", reply_markup=get_back_keyboard()); return
            with open("report_log.txt", "r", encoding="utf-8") as f: logs = f.read()
            if len(logs) > 4000: send_document(chat_id, "report_log.txt", caption="📜 السجل")
            else: send_message(chat_id, f"📜 السجل:\n\n{logs}", reply_markup=get_back_keyboard())

        elif data == "delete_all_users" and is_admin_user(user_id):
            delete_all_users()
            send_message(chat_id, "🔄 تم حذف الجميع.", reply_markup=get_owner_panel_keyboard())

        elif data == "set_welcome_media" and is_admin_user(user_id):
            user_data[user_id]["waiting_for"] = "set_welcome_media"
            cur = "(لا يوجد)"
            if WELCOME_MEDIA.get('file_id'): cur = "🖼️ File ID"
            elif WELCOME_MEDIA.get('url'): cur = f"🔗 {WELCOME_MEDIA['url'][:30]}"
            elif WELCOME_MEDIA.get('path'): cur = f"📁 {WELCOME_MEDIA['path']}"
            send_message(chat_id, f"{Z('فيديو القائمة الرئيسية')}\n\n📌 الحالي: {cur}\n\n"
                         "📤 أرسل فيديو أو GIF أو صورة، أو اكتب:\n• رابط URL\n• مسار ملف\n• 🗑️ حذف",
                         reply_markup=get_back_keyboard())

        elif data in ("set_report_start_media", "set_report_flight_media") and is_admin_user(user_id):
            kind = "start" if data == "set_report_start_media" else "flight"
            label = "بداية التبليغ" if kind == "start" else "التطيير"
            current = "موجود" if REPORT_MEDIA.get(kind) else "غير محدد"
            user_data[user_id]["waiting_for"] = f"set_report_{kind}_media"
            send_message(chat_id,
                         f"🎬 فيديو {label}\n\n📌 الحالي: {current}\n\n"
                         "📤 أرسل الفيديو الآن، أو أرسل كلمة (حذف) لإزالته.",
                         reply_markup=get_back_keyboard())

        elif data == "delete_welcome_media" and is_admin_user(user_id):
            if WELCOME_MEDIA.get('path') and os.path.exists(WELCOME_MEDIA['path']):
                try: os.remove(WELCOME_MEDIA['path'])
                except Exception: pass
            set_welcome_media()
            send_message(chat_id, "🗑️ تم الحذف.", reply_markup=get_owner_panel_keyboard())

        elif data == "add_admin" and is_admin_user(user_id):
            user_data[user_id]["waiting_for"] = "add_admin"
            send_message(chat_id, "➕ أرسل معرف الأدمن الجديد:", reply_markup=get_back_keyboard())

        elif data == "remove_admin" and is_admin_user(user_id):
            if len(ADMIN_IDS) <= 1:
                send_message(chat_id, "❌ لا يمكن حذف الأدمن الوحيد!",
                             reply_markup=get_owner_panel_keyboard()); return
            kb = {"inline_keyboard": []}
            for aid in ADMIN_IDS:
                if aid != OWNER_ID:
                    kb["inline_keyboard"].append([B(f"🗑️ {aid}", f"del_admin_{aid}", style="danger")])
            kb["inline_keyboard"].append([B("🔙 الرجــوع للرئيسيــة", "admin_panel")])
            send_message(chat_id, "اختر الأدمن:", reply_markup=kb)

        elif data.startswith("del_admin_") and is_admin_user(user_id):
            ta = int(data.replace("del_admin_", ""))
            if ta in ADMIN_IDS and ta != OWNER_ID:
                ADMIN_IDS.remove(ta); save_admins()
                send_message(chat_id, f"✅ تم حذف {ta}.", reply_markup=get_owner_panel_keyboard())

        elif data == "show_admins" and is_admin_user(user_id):
            txt = f"{Z('قائمة الأدمنية')}\n\n"
            for aid in ADMIN_IDS:
                role = "👑 المالك" if aid == OWNER_ID else "🛡️ أدمن"
                txt += f"• {aid} - {role}\n"
            send_message(chat_id, txt, reply_markup=get_back_keyboard())

    except Exception as e:
        debug_log(f"callback error: {e}")

# ============================== تأكيد البلاغ ==============================
def show_report_confirmation(user_id, chat_id, message_id, rtype, title):
    user_data[user_id]["report_type"] = rtype
    user_data[user_id]["waiting_for"] = "set_klisha_for_report"
    text = (f"✅ {Z(title)}\n\n"
            f"📝 أرسل الكليشة (نص البلاغ) اللي عايز تبعتها:")
    edit_message(chat_id, message_id, text, reply_markup=get_back_keyboard())

# ============================== النصوص ==============================
def handle_text_message(user_id, chat_id, text, message_id):
    _ensure_user(user_id)
    waiting = user_data[user_id].get("waiting_for")

    if not waiting:
        if text.strip().lower() == "/start": handle_start(user_id, chat_id, "User")
        return

    if text.strip().lower() == "/start":
        tmp_c = user_data[user_id].get("temp_client")
        if tmp_c:
            try: run_async(lambda c=tmp_c: c.disconnect(), timeout=10)
            except Exception: pass
        user_data[user_id]["temp_client"] = None
        user_data[user_id]["temp_phone"] = None
        user_data[user_id]["temp_phone_hash"] = None
        user_data[user_id]["waiting_for"] = None
        handle_start(user_id, chat_id, "User"); return

    if waiting == "upload_backup" and is_admin_user(user_id):
        send_message(chat_id, "❌ لم يصل الملف.", reply_markup=get_backup_menu_keyboard()); return

    if waiting == "upload_sessions_json":
        safe_delete_message(chat_id, message_id)
        send_message(chat_id, "❌ لم يصل ملف JSON. أرسله كمستند.",
                     reply_markup=get_back_keyboard())
        user_data[user_id]["waiting_for"] = None; return

    if waiting == "bot_target_username":
        safe_delete_message(chat_id, message_id)
        bot_user = text.strip().lstrip("@")
        if not re.fullmatch(r"[A-Za-z0-9_]{4,32}", bot_user):
            send_message(chat_id, "❌ يوزر غير صالح.",
                         reply_markup=get_back_keyboard()); return
        user_data[user_id]["bot_target"] = {"username": bot_user, "msg_ids": []}
        user_data[user_id]["waiting_for"] = "bot_target_links"
        send_message(chat_id,
                     f"✅ البوت: @{bot_user}\n\n"
                     "2️⃣ أرسل الآن **روابط الرسايل** (سطر لكل رابط).\n\n"
                     "مثال:\n"
                     f"`https://t.me/{bot_user}/123`\n"
                     f"`https://t.me/{bot_user}/456`",
                     reply_markup=get_back_keyboard(),
                     parse_mode="Markdown")
        return

    if waiting == "bot_target_links":
        safe_delete_message(chat_id, message_id)
        bot_user = user_data[user_id].get("bot_target", {}).get("username")
        if not bot_user:
            send_message(chat_id, "❌ حدث خطأ. ابدأ من جديد.",
                         reply_markup=get_back_keyboard())
            user_data[user_id]["waiting_for"] = None; return
        msg_ids = []
        for line in text.splitlines():
            line = line.strip()
            if not line: continue
            m = re.search(r"t\.me/(?:[A-Za-z0-9_]+)/(\d+)", line)
            if m: msg_ids.append(int(m.group(1)))
        if not msg_ids:
            send_message(chat_id, "❌ مفيش روابط صالحة.",
                         reply_markup=get_back_keyboard()); return
        user_data[user_id]["bot_target"]["msg_ids"] = msg_ids
        user_data[user_id]["waiting_for"] = "set_klisha_for_report"
        user_data[user_id]["report_type"] = "report_other_generic"
        user_data[user_id]["is_bot_report"] = True
        send_message(chat_id,
                     f"✅ تم استلام {len(msg_ids)} رسالة.\n\n"
                     "3️⃣ أرسل الكليشة (نص البلاغ):",
                     reply_markup=get_back_keyboard())
        return

    if waiting == "private_invite_link":
        safe_delete_message(chat_id, message_id)
        invite = text.strip()
        if not re.match(r"(?:https?://)?t\.me/(?:\+|joinchat/)", invite, re.I):
            send_message(chat_id, "❌ رابط دعوة غير صالح.",
                         reply_markup=get_back_keyboard()); return
        user_data[user_id]["private_invite"] = invite
        user_data[user_id]["waiting_for"] = None
        send_message(chat_id, "⏳ جاري انضمام الحسابات للقناة...",
                     reply_markup=get_back_keyboard())
        threading.Thread(target=lambda: _join_private_channel(
            user_id, chat_id, invite), daemon=True).start()
        return

    if waiting == "private_msg_links":
        safe_delete_message(chat_id, message_id)
        raw_links = [l.strip() for l in text.splitlines() if l.strip()]
        links = []
        for l in raw_links:
            if re.match(r"(?:https?://)?t\.me/c/\d+/\d+", l, re.I):
                links.append(l)
        if not links:
            send_message(chat_id, "❌ مفيش روابط صالحة.\n\n"
                         "**مثال:** `https://t.me/c/1234567890/123`",
                         reply_markup=get_back_keyboard(),
                         parse_mode="Markdown"); return
        user_data[user_id]["selected_posts"] = links
        user_data[user_id]["waiting_for"] = None
        send_message(chat_id, f"✅ تم تحديد {len(links)} رسالة.\n\n"
                     "🏷️ اختر نوع البلاغ:",
                     reply_markup=get_report_types_keyboard())
        return

    if waiting == "set_klisha_for_report":
        safe_delete_message(chat_id, message_id)
        if not text.strip():
            send_message(chat_id, "❌ الكليشة فاضية.",
                         reply_markup=get_back_keyboard()); return
        user_data[user_id]["report_reason"] = text.strip()
        user_data[user_id]["waiting_for"] = "set_report_count"
        send_message(chat_id,
                     f"✅ تم حفظ الكليشة.\n\n🔢 أرسل عدد البلاغات لكل منشور:",
                     reply_markup=get_back_keyboard())
        return

    if waiting == "set_notify_channel" and is_admin_user(user_id):
        safe_delete_message(chat_id, message_id)
        val = text.strip()
        try:
            if val.startswith("-100") or val.lstrip("-").isdigit():
                ch_id = int(val)
                result = send_message(ch_id, "✅ تم تفعيل قناة الإشعارات.")
                if result.get("ok"):
                    set_notify_channel(ch_id, None)
                    send_message(chat_id, f"✅ تم تعيين القناة: `{ch_id}`",
                                 reply_markup=get_owner_panel_keyboard(), parse_mode="Markdown")
                else:
                    send_message(chat_id, "❌ فشل الإرسال. تأكد أن البوت أدمن.",
                                 reply_markup=get_owner_panel_keyboard())
            else:
                uname = val.lstrip("@")
                result = send_message(f"@{uname}", "✅ تم تفعيل قناة الإشعارات.")
                if result.get("ok"):
                    set_notify_channel(f"@{uname}", uname)
                    send_message(chat_id, f"✅ تم تعيين القناة: @{uname}",
                                 reply_markup=get_owner_panel_keyboard())
                else:
                    send_message(chat_id, "❌ فشل الإرسال. تأكد أن البوت أدمن.",
                                 reply_markup=get_owner_panel_keyboard())
        except Exception as e:
            send_message(chat_id, f"❌ خطأ: {e}", reply_markup=get_owner_panel_keyboard())
        user_data[user_id]["waiting_for"] = None; return

    if waiting == "set_force_sub" and is_admin_user(user_id):
        safe_delete_message(chat_id, message_id)
        val = text.strip()
        try:
            if val.startswith("-100") or val.lstrip("-").isdigit():
                ch_id = int(val)
                test = send_message(ch_id, "✅ تم تفعيل الاشتراك الإجباري.")
                if test.get("ok"):
                    set_force_sub(ch_id, None, None)
                    send_message(chat_id, f"✅ تم تفعيل الاشتراك على: `{ch_id}`",
                                 reply_markup=get_owner_panel_keyboard(), parse_mode="Markdown")
                else:
                    send_message(chat_id, "❌ فشل. تأكد أن البوت أدمن.",
                                 reply_markup=get_owner_panel_keyboard())
            else:
                uname = val.lstrip("@")
                test = send_message(f"@{uname}", "✅ تم تفعيل الاشتراك الإجباري.")
                if test.get("ok"):
                    set_force_sub(f"@{uname}", uname, f"https://t.me/{uname}")
                    send_message(chat_id, f"✅ تم التفعيل على: @{uname}",
                                 reply_markup=get_owner_panel_keyboard())
                else:
                    send_message(chat_id, "❌ فشل. تأكد أن البوت أدمن.",
                                 reply_markup=get_owner_panel_keyboard())
        except Exception as e:
            send_message(chat_id, f"❌ خطأ: {e}", reply_markup=get_owner_panel_keyboard())
        user_data[user_id]["waiting_for"] = None; return

    if waiting == "add_account_phone":
        safe_delete_message(chat_id, message_id)
        phone = text.strip().replace(" ", "")
        if not phone.startswith("+"): phone = "+" + phone
        if not re.fullmatch(r"\+\d{7,15}", phone):
            send_message(chat_id, "❌ صيغة الرقم غير صحيحة.\n\n"
                         "أرسل الرقم بصيغة دولية مثل: `+201234567890`",
                         reply_markup=get_phone_cancel_keyboard(), parse_mode="Markdown"); return
        try:
            session_name = f"account_{user_id}_{int(time.time())}"
            c = Client(session_name, API_ID, API_HASH, in_memory=True)
            init_pyrogram_loop()
            run_async(lambda cc=c: cc.connect(), timeout=30)
            sent = run_async(lambda cc=c, N=phone: cc.send_code(N), timeout=30)
            user_data[user_id]["temp_client"] = c
            user_data[user_id]["temp_phone"] = phone
            user_data[user_id]["temp_phone_hash"] = sent.phone_code_hash
            user_data[user_id]["waiting_for"] = "add_account_code"
            send_message(chat_id,
                         f"{decorate_title('تم إرسال الكود')}\n\n"
                         f"📱 الرقم: `{phone}`\n\n"
                         "✉️ أرسل الآن الكود بالشكل ده:\n`8 3 2 1 1`\n\n⚠️ بين كل رقم مسافة.",
                         reply_markup=get_phone_cancel_keyboard(), parse_mode="Markdown")
        except PhoneNumberInvalid:
            send_message(chat_id, "❌ رقم الهاتف غير صالح.", reply_markup=get_phone_cancel_keyboard())
            user_data[user_id]["waiting_for"] = None
        except Exception as e:
            send_message(chat_id, f"❌ فشل إرسال الكود:\n`{e}`",
                         reply_markup=get_phone_cancel_keyboard(), parse_mode="Markdown")
            user_data[user_id]["waiting_for"] = None
        return

    if waiting == "add_account_code":
        safe_delete_message(chat_id, message_id)
        c = user_data[user_id].get("temp_client")
        phone = user_data[user_id].get("temp_phone")
        phone_hash = user_data[user_id].get("temp_phone_hash")
        if not c or not phone or not phone_hash:
            send_message(chat_id, "❌ انتهت الجلسة. ابدأ من جديد.",
                         reply_markup=get_main_keyboard(user_id))
            user_data[user_id]["waiting_for"] = None; return
        code = re.sub(r"[\s\-\.]", "", text.strip())
        if not code.isdigit() or len(code) < 3:
            send_message(chat_id, "❌ صيغة الكود غير صحيحة.\n\n"
                         "أرسل الأرقام مفصولة بمسافات، مثال:\n`8 3 2 1 1`",
                         reply_markup=get_phone_cancel_keyboard(), parse_mode="Markdown"); return

        async def try_sign_in():
            try:
                await c.sign_in(phone, phone_hash, code); return ("ok", None)
            except SessionPasswordNeeded: return ("2fa", None)
            except PhoneCodeInvalid: return ("bad_code", "الكود غير صحيح")
            except PhoneCodeExpired: return ("expired", "انتهت صلاحية الكود")
            except Exception as ex: return ("err", str(ex))

        status, err = run_async(try_sign_in, timeout=30)
        if status == "2fa":
            user_data[user_id]["waiting_for"] = "add_account_password"
            send_message(chat_id, f"{decorate_title('كلمة مرور ثنائية')}\n\n"
                         "🔒 حسابك محمي بـ 2FA.\n📝 أرسل كلمة المرور:",
                         reply_markup=get_phone_cancel_keyboard()); return
        if status == "bad_code":
            send_message(chat_id, f"❌ {err}. أعد إرسال الكود.",
                         reply_markup=get_phone_cancel_keyboard()); return
        if status == "expired":
            send_message(chat_id, f"❌ {err}. ابدأ من جديد.",
                         reply_markup=get_main_keyboard(user_id))
            try: run_async(lambda cc=c: cc.disconnect(), timeout=10)
            except Exception: pass
            user_data[user_id]["temp_client"] = None
            user_data[user_id]["waiting_for"] = None; return
        if status == "err":
            send_message(chat_id, f"❌ خطأ: {err}", reply_markup=get_phone_cancel_keyboard()); return

        try:
            me = run_async(lambda cc=c: cc.get_me(), timeout=30)
            session_string = run_async(lambda cc=c: cc.export_session_string(), timeout=30)
        except Exception as e:
            send_message(chat_id, f"❌ فشل جلب البيانات: {e}",
                         reply_markup=get_main_keyboard(user_id))
            user_data[user_id]["waiting_for"] = None; return
        info = {"first_name": me.first_name or "بدون اسم", "id": me.id,
                "number": phone, "session_string": session_string,
                "session_type": "pyrogram", "client": c}
        accounts = user_data[user_id].setdefault("accounts", [])
        existing = next((a for a in accounts
                         if a.get("id") == info["id"] or a.get("number") == phone), None)
        if existing:
            existing.update(info); result = f"🔄 تحديث: {info['first_name']}"
        else:
            accounts.append(info); update_user_stats(user_id, accounts_added=1)
            result = f"✅ إضافة: {info['first_name']}"
        save_user_accounts(user_id)
        notify_owner(f"✅ حساب جديد\n👤 {user_id}\n📱 {phone}")
        send_message(chat_id, f"{Z('تم بنجاح')}\n\n{result}",
                     reply_markup=get_main_keyboard(user_id))
        user_data[user_id]["temp_client"] = None
        user_data[user_id]["temp_phone"] = None
        user_data[user_id]["temp_phone_hash"] = None
        user_data[user_id]["waiting_for"] = None; return

    if waiting == "add_account_password":
        safe_delete_message(chat_id, message_id)
        c = user_data[user_id].get("temp_client")
        phone = user_data[user_id].get("temp_phone")
        if not c or not phone:
            send_message(chat_id, "❌ انتهت الجلسة.", reply_markup=get_main_keyboard(user_id))
            user_data[user_id]["waiting_for"] = None; return

        async def try_check_password():
            try:
                await c.check_password(text); return ("ok", None)
            except PasswordHashInvalid: return ("wrong", "كلمة المرور خاطئة")
            except Exception as ex: return ("err", str(ex))

        status, err = run_async(try_check_password, timeout=30)
        if status == "wrong":
            send_message(chat_id, f"❌ {err}. أعد المحاولة.",
                         reply_markup=get_phone_cancel_keyboard()); return
        if status == "err":
            send_message(chat_id, f"❌ خطأ: {err}",
                         reply_markup=get_phone_cancel_keyboard()); return
        try:
            me = run_async(lambda cc=c: cc.get_me(), timeout=30)
            session_string = run_async(lambda cc=c: cc.export_session_string(), timeout=30)
        except Exception as e:
            send_message(chat_id, f"❌ فشل: {e}", reply_markup=get_main_keyboard(user_id))
            user_data[user_id]["waiting_for"] = None; return
        info = {"first_name": me.first_name or "بدون اسم", "id": me.id,
                "number": phone, "session_string": session_string,
                "session_type": "pyrogram", "client": c}
        accounts = user_data[user_id].setdefault("accounts", [])
        existing = next((a for a in accounts
                         if a.get("id") == info["id"] or a.get("number") == phone), None)
        if existing:
            existing.update(info); result = f"🔄 تحديث: {info['first_name']}"
        else:
            accounts.append(info); update_user_stats(user_id, accounts_added=1)
            result = f"✅ إضافة: {info['first_name']}"
        save_user_accounts(user_id)
        notify_owner(f"✅ حساب جديد (2FA)\n👤 {user_id}\n📱 {phone}")
        send_message(chat_id, f"{Z('تم بنجاح')}\n\n{result}",
                     reply_markup=get_main_keyboard(user_id))
        user_data[user_id]["temp_client"] = None
        user_data[user_id]["temp_phone"] = None
        user_data[user_id]["temp_phone_hash"] = None
        user_data[user_id]["waiting_for"] = None; return

    if waiting == "add_admin" and is_admin_user(user_id):
        try:
            tid = int(text)
            if tid not in ADMIN_IDS:
                ADMIN_IDS.append(tid); save_admins()
                send_message(chat_id, f"✅ تم إضافة {tid} كأدمن.",
                             reply_markup=get_owner_panel_keyboard())
            else: send_message(chat_id, "⚠️ أدمن بالفعل.", reply_markup=get_owner_panel_keyboard())
        except Exception: send_message(chat_id, "❌ رقم غير صحيح.", reply_markup=get_back_keyboard())
        user_data[user_id]["waiting_for"] = None; return

    if waiting == "owner_add_user" and is_admin_user(user_id):
        try:
            tid = int(text)
            send_message(chat_id, f"✅ تم منح {tid} اشتراك.",
                         reply_markup=get_owner_panel_keyboard())
        except Exception: send_message(chat_id, "❌ رقم غير صحيح.", reply_markup=get_back_keyboard())
        user_data[user_id]["waiting_for"] = None; return

    if waiting == "owner_remove_user" and is_admin_user(user_id):
        try:
            tid = int(text)
            send_message(chat_id, f"✅ تم إلغاء اشتراك {tid}.",
                         reply_markup=get_owner_panel_keyboard())
        except Exception: send_message(chat_id, "❌ رقم غير صحيح.", reply_markup=get_back_keyboard())
        user_data[user_id]["waiting_for"] = None; return

    if waiting == "owner_broadcast" and is_admin_user(user_id):
        stats = load_stats(); sent = 0
        for uid in stats.keys():
            try:
                send_message(int(uid), f"📢 إذاعة:\n\n{text}"); sent += 1; time.sleep(0.1)
            except Exception: pass
        send_message(chat_id, f"📢 تم الإرسال لـ {sent} مستخدم.",
                     reply_markup=get_owner_panel_keyboard())
        user_data[user_id]["waiting_for"] = None; return

    if waiting == "set_welcome_media" and is_admin_user(user_id):
        if text.strip().lower() in ("حذف", "delete"):
            if WELCOME_MEDIA.get('path') and os.path.exists(WELCOME_MEDIA['path']):
                try: os.remove(WELCOME_MEDIA['path'])
                except Exception: pass
            set_welcome_media()
            send_message(chat_id, "🗑️ تم الحذف.", reply_markup=get_owner_panel_keyboard())
        elif text.strip().startswith("http"):
            set_welcome_media(url=text.strip(), media_type='url')
            send_message(chat_id, "✅ تم التعيين.", reply_markup=get_owner_panel_keyboard())
        elif os.path.exists(text.strip()):
            set_welcome_media(path=text.strip(), media_type='path')
            send_message(chat_id, "✅ تم التعيين.", reply_markup=get_owner_panel_keyboard())
        else:
            set_welcome_media(file_id=text.strip(), media_type='file_id')
            send_message(chat_id, "✅ تم التعيين.", reply_markup=get_owner_panel_keyboard())
        user_data[user_id]["waiting_for"] = None; return

    if waiting in ("set_report_start_media", "set_report_flight_media") and is_admin_user(user_id):
        kind = "start" if waiting == "set_report_start_media" else "flight"
        if text.strip().lower() in ("حذف", "delete"):
            set_report_media(kind, None)
            send_message(chat_id, "🗑️ تم حذف فيديو الحالة.", reply_markup=get_owner_panel_keyboard())
        else:
            send_message(chat_id, "📤 أرسل الفيديو كفيديو تيليجرام، أو اكتب (حذف).",
                         reply_markup=get_back_keyboard())
        user_data[user_id]["waiting_for"] = None; return

    if waiting == "select_post":
        safe_delete_message(chat_id, message_id)
        links = [l.strip() for l in text.split() if l.strip()]
        user_data[user_id]["selected_posts"] = links
        send_message(chat_id, f"✅ تم تحديد {len(links)} منشور.",
                     reply_markup=get_main_keyboard(user_id))
        user_data[user_id]["waiting_for"] = None; return

    if waiting == "set_sleep":
        safe_delete_message(chat_id, message_id)
        try:
            global report_delay
            report_delay = max(0, int(text))
            user_data[user_id]["report_delay"] = report_delay
            send_message(chat_id, f"✅ السليب: {report_delay} ثانية.",
                         reply_markup=get_main_keyboard(user_id))
        except Exception: send_message(chat_id, "❌ رقم غير صحيح.", reply_markup=get_back_keyboard())
        user_data[user_id]["waiting_for"] = None; return

    if waiting == "set_count":
        safe_delete_message(chat_id, message_id)
        try:
            c = int(text)
            if c <= 0: raise ValueError
            user_data[user_id]["message_count"] = c
            send_message(chat_id, f"✅ عدد البلاغات: {c}.", reply_markup=get_main_keyboard(user_id))
        except Exception: send_message(chat_id, "❌ رقم غير صحيح.", reply_markup=get_back_keyboard())
        user_data[user_id]["waiting_for"] = None; return

    if waiting == "set_report_count":
        safe_delete_message(chat_id, message_id)
        try:
            c = int(text)
            if c <= 0: raise ValueError
            user_data[user_id]["message_count"] = c
            is_reporting[user_id] = True
            if is_admin_user(user_id):
                cnt = len(get_all_accounts_for_admin(user_id))
                if cnt == 0: cnt = len(user_data[user_id].get("accounts", []))
            else:
                cnt = len(user_data[user_id].get("accounts", []))
            status_msg = send_message(chat_id,
                                      get_reporting_status_text(0, 0, cnt, 0),
                                      reply_markup=get_stop_keyboard())
            if not status_msg.get("ok"):
                is_reporting[user_id] = False
                send_message(chat_id, "❌ فشل.", reply_markup=get_main_keyboard(user_id)); return
            smid = status_msg["result"]["message_id"]
            def worker():
                try: run_async(lambda: perform_real_reporting(user_id, chat_id, smid), timeout=24*60*60)
                except Exception as e:
                    is_reporting[user_id] = False; debug_log(f"reporting worker: {e}")
            threading.Thread(target=worker, daemon=True).start()
        except Exception: send_message(chat_id, "❌ رقم غير صحيح.", reply_markup=get_back_keyboard())
        user_data[user_id]["waiting_for"] = None; return

    if waiting == "select_user_targets":
        safe_delete_message(chat_id, message_id)
        targets = []
        for line in text.split("\n"):
            line = line.strip()
            if not line: continue
            if "t.me/" in line:
                line = line.split("t.me/")[-1].split("/")[0].split("?")[0]
            line = line.lstrip("@")
            if line: targets.append(line)
        if not targets:
            send_message(chat_id, "❌ لا يوجد مستخدمون صالحون.", reply_markup=get_back_keyboard())
            user_data[user_id]["waiting_for"] = None; return
        user_data[user_id]["target_users"] = targets
        user_data[user_id]["waiting_for"] = None
        send_message(chat_id, f"✅ {len(targets)} مستخدم.\n🏷️ اختر نوع البلاغ:",
                     reply_markup=get_user_report_types_keyboard()); return

    if waiting == "set_user_report_reason":
        safe_delete_message(chat_id, message_id)
        user_data[user_id]["report_reason"] = text
        user_data[user_id]["waiting_for"] = "set_report_count_user"
        send_message(chat_id, "🔢 كم عدد البلاغات لكل مستخدم؟", reply_markup=get_back_keyboard()); return

    if waiting == "set_report_count_user":
        safe_delete_message(chat_id, message_id)
        try:
            c = int(text)
            if c <= 0: raise ValueError
            user_data[user_id]["message_count"] = c
            if not user_data[user_id].get("target_users"):
                send_message(chat_id, "⚠️ لم يتم تحديد مستخدمين.",
                             reply_markup=get_back_keyboard())
                user_data[user_id]["waiting_for"] = None; return
            is_reporting[user_id] = True
            if is_admin_user(user_id):
                cnt = len(get_all_accounts_for_admin(user_id))
                if cnt == 0: cnt = len(user_data[user_id].get("accounts", []))
            else:
                cnt = len(user_data[user_id].get("accounts", []))
            status_msg = send_message(chat_id,
                                      get_reporting_status_text(0, 0, cnt, 0),
                                      reply_markup=get_stop_keyboard())
            if not status_msg.get("ok"):
                is_reporting[user_id] = False
                send_message(chat_id, "❌ فشل.", reply_markup=get_main_keyboard(user_id)); return
            smid = status_msg["result"]["message_id"]
            def worker():
                try: run_async(lambda: perform_user_reporting(user_id, chat_id, smid), timeout=24*60*60)
                except Exception as e:
                    is_reporting[user_id] = False; debug_log(f"user reporting worker: {e}")
            threading.Thread(target=worker, daemon=True).start()
        except Exception: send_message(chat_id, "❌ رقم غير صحيح.", reply_markup=get_back_keyboard())
        user_data[user_id]["waiting_for"] = None; return

def handle_start_reporting(user_id, chat_id):
    data = user_data.get(user_id, {})
    if not is_admin_user(user_id):
        if not data.get("accounts"):
            send_message(chat_id, "⚠️ أضف حساباً أولاً.", reply_markup=get_back_keyboard()); return
    if not data.get("selected_posts"):
        send_message(chat_id, "⚠️ حدد منشورات أولاً.", reply_markup=get_back_keyboard()); return
    if not data.get("report_type"):
        send_message(chat_id, "⚠️ حدد نوع البلاغ أولاً.", reply_markup=get_back_keyboard()); return
    if is_reporting.get(user_id):
        send_message(chat_id, "⏳ يوجد تبليغ جارٍ.", reply_markup=get_stop_keyboard()); return
    user_data[user_id]["waiting_for"] = "set_report_count"
    send_message(chat_id, "🔢 كم عدد البلاغات لكل منشور؟", reply_markup=get_back_keyboard())

def handle_start_user_reporting(user_id, chat_id):
    data = user_data.get(user_id, {})
    if not is_admin_user(user_id):
        if not data.get("accounts"):
            send_message(chat_id, "⚠️ أضف حساباً أولاً.", reply_markup=get_back_keyboard()); return
    if not data.get("target_users"):
        send_message(chat_id, "⚠️ حدد مستخدمين أولاً.", reply_markup=get_back_keyboard()); return
    if not data.get("user_report_type"):
        send_message(chat_id, "⚠️ حدد نوع البلاغ أولاً.", reply_markup=get_back_keyboard()); return
    if is_reporting.get(user_id):
        send_message(chat_id, "⏳ يوجد تبليغ جارٍ.", reply_markup=get_stop_keyboard()); return
    user_data[user_id]["waiting_for"] = "set_report_count_user"
    send_message(chat_id, "🔢 كم عدد البلاغات لكل مستخدم؟", reply_markup=get_back_keyboard())

# ============================== Polling ==============================
def get_updates(offset=None):
    data = {"limit": 100, "timeout": 30}
    if offset: data["offset"] = offset
    r = tg_request("getUpdates", data, retries=5)
    return r.get("result", [])

def process_updates(updates):
    global last_update_id
    for upd in updates:
        uid = upd.get("update_id", 0)
        if uid > last_update_id: last_update_id = uid

        if "message" in upd:
            msg = upd["message"]
            user_id = msg["from"]["id"]
            chat_id = msg["chat"]["id"]
            text = msg.get("text", "")
            message_id = msg.get("message_id", 0)
            _ensure_user(user_id)

            if not is_admin_user(user_id) and not check_user_joined(user_id):
                send_force_sub_message(chat_id, user_id); continue

            if ("document" in msg and
                    user_data.get(user_id, {}).get("waiting_for") == "upload_sessions_json"):
                user_data[user_id]["waiting_for"] = None
                upload_sessions_json(user_id, chat_id, msg["document"])
                continue

            if ("document" in msg and is_admin_user(user_id)
                    and user_data.get(user_id, {}).get("waiting_for") == "upload_backup"):
                user_data[user_id]["waiting_for"] = None
                try:
                    send_message(chat_id, "⏳ جاري تنزيل وتفعيل النسخة...")
                    ok, name = upload_backup_from_telegram(chat_id, msg["document"])
                    if ok:
                        send_message(chat_id, f"✅ تم تفعيل النسخة: {name}\n"
                                     f"👥 المستخدمين: {len(user_data)}",
                                     reply_markup=get_owner_panel_keyboard())
                    else:
                        send_message(chat_id, "❌ فشل.", reply_markup=get_backup_menu_keyboard())
                except Exception as e:
                    send_message(chat_id, f"❌ فشل: {e}", reply_markup=get_backup_menu_keyboard())
                continue

            if is_admin_user(user_id) and user_data.get(user_id, {}).get("waiting_for") == "set_welcome_media":
                if "video" in msg:
                    fid = msg["video"]["file_id"]
                    set_welcome_media(file_id=fid, media_type='video')
                    send_message(chat_id, "🎬 تم تعيين فيديو القائمة الرئيسية.", reply_markup=get_owner_panel_keyboard())
                    user_data[user_id]["waiting_for"] = None; continue
                elif "animation" in msg:
                    fid = msg["animation"]["file_id"]
                    set_welcome_media(file_id=fid, media_type='file_id')
                    send_message(chat_id, "🖼️ تم تعيين GIF.", reply_markup=get_owner_panel_keyboard())
                    user_data[user_id]["waiting_for"] = None; continue
                elif "photo" in msg:
                    fid = msg["photo"][-1]["file_id"]
                    set_welcome_media(file_id=fid, media_type='file_id')
                    send_message(chat_id, "🖼️ تم تعيين الصورة.", reply_markup=get_owner_panel_keyboard())
                    user_data[user_id]["waiting_for"] = None; continue

            report_media_waiting = user_data.get(user_id, {}).get("waiting_for")
            if (is_admin_user(user_id) and report_media_waiting in
                    ("set_report_start_media", "set_report_flight_media")):
                if "video" in msg:
                    kind = "start" if report_media_waiting == "set_report_start_media" else "flight"
                    set_report_media(kind, msg["video"]["file_id"])
                    label = "بداية التبليغ" if kind == "start" else "التطيير"
                    send_message(chat_id, f"✅ تم حفظ فيديو {label}.",
                                 reply_markup=get_owner_panel_keyboard())
                    user_data[user_id]["waiting_for"] = None; continue

            if text and text.strip().lower() == "/start":
                handle_start(user_id, chat_id, msg["from"].get("first_name", "User"))
            else:
                handle_text_message(user_id, chat_id, text, message_id)

        if "callback_query" in upd:
            handle_callback(upd["callback_query"])

# ============================== Main ==============================
def main():
    print("🚀 بدء تشغيل البوت...", flush=True)
    if not _acquire_lock():
        print("❌ يوجد نسخة أخرى من البوت شغالة بالفعل!", flush=True); return
    atexit.register(_release_lock)
    test = tg_request("getMe")
    if test.get("ok"):
        print(f"✅ Bot: @{test['result'].get('username')}", flush=True)
        print(f"✅ Version: {BOT_VERSION}", flush=True)
        load_all_accounts()
        print(f"✅ Loaded accounts for {len(user_data)} users", flush=True)
        threading.Thread(target=check_all_sessions_on_startup, daemon=True).start()
        print(f"✅ Admins: {ADMIN_IDS}", flush=True)
    else:
        print(f"❌ Connection failed: {test.get('description')}", flush=True)
        _release_lock(); return
    global last_update_id
    errs = 0
    while True:
        try:
            ups = get_updates(last_update_id + 1)
            if ups: process_updates(ups); errs = 0
            time.sleep(1)
        except KeyboardInterrupt:
            print("⏹ Stopped.", flush=True); save_all_accounts(); save_admins(); break
        except Exception as e:
            errs += 1; wait = min(2 ** errs, 60)
            print(f"❌ Error #{errs}: {e}", flush=True); time.sleep(wait)

# ============================== Auto Restart ==============================
def run_with_auto_restart():
    restart_count = 0
    max_restarts_per_hour = 30
    restart_times = []
    while True:
        now = time.time()
        restart_times = [t for t in restart_times if now - t < 3600]
        if len(restart_times) >= max_restarts_per_hour:
            print(f"⛔ البوت وقع {max_restarts_per_hour} مرة في ساعة — توقف.", flush=True)
            break
        try:
            print(f"▶️ تشغيل البوت (محاولة #{restart_count + 1})...", flush=True)
            restart_count += 1
            main()
            print("⏹ البوت اتوقف بشكل طبيعي.", flush=True); break
        except KeyboardInterrupt:
            print("⏹ تم الإيقاف يدوياً.", flush=True); break
        except SystemExit:
            print("⏹ البوت خرج بشكل طبيعي.", flush=True); break
        except Exception as e:
            import traceback
            print(f"❌ البوت وقع: {e}", flush=True)
            traceback.print_exc()
            restart_times.append(time.time())
            wait = min(5 + restart_count, 60)
            print(f"⏳ هيرجع بعد {wait} ثانية...", flush=True)
            time.sleep(wait)

if __name__ == '__main__':
    run_with_auto_restart()
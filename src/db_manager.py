import sys
import os
import ssl
import sqlite3
import pandas as pd
import shutil
import threading
import bcrypt
from datetime import datetime, timedelta
import urllib3
import requests

from src.logger import log, log_error, log_info, log_warning, cleanup_old_logs

urllib3.disable_warnings()

_orig_session_init = requests.Session.__init__
def _no_ssl_session_init(self, *args, **kwargs):
    _orig_session_init(self, *args, **kwargs)
requests.Session.__init__ = _no_ssl_session_init

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

try:
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
    HAS_GSHEETS = True
except ImportError:
    HAS_GSHEETS = False


MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_MINUTES = 5
BACKUP_KEEP_DAYS = 30


def get_secure_credentials_path():
    if sys.platform == "win32":
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
    else:
        base = os.path.join(os.path.expanduser("~"), ".config")
    secure_dir = os.path.join(base, "Komplaynsbot")
    os.makedirs(secure_dir, exist_ok=True)
    return os.path.join(secure_dir, "credentials.json")


def migrate_credentials():
    secure_path = get_secure_credentials_path()
    if os.path.exists(secure_path):
        return secure_path
    old_paths = [
        os.path.join(BASE_DIR, "data", "credentials.json"),
        os.path.join(BASE_DIR, "credentials.json"),
    ]
    for old in old_paths:
        if os.path.exists(old):
            try:
                shutil.copy2(old, secure_path)
                log_info("credentials.json xavfsiz joyga ko'chirildi")
                try:
                    os.remove(old)
                except OSError:
                    pass
                return secure_path
            except (OSError, shutil.SameFileError) as e:
                log_error(e, "credentials ko'chirish")
    return secure_path


VILOYATLAR = [
    "Toshkent shahri", "Toshkent viloyati", "Samarqand viloyati",
    "Buxoro viloyati", "Farg'ona viloyati", "Andijon viloyati",
    "Namangan viloyati", "Qashqadaryo viloyati", "Surxondaryo viloyati",
    "Jizzax viloyati", "Sirdaryo viloyati", "Navoiy viloyati",
    "Xorazm viloyati", "Qoraqalpog'iston Respublikasi",
]

TASHKILOTLAR = [
    "Kadastr agentligi hududiy boshqarmasi",
    "Davlat kadastrlari palatasi hududiy boshqarmasi",
]

KATEGORIYALAR = [
    "Pora / Tamagirlik",
    "Sudsiz harakat",
    "Byurokratiya / Suduradi",
    "Tanish-bilishchilik",
    "Qonunga xilof harakat",
    "Boshqa",
]


class DatabaseManager:
    def __init__(self, db_path=None):
        data_dir = os.path.join(BASE_DIR, "data")
        os.makedirs(data_dir, exist_ok=True)
        self.db_path = db_path if db_path else os.path.join(data_dir, "murojaatlar.db")

        self.json_key_path = migrate_credentials()
        self.sheet_name = "Murojaatlar_Bazasi"

        self._init_db()
        self._seed_xodimlar()
        self._auto_backup()
        self._cleanup_old_backups()
        cleanup_old_logs(days=30)

        self.client = self._connect_gsheets()
        self.sheet = self._ensure_worksheet("Murojaatlar", [
            '#', 'Yaratilgan sana', 'F.I.Sh.', 'Telefon', 'Viloyat', 'Tuman',
            'Yoʻnalish', 'Aniq_Yonalish', 'Holat', 'Murojaat matni', 'Javob',
            'Javob bergan', 'Javob sanasi', 'Ijro_Holati', 'Organish_Natijasi',
            'Biriktirilgan_Fayl', 'Masul_Komplayens', 'Chora_Turi', 'Manba'
        ], 20)
        self.users_sheet = self._ensure_worksheet("Foydalanuvchilar",
                                                   ['ID', 'Username', 'Password', 'Role', 'Active'], 5)
        self.audit_sheet = self._ensure_worksheet("Kirishlar_Tarixi",
                                                   ['ID', 'Foydalanuvchi', 'Rol', 'Kirish vaqti', 'Kompyuter nomi'], 5)

        self._sync_users()
        self._sync_murojaatlar()
        self._process_pending_queue()
        log_info("Dastur ishga tushdi")

    def _seed_xodimlar(self):
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM xodimlar")
                count = cursor.fetchone()[0]
                if count > 0:
                    return
                log_info("Xodimlar jadvali to'ldirilmoqda...")
                for vil in VILOYATLAR:
                    for tash in TASHKILOTLAR:
                        cursor.execute(
                            """INSERT INTO xodimlar 
                               (viloyat, tashkilot_turi, fish, telefon, telegram_username) 
                               VALUES (?, ?, ?, ?, ?)""",
                            (vil, tash, "", "", "")
                        )
                conn.commit()
                log_info(f"{len(VILOYATLAR) * len(TASHKILOTLAR)} ta xodim qo'shildi")
        except Exception as e:
            log_error(e, "seed_xodimlar")

    @staticmethod
    def hash_password(password):
        if isinstance(password, str):
            password = password.encode('utf-8')
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password, salt).decode('utf-8')

    @staticmethod
    def check_password(password, hashed):
        if not hashed:
            return False
        try:
            if isinstance(password, str):
                password = password.encode('utf-8')
            if isinstance(hashed, str):
                hashed = hashed.encode('utf-8')
            return bcrypt.checkpw(password, hashed)
        except (ValueError, TypeError):
            return False

    @staticmethod
    def is_hashed(password):
        if not password:
            return False
        pwd_str = str(password)
        return pwd_str.startswith(('$2b$', '$2a$', '$2y$')) and len(pwd_str) == 60

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _auto_backup(self):
        try:
            if os.path.exists(self.db_path):
                backup_dir = os.path.join(BASE_DIR, "data", "backup")
                os.makedirs(backup_dir, exist_ok=True)
                b_path = os.path.join(backup_dir,
                                      f"murojaatlar_{datetime.now().strftime('%Y_%m_%d')}.db")
                if not os.path.exists(b_path):
                    shutil.copy2(self.db_path, b_path)
                    log_info(f"Backup: {b_path}")
        except Exception as e:
            log_error(e, "auto_backup")

    def _cleanup_old_backups(self):
        try:
            backup_dir = os.path.join(BASE_DIR, "data", "backup")
            if not os.path.exists(backup_dir):
                return
            cutoff = datetime.now().timestamp() - (BACKUP_KEEP_DAYS * 86400)
            removed = 0
            for f in os.listdir(backup_dir):
                if f.endswith(".db"):
                    fpath = os.path.join(backup_dir, f)
                    if os.path.isfile(fpath) and os.path.getmtime(fpath) < cutoff:
                        try:
                            os.remove(fpath)
                            removed += 1
                        except OSError:
                            pass
            if removed:
                log_info(f"{removed} ta eski backup o'chirildi")
        except Exception as e:
            log_error(e, "cleanup_backups")

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS murojaatlar (
                    id INTEGER PRIMARY KEY, yaratilgan_sana TEXT, fish TEXT, telefon TEXT, viloyat TEXT, tuman TEXT,
                    yonalish TEXT, aniq_yonalish TEXT, holat TEXT, murojaat_matni TEXT, javob TEXT, javob_bergan TEXT,
                    javob_sanasi TEXT, ijro_holati TEXT, organish_natijasi TEXT DEFAULT '', biriktirilgan_fayl TEXT DEFAULT '',
                    masul_komplayens TEXT DEFAULT '', chora_turi TEXT DEFAULT 'Chora ko‘rilmagan', manba TEXT DEFAULT 'Telegram bot',
                    kategoriya TEXT DEFAULT '', yaratgan TEXT DEFAULT '', yangilangan_vaqt TEXT DEFAULT '',
                    arxiv INTEGER DEFAULT 0
                )
            """)
            # Mavjud bazaga yangi ustunlar qo'shish (xavfsiz)
            for col_sql in [
                "ALTER TABLE murojaatlar ADD COLUMN kategoriya TEXT DEFAULT ''",
                "ALTER TABLE murojaatlar ADD COLUMN yaratgan TEXT DEFAULT ''",
                "ALTER TABLE murojaatlar ADD COLUMN yangilangan_vaqt TEXT DEFAULT ''",
                "ALTER TABLE murojaatlar ADD COLUMN arxiv INTEGER DEFAULT 0",
            ]:
                try:
                    cursor.execute(col_sql)
                except sqlite3.OperationalError:
                    pass

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS xodimlar (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, viloyat TEXT, tashkilot_turi TEXT, fish TEXT, telefon TEXT, telegram_username TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT, role TEXT, active INTEGER DEFAULT 1
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, role TEXT, kirish_vaqti TEXT, kompyuter TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS login_attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT, attempt_time TEXT, success INTEGER DEFAULT 0
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS murojaat_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    murojaat_id INTEGER, old_status TEXT, new_status TEXT,
                    old_chora TEXT, new_chora TEXT, old_masul TEXT, new_masul TEXT,
                    natija TEXT, ozgartirgan TEXT, ozgartirgan_rol TEXT, ozgartirilgan_vaqt TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS murojaat_fayllar (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    murojaat_id INTEGER, fayl_nomi TEXT, fayl_yoli TEXT,
                    yuklangan_vaqt TEXT, yuklagan TEXT
                )
            """)
            # YANGI: Izohlar jadvali
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS murojaat_izohlar (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    murojaat_id INTEGER,
                    izoh TEXT,
                    yozgan TEXT,
                    yozgan_rol TEXT,
                    yozilgan_vaqt TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pending_sync (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action_type TEXT, murojaat_id INTEGER,
                    payload TEXT, created_at TEXT, retry_count INTEGER DEFAULT 0
                )
            """)
            cursor.execute("CREATE TABLE IF NOT EXISTS sozlamalar (key TEXT PRIMARY KEY, val TEXT)")

            cursor.execute("SELECT COUNT(*) FROM users")
            if cursor.fetchone()[0] == 0:
                admin_hash = self.hash_password("admin123")
                rahbar_hash = self.hash_password("1977")
                cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                               ("admin", admin_hash, "admin"))
                cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                               ("rahbar", rahbar_hash, "kuzatuvchi"))
                log_info("Standart foydalanuvchilar yaratildi")
            conn.commit()

    def _connect_gsheets(self):
        if not HAS_GSHEETS or not os.path.exists(self.json_key_path):
            log_warning("Google Sheets ulanmagan")
            return None
        try:
            scope = ["https://www.googleapis.com/auth/spreadsheets",
                     "https://www.googleapis.com/auth/drive"]
            creds = ServiceAccountCredentials.from_json_keyfile_name(self.json_key_path, scope)
            client = gspread.authorize(creds)
            log_info("Google Sheets ulandi")
            return client
        except Exception as e:
            log_error(e, "gsheets ulanish")
            return None

    def _ensure_worksheet(self, title, headers, cols):
        if self.client is None:
            return None
        try:
            spreadsheet = self.client.open(self.sheet_name)
            try:
                sheet = spreadsheet.worksheet(title)
            except Exception:
                sheet = spreadsheet.add_worksheet(title=title, rows="1000", cols=str(cols))
            if not sheet.row_values(1):
                sheet.insert_row(headers, 1)
            return sheet
        except Exception as e:
            log_error(e, f"worksheet '{title}'")
            return None

    def _add_to_pending(self, action_type, murojaat_id, payload=""):
        try:
            import json
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO pending_sync (action_type, murojaat_id, payload, created_at)
                    VALUES (?, ?, ?, ?)
                """, (action_type, murojaat_id, json.dumps(payload) if payload else "",
                      datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                conn.commit()
                log_warning(f"Offline: {action_type} #{murojaat_id}")
                return True
        except Exception as e:
            log_error(e, "add_to_pending")
            return False

    def _process_pending_queue(self):
        if self.client is None:
            return
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, action_type, murojaat_id FROM pending_sync ORDER BY id ASC")
                rows = cursor.fetchall()
                if not rows:
                    return
                log_info(f"Pending: {len(rows)} ta amal")
                processed = 0
                for row in rows:
                    pid, action, m_id = row
                    try:
                        if action == "update":
                            row_data = self._get_row_by_id(m_id)
                            if row_data and self.sheet:
                                self._sync_single_row_to_cloud(row_data)
                        cursor.execute("DELETE FROM pending_sync WHERE id = ?", (pid,))
                        processed += 1
                    except Exception as e:
                        log_error(e, f"pending #{pid}")
                        cursor.execute("UPDATE pending_sync SET retry_count = retry_count + 1 WHERE id = ?", (pid,))
                conn.commit()
                if processed:
                    log_info(f"Pending: {processed} ta bajarildi")
        except Exception as e:
            log_error(e, "process_pending")

    def get_pending_count(self):
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM pending_sync")
                return cursor.fetchone()[0]
        except Exception:
            return 0

    def _check_rate_limit(self, username):
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cutoff = (datetime.now() - timedelta(minutes=LOCKOUT_MINUTES)).strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute("""
                    SELECT COUNT(*) FROM login_attempts
                    WHERE username = ? AND success = 0 AND attempt_time > ?
                """, (username, cutoff))
                fail_count = cursor.fetchone()[0]
                if fail_count >= MAX_LOGIN_ATTEMPTS:
                    cursor.execute("""
                        SELECT attempt_time FROM login_attempts
                        WHERE username = ? AND success = 0
                        ORDER BY attempt_time DESC LIMIT 1
                    """, (username,))
                    row = cursor.fetchone()
                    if row:
                        try:
                            last_attempt = datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
                            remaining = LOCKOUT_MINUTES - int((datetime.now() - last_attempt).total_seconds() / 60)
                            return True, max(0, remaining)
                        except (ValueError, TypeError):
                            pass
                    return True, LOCKOUT_MINUTES
                return False, 0
        except Exception as e:
            log_error(e, "rate_limit")
            return False, 0

    def _log_login_attempt(self, username, success):
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO login_attempts (username, attempt_time, success)
                    VALUES (?, ?, ?)
                """, (username, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 1 if success else 0))
                cutoff = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute("DELETE FROM login_attempts WHERE attempt_time < ?", (cutoff,))
                conn.commit()
        except Exception as e:
            log_error(e, "log_login_attempt")

    def log_user_entry(self, username, role):
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        comp_name = os.environ.get('COMPUTERNAME', 'Noma\'lum')
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO audit_logs (username, role, kirish_vaqti, kompyuter) VALUES (?, ?, ?, ?)",
                    (username, role, now_str, comp_name))
                log_id = cursor.lastrowid
                conn.commit()
            if self.audit_sheet:
                threading.Thread(
                    target=lambda: self.audit_sheet.append_row(
                        [str(log_id), str(username), str(role), now_str, comp_name]),
                    daemon=True).start()
            log_info(f"Login: {username} ({role})")
        except Exception as e:
            log_error(e, "log_user_entry")

    def check_user_login(self, username, password):
        username = str(username).strip()
        password = str(password).strip()

        blocked, remaining = self._check_rate_limit(username)
        if blocked:
            log_warning(f"Bloklangan: {username} ({remaining} daqiqa)")
            return None

        found_role = None
        found_password = None

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT password, role FROM users WHERE username = ? AND active = 1",
                (username,))
            res = cursor.fetchone()
            if res:
                found_password, found_role = res

        if not found_role and self.users_sheet:
            try:
                records = self.users_sheet.get_all_records()
                for row in records:
                    if (str(row.get('Username', '')).strip() == username
                            and int(row.get('Active', 1)) == 1):
                        cloud_password = str(row.get('Password', '')).strip()
                        cloud_role = str(row.get('Role', '')).strip()
                        if self.is_hashed(cloud_password):
                            if self.check_password(password, cloud_password):
                                found_role = cloud_role
                                found_password = cloud_password
                        else:
                            if cloud_password == password:
                                found_role = cloud_role
                                found_password = self.hash_password(password)
                        if found_role:
                            with self._get_connection() as conn:
                                cursor = conn.cursor()
                                cursor.execute(
                                    "INSERT OR REPLACE INTO users (username, password, role, active) VALUES (?, ?, ?, 1)",
                                    (username, found_password, found_role))
                                conn.commit()
                            break
            except Exception as e:
                log_error(e, "cloud login")

        if found_role and found_password:
            if self.is_hashed(found_password):
                if self.check_password(password, found_password):
                    self._log_login_attempt(username, True)
                    self.log_user_entry(username, found_role)
                    return found_role
                else:
                    self._log_login_attempt(username, False)
                    return None
            else:
                if found_password == password:
                    new_hash = self.hash_password(password)
                    try:
                        with self._get_connection() as conn:
                            cursor = conn.cursor()
                            cursor.execute("UPDATE users SET password = ? WHERE username = ?", (new_hash, username))
                            conn.commit()
                    except Exception as e:
                        log_error(e, "hash eski parol")
                    if self.users_sheet:
                        def _update_cloud_pwd():
                            try:
                                cell = self.users_sheet.find(username, in_column=2)
                                if cell:
                                    self.users_sheet.update_cell(cell.row, 3, new_hash)
                            except Exception as e:
                                log_error(e, "cloud pwd")
                        threading.Thread(target=_update_cloud_pwd, daemon=True).start()
                    self._log_login_attempt(username, True)
                    self.log_user_entry(username, found_role)
                    return found_role
                else:
                    self._log_login_attempt(username, False)
                    return None
        self._log_login_attempt(username, False)
        return None

    def _sync_users(self):
        if self.users_sheet is None:
            return
        try:
            cloud_records = self.users_sheet.get_all_records()
            cloud_usernames = set()
            with self._get_connection() as conn:
                cursor = conn.cursor()
                for row in cloud_records:
                    un = str(row.get('Username', '')).strip()
                    pw = str(row.get('Password', '')).strip()
                    rl = str(row.get('Role', '')).strip()
                    act = int(row.get('Active', 1))
                    if not un or un == 'DELETED':
                        continue
                    cloud_usernames.add(un)
                    if pw and not self.is_hashed(pw):
                        pw = self.hash_password(pw)
                        try:
                            cell = self.users_sheet.find(un, in_column=2)
                            if cell:
                                self.users_sheet.update_cell(cell.row, 3, pw)
                        except Exception as e:
                            log_error(e, "cloud user hash")
                    cursor.execute("SELECT id FROM users WHERE username = ?", (un,))
                    if not cursor.fetchone():
                        cursor.execute("INSERT INTO users (username, password, role, active) VALUES (?, ?, ?, ?)",
                                       (un, pw, rl, act))
                    else:
                        cursor.execute("UPDATE users SET password = ?, role = ?, active = ? WHERE username = ?",
                                       (pw, rl, act, un))
                conn.commit()
                cursor.execute("SELECT id, username, password, role, active FROM users WHERE active = 1")
                new_cloud_rows = [[str(u[0]), str(u[1]), str(u[2]), str(u[3]), int(u[4])]
                                  for u in cursor.fetchall() if u[1] not in cloud_usernames]
                if new_cloud_rows:
                    self.users_sheet.append_rows(new_cloud_rows)
        except Exception as e:
            log_error(e, "sync_users")

    def _sync_murojaatlar(self):
        if self.sheet is None:
            return
        try:
            records = self.sheet.get_all_records()
            cloud_ids = set()
            with self._get_connection() as conn:
                cursor = conn.cursor()
                df = pd.DataFrame(records)
                for _, row in df.iterrows():
                    try:
                        m_id = int(row.get('#', 0))
                    except (ValueError, TypeError):
                        continue
                    if m_id <= 9:
                        continue
                    cloud_ids.add(m_id)
                    cursor.execute("SELECT id FROM murojaatlar WHERE id = ?", (m_id,))
                    if not cursor.fetchone():
                        cursor.execute("""INSERT INTO murojaatlar (id, yaratilgan_sana, fish, telefon, viloyat, tuman, yonalish, aniq_yonalish, holat, murojaat_matni, javob, javob_bergan, javob_sanasi, ijro_holati, organish_natijasi, biriktirilgan_fayl, masul_komplayens, chora_turi, manba) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                                       (m_id, str(row.get('Yaratilgan sana', '')),
                                        str(row.get('F.I.Sh.', '')), str(row.get('Telefon', '')),
                                        str(row.get('Viloyat', '')), str(row.get('Tuman', '')),
                                        str(row.get('Yoʻnalish', '')), str(row.get('Aniq_Yonalish', '')),
                                        str(row.get('Holat', '')), str(row.get('Murojaat matni', '')),
                                        str(row.get('Javob', '')), str(row.get('Javob bergan', '')),
                                        str(row.get('Javob sanasi', '')),
                                        str(row.get('Ijro_Holati', 'O‘rganishga yuborilgan')),
                                        str(row.get('Organish_Natijasi', '')),
                                        str(row.get('Biriktirilgan_Fayl', '')),
                                        str(row.get('Masul_Komplayens', '')),
                                        str(row.get('Chora_Turi', 'Chora ko‘rilmagan')),
                                        str(row.get('Manba', 'Telegram bot'))))
                    else:
                        cursor.execute("""UPDATE murojaatlar SET holat = ?, ijro_holati = ?, organish_natijasi = ?, biriktirilgan_fayl = ?, masul_komplayens = ?, chora_turi = ?, javob = ?, javob_bergan = ?, javob_sanasi = ? WHERE id = ?""",
                                       (str(row.get('Holat', '')), str(row.get('Ijro_Holati', '')),
                                        str(row.get('Organish_Natijasi', '')),
                                        str(row.get('Biriktirilgan_Fayl', '')),
                                        str(row.get('Masul_Komplayens', '')),
                                        str(row.get('Chora_Turi', '')), str(row.get('Javob', '')),
                                        str(row.get('Javob bergan', '')), str(row.get('Javob sanasi', '')),
                                        m_id))
                conn.commit()
                cursor.execute("SELECT * FROM murojaatlar WHERE id > 9")
                missing = [[str(x) if x is not None else "" for x in r]
                           for r in cursor.fetchall() if r[0] not in cloud_ids]
                if missing:
                    self.sheet.append_rows(missing)
        except Exception as e:
            log_error(e, "sync_murojaatlar")

    def get_all_records(self):
        with self._get_connection() as conn:
            df = pd.read_sql_query("SELECT * FROM murojaatlar WHERE id > 9 ORDER BY id DESC", conn)
            df = df.rename(columns={
                'id': '#', 'yaratilgan_sana': 'Yaratilgan sana', 'fish': 'F.I.Sh.',
                'telefon': 'Telefon', 'viloyat': 'Viloyat', 'tuman': 'Tuman',
                'yonalish': 'Yoʻnalish', 'aniq_yonalish': 'Aniq_Yonalish', 'holat': 'Holat',
                'murojaat_matni': 'Murojaat matni', 'javob': 'Javob',
                'javob_bergan': 'Javob bergan', 'javob_sanasi': 'Javob sanasi',
                'ijro_holati': 'Ijro_Holati', 'organish_natijasi': 'Organish_Natijasi',
                'biriktirilgan_fayl': 'Biriktirilgan_Fayl',
                'masul_komplayens': 'Masul_Komplayens', 'chora_turi': 'Chora_Turi',
                'manba': 'Manba', 'kategoriya': 'Kategoriya',
                'yaratgan': 'Yaratgan', 'yangilangan_vaqt': 'Yangilangan',
                'arxiv': 'Arxiv'
            })
            if 'Manba' not in df.columns:
                df['Manba'] = 'Telegram bot'
            df['Manba'] = df['Manba'].fillna('Telegram bot')
            return df

    def _get_row_by_id(self, m_id):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM murojaatlar WHERE id = ?", (m_id,))
            return cursor.fetchone()

    def update_murojaat_ijro(self, m_id, ijro_holati, organish_natijasi,
                             biriktirilgan_fayl='', masul_komplayens='',
                             chora_turi='Chora ko‘rilmagan', kategoriya='',
                             ozgartirgan='', ozgartirgan_rol=''):
        old_data = None
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT ijro_holati, chora_turi, masul_komplayens FROM murojaatlar WHERE id = ?",
                (m_id,))
            old_data = cursor.fetchone()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE murojaatlar SET 
                    ijro_holati = ?, organish_natijasi = ?, biriktirilgan_fayl = ?, 
                    masul_komplayens = ?, chora_turi = ?, kategoriya = ?,
                    yangilangan_vaqt = ?, yaratgan = ?
                WHERE id = ?
            """, (ijro_holati, organish_natijasi, biriktirilgan_fayl,
                  masul_komplayens, chora_turi, kategoriya,
                  datetime.now().strftime("%Y-%m-%d %H:%M:%S"), ozgartirgan, m_id))
            conn.commit()

        if old_data:
            old_ijro, old_chora, old_masul = old_data
            if (old_ijro != ijro_holati or old_chora != chora_turi
                    or old_masul != masul_komplayens):
                try:
                    with self._get_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute("""
                            INSERT INTO murojaat_history 
                            (murojaat_id, old_status, new_status, old_chora, new_chora,
                             old_masul, new_masul, natija, ozgartirgan, ozgartirgan_rol, ozgartirilgan_vaqt)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (m_id, old_ijro, ijro_holati, old_chora, chora_turi,
                              old_masul, masul_komplayens, organish_natijasi,
                              ozgartirgan, ozgartirgan_rol,
                              datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                        conn.commit()
                except Exception as e:
                    log_error(e, "history")

        row_data = self._get_row_by_id(m_id)
        if row_data:
            if self.sheet:
                try:
                    self._sync_single_row_to_cloud(row_data)
                except Exception as e:
                    log_error(e, "cloud sync")
                    self._add_to_pending("update", m_id)
            else:
                self._add_to_pending("update", m_id)

    # ================= YANGI: IZOHLAR =================
    def add_izoh(self, m_id, izoh, yozgan='', yozgan_rol=''):
        """Murojaatga izoh qo'shish."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO murojaat_izohlar 
                    (murojaat_id, izoh, yozgan, yozgan_rol, yozilgan_vaqt)
                    VALUES (?, ?, ?, ?, ?)
                """, (m_id, izoh, yozgan, yozgan_rol,
                      datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                conn.commit()
                return True
        except Exception as e:
            log_error(e, "add_izoh")
            return False

    def get_murojaat_izohlar(self, m_id):
        """Murojaat izohlarini qaytaradi."""
        try:
            with self._get_connection() as conn:
                df = pd.read_sql_query("""
                    SELECT id, izoh, yozgan as 'Kim', yozgan_rol as 'Rol',
                           yozilgan_vaqt as 'Vaqt'
                    FROM murojaat_izohlar
                    WHERE murojaat_id = ?
                    ORDER BY id DESC
                """, conn, params=(m_id,))
                return df
        except Exception as e:
            log_error(e, "get_izohlar")
            return pd.DataFrame()

    def delete_izoh(self, izoh_id):
        """Izohni o'chirish (faqat admin)."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM murojaat_izohlar WHERE id = ?", (izoh_id,))
                conn.commit()
                return True
        except Exception as e:
            log_error(e, "delete_izoh")
            return False

    # ================= YANGI: ARXIV =================
    def archive_murojaat(self, m_id, arxiv=1):
        """Murojaatni arxivga qo'yish yoki qaytarish."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE murojaatlar SET arxiv = ? WHERE id = ?", (arxiv, m_id))
                conn.commit()
                return True
        except Exception as e:
            log_error(e, "archive")
            return False

    def get_murojaat_history(self, m_id):
        with self._get_connection() as conn:
            df = pd.read_sql_query("""
                SELECT ozgartirilgan_vaqt as 'Vaqt', ozgartirgan as 'Kim',
                       ozgartirgan_rol as 'Rol', old_status as 'Eski holat',
                       new_status as 'Yangi holat', old_chora as 'Eski chora',
                       new_chora as 'Yangi chora', natija as 'Natija'
                FROM murojaat_history WHERE murojaat_id = ? ORDER BY id DESC
            """, conn, params=(m_id,))
            return df

    def _sync_single_row_to_cloud(self, row_data):
        try:
            cell = self.sheet.find(str(row_data[0]), in_column=1)
            values = [str(x) if x is not None else "" for x in row_data[:19]]
            if cell:
                self.sheet.update(f"A{cell.row}:S{cell.row}", [values])
            else:
                self.sheet.append_row(values)
        except Exception as e:
            log_error(e, "sync_single_row")
            raise

    def insert_phone_murojaat(self, fish, telefon, viloyat, tuman, yonalish, matn,
                              masul_komplayens, kategoriya='', yaratgan=''):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COALESCE(MAX(id), 100) FROM murojaatlar")
            new_id = max(cursor.fetchone()[0] + 1, 101)
            aniq_y = ("Davlat kadastrlari palatasi hududiy boshqarmasi"
                      if "palata" in yonalish.lower()
                      else "Kadastr agentligi hududiy boshqarmasi")
            cursor.execute("""INSERT INTO murojaatlar 
                (id, yaratilgan_sana, fish, telefon, viloyat, tuman, yonalish, aniq_yonalish, 
                 holat, murojaat_matni, javob, javob_bergan, javob_sanasi, ijro_holati, 
                 organish_natijasi, biriktirilgan_fayl, masul_komplayens, chora_turi, manba,
                 kategoriya, yaratgan, yangilangan_vaqt) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Yangi', ?, '', '', '', 'O‘rganishga yuborilgan', 
                        '', '', ?, 'Chora ko‘rilmagan', 'Ishonch telefoni (+998-71-273-19-66)',
                        ?, ?, ?)""",
                           (new_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            fish, telefon, viloyat, tuman, yonalish, aniq_y, matn,
                            masul_komplayens, kategoriya, yaratgan,
                            datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit()
        row_data = self._get_row_by_id(new_id)
        if row_data and self.sheet:
            threading.Thread(target=lambda: self._sync_single_row_to_cloud(row_data), daemon=True).start()
        log_info(f"Yangi telefon murojaat: #{new_id}")
        return new_id

    def add_murojaat_fayl(self, m_id, fayl_nomi, fayl_yoli, yuklagan=''):
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO murojaat_fayllar 
                    (murojaat_id, fayl_nomi, fayl_yoli, yuklangan_vaqt, yuklagan)
                    VALUES (?, ?, ?, ?, ?)
                """, (m_id, fayl_nomi, fayl_yoli,
                      datetime.now().strftime("%Y-%m-%d %H:%M:%S"), yuklagan))
                conn.commit()
                return True
        except Exception as e:
            log_error(e, "add_fayl")
            return False

    def get_murojaat_fayllar(self, m_id):
        with self._get_connection() as conn:
            return pd.read_sql_query("""
                SELECT id, fayl_nomi, fayl_yoli, yuklangan_vaqt as 'Yuklangan', yuklagan as 'Kim'
                FROM murojaat_fayllar WHERE murojaat_id = ? ORDER BY id DESC
            """, conn, params=(m_id,))

    def delete_murojaat_fayl(self, fayl_id):
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT fayl_yoli FROM murojaat_fayllar WHERE id = ?", (fayl_id,))
                row = cursor.fetchone()
                if row:
                    fayl_yoli = row[0]
                    try:
                        if fayl_yoli and os.path.exists(fayl_yoli):
                            os.remove(fayl_yoli)
                    except OSError:
                        pass
                    cursor.execute("DELETE FROM murojaat_fayllar WHERE id = ?", (fayl_id,))
                    conn.commit()
                    return True
        except Exception as e:
            log_error(e, "delete_fayl")
        return False

    def bulk_update_status(self, m_id_list, new_status, new_chora, new_masul,
                           ozgartirgan='', ozgartirgan_rol=''):
        updated = 0
        for m_id in m_id_list:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT ijro_holati, chora_turi, masul_komplayens FROM murojaatlar WHERE id = ?",
                        (m_id,))
                    old = cursor.fetchone()
                    if not old:
                        continue
                    cursor.execute("""
                        UPDATE murojaatlar SET ijro_holati = ?, chora_turi = ?, 
                            masul_komplayens = ?, yangilangan_vaqt = ?
                        WHERE id = ?
                    """, (new_status, new_chora, new_masul,
                          datetime.now().strftime("%Y-%m-%d %H:%M:%S"), m_id))
                    cursor.execute("""
                        INSERT INTO murojaat_history 
                        (murojaat_id, old_status, new_status, old_chora, new_chora,
                         old_masul, new_masul, natija, ozgartirgan, ozgartirgan_rol, ozgartirilgan_vaqt)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (m_id, old[0], new_status, old[1], new_chora,
                          old[2], new_masul, "(Bulk)",
                          ozgartirgan, ozgartirgan_rol,
                          datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                    conn.commit()
                updated += 1
            except Exception as e:
                log_error(e, f"bulk #{m_id}")
        log_info(f"Bulk: {updated} ta")
        return updated

    def get_trend_stats(self, days=30):
        try:
            with self._get_connection() as conn:
                df = pd.read_sql_query("SELECT yaratilgan_sana FROM murojaatlar WHERE id > 9", conn)
            if df.empty:
                return {"current": 0, "previous": 0, "change_pct": 0, "change_abs": 0}
            df['DT'] = pd.to_datetime(df['yaratilgan_sana'], errors='coerce')
            df = df.dropna(subset=['DT'])
            now = datetime.now()
            current_start = now - timedelta(days=days)
            previous_start = current_start - timedelta(days=days)
            current = len(df[df['DT'] >= current_start])
            previous = len(df[(df['DT'] >= previous_start) & (df['DT'] < current_start)])
            change_abs = current - previous
            change_pct = (change_abs / previous * 100) if previous > 0 else 0
            return {"current": current, "previous": previous,
                    "change_abs": change_abs, "change_pct": round(change_pct, 1)}
        except Exception as e:
            log_error(e, "trend")
            return {"current": 0, "previous": 0, "change_abs": 0, "change_pct": 0}

    def get_settings(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT key, val FROM sozlamalar")
            return {row[0]: row[1] for row in cursor.fetchall()}

    def update_settings(self, settings_dict):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            for k, v in settings_dict.items():
                cursor.execute("INSERT OR REPLACE INTO sozlamalar (key, val) VALUES (?, ?)", (k, v))
            conn.commit()

    def get_xodimlar(self):
        with self._get_connection() as conn:
            return pd.read_sql_query(
                "SELECT * FROM xodimlar ORDER BY viloyat ASC, tashkilot_turi ASC", conn)

    def save_xodim(self, x_id, fish, telefon, telegram_username):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE xodimlar SET fish = ?, telefon = ?, telegram_username = ? WHERE id = ?",
                (fish, telefon, telegram_username, x_id))
            conn.commit()

    def add_xodim(self, viloyat, tashkilot_turi, fish, telefon, telegram_username):
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """INSERT INTO xodimlar 
                       (viloyat, tashkilot_turi, fish, telefon, telegram_username) 
                       VALUES (?, ?, ?, ?, ?)""",
                    (viloyat, tashkilot_turi, fish, telefon, telegram_username))
                conn.commit()
                return True
        except Exception as e:
            log_error(e, "add_xodim")
            return False

    def delete_xodim(self, x_id):
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM xodimlar WHERE id = ?", (x_id,))
                conn.commit()
                return True
        except Exception as e:
            log_error(e, "delete_xodim")
            return False

    def find_xodim_for_region(self, viloyat, masul_turi=''):
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                m_low = str(masul_turi).lower()
                if 'palata' in m_low:
                    org_filter = '%palata%'
                elif 'agentlik' in m_low:
                    org_filter = '%agentlik%'
                else:
                    org_filter = '%'
                cursor.execute("""
                    SELECT fish, telefon, telegram_username FROM xodimlar
                    WHERE viloyat = ? AND LOWER(tashkilot_turi) LIKE ? LIMIT 1
                """, (viloyat, org_filter))
                row = cursor.fetchone()
                if not row:
                    cursor.execute(
                        "SELECT fish, telefon, telegram_username FROM xodimlar WHERE viloyat = ? LIMIT 1",
                        (viloyat,))
                    row = cursor.fetchone()
                if row:
                    return {'fish': row[0] or '', 'telefon': row[1] or '', 'username': row[2] or ''}
        except Exception as e:
            log_error(e, "find_xodim")
        return {}

    def get_all_users(self):
        with self._get_connection() as conn:
            return pd.read_sql_query("SELECT id, username, password, role FROM users", conn)

    def add_user(self, username, password, role):
        try:
            hashed = self.hash_password(password)
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                               (username, hashed, role))
                user_id = cursor.lastrowid
                conn.commit()
            if self.users_sheet:
                threading.Thread(
                    target=lambda: self.users_sheet.append_row(
                        [str(user_id), str(username), str(hashed), str(role), 1]),
                    daemon=True).start()
            return True
        except sqlite3.IntegrityError:
            return False
        except Exception as e:
            log_error(e, "add_user")
            return False

    def update_user(self, user_id, username, password, role):
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                if not str(password).strip():
                    cursor.execute("SELECT password FROM users WHERE id = ?", (user_id,))
                    r = cursor.fetchone()
                    if r:
                        password = r[0]
                else:
                    if not self.is_hashed(password):
                        password = self.hash_password(password)
                cursor.execute("UPDATE users SET username = ?, password = ?, role = ? WHERE id = ?",
                               (username, password, role, user_id))
                conn.commit()
        except sqlite3.IntegrityError:
            return False
        except Exception as e:
            log_error(e, "update_user")
            return False
        if self.users_sheet:
            def _upd_cloud():
                try:
                    cell = self.users_sheet.find(str(user_id), in_column=1)
                    vals = [str(user_id), str(username), str(password), str(role), 1]
                    if cell:
                        self.users_sheet.update(f"A{cell.row}:E{cell.row}", [vals])
                    else:
                        self.users_sheet.append_row(vals)
                except Exception as e:
                    log_error(e, "cloud update_user")
            threading.Thread(target=_upd_cloud, daemon=True).start()
        return True

    def delete_user(self, user_id):
        if str(user_id) == "1":
            return False
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
            conn.commit()
        if self.users_sheet:
            def del_cloud():
                try:
                    cell = self.users_sheet.find(str(user_id), in_column=1)
                    if cell:
                        self.users_sheet.update(f"A{cell.row}:E{cell.row}",
                                                 [[str(user_id), "DELETED", "", "", 0]])
                except Exception as e:
                    log_error(e, "cloud delete_user")
            threading.Thread(target=del_cloud, daemon=True).start()
        return True

    def get_audit_logs(self):
        with self._get_connection() as conn:
            return pd.read_sql_query(
                "SELECT id as '#', username as 'Foydalanuvchi', role as 'Rol', kirish_vaqti as 'Kirish vaqti', kompyuter as 'Kompyuter' FROM audit_logs ORDER BY id DESC LIMIT 200",
                conn)

    def sync_pull_from_cloud(self):
        if self.client is None:
            raise RuntimeError("Google Sheets ulanmagan")
        self._sync_users()
        self._sync_murojaatlar()
        self._process_pending_queue()

    def _sync_pull_from_cloud(self):
        return self.sync_pull_from_cloud()

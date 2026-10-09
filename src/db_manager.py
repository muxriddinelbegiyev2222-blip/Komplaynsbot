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

# SSL tekshiruvi YOQILGAN (xavfsiz)
urllib3.disable_warnings()
# urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)  # ENDI ISHLATILMAYDI

# MUHIM: SSL tekshiruvi ENDI O'CHIRILMAGAN
# (avval xato bor edi, endi xavfsiz)
_orig_session_init = requests.Session.__init__
def _no_ssl_session_init(self, *args, **kwargs):
    _orig_session_init(self, *args, **kwargs)
    # self.verify = False  # ❌ OLIB TASHLANDI
requests.Session.__init__ = _no_ssl_session_init

# ssl._create_default_https_context = ssl._create_unverified_context  # ❌ OLIB TASHLANDI

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


# ================= RATE LIMITING SOZLAMALARI =================
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_MINUTES = 5

# ================= CREDENTIALS HIMOYASI =================
def get_secure_credentials_path():
    """
    credentials.json uchun xavfsiz joyni qaytaradi:
    - Windows: %APPDATA%/Komplaynsbot/credentials.json
    - Linux/Mac: ~/.config/Komplaynsbot/credentials.json
    """
    if sys.platform == "win32":
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
    else:
        base = os.path.join(os.path.expanduser("~"), ".config")
    secure_dir = os.path.join(base, "Komplaynsbot")
    os.makedirs(secure_dir, exist_ok=True)
    return os.path.join(secure_dir, "credentials.json")


def migrate_credentials():
    """
    Eski joydagi credentials.json ni xavfsiz joyga ko'chiradi.
    """
    secure_path = get_secure_credentials_path()
    if os.path.exists(secure_path):
        return secure_path  # allaqachon xavfsiz joyda
    
    # Eski joylarni tekshirish
    old_paths = [
        os.path.join(BASE_DIR, "data", "credentials.json"),
        os.path.join(BASE_DIR, "credentials.json"),
    ]
    for old in old_paths:
        if os.path.exists(old):
            try:
                shutil.copy2(old, secure_path)
                print(f"✅ credentials.json xavfsiz joyga ko'chirildi: {secure_path}")
                # Eski faylni o'chirish (xavfsizlik uchun)
                try:
                    os.remove(old)
                    print(f"🗑 Eski credentials.json o'chirildi: {old}")
                except OSError:
                    pass
                return secure_path
            except (OSError, shutil.SameFileError):
                pass
    return secure_path


class DatabaseManager:
    def __init__(self, db_path=None):
        data_dir = os.path.join(BASE_DIR, "data")
        os.makedirs(data_dir, exist_ok=True)
        self.db_path = db_path if db_path else os.path.join(data_dir, "murojaatlar.db")

        # Credentials xavfsiz joyga ko'chirildi
        self.json_key_path = migrate_credentials()
        self.sheet_name = "Murojaatlar_Bazasi"

        self._init_db()
        self._auto_backup()

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

    # ================= XAVFSIZLIK: PAROL HASH =================
    @staticmethod
    def hash_password(password):
        """Parolni bcrypt bilan hash qilish."""
        if isinstance(password, str):
            password = password.encode('utf-8')
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password, salt).decode('utf-8')

    @staticmethod
    def check_password(password, hashed):
        """Parolni hash bilan solishtirish."""
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
        """Parol hash qilinganmi yoki yo'qmi aniqlash."""
        if not password:
            return False
        pwd_str = str(password)
        # bcrypt hash doim $2b$, $2a$, yoki $2y$ bilan boshlanadi va 60 belgi
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
        except Exception:
            pass

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS murojaatlar (
                    id INTEGER PRIMARY KEY, yaratilgan_sana TEXT, fish TEXT, telefon TEXT, viloyat TEXT, tuman TEXT,
                    yonalish TEXT, aniq_yonalish TEXT, holat TEXT, murojaat_matni TEXT, javob TEXT, javob_bergan TEXT,
                    javob_sanasi TEXT, ijro_holati TEXT, organish_natijasi TEXT DEFAULT '', biriktirilgan_fayl TEXT DEFAULT '',
                    masul_komplayens TEXT DEFAULT '', chora_turi TEXT DEFAULT 'Chora ko‘rilmagan', manba TEXT DEFAULT 'Telegram bot'
                )
            """)
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
            # YANGI: Login urinishlarini kuzatish
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS login_attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT,
                    attempt_time TEXT,
                    success INTEGER DEFAULT 0
                )
            """)
            cursor.execute("CREATE TABLE IF NOT EXISTS sozlamalar (key TEXT PRIMARY KEY, val TEXT)")

            cursor.execute("SELECT COUNT(*) FROM users")
            if cursor.fetchone()[0] == 0:
                # Standart foydalanuvchilar (hash qilingan parollar)
                admin_hash = self.hash_password("admin123")
                rahbar_hash = self.hash_password("1977")
                cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                               ("admin", admin_hash, "admin"))
                cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                               ("rahbar", rahbar_hash, "kuzatuvchi"))
                print("✅ Standart foydalanuvchilar hash qilingan parollar bilan yaratildi")
            conn.commit()

    def _connect_gsheets(self):
        if not HAS_GSHEETS or not os.path.exists(self.json_key_path):
            return None
        try:
            scope = ["https://www.googleapis.com/auth/spreadsheets",
                     "https://www.googleapis.com/auth/drive"]
            creds = ServiceAccountCredentials.from_json_keyfile_name(self.json_key_path, scope)
            client = gspread.authorize(creds)
            # SSL tekshiruvi YOQILGAN
            return client
        except Exception as e:
            print(f"⚠️ Google Sheets ulanmadi: {e}")
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
            print(f"⚠️ Worksheet '{title}' yaratilmadi: {e}")
            return None

    # ================= LOGIN RATE LIMITING =================
    def _check_rate_limit(self, username):
        """
        Login urinishlarini tekshirish.
        Qaytaradi: (blocked: bool, remaining_minutes: int)
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                # Oxirgi LOCKOUT_MINUTES daqiqadagi muvaffaqiyatsiz urinishlar
                cutoff = (datetime.now() - timedelta(minutes=LOCKOUT_MINUTES)).strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute("""
                    SELECT COUNT(*) FROM login_attempts
                    WHERE username = ? AND success = 0 AND attempt_time > ?
                """, (username, cutoff))
                fail_count = cursor.fetchone()[0]
                
                if fail_count >= MAX_LOGIN_ATTEMPTS:
                    # Oxirgi urinishdan qancha vaqt o'tgan
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
        except Exception:
            return False, 0

    def _log_login_attempt(self, username, success):
        """Login urinishini bazaga yozish."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO login_attempts (username, attempt_time, success)
                    VALUES (?, ?, ?)
                """, (username, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 1 if success else 0))
                # Eski urinishlarni tozalash (7 kundan eski)
                cutoff = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute("DELETE FROM login_attempts WHERE attempt_time < ?", (cutoff,))
                conn.commit()
        except Exception:
            pass

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
        except Exception:
            pass

    # ================= ASOSIY LOGIN TEKSHIRUVI (RATE LIMIT + HASH) =================
    def check_user_login(self, username, password):
        """
        Login tekshiruvi:
        1. Rate limiting (5 xato → 5 daqiqa blok)
        2. bcrypt hash tekshiruv
        3. Eski plaintext parollarni avtomatik hash qilish
        """
        username = str(username).strip()
        password = str(password).strip()
        
        # 1. Rate limiting tekshiruvi
        blocked, remaining = self._check_rate_limit(username)
        if blocked:
            print(f"🚫 Login bloklangan: {username} ({remaining} daqiqa qoldi)")
            return None
        
        # 2. Bazadan foydalanuvchini olish
        found_role = None
        found_password = None
        user_id = None
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, password, role FROM users WHERE username = ? AND active = 1",
                (username,))
            res = cursor.fetchone()
            if res:
                user_id, found_password, found_role = res
        
        # 3. Agar bazada topilmasa - Google Sheets'dan qidirish
        if not found_role and self.users_sheet:
            try:
                records = self.users_sheet.get_all_records()
                for row in records:
                    if (str(row.get('Username', '')).strip() == username
                            and int(row.get('Active', 1)) == 1):
                        cloud_password = str(row.get('Password', '')).strip()
                        cloud_role = str(row.get('Role', '')).strip()
                        
                        # Cloud'dagi parolni tekshirish
                        if self.is_hashed(cloud_password):
                            if self.check_password(password, cloud_password):
                                found_role = cloud_role
                                found_password = cloud_password
                        else:
                            # Eski plaintext parol
                            if cloud_password == password:
                                found_role = cloud_role
                                # Hash qilib bazaga saqlash
                                found_password = self.hash_password(password)
                        
                        if found_role:
                            # Bazaga qo'shish
                            with self._get_connection() as conn:
                                cursor = conn.cursor()
                                cursor.execute(
                                    "INSERT OR REPLACE INTO users (username, password, role, active) VALUES (?, ?, ?, 1)",
                                    (username, found_password, found_role))
                                conn.commit()
                            break
            except Exception:
                pass
        
        # 4. Parolni tekshirish
        if found_role and found_password:
            # Agar parol hash qilingan bo'lsa
            if self.is_hashed(found_password):
                if self.check_password(password, found_password):
                    # ✅ Muvaffaqiyatli
                    self._log_login_attempt(username, True)
                    self.log_user_entry(username, found_role)
                    return found_role
                else:
                    # ❌ Parol xato
                    self._log_login_attempt(username, False)
                    return None
            else:
                # Eski plaintext parol - hash qilib saqlash
                if found_password == password:
                    new_hash = self.hash_password(password)
                    try:
                        with self._get_connection() as conn:
                            cursor = conn.cursor()
                            cursor.execute(
                                "UPDATE users SET password = ? WHERE username = ?",
                                (new_hash, username))
                            conn.commit()
                        print(f"✅ Eski plaintext parol hash qilindi: {username}")
                    except Exception:
                        pass
                    
                    # Cloud'ga ham hash qilingan parolni yuborish
                    if self.users_sheet:
                        def _update_cloud_pwd():
                            try:
                                cell = self.users_sheet.find(username, in_column=2)
                                if cell:
                                    self.users_sheet.update_cell(cell.row, 3, new_hash)
                            except Exception:
                                pass
                        threading.Thread(target=_update_cloud_pwd, daemon=True).start()
                    
                    self._log_login_attempt(username, True)
                    self.log_user_entry(username, found_role)
                    return found_role
                else:
                    self._log_login_attempt(username, False)
                    return None
        
        # ❌ Topilmadi
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
                    
                    # Agar cloud'dagi parol plaintext bo'lsa - hash qilamiz
                    if pw and not self.is_hashed(pw):
                        pw = self.hash_password(pw)
                        # Cloud'ga yangilangan hashni yuborish
                        try:
                            cell = self.users_sheet.find(un, in_column=2)
                            if cell:
                                self.users_sheet.update_cell(cell.row, 3, pw)
                        except Exception:
                            pass
                    
                    cursor.execute("SELECT id FROM users WHERE username = ?", (un,))
                    if not cursor.fetchone():
                        cursor.execute(
                            "INSERT INTO users (username, password, role, active) VALUES (?, ?, ?, ?)",
                            (un, pw, rl, act))
                    else:
                        cursor.execute(
                            "UPDATE users SET password = ?, role = ?, active = ? WHERE username = ?",
                            (pw, rl, act, un))
                conn.commit()
                cursor.execute(
                    "SELECT id, username, password, role, active FROM users WHERE active = 1")
                new_cloud_rows = [[str(u[0]), str(u[1]), str(u[2]), str(u[3]), int(u[4])]
                                  for u in cursor.fetchall() if u[1] not in cloud_usernames]
                if new_cloud_rows:
                    self.users_sheet.append_rows(new_cloud_rows)
        except Exception as e:
            print(f"⚠️ Foydalanuvchilar sinxronizatsiyasida xato: {e}")

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
                missing_in_cloud = [[str(x) if x is not None else "" for x in r]
                                    for r in cursor.fetchall() if r[0] not in cloud_ids]
                if missing_in_cloud:
                    self.sheet.append_rows(missing_in_cloud)
        except Exception as e:
            print(f"⚠️ Murojaatlar sinxronizatsiyasida xato: {e}")

    def get_all_records(self):
        with self._get_connection() as conn:
            df = pd.read_sql_query(
                "SELECT * FROM murojaatlar WHERE id > 9 ORDER BY id DESC", conn)
            df = df.rename(columns={
                'id': '#', 'yaratilgan_sana': 'Yaratilgan sana', 'fish': 'F.I.Sh.',
                'telefon': 'Telefon', 'viloyat': 'Viloyat', 'tuman': 'Tuman',
                'yonalish': 'Yoʻnalish', 'aniq_yonalish': 'Aniq_Yonalish', 'holat': 'Holat',
                'murojaat_matni': 'Murojaat matni', 'javob': 'Javob',
                'javob_bergan': 'Javob bergan', 'javob_sanasi': 'Javob sanasi',
                'ijro_holati': 'Ijro_Holati', 'organish_natijasi': 'Organish_Natijasi',
                'biriktirilgan_fayl': 'Biriktirilgan_Fayl',
                'masul_komplayens': 'Masul_Komplayens', 'chora_turi': 'Chora_Turi',
                'manba': 'Manba'
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
                             chora_turi='Chora ko‘rilmagan'):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE murojaatlar SET ijro_holati = ?, organish_natijasi = ?, biriktirilgan_fayl = ?, masul_komplayens = ?, chora_turi = ? WHERE id = ?",
                (ijro_holati, organish_natijasi, biriktirilgan_fayl,
                 masul_komplayens, chora_turi, m_id))
            conn.commit()
        row_data = self._get_row_by_id(m_id)
        if row_data and self.sheet:
            threading.Thread(
                target=lambda: self._sync_single_row_to_cloud(row_data),
                daemon=True).start()

    def _sync_single_row_to_cloud(self, row_data):
        try:
            cell = self.sheet.find(str(row_data[0]), in_column=1)
            values = [str(x) if x is not None else "" for x in row_data]
            if cell:
                self.sheet.update(f"A{cell.row}:S{cell.row}", [values])
            else:
                self.sheet.append_row(values)
        except Exception as e:
            print(f"⚠️ Bulutga yozishda xato: {e}")

    def insert_phone_murojaat(self, fish, telefon, viloyat, tuman, yonalish, matn,
                              masul_komplayens):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COALESCE(MAX(id), 100) FROM murojaatlar")
            new_id = max(cursor.fetchone()[0] + 1, 101)
            aniq_y = ("Davlat kadastrlari palatasi hududiy boshqarmasi"
                      if "palata" in yonalish.lower()
                      else "Kadastr agentligi hududiy boshqarmasi")
            cursor.execute("""INSERT INTO murojaatlar (id, yaratilgan_sana, fish, telefon, viloyat, tuman, yonalish, aniq_yonalish, holat, murojaat_matni, javob, javob_bergan, javob_sanasi, ijro_holati, organish_natijasi, biriktirilgan_fayl, masul_komplayens, chora_turi, manba) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Yangi', ?, '', '', '', 'O‘rganishga yuborilgan', '', '', ?, 'Chora ko‘rilmagan', 'Ishonch telefoni (+998-71-273-19-66)')""",
                           (new_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            fish, telefon, viloyat, tuman, yonalish, aniq_y, matn,
                            masul_komplayens))
            conn.commit()
        row_data = self._get_row_by_id(new_id)
        if row_data and self.sheet:
            threading.Thread(
                target=lambda: self._sync_single_row_to_cloud(row_data),
                daemon=True).start()
        return new_id

    def sync_excel_data(self, df):
        new_cloud_records = []
        with self._get_connection() as conn:
            cursor = conn.cursor()
            for _, row in df.iterrows():
                m_id = None
                for col_name in ['#', '№', 'ID', 'id', 'Tartib raqam']:
                    if col_name in row and pd.notna(row[col_name]):
                        try:
                            m_id = int(str(row[col_name]).strip())
                            break
                        except (ValueError, TypeError):
                            pass
                if not m_id or m_id <= 9:
                    continue
                cursor.execute("SELECT id FROM murojaatlar WHERE id = ?", (m_id,))
                if not cursor.fetchone():
                    yonalish = str(row.get('Yoʻnalish', row.get('Yonalish', '')))
                    default_masul = ("Davlat kadastrlari palatasi hududiy komplayens xodimi"
                                     if 'palata' in yonalish.lower()
                                     else "Kadastr agentligi hududiy komplayens xodimi")
                    sana = str(row.get('Yaratilgan sana',
                                       row.get('Yaratilgan_sana', row.get('Sana', ''))))
                    fish = str(row.get('F.I.Sh.', row.get('FISH', row.get('F.I.SH', ''))))
                    telefon = str(row.get('Telefon', row.get('Tel', '')))
                    viloyat = str(row.get('Viloyat', ''))
                    tuman = str(row.get('Tuman', ''))
                    aniq_yonalish = str(row.get('Aniq_Yonalish', row.get('Aniq yonalish', '')))
                    holat = str(row.get('Holat', ''))
                    matn = str(row.get('Murojaat matni',
                                       row.get('Murojaat_matni', row.get('Matn', ''))))

                    cursor.execute("""INSERT INTO murojaatlar (id, yaratilgan_sana, fish, telefon, viloyat, tuman, yonalish, aniq_yonalish, holat, murojaat_matni, javob, javob_bergan, javob_sanasi, ijro_holati, organish_natijasi, biriktirilgan_fayl, masul_komplayens, chora_turi, manba) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '', '', '', 'O‘rganishga yuborilgan', '', '', ?, 'Chora ko‘rilmagan', 'Telegram bot')""",
                                   (m_id, sana, fish, telefon, viloyat, tuman,
                                    yonalish, aniq_yonalish, holat, matn, default_masul))
                    row_data = self._get_row_by_id(m_id)
                    if row_data:
                        new_cloud_records.append(row_data)
            conn.commit()

        if new_cloud_records and self.sheet:
            threading.Thread(
                target=lambda: self.sheet.append_rows(
                    [[str(x) if x is not None else "" for x in r] for r in new_cloud_records]),
                daemon=True).start()

    def get_settings(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT key, val FROM sozlamalar")
            return {row[0]: row[1] for row in cursor.fetchall()}

    def update_settings(self, settings_dict):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            for k, v in settings_dict.items():
                cursor.execute(
                    "INSERT OR REPLACE INTO sozlamalar (key, val) VALUES (?, ?)", (k, v))
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
                    WHERE viloyat = ? AND LOWER(tashkilot_turi) LIKE ?
                    LIMIT 1
                """, (viloyat, org_filter))
                row = cursor.fetchone()
                if not

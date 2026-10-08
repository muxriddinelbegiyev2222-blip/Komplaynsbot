import sys
import os
import ssl
import sqlite3
import pandas as pd
import shutil
import threading
from datetime import datetime
import urllib3
import requests

# Korporativ tarmoq va antiviruslar SSL tekshiruvini chetlab o'tish (SSL xatosini bartaraf qilish)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

_orig_session_init = requests.Session.__init__
def _no_ssl_session_init(self, *args, **kwargs):
    _orig_session_init(self, *args, **kwargs)
    self.verify = False
requests.Session.__init__ = _no_ssl_session_init

try:
    ssl._create_default_https_context = ssl._create_unverified_context
except Exception:
    pass

# .exe fayl turgan haqiqiy papkani aniqlash
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

LOG_FILE = os.path.join(BASE_DIR, "debug_log.txt")

def log(msg):
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
    except Exception:
        pass

try:
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write("=== DASTUR ISHGA TUSHDI ===\n")
except Exception:
    pass

try:
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
    HAS_GSHEETS = True
    log("1. gspread va oauth2client: MAVJUD (OK)")
except ImportError as e:
    HAS_GSHEETS = False
    log(f"1. XATO: Kutubxona topilmadi: {e}")

class DatabaseManager:
    def __init__(self, db_path=None):
        data_dir = os.path.join(BASE_DIR, "data")
        os.makedirs(data_dir, exist_ok=True)
        
        self.db_path = db_path if db_path else os.path.join(data_dir, "murojaatlar.db")
        
        # credentials.json faylini qidirish
        p1 = os.path.join(data_dir, "credentials.json")
        p2 = os.path.join(BASE_DIR, "credentials.json")
        if os.path.exists(p1):
            self.json_key_path = p1
        elif os.path.exists(p2):
            self.json_key_path = p2
        else:
            self.json_key_path = p1
            
        log(f"2. Kalit manzili: {self.json_key_path} | Fayl mavjudmi: {os.path.exists(self.json_key_path)}")
        
        self.sheet_name = "Murojaatlar_Bazasi"
        
        self.gsheet_headers = [
            '#', 'Yaratilgan sana', 'F.I.Sh.', 'Telefon', 'Viloyat', 'Tuman', 
            'Yoʻnalish', 'Aniq_Yonalish', 'Holat', 'Murojaat matni', 'Javob', 
            'Javob bergan', 'Javob sanasi', 'Ijro_Holati', 'Organish_Natijasi', 
            'Biriktirilgan_Fayl', 'Masul_Komplayens', 'Chora_Turi', 'Manba'
        ]
        self.users_headers = ['ID', 'Username', 'Password', 'Role', 'Active']
        
        self._init_db()
        self._auto_backup()
        
        self.client = self._connect_gsheets()
        self.sheet = self._ensure_worksheet_and_headers()
        self.users_sheet = self._ensure_users_worksheet()
        
        self._sync_all()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _auto_backup(self):
        try:
            if os.path.exists(self.db_path):
                backup_dir = os.path.join(BASE_DIR, "data", "backup")
                os.makedirs(backup_dir, exist_ok=True)
                today_str = datetime.now().strftime("%Y_%m_%d")
                b_path = os.path.join(backup_dir, f"murojaatlar_{today_str}.db")
                if not os.path.exists(b_path):
                    shutil.copy2(self.db_path, b_path)
        except Exception as e:
            log(f"Backup xatosi: {e}")

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS murojaatlar (
                    id INTEGER PRIMARY KEY,
                    yaratilgan_sana TEXT, fish TEXT, telefon TEXT, viloyat TEXT, tuman TEXT,
                    yonalish TEXT, aniq_yonalish TEXT, holat TEXT, murojaat_matni TEXT,
                    javob TEXT, javob_bergan TEXT, javob_sanasi TEXT, ijro_holati TEXT,
                    organish_natijasi TEXT DEFAULT '', biriktirilgan_fayl TEXT DEFAULT '',
                    masul_komplayens TEXT DEFAULT '', chora_turi TEXT DEFAULT 'Chora ko‘rilmagan',
                    manba TEXT DEFAULT 'Telegram bot'
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS xodimlar (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, viloyat TEXT, tashkilot_turi TEXT,
                    fish TEXT, telefon TEXT, telegram_username TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, 
                    username TEXT UNIQUE, 
                    password TEXT, 
                    role TEXT, 
                    active INTEGER DEFAULT 1
                )
            """)
            cursor.execute("SELECT COUNT(*) FROM users")
            if cursor.fetchone()[0] == 0:
                cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", ("admin", "admin123", "admin"))
            
            cursor.execute("SELECT COUNT(*) FROM xodimlar")
            if cursor.fetchone()[0] == 0:
                regions = ["Buxoro viloyati", "Farg'ona viloyati", "Jizzax viloyati", "Namangan viloyati", "Navoiy viloyati", "Qashqadaryo viloyati", "Qoraqalpog'iston Respublikasi", "Samarqand viloyati", "Sirdaryo viloyati", "Surxondaryo viloyati", "Toshkent shahri", "Toshkent viloyati", "Xorazm viloyati"]
                for reg in regions:
                    cursor.execute("INSERT INTO xodimlar (viloyat, tashkilot_turi, fish, telefon, telegram_username) VALUES (?, ?, ?, ?, ?)", (reg, "Kadastr agentligi", "Mas'ul xodim", "+998", ""))
                    cursor.execute("INSERT INTO xodimlar (viloyat, tashkilot_turi, fish, telefon, telegram_username) VALUES (?, ?, ?, ?, ?)", (reg, "Davlat kadastrlari palatasi", "Mas'ul xodim", "+998", ""))
            
            cursor.execute("CREATE TABLE IF NOT EXISTS sozlamalar (key TEXT PRIMARY KEY, val TEXT)")
            default_settings = {
                "sla_days": "2",
                "report_header": "O‘ZBEKISTON RESPUBLIKASI KADASTR AGENTLIGI\nKORRUPSIYAGA QARSHI KURASHISH BO‘LIMI",
                "tg_template": "⚡️ KORRUPSIYAGA QARSHI KOMPLAYENS NAZORAT\n📌 Murojaat № {id}\n📡 Manba: {manba}\n👤 Fuqaro: {fish} (Tel: {tel})\n📍 Hudud: {viloyat}, {tuman}\n🕒 Sana: {sana}\n\n📝 MAZMUNI:\n{matn}\n\n⚠️ Iltimos, ushbu murojaatni zudlik bilan o‘rganib xulosa taqdim eting!"
            }
            for k, v in default_settings.items():
                cursor.execute("INSERT OR IGNORE INTO sozlamalar (key, val) VALUES (?, ?)", (k, v))
            conn.commit()

    def _connect_gsheets(self):
        if not HAS_GSHEETS:
            return None
        if not os.path.exists(self.json_key_path):
            log(f"3. XATO: credentials.json topilmadi: {self.json_key_path}")
            return None
        try:
            scope = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
            ]
            creds = ServiceAccountCredentials.from_json_keyfile_name(self.json_key_path, scope)
            client = gspread.authorize(creds)
            if hasattr(client, 'http_client') and hasattr(client.http_client, 'session'):
                client.http_client.session.verify = False
            log("3. Google Sheets bilan ulanish muvaffaqiyatli (OK)")
            return client
        except Exception as e:
            log(f"3. XATO: Google Sheets ga ulanishda xato: {e}")
            return None

    def _open_spreadsheet(self):
        if self.client is None:
            return None
        return self.client.open(self.sheet_name)

    def _ensure_worksheet_and_headers(self):
        if self.client is None:
            return None
        try:
            spreadsheet = self._open_spreadsheet()
            try:
                sheet = spreadsheet.worksheet("Murojaatlar")
            except Exception:
                sheet = spreadsheet.add_worksheet(title="Murojaatlar", rows="1000", cols="20")
            headers = sheet.row_values(1)
            if not headers:
                sheet.insert_row(self.gsheet_headers, 1)
                log("4. 'Murojaatlar' varaqasiga sarlavhalar yozildi (OK)")
            else:
                log("4. 'Murojaatlar' varaqasi topildi (OK)")
            return sheet
        except Exception as e:
            log(f"4. XATO: 'Murojaatlar' varaqasi xatosi: {e}")
            return None

    def _ensure_users_worksheet(self):
        if self.client is None:
            return None
        try:
            spreadsheet = self._open_spreadsheet()
            try:
                sheet = spreadsheet.worksheet("Foydalanuvchilar")
            except Exception:
                sheet = spreadsheet.add_worksheet(title="Foydalanuvchilar", rows="100", cols="5")
            headers = sheet.row_values(1)
            if not headers:
                sheet.insert_row(self.users_headers, 1)
                log("5. 'Foydalanuvchilar' varaqasiga sarlavhalar yozildi (OK)")
            else:
                log("5. 'Foydalanuvchilar' varaqasi topildi (OK)")
            return sheet
        except Exception as e:
            log(f"5. XATO: 'Foydalanuvchilar' varaqasi xatosi: {e}")
            return None

    def _sync_all(self):
        self._sync_users()
        self._sync_murojaatlar()

    def _sync_users(self):
        if self.users_sheet is None:
            return
        try:
            cloud_records = self.users_sheet.get_all_records()
            cloud_usernames = set()
            with self._get_connection() as conn:
                cursor = conn.cursor()
                if cloud_records:
                    for row in cloud_records:
                        username = str(row.get('Username', '')).strip()
                        password = str(row.get('Password', '')).strip()
                        role = str(row.get('Role', '')).strip()
                        try:
                            active = int(row.get('Active', 1))
                        except Exception:
                            active = 1
                        if not username or username == 'DELETED':
                            continue
                        cloud_usernames.add(username)
                        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
                        if not cursor.fetchone():
                            cursor.execute("INSERT INTO users (username, password, role, active) VALUES (?, ?, ?, ?)", (username, password, role, active))
                        else:
                            cursor.execute("UPDATE users SET password = ?, role = ?, active = ? WHERE username = ?", (password, role, active, username))
                    conn.commit()
                
                cursor.execute("SELECT id, username, password, role, active FROM users WHERE active = 1")
                local_users = cursor.fetchall()
                new_cloud_rows = []
                for u in local_users:
                    if u[1] not in cloud_usernames:
                        new_cloud_rows.append([str(u[0]), str(u[1]), str(u[2]), str(u[3]), int(u[4])])
                if new_cloud_rows:
                    self.users_sheet.append_rows(new_cloud_rows)
                    log(f"6. Bulutga {len(new_cloud_rows)} ta foydalanuvchi yozildi (OK)")
        except Exception as e:
            log(f"Foydalanuvchilar sinxronizatsiyasi xatosi: {e}")

    def _sync_murojaatlar(self):
        if self.sheet is None:
            return
        try:
            records = self.sheet.get_all_records()
            cloud_ids = set()
            with self._get_connection() as conn:
                cursor = conn.cursor()
                if records:
                    df = pd.DataFrame(records)
                    for _, row in df.iterrows():
                        try:
                            m_id = int(row.get('#', 0))
                        except Exception:
                            continue
                        if m_id <= 9: continue
                        cloud_ids.add(m_id)
                        cursor.execute("SELECT id FROM murojaatlar WHERE id = ?", (m_id,))
                        if not cursor.fetchone():
                            cursor.execute("""
                                INSERT INTO murojaatlar (
                                    id, yaratilgan_sana, fish, telefon, viloyat, tuman, yonalish, aniq_yonalish, holat, murojaat_matni, javob, javob_bergan, javob_sanasi, ijro_holati, organish_natijasi, biriktirilgan_fayl, masul_komplayens, chora_turi, manba
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (
                                m_id, str(row.get('Yaratilgan sana', '')), str(row.get('F.I.Sh.', '')), str(row.get('Telefon', '')), 
                                str(row.get('Viloyat', '')), str(row.get('Tuman', '')), str(row.get('Yoʻnalish', '')), str(row.get('Aniq_Yonalish', '')), 
                                str(row.get('Holat', '')), str(row.get('Murojaat matni', '')), str(row.get('Javob', '')), str(row.get('Javob bergan', '')), 
                                str(row.get('Javob sanasi', '')), str(row.get('Ijro_Holati', 'O‘rganishga yuborilgan')), str(row.get('Organish_Natijasi', '')), 
                                str(row.get('Biriktirilgan_Fayl', '')), str(row.get('Masul_Komplayens', '')), str(row.get('Chora_Turi', 'Chora ko‘rilmagan')), str(row.get('Manba', 'Telegram bot'))
                            ))
                        else:
                            cursor.execute("""
                                UPDATE murojaatlar SET holat = ?, ijro_holati = ?, organish_natijasi = ?, biriktirilgan_fayl = ?, masul_komplayens = ?, chora_turi = ?, javob = ?, javob_bergan = ?, javob_sanasi = ? WHERE id = ?
                            """, (
                                str(row.get('Holat', '')), str(row.get('Ijro_Holati', '')), str(row.get('Organish_Natijasi', '')), 
                                str(row.get('Biriktirilgan_Fayl', '')), str(row.get('Masul_Komplayens', '')), str(row.get('Chora_Turi', '')), 
                                str(row.get('Javob', '')), str(row.get('Javob bergan', '')), str(row.get('Javob sanasi', '')), m_id
                            ))
                    conn.commit()
                
                cursor.execute("SELECT * FROM murojaatlar WHERE id > 9")
                local_rows = cursor.fetchall()
                missing_in_cloud = []
                for r in local_rows:
                    if r[0] not in cloud_ids:
                        missing_in_cloud.append([str(x) if x is not None else "" for x in r])
                if missing_in_cloud:
                    self.sheet.append_rows(missing_in_cloud)
                    log(f"7. Bulutga {len(missing_in_cloud)} ta murojaat yozildi (OK)")
        except Exception as e:
            log(f"Murojaatlar sinxronizatsiyasi xatosi: {e}")

    def check_user_login(self, username, password):
        username = str(username).strip()
        password = str(password).strip()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT role FROM users WHERE username = ? AND password = ? AND active = 1", (username, password))
            res = cursor.fetchone()
            if res:
                return res[0]
                
        if self.users_sheet is not None:
            try:
                records = self.users_sheet.get_all_records()
                for row in records:
                    u_name = str(row.get('Username', '')).strip()
                    u_pass = str(row.get('Password', '')).strip()
                    u_role = str(row.get('Role', '')).strip()
                    try:
                        u_act = int(row.get('Active', 1))
                    except Exception:
                        u_act = 1
                    if u_name == username and u_pass == password and u_act == 1:
                        with self._get_connection() as conn:
                            cursor = conn.cursor()
                            cursor.execute("INSERT OR REPLACE INTO users (username, password, role, active) VALUES (?, ?, ?, ?)", (u_name, u_pass, u_role, u_act))
                            conn.commit()
                        return u_role
            except Exception as e:
                log(f"Login tekshirish xatosi: {e}")
        return None

    def get_all_users(self):
        with self._get_connection() as conn:
            return pd.read_sql_query("SELECT id, username, password, role FROM users", conn)

    def add_user(self, username, password, role):
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", (username, password, role))
                user_id = cursor.lastrowid
                conn.commit()
            self._sync_single_user_to_cloud(user_id, username, password, role, 1)
            return True
        except sqlite3.IntegrityError:
            return False

    def update_user(self, user_id, username, password, role):
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE users SET username = ?, password = ?, role = ? WHERE id = ?", (username, password, role, user_id))
                conn.commit()
            self._sync_single_user_to_cloud(user_id, username, password, role, 1)
            return True
        except Exception:
            return False

    def delete_user(self, user_id):
        if str(user_id) == "1":
            return False
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
            conn.commit()
        self._sync_single_user_to_cloud(user_id, "DELETED", "", "", 0)
        return True

    def _sync_single_user_to_cloud(self, user_id, username, password, role, active=1):
        if self.users_sheet is None:
            return
        def push_user():
            try:
                values = [str(user_id), str(username), str(password), str(role), int(active)]
                cell = None
                try:
                    cell = self.users_sheet.find(str(user_id), in_column=1)
                except Exception:
                    pass
                if cell:
                    self.users_sheet.update(f"A{cell.row}:E{cell.row}", [values])
                else:
                    self.users_sheet.append_row(values)
            except Exception as e:
                log(f"Foydalanuvchini yozish xatosi: {e}")
        threading.Thread(target=push_user, daemon=True).start()

    def _sync_single_row_to_cloud(self, row_data):
        if self.sheet is None:
            return
        def push_data():
            try:
                m_id = str(row_data[0])
                cell = self.sheet.find(m_id, in_column=1)
                values = [str(x) if x is not None else "" for x in row_data]
                if cell:
                    self.sheet.update(f"A{cell.row}:S{cell.row}", [values])
                else:
                    self.sheet.append_row(values)
            except Exception as e:
                log(f"Murojaatni yozish xatosi: {e}")
        threading.Thread(target=push_data, daemon=True).start()

    def _sync_batch_to_cloud(self, new_rows_data_list):
        if self.sheet is None or not new_rows_data_list:
            return
        def push_batch():
            try:
                batch_values = [[str(x) if x is not None else "" for x in r] for r in new_rows_data_list]
                if batch_values:
                    self.sheet.append_rows(batch_values)
            except Exception as e:
                log(f"Batch yozish xatosi: {e}")
        threading.Thread(target=push_batch, daemon=True).start()

    def _get_row_by_id(self, m_id):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM murojaatlar WHERE id = ?", (m_id,))
            return cursor.fetchone()

    def get_settings(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT key, val FROM sozlamalar")
            return {row[0]: row[1] for row in cursor.fetchall()}

    def update_settings(self, settings_dict):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            for k, v in settings_dict.items():
                cursor.execute("UPDATE sozlamalar SET val = ? WHERE key = ?", (v, k))
            conn.commit()

    def sync_excel_data(self, df):
        new_cloud_records = []
        with self._get_connection() as conn:
            cursor = conn.cursor()
            for _, row in df.iterrows():
                try:
                    m_id = int(row.get('#', 0))
                except Exception:
                    continue
                if m_id <= 9: continue
                
                cursor.execute("SELECT id FROM murojaatlar WHERE id = ?", (m_id,))
                exists = cursor.fetchone()
                y_str = str(row.get('Yoʻnalish', '')).lower()
                default_masul = "Davlat kadastrlari palatasi hududiy komplayens xodimi" if 'palata' in y_str else "Kadastr agentligi hududiy komplayens xodimi"

                if not exists:
                    cursor.execute("""
                        INSERT INTO murojaatlar (
                            id, yaratilgan_sana, fish, telefon, viloyat, tuman, yonalish, aniq_yonalish, holat, murojaat_matni, javob, javob_bergan, javob_sanasi, ijro_holati, organish_natijasi, biriktirilgan_fayl, masul_komplayens, chora_turi, manba
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'O‘rganishga yuborilgan', '', '', ?, 'Chora ko‘rilmagan', 'Telegram bot')
                    """, (
                        m_id, str(row.get('Yaratilgan sana', '')), str(row.get('F.I.Sh.', '')), str(row.get('Telefon', '')), 
                        str(row.get('Viloyat', '')), str(row.get('Tuman', '')), str(row.get('Yoʻnalish', '')), str(row.get('Aniq_Yonalish', '')), 
                        str(row.get('Holat', '')), str(row.get('Murojaat matni', '')), str(row.get('Javob', '')), str(row.get('Javob bergan', '')), 
                        str(row.get('Javob sanasi', '')), default_masul
                    ))
                    row_data = self._get_row_by_id(m_id)
                    if row_data:
                        new_cloud_records.append(row_data)
            conn.commit()
            
        if new_cloud_records:
            self._sync_batch_to_cloud(new_cloud_records)

    def insert_phone_murojaat(self, fish, telefon, viloyat, tuman, yonalish, matn, masul_komplayens):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COALESCE(MAX(id), 100) FROM murojaatlar")
            new_id = max(cursor.fetchone()[0] + 1, 101)
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            aniq_y = "Davlat kadastrlari palatasi hududiy boshqarmasi" if "palata" in yonalish.lower() else "Kadastr agentligi hududiy boshqarmasi"
            
            cursor.execute("""
                INSERT INTO murojaatlar (
                    id, yaratilgan_sana, fish, telefon, viloyat, tuman, yonalish, aniq_yonalish, holat, murojaat_matni, javob, javob_bergan, javob_sanasi, ijro_holati, organish_natijasi, biriktirilgan_fayl, masul_komplayens, chora_turi, manba
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Yangi', ?, '', '', '', 'O‘rganishga yuborilgan', '', '', ?, 'Chora ko‘rilmagan', 'Ishonch telefoni (+998-71-273-19-66)')
            """, (new_id, now_str, fish, telefon, viloyat, tuman, yonalish, aniq_y, matn, masul_komplayens))
            conn.commit()
            
        row_data = self._get_row_by_id(new_id)
        if row_data:
            self._sync_single_row_to_cloud(row_data)
        return new_id

    def update_murojaat_ijro(self, m_id, ijro_holati, organish_natijasi, biriktirilgan_fayl='', masul_komplayens='', chora_turi='Chora ko‘rilmagan'):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE murojaatlar SET ijro_holati = ?, organish_natijasi = ?, biriktirilgan_fayl = ?, masul_komplayens = ?, chora_turi = ? WHERE id = ?", (ijro_holati, organish_natijasi, biriktirilgan_fayl, masul_komplayens, chora_turi, m_id))
            conn.commit()
            
        row_data = self._get_row_by_id(m_id)
        if row_data:
            self._sync_single_row_to_cloud(row_data)

    def get_all_records(self):
        with self._get_connection() as conn:
            df = pd.read_sql_query("SELECT * FROM murojaatlar WHERE id > 9 ORDER BY id DESC", conn)
            df = df.rename(columns={'id': '#', 'yaratilgan_sana': 'Yaratilgan sana', 'fish': 'F.I.Sh.', 'telefon': 'Telefon', 'viloyat': 'Viloyat', 'tuman': 'Tuman', 'yonalish': 'Yoʻnalish', 'aniq_yonalish': 'Aniq_Yonalish', 'holat': 'Holat', 'murojaat_matni': 'Murojaat matni', 'javob': 'Javob', 'javob_bergan': 'Javob bergan', 'javob_sanasi': 'Javob sanasi', 'ijro_holati': 'Ijro_Holati', 'organish_natijasi': 'Organish_Natijasi', 'biriktirilgan_fayl': 'Biriktirilgan_Fayl', 'masul_komplayens': 'Masul_Komplayens', 'chora_turi': 'Chora_Turi', 'manba': 'Manba'})
            if 'Manba' not in df.columns:
                df['Manba'] = 'Telegram bot'
            df['Manba'] = df['Manba'].fillna('Telegram bot')
            return df

    def get_xodimlar(self):
        with self._get_connection() as conn:
            return pd.read_sql_query("SELECT * FROM xodimlar ORDER BY viloyat ASC, tashkilot_turi ASC", conn)

    def save_xodim(self, x_id, fish, telefon, telegram_username):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE xodimlar SET fish = ?, telefon = ?, telegram_username = ? WHERE id = ?", (fish, telefon, telegram_username, x_id))
            conn.commit()

    def find_xodim_for_region(self, viloyat, masul_str):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            t_type = "Davlat kadastrlari palatasi" if "palata" in str(masul_str).lower() else "Kadastr agentligi"
            cursor.execute("SELECT fish, telefon, telegram_username FROM xodimlar WHERE viloyat = ? AND tashkilot_turi = ?", (viloyat, t_type))
            row = cursor.fetchone()
            if row:
                return {"fish": row[0], "telefon": row[1], "username": row[2]}
            return {"fish": "Noma'lum", "telefon": "", "username": ""}

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

# 1. SSL TEKSHIRUVINI CHETLAB O'TISH (RAHBAR KOMPYUTERI VA GOOGLE SHEETS UCHUN)
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

class DatabaseManager:
    def __init__(self, db_path=None):
        data_dir = os.path.join(BASE_DIR, "data")
        os.makedirs(data_dir, exist_ok=True)
        self.db_path = db_path if db_path else os.path.join(data_dir, "murojaatlar.db")
        
        p1 = os.path.join(data_dir, "credentials.json")
        p2 = os.path.join(BASE_DIR, "credentials.json")
        self.json_key_path = p1 if os.path.exists(p1) else (p2 if os.path.exists(p2) else p1)
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
        self.users_sheet = self._ensure_worksheet("Foydalanuvchilar", ['ID', 'Username', 'Password', 'Role', 'Active'], 5)
        self.audit_sheet = self._ensure_worksheet("Kirishlar_Tarixi", ['ID', 'Foydalanuvchi', 'Rol', 'Kirish vaqti', 'Kompyuter nomi'], 5)
        
        self._sync_users()
        self._sync_murojaatlar()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _auto_backup(self):
        try:
            if os.path.exists(self.db_path):
                backup_dir = os.path.join(BASE_DIR, "data", "backup")
                os.makedirs(backup_dir, exist_ok=True)
                b_path = os.path.join(backup_dir, f"murojaatlar_{datetime.now().strftime('%Y_%m_%d')}.db")
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
            cursor.execute("CREATE TABLE IF NOT EXISTS sozlamalar (key TEXT PRIMARY KEY, val TEXT)")
            
            cursor.execute("SELECT COUNT(*) FROM users")
            if cursor.fetchone()[0] == 0:
                cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", ("admin", "admin123", "admin"))
                cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", ("rahbar", "1977", "kuzatuvchi"))
            conn.commit()

    def _connect_gsheets(self):
        if not HAS_GSHEETS or not os.path.exists(self.json_key_path):
            return None
        try:
            scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
            creds = ServiceAccountCredentials.from_json_keyfile_name(self.json_key_path, scope)
            client = gspread.authorize(creds)
            if hasattr(client, 'http_client') and hasattr(client.http_client, 'session'):
                client.http_client.session.verify = False
            return client
        except Exception:
            return None

    def _ensure_worksheet(self, title, headers, cols):
        if self.client is None: return None
        try:
            spreadsheet = self.client.open(self.sheet_name)
            try:
                sheet = spreadsheet.worksheet(title)
            except Exception:
                sheet = spreadsheet.add_worksheet(title=title, rows="1000", cols=str(cols))
            if not sheet.row_values(1):
                sheet.insert_row(headers, 1)
            return sheet
        except Exception:
            return None

    def log_user_entry(self, username, role):
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        comp_name = os.environ.get('COMPUTERNAME', 'Noma\'lum')
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO audit_logs (username, role, kirish_vaqti, kompyuter) VALUES (?, ?, ?, ?)", (username, role, now_str, comp_name))
                log_id = cursor.lastrowid
                conn.commit()
            if self.audit_sheet:
                threading.Thread(target=lambda: self.audit_sheet.append_row([str(log_id), str(username), str(role), now_str, comp_name]), daemon=True).start()
        except Exception:
            pass

    def check_user_login(self, username, password):
        username = str(username).strip()
        password = str(password).strip()
        found_role = None
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT role FROM users WHERE username = ? AND password = ? AND active = 1", (username, password))
            res = cursor.fetchone()
            if res:
                found_role = res[0]
                
        if not found_role and self.users_sheet:
            try:
                records = self.users_sheet.get_all_records()
                for row in records:
                    if str(row.get('Username', '')).strip() == username and str(row.get('Password', '')).strip() == password and int(row.get('Active', 1)) == 1:
                        found_role = str(row.get('Role', '')).strip()
                        with self._get_connection() as conn:
                            cursor = conn.cursor()
                            cursor.execute("INSERT OR REPLACE INTO users (username, password, role, active) VALUES (?, ?, ?, 1)", (username, password, found_role))
                            conn.commit()
                        break
            except Exception:
                pass
                
        if found_role:
            self.log_user_entry(username, found_role)
            return found_role
        return None

    def _sync_users(self):
        if self.users_sheet is None: return
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
                    if not un or un == 'DELETED': continue
                    cloud_usernames.add(un)
                    cursor.execute("SELECT id FROM users WHERE username = ?", (un,))
                    if not cursor.fetchone():
                        cursor.execute("INSERT INTO users (username, password, role, active) VALUES (?, ?, ?, ?)", (un, pw, rl, act))
                    else:
                        cursor.execute("UPDATE users SET password = ?, role = ?, active = ? WHERE username = ?", (pw, rl, act, un))
                conn.commit()
                cursor.execute("SELECT id, username, password, role, active FROM users WHERE active = 1")
                new_cloud_rows = [[str(u[0]), str(u[1]), str(u[2]), str(u[3]), int(u[4])] for u in cursor.fetchall() if u[1] not in cloud_usernames]
                if new_cloud_rows:
                    self.users_sheet.append_rows(new_cloud_rows)
        except Exception:
            pass

    def _sync_murojaatlar(self):
        if self.sheet is None: return
        try:
            records = self.sheet.get_all_records()
            cloud_ids = set()
            with self._get_connection() as conn:
                cursor = conn.cursor()
                df = pd.DataFrame(records)
                for _, row in df.iterrows():
                    try: m_id = int(row.get('#', 0))
                    except: continue
                    if m_id <= 9: continue
                    cloud_ids.add(m_id)
                    cursor.execute("SELECT id FROM murojaatlar WHERE id = ?", (m_id,))
                    if not cursor.fetchone():
                        cursor.execute("""INSERT INTO murojaatlar (id, yaratilgan_sana, fish, telefon, viloyat, tuman, yonalish, aniq_yonalish, holat, murojaat_matni, javob, javob_bergan, javob_sanasi, ijro_holati, organish_natijasi, biriktirilgan_fayl, masul_komplayens, chora_turi, manba) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", 
                        (m_id, str(row.get('Yaratilgan sana', '')), str(row.get('F.I.Sh.', '')), str(row.get('Telefon', '')), str(row.get('Viloyat', '')), str(row.get('Tuman', '')), str(row.get('Yoʻnalish', '')), str(row.get('Aniq_Yonalish', '')), str(row.get('Holat', '')), str(row.get('Murojaat matni', '')), str(row.get('Javob', '')), str(row.get('Javob bergan', '')), str(row.get('Javob sanasi', '')), str(row.get('Ijro_Holati', 'O‘rganishga yuborilgan')), str(row.get('Organish_Natijasi', '')), str(row.get('Biriktirilgan_Fayl', '')), str(row.get('Masul_Komplayens', '')), str(row.get('Chora_Turi', 'Chora ko‘rilmagan')), str(row.get('Manba', 'Telegram bot'))))
                    else:
                        cursor.execute("""UPDATE murojaatlar SET holat = ?, ijro_holati = ?, organish_natijasi = ?, biriktirilgan_fayl = ?, masul_komplayens = ?, chora_turi = ?, javob = ?, javob_bergan = ?, javob_sanasi = ? WHERE id = ?""", 
                        (str(row.get('Holat', '')), str(row.get('Ijro_Holati', '')), str(row.get('Organish_Natijasi', '')), str(row.get('Biriktirilgan_Fayl', '')), str(row.get('Masul_Komplayens', '')), str(row.get('Chora_Turi', '')), str(row.get('Javob', '')), str(row.get('Javob bergan', '')), str(row.get('Javob sanasi', '')), m_id))
                conn.commit()
                cursor.execute("SELECT * FROM murojaatlar WHERE id > 9")
                missing_in_cloud = [[str(x) if x is not None else "" for x in r] for r in cursor.fetchall() if r[0] not in cloud_ids]
                if missing_in_cloud:
                    self.sheet.append_rows(missing_in_cloud)
        except Exception:
            pass

    def get_all_records(self):
        with self._get_connection() as conn:
            df = pd.read_sql_query("SELECT * FROM murojaatlar WHERE id > 9 ORDER BY id DESC", conn)
            df = df.rename(columns={'id': '#', 'yaratilgan_sana': 'Yaratilgan sana', 'fish': 'F.I.Sh.', 'telefon': 'Telefon', 'viloyat': 'Viloyat', 'tuman': 'Tuman', 'yonalish': 'Yoʻnalish', 'aniq_yonalish': 'Aniq_Yonalish', 'holat': 'Holat', 'murojaat_matni': 'Murojaat matni', 'javob': 'Javob', 'javob_bergan': 'Javob bergan', 'javob_sanasi': 'Javob sanasi', 'ijro_holati': 'Ijro_Holati', 'organish_natijasi': 'Organish_Natijasi', 'biriktirilgan_fayl': 'Biriktirilgan_Fayl', 'masul_komplayens': 'Masul_Komplayens', 'chora_turi': 'Chora_Turi', 'manba': 'Manba'})
            if 'Manba' not in df.columns: df['Manba'] = 'Telegram bot'
            df['Manba'] = df['Manba'].fillna('Telegram bot')
            return df

    def _get_row_by_id(self, m_id):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM murojaatlar WHERE id = ?", (m_id,))
            return cursor.fetchone()

    def update_murojaat_ijro(self, m_id, ijro_holati, organish_natijasi, biriktirilgan_fayl='', masul_komplayens='', chora_turi='Chora ko‘rilmagan'):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE murojaatlar SET ijro_holati = ?, organish_natijasi = ?, biriktirilgan_fayl = ?, masul_komplayens = ?, chora_turi = ? WHERE id = ?", (ijro_holati, organish_natijasi, biriktirilgan_fayl, masul_komplayens, chora_turi, m_id))
            conn.commit()
        row_data = self._get_row_by_id(m_id)
        if row_data and self.sheet:
            threading.Thread(target=lambda: self._sync_single_row_to_cloud(row_data), daemon=True).start()

    def _sync_single_row_to_cloud(self, row_data):
        try:
            cell = self.sheet.find(str(row_data[0]), in_column=1)
            values = [str(x) if x is not None else "" for x in row_data]
            if cell: self.sheet.update(f"A{cell.row}:S{cell.row}", [values])
            else: self.sheet.append_row(values)
        except Exception:
            pass

    def insert_phone_murojaat(self, fish, telefon, viloyat, tuman, yonalish, matn, masul_komplayens):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COALESCE(MAX(id), 100) FROM murojaatlar")
            new_id = max(cursor.fetchone()[0] + 1, 101)
            aniq_y = "Davlat kadastrlari palatasi hududiy boshqarmasi" if "palata" in yonalish.lower() else "Kadastr agentligi hududiy boshqarmasi"
            cursor.execute("""INSERT INTO murojaatlar (id, yaratilgan_sana, fish, telefon, viloyat, tuman, yonalish, aniq_yonalish, holat, murojaat_matni, javob, javob_bergan, javob_sanasi, ijro_holati, organish_natijasi, biriktirilgan_fayl, masul_komplayens, chora_turi, manba) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Yangi', ?, '', '', '', 'O‘rganishga yuborilgan', '', '', ?, 'Chora ko‘rilmagan', 'Ishonch telefoni (+998-71-273-19-66)')""", (new_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), fish, telefon, viloyat, tuman, yonalish, aniq_y, matn, masul_komplayens))
            conn.commit()
        row_data = self._get_row_by_id(new_id)
        if row_data and self.sheet:
            threading.Thread(target=lambda: self._sync_single_row_to_cloud(row_data), daemon=True).start()
        return new_id

    def sync_excel_data(self, df):
        new_cloud_records = []
        with self._get_connection() as conn:
            cursor = conn.cursor()
            for _, row in df.iterrows():
                try: m_id = int(row.get('#', 0))
                except: continue
                if m_id <= 9: continue
                cursor.execute("SELECT id FROM murojaatlar WHERE id = ?", (m_id,))
                if not cursor.fetchone():
                    default_masul = "Davlat kadastrlari palatasi hududiy komplayens xodimi" if 'palata' in str(row.get('Yoʻnalish', '')).lower() else "Kadastr agentligi hududiy komplayens xodimi"
                    cursor.execute("""INSERT INTO murojaatlar (id, yaratilgan_sana, fish, telefon, viloyat, tuman, yonalish, aniq_yonalish, holat, murojaat_matni, javob, javob_bergan, javob_sanasi, ijro_holati, organish_natijasi, biriktirilgan_fayl, masul_komplayens, chora_turi, manba) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'O‘rganishga yuborilgan', '', '', ?, 'Chora ko‘rilmagan', 'Telegram bot')""", (m_id, str(row.get('Yaratilgan sana', '')), str(row.get('F.I.Sh.', '')), str(row.get('Telefon', '')), str(row.get('Viloyat', '')), str(row.get('Tuman', '')), str(row.get('Yoʻnalish', '')), str(row.get('Aniq_Yonalish', '')), str(row.get('Holat', '')), str(row.get('Murojaat matni', '')), str(row.get('Javob', '')), str(row.get('Javob bergan', '')), str(row.get('Javob sanasi', '')), default_masul))
                    row_data = self._get_row_by_id(m_id)
                    if row_data: new_cloud_records.append(row_data)
            conn.commit()
        if new_cloud_records and self.sheet:
            threading.Thread(target=lambda: self.sheet.append_rows([[str(x) if x is not None else "" for x in r] for r in new_cloud_records]), daemon=True).start()

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
            return pd.read_sql_query("SELECT * FROM xodimlar ORDER BY viloyat ASC, tashkilot_turi ASC", conn)

    def save_xodim(self, x_id, fish, telefon, telegram_username):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE xodimlar SET fish = ?, telefon = ?, telegram_username = ? WHERE id = ?", (fish, telefon, telegram_username, x_id))
            conn.commit()

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
            if self.users_sheet: threading.Thread(target=lambda: self.users_sheet.append_row([str(user_id), str(username), str(password), str(role), 1]), daemon=True).start()
            return True
        except sqlite3.IntegrityError:
            return False

    def delete_user(self, user_id):
        if str(user_id) == "1": return False
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
            conn.commit()
        if self.users_sheet:
            def del_cloud():
                try:
                    cell = self.users_sheet.find(str(user_id), in_column=1)
                    if cell: self.users_sheet.update(f"A{cell.row}:E{cell.row}", [[str(user_id), "DELETED", "", "", 0]])
                except: pass
            threading.Thread(target=del_cloud, daemon=True).start()
        return True

    def get_audit_logs(self):
        with self._get_connection() as conn:
            return pd.read_sql_query("SELECT id as '#', username as 'Foydalanuvchi', role as 'Rol', kirish_vaqti as 'Kirish vaqti', kompyuter as 'Kompyuter' FROM audit_logs ORDER BY id DESC LIMIT 200", conn)

import sqlite3
import pandas as pd
import os
import shutil
import threading
from datetime import datetime

# Google Sheets ulanishi uchun
try:
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
    HAS_GSHEETS = True
except ImportError:
    HAS_GSHEETS = False

class DatabaseManager:
    def __init__(self, db_path=None):
        if db_path is None:
            os.makedirs("data", exist_ok=True)
            db_path = os.path.join("data", "murojaatlar.db")
        self.db_path = db_path
        
        # credentials.json fayli data ichida yoki asosiy papkada bo'lishi mumkin
        self.json_key_path = os.path.join("data", "credentials.json")
        if not os.path.exists(self.json_key_path):
            self.json_key_path = "credentials.json"
            
        # Jadvalingizning aniq ID raqami
        self.sheet_id = "17igQpL4sNkEyQnIkJ58oqWVKQpVHh0mj4njx-UJXN34"
        
        self.gsheet_headers = [
            '#', 'Yaratilgan sana', 'F.I.Sh.', 'Telefon', 'Viloyat', 'Tuman', 
            'Yoʻnalish', 'Aniq_Yonalish', 'Holat', 'Murojaat matni', 'Javob', 
            'Javob bergan', 'Javob sanasi', 'Ijro_Holati', 'Organish_Natijasi', 
            'Biriktirilgan_Fayl', 'Masul_Komplayens', 'Chora_Turi', 'Manba'
        ]
        
        self.users_headers = ['ID', 'Username', 'Password', 'Role', 'Active']
        
        self._init_db()
        self._auto_backup()
        
        # Bulutga (Google Sheets) ID orqali to'g'ridan-to'g'ri ulanish
        self.client = self._connect_gsheets()
        self.sheet = self._ensure_worksheet_and_headers()
        self.users_sheet = self._ensure_users_worksheet()
        
        # Dastur ochilishi bilan bulut va lokal baza o'rtasida to'liq sinxronizatsiya
        self._sync_all()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _auto_backup(self):
        try:
            if os.path.exists(self.db_path):
                backup_dir = os.path.join("data", "backup")
                os.makedirs(backup_dir, exist_ok=True)
                today_str = datetime.now().strftime("%Y_%m_%d")
                b_path = os.path.join(backup_dir, f"murojaatlar_{today_str}.db")
                if not os.path.exists(b_path):
                    shutil.copy2(self.db_path, b_path)
        except Exception:
            pass

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
        if not HAS_GSHEETS or not os.path.exists(self.json_key_path): 
            return None
        try:
            scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
            creds = ServiceAccountCredentials.from_json_keyfile_name(self.json_key_path, scope)
            return gspread.authorize(creds)
        except Exception: 
            return None

    def _ensure_worksheet_and_headers(self):
        if self.client is None: 
            return None
        try:
            spreadsheet = self.client.open_by_key(self.sheet_id)
            try: 
                sheet = spreadsheet.worksheet("Murojaatlar")
            except gspread.exceptions.WorksheetNotFound: 
                sheet = spreadsheet.add_worksheet(title="Murojaatlar", rows="1000", cols="20")
                
            headers = sheet.row_values(1)
            if not headers:
                sheet.insert_row(self.gsheet_headers, 1)
                sheet.format('A1:S1', {'textFormat': {'bold': True}})
            return sheet
        except Exception: 
            return None

    def _ensure_users_worksheet(self):
        if self.client is None: 
            return None
        try:
            spreadsheet = self.client.open_by_key(self.sheet_id)
            try: 
                sheet = spreadsheet.worksheet("Foydalanuvchilar")
            except gspread.exceptions.WorksheetNotFound: 
                sheet = spreadsheet.add_worksheet(title="Foydalanuvchilar", rows="100", cols="5")
                
            headers = sheet.row_values(1)
            if not headers:
                sheet.insert_row(self.users_headers, 1)
                sheet.format('A1:E1', {'textFormat': {'bold': True}})
            return sheet
        except Exception: 
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
                        except:
                            active = 1
                        if not username or username == 'DELETED': 
                            continue
                        cloud_usernames.add(username)
                        
                        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
                        exists = cursor.fetchone()
                        if not exists:
                            cursor.execute("INSERT INTO users (username, password, role, active) VALUES (?, ?, ?, ?)", 
                                           (username, password, role, active))
                        else:
                            cursor.execute("UPDATE users SET password = ?, role = ?, active = ? WHERE username = ?", 
                                           (password, role, active, username))
                    conn.commit()
                
                cursor.execute("SELECT id, username, password, role, active FROM users WHERE active = 1")
                local_users = cursor.fetchall()
                
                new_cloud_rows = []
                for u in local_users:
                    u_id, u_name, u_pass, u_role, u_act = u
                    if u_name not in cloud_usernames:
                        new_cloud_rows.append([str(u_id), str(u_name), str(u_pass), str(u_role), int(u_act)])
                
                if new_cloud_rows:
                    self.users_sheet.append_rows(new_cloud_rows)
        except Exception:
            pass

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
                        except:
                            continue
                        if m_id <= 9: continue
                        cloud_ids.add(m_id)
                        
                        cursor.execute("SELECT id FROM murojaatlar WHERE id = ?", (m_id,))
                        exists = cursor.fetchone()
                        if not exists:
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
        except Exception: 
            pass

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
                    except:
                        u_act = 1
                    if u_name == username and u_pass == password and u_act == 1:
                        with self._get_connection() as conn:
                            cursor = conn.cursor()
                            cursor.execute("INSERT OR REPLACE INTO users (username, password, role, active) VALUES (?, ?, ?, ?)", 
                                           (u_name, u_pass, u_role, u_act))
                            conn.commit()
                        return u_role
            except Exception:
                pass
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
        except: 
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

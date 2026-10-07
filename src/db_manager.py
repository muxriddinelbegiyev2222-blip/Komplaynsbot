import sqlite3
import pandas as pd
import os
import shutil
from datetime import datetime

class DatabaseManager:
    def __init__(self, db_path=None):
        if db_path is None:
            os.makedirs("data", exist_ok=True)
            db_path = os.path.join("data", "murojaatlar.db")
        self.db_path = db_path
        self._init_db()
        self._auto_backup()

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
                CREATE TABLE IF NOT EXISTS sozlamalar (
                    key TEXT PRIMARY KEY, val TEXT
                )
            """)

            cursor.execute("SELECT COUNT(*) FROM xodimlar")
            if cursor.fetchone()[0] == 0:
                regions = [
                    "Buxoro viloyati", "Farg'ona viloyati", "Jizzax viloyati", "Namangan viloyati", "Navoiy viloyati", "Qashqadaryo viloyati", "Qoraqalpog'iston Respublikasi", "Samarqand viloyati", "Sirdaryo viloyati", "Surxondaryo viloyati", "Toshkent shahri", "Toshkent viloyati", "Xorazm viloyati"
                ]
                for reg in regions:
                    cursor.execute("INSERT INTO xodimlar (viloyat, tashkilot_turi, fish, telefon, telegram_username) VALUES (?, ?, ?, ?, ?)", (reg, "Kadastr agentligi", "Mas'ul xodim", "+998", ""))
                    cursor.execute("INSERT INTO xodimlar (viloyat, tashkilot_turi, fish, telefon, telegram_username) VALUES (?, ?, ?, ?, ?)", (reg, "Davlat kadastrlari palatasi", "Mas'ul xodim", "+998", ""))

            # Default sozlamalar
            default_settings = {
                "sla_days": "2",
                "report_header": "O‘ZBEKISTON RESPUBLIKASI KADASTR AGENTLIGI\nKORRUPSIYAGA QARSHI KURASHISH BO‘LIMI",
                "tg_template": "⚡️ KORRUPSIYAGA QARSHI KOMPLAYENS NAZORAT\n📌 Murojaat № {id}\n📡 Manba: {manba}\n👤 Fuqaro: {fish} (Tel: {tel})\n📍 Hudud: {viloyat}, {tuman}\n🕒 Sana: {sana}\n\n📝 MAZMUNI:\n{matn}\n\n⚠️ Iltimos, ushbu murojaatni zudlik bilan (2 kun ichida) o‘rganib xulosa taqdim eting!"
            }
            for k, v in default_settings.items():
                cursor.execute("INSERT OR IGNORE INTO sozlamalar (key, val) VALUES (?, ?)", (k, v))
            conn.commit()

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
        with self._get_connection() as conn:
            cursor = conn.cursor()
            for _, row in df.iterrows():
                m_id = int(row.get('#', 0))
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
                    """, (m_id, str(row.get('Yaratilgan sana', '')), str(row.get('F.I.Sh.', '')), str(row.get('Telefon', '')), str(row.get('Viloyat', '')), str(row.get('Tuman', '')), str(row.get('Yoʻnalish', '')), str(row.get('Aniq_Yonalish', '')), str(row.get('Holat', '')), str(row.get('Murojaat matni', '')), str(row.get('Javob', '')), str(row.get('Javob bergan', '')), str(row.get('Javob sanasi', '')), default_masul))
                else:
                    cursor.execute("UPDATE murojaatlar SET holat = ?, javob = ?, javob_bergan = ?, javob_sanasi = ?, aniq_yonalish = ? WHERE id = ?", (str(row.get('Holat', '')), str(row.get('Javob', '')), str(row.get('Javob bergan', '')), str(row.get('Javob sanasi', '')), str(row.get('Aniq_Yonalish', '')), m_id))
            conn.commit()

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
            return new_id

    def update_murojaat_ijro(self, m_id, ijro_holati, organish_natijasi, biriktirilgan_fayl='', masul_komplayens='', chora_turi='Chora ko‘rilmagan'):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE murojaatlar SET ijro_holati = ?, organish_natijasi = ?, biriktirilgan_fayl = ?, masul_komplayens = ?, chora_turi = ? WHERE id = ?", (ijro_holati, organish_natijasi, biriktirilgan_fayl, masul_komplayens, chora_turi, m_id))
            conn.commit()

    def get_all_records(self):
        with self._get_connection() as conn:
            df = pd.read_sql_query("SELECT * FROM murojaatlar WHERE id > 9 ORDER BY id DESC", conn)
            df = df.rename(columns={'id': '#', 'yaratilgan_sana': 'Yaratilgan sana', 'fish': 'F.I.Sh.', 'telefon': 'Telefon', 'viloyat': 'Viloyat', 'tuman': 'Tuman', 'yonalish': 'Yoʻnalish', 'aniq_yonalish': 'Aniq_Yonalish', 'holat': 'Holat', 'murojaat_matni': 'Murojaat matni', 'javob': 'Javob', 'javob_bergan': 'Javob bergan', 'javob_sanasi': 'Javob sanasi', 'ijro_holati': 'Ijro_Holati', 'organish_natijasi': 'Organish_Natijasi', 'biriktirilgan_fayl': 'Biriktirilgan_Fayl', 'masul_komplayens': 'Masul_Komplayens', 'chora_turi': 'Chora_Turi', 'manba': 'Manba'})
            if 'Manba' not in df.columns: df['Manba'] = 'Telegram bot'
            df['Manba'] = df['Manba'].fillna('Telegram bot')
            return df

    def get_xodimlar(self):
        with self._get_connection() as conn: return pd.read_sql_query("SELECT * FROM xodimlar ORDER BY viloyat ASC, tashkilot_turi ASC", conn)

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
            if row: return {"fish": row[0], "telefon": row[1], "username": row[2]}
            return {"fish": "Noma'lum", "telefon": "", "username": ""}

import sqlite3
import pandas as pd
import os

class DatabaseManager:
    def __init__(self, db_path=None):
        if db_path is None:
            os.makedirs("data", exist_ok=True)
            db_path = os.path.join("data", "murojaatlar.db")
        self.db_path = db_path
        self._init_db()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS murojaatlar (
                    id INTEGER PRIMARY KEY,
                    yaratilgan_sana TEXT,
                    fish TEXT,
                    telefon TEXT,
                    viloyat TEXT,
                    tuman TEXT,
                    yonalish TEXT,
                    aniq_yonalish TEXT,
                    holat TEXT,
                    murojaat_matni TEXT,
                    javob TEXT,
                    javob_bergan TEXT,
                    javob_sanasi TEXT,
                    kategoriya TEXT,
                    ijro_holati TEXT,
                    organish_natijasi TEXT DEFAULT '',
                    biriktirilgan_fayl TEXT DEFAULT ''
                )
            """)
            conn.commit()

    def sync_excel_data(self, df):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            for _, row in df.iterrows():
                m_id = int(row.get('#', 0))
                # 1 dan 9 gacha bo'lgan test xabarlarni umuman bazaga kiritmaymiz
                if m_id <= 9:
                    continue

                cursor.execute("SELECT id FROM murojaatlar WHERE id = ?", (m_id,))
                exists = cursor.fetchone()

                if not exists:
                    cursor.execute("""
                        INSERT INTO murojaatlar (
                            id, yaratilgan_sana, fish, telefon, viloyat, tuman,
                            yonalish, aniq_yonalish, holat, murojaat_matni, javob, javob_bergan,
                            javob_sanasi, kategoriya, ijro_holati, organish_natijasi, biriktirilgan_fayl
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        m_id,
                        str(row.get('Yaratilgan sana', '')),
                        str(row.get('F.I.Sh.', '')),
                        str(row.get('Telefon', '')),
                        str(row.get('Viloyat', '')),
                        str(row.get('Tuman', '')),
                        str(row.get('Yoʻnalish', '')),
                        str(row.get('Aniq_Yonalish', '')),
                        str(row.get('Holat', '')),
                        str(row.get('Murojaat matni', '')),
                        str(row.get('Javob', '')),
                        str(row.get('Javob bergan', '')),
                        str(row.get('Javob sanasi', '')),
                        str(row.get('Kategoriya', '')),
                        'O‘rganishga yuborilgan',
                        '',
                        ''
                    ))
                else:
                    cursor.execute("""
                        UPDATE murojaatlar SET
                            holat = ?, javob = ?, javob_bergan = ?, javob_sanasi = ?,
                            aniq_yonalish = ?, kategoriya = ?
                        WHERE id = ?
                    """, (
                        str(row.get('Holat', '')),
                        str(row.get('Javob', '')),
                        str(row.get('Javob bergan', '')),
                        str(row.get('Javob sanasi', '')),
                        str(row.get('Aniq_Yonalish', '')),
                        str(row.get('Kategoriya', '')),
                        m_id
                    ))
            conn.commit()

    def update_murojaat_ijro(self, m_id, ijro_holati, organish_natijasi, biriktirilgan_fayl=''):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE murojaatlar 
                SET ijro_holati = ?, organish_natijasi = ?, biriktirilgan_fayl = ?
                WHERE id = ?
            """, (ijro_holati, organish_natijasi, biriktirilgan_fayl, m_id))
            conn.commit()

    def get_all_records(self):
        with self._get_connection() as conn:
            df = pd.read_sql_query("SELECT * FROM murojaatlar WHERE id > 9 ORDER BY id DESC", conn)
            df = df.rename(columns={
                'id': '#',
                'yaratilgan_sana': 'Yaratilgan sana',
                'fish': 'F.I.Sh.',
                'telefon': 'Telefon',
                'viloyat': 'Viloyat',
                'tuman': 'Tuman',
                'yonalish': 'Yoʻnalish',
                'aniq_yonalish': 'Aniq_Yonalish',
                'holat': 'Holat',
                'murojaat_matni': 'Murojaat matni',
                'javob': 'Javob',
                'javob_bergan': 'Javob bergan',
                'javob_sanasi': 'Javob sanasi',
                'kategoriya': 'Kategoriya',
                'ijro_holati': 'Ijro_Holati',
                'organish_natijasi': 'Organish_Natijasi',
                'biriktirilgan_fayl': 'Biriktirilgan_Fayl'
            })
            return df

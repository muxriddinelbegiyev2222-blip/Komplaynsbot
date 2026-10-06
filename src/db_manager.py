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
                    is_1097 INTEGER,
                    ijro_holati TEXT DEFAULT 'Javob berilgan',
                    chora_mazmuni TEXT DEFAULT ''
                )
            """)
            conn.commit()

    def sync_excel_data(self, df):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            for _, row in df.iterrows():
                m_id = int(row.get('#', 0))
                cursor.execute("SELECT id FROM murojaatlar WHERE id = ?", (m_id,))
                exists = cursor.fetchone()

                if not exists:
                    cursor.execute("""
                        INSERT INTO murojaatlar (
                            id, yaratilgan_sana, fish, telefon, viloyat, tuman,
                            yonalish, aniq_yonalish, holat, murojaat_matni, javob, javob_bergan,
                            javob_sanasi, kategoriya, is_1097, ijro_holati, chora_mazmuni
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
                        int(row.get('is_1097', 0)),
                        'Javob berilgan',
                        ''
                    ))
                else:
                    cursor.execute("""
                        UPDATE murojaatlar SET
                            holat = ?, javob = ?, javob_bergan = ?, javob_sanasi = ?,
                            aniq_yonalish = ?, kategoriya = ?, is_1097 = ?
                        WHERE id = ?
                    """, (
                        str(row.get('Holat', '')),
                        str(row.get('Javob', '')),
                        str(row.get('Javob bergan', '')),
                        str(row.get('Javob sanasi', '')),
                        str(row.get('Aniq_Yonalish', '')),
                        str(row.get('Kategoriya', '')),
                        int(row.get('is_1097', 0)),
                        m_id
                    ))
            conn.commit()

    def update_murojaat_ijro(self, m_id, ijro_holati, chora_mazmuni):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE murojaatlar 
                SET ijro_holati = ?, chora_mazmuni = ?
                WHERE id = ?
            """, (ijro_holati, chora_mazmuni, m_id))
            conn.commit()

    def get_all_records(self):
        with self._get_connection() as conn:
            df = pd.read_sql_query("SELECT * FROM murojaatlar ORDER BY id DESC", conn)
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
                'chora_mazmuni': 'Chora_Mazmuni'
            })
            return df

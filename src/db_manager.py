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
                    holat TEXT,
                    murojaat_matni TEXT,
                    javob TEXT,
                    javob_bergan TEXT,
                    javob_sanasi TEXT,
                    tashkilot_turi TEXT,
                    kategoriya TEXT,
                    is_1097 INTEGER,
                    ijro_vaqti_soat REAL
                )
            """)
            conn.commit()

    def sync_dataframe(self, df):
        """Pandas DataFrame-ni bazaga sinxronizatsiya qilish (Deduplikatsiya bilan)"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            for _, row in df.iterrows():
                cursor.execute("""
                    INSERT INTO murojaatlar (
                        id, yaratilgan_sana, fish, telefon, viloyat, tuman,
                        yonalish, holat, murojaat_matni, javob, javob_bergan,
                        javob_sanasi, tashkilot_turi, kategoriya, is_1097, ijro_vaqti_soat
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        holat=excluded.holat,
                        javob=excluded.javob,
                        javob_bergan=excluded.javob_bergan,
                        javob_sanasi=excluded.javob_sanasi,
                        ijro_vaqti_soat=excluded.ijro_vaqti_soat
                """, (
                    int(row.get('#', 0)),
                    str(row.get('Yaratilgan sana', '')),
                    str(row.get('F.I.Sh.', '')),
                    str(row.get('Telefon', '')),
                    str(row.get('Viloyat', '')),
                    str(row.get('Tuman', '')),
                    str(row.get('Yoʻnalish', '')),
                    str(row.get('Holat', '')),
                    str(row.get('Murojaat matni', '')),
                    str(row.get('Javob', '')),
                    str(row.get('Javob bergan', '')),
                    str(row.get('Javob sanasi', '')),
                    str(row.get('Tashkilot_Turi', '')),
                    str(row.get('Kategoriya', '')),
                    1 if row.get('1097_Yuborilgan') else 0,
                    float(row.get('Ijro_Vaqti_Soat', 0.0))
                ))
            conn.commit()

    def get_all_records_df(self):
        with self._get_connection() as conn:
            df = pd.read_sql_query("SELECT * FROM murojaatlar ORDER BY id DESC", conn)
            # Ustun nomlarini dastur standartiga moslash
            df = df.rename(columns={
                'id': '#',
                'yaratilgan_sana': 'Yaratilgan sana',
                'fish': 'F.I.Sh.',
                'telefon': 'Telefon',
                'viloyat': 'Viloyat',
                'tuman': 'Tuman',
                'yonalish': 'Yoʻnalish',
                'holat': 'Holat',
                'murojaat_matni': 'Murojaat matni',
                'javob': 'Javob',
                'javob_bergan': 'Javob bergan',
                'javob_sanasi': 'Javob sanasi',
                'tashkilot_turi': 'Tashkilot_Turi',
                'kategoriya': 'Kategoriya',
                'is_1097': '1097_Yuborilgan',
                'ijro_vaqti_soat': 'Ijro_Vaqti_Soat'
            })
            df['1097_Yuborilgan'] = df['1097_Yuborilgan'] == 1
            return df

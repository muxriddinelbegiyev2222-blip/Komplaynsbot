import pandas as pd
import os
from datetime import datetime, timedelta
from src.db_manager import DatabaseManager

class DataLoader:
    def __init__(self, excel_path=None):
        self.db = DatabaseManager()
        self.df = pd.DataFrame()
        self.filtered_df = pd.DataFrame()
        
        default_file = os.path.join("data", "murojaatlar.xlsx")
        if excel_path and os.path.exists(excel_path):
            self.load_from_excel(excel_path)
        elif os.path.exists(default_file):
            self.load_from_excel(default_file)
        else:
            self.refresh_data()

    def load_from_excel(self, file_path):
        raw_df = pd.read_excel(file_path)
        raw_df.columns = [col.strip() for col in raw_df.columns]
        self._classify(raw_df)
        self.db.sync_excel_data(raw_df)
        self.refresh_data()

    def refresh_data(self):
        self.df = self.db.get_all_records()
        if not self.df.empty:
            self.df['DT'] = pd.to_datetime(self.df['Yaratilgan sana'], errors='coerce')
        self.filtered_df = self.df.copy()

    def _classify(self, df):
        # 1. Botdagi 5 ta yo'nalishni aniq belgilash
        def get_exact_yonalish(val):
            s = str(val).strip()
            if 'markaziy apparati' in s and 'Kadastr agentligi' in s:
                return 'Kadastr agentligi markaziy apparati'
            elif 'hududiy boshqarmasi' in s and 'Kadastr agentligi' in s:
                return 'Kadastr agentligi hududiy boshqarmasi'
            elif 'markaziy apparati' in s and 'palatasi' in s:
                return 'Davlat kadastrlari palatasi markaziy apparati'
            elif 'hududiy boshqarmasi' in s and 'palatasi' in s:
                return 'Davlat kadastrlari palatasi hududiy boshqarmasi'
            return 'Boshqa tizim tashkiloti'

        # 2. 1097 ga yo'naltirilganlik (Javob matnida 1097 mavjudligi)
        def check_1097(val):
            return 1 if '1097' in str(val) else 0

        # 3. Haqiqiy korrupsiya alomati (Murojaat matnidagi kalit so'zlar)
        corruption_words = [
            'pora', 'tamagir', 'ta’magir', 'тамагир', 'таъмагир', 'порахоʻр', 'порахор',
            'korup', 'корруп', 'каруп', 'karup', 'pul talab', 'пул талаб', 
            'pora olish', 'pora berish', 'suiiste', 'суиисте'
        ]
        test_words = ['test', 'тест', 'lorem', 'фыва', 'alo', 'yangilash', '123']

        def get_cat(row):
            matn = str(row.get('Murojaat matni', '')).lower()
            name = str(row.get('F.I.Sh.', '')).lower()
            
            if any(w in matn for w in test_words) or any(w in name for w in ['test', 'nnn', 'ааа']):
                return 'Test/Texnik'
            elif any(w in matn for w in corruption_words):
                return 'Korrupsiyaga oid'
            elif '1097' in str(row.get('Javob', '')):
                return '1097 ga yo‘naltirilgan'
            return 'Sohaviy/Umumiy'

        df['Aniq_Yonalish'] = df['Yoʻnalish'].apply(get_exact_yonalish)
        df['is_1097'] = df['Javob'].apply(check_1097)
        df['Kategoriya'] = df.apply(get_cat, axis=1)

    def filter_data(self, period='Barchasi', yonalish='Barchasi', category='Barchasi'):
        temp = self.df.copy()
        if temp.empty:
            self.filtered_df = temp
            return temp

        # Vaqt filtri (Sana bo'yicha aniq qirqish)
        if 'DT' in temp.columns and temp['DT'].notnull().any():
            max_date = temp['DT'].max() # Bazadagi eng oxirgi kunga nisbatan
            if period == 'Joriy hafta':
                start_week = max_date - timedelta(days=7)
                temp = temp[temp['DT'] >= start_week]
            elif period == 'Joriy oy':
                temp = temp[(temp['DT'].dt.year == max_date.year) & (temp['DT'].dt.month == max_date.month)]
            elif period == 'Joriy yil':
                temp = temp[temp['DT'].dt.year == max_date.year]

        # Yo'nalish filtri (Botingizdagi ro'yxat bo'yicha)
        if yonalish != 'Barchasi':
            temp = temp[temp['Aniq_Yonalish'] == yonalish]

        # Kategoriya filtri
        if category == 'Korrupsiyaga oid':
            temp = temp[temp['Kategoriya'] == 'Korrupsiyaga oid']
        elif category == '1097 ga yo‘naltirilgan':
            temp = temp[temp['is_1097'] == 1]
        elif category == 'Sohaviy/Umumiy':
            temp = temp[temp['Kategoriya'] == 'Sohaviy/Umumiy']

        self.filtered_df = temp
        return temp

    def get_kpi_stats(self):
        d = self.filtered_df
        total = len(d)
        if total == 0:
            return {"total": 0, "korrupsiya": 0, "sent_1097": 0, "organishda": 0, "bartaraf": 0}

        korrupsiya_count = len(d[d['Kategoriya'] == 'Korrupsiyaga oid'])
        sent_1097_count = len(d[d['is_1097'] == 1])
        organishda_count = len(d[d['Ijro_Holati'].astype(str).str.contains("O'rganishda|Yangi", case=False, na=False)])
        bartaraf_count = len(d[d['Ijro_Holati'].astype(str).str.contains("Bartaraf|Ijobiy|Chora|Javob berilgan", case=False, na=False)])

        return {
            "total": total,
            "korrupsiya": korrupsiya_count,
            "sent_1097": sent_1097_count,
            "organishda": organishda_count,
            "bartaraf": bartaraf_count
        }

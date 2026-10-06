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
        
        if '#' in raw_df.columns:
            raw_df = raw_df[raw_df['#'] > 9]

        self._classify(raw_df)
        self.db.sync_excel_data(raw_df)
        self.refresh_data()

    def refresh_data(self):
        self.df = self.db.get_all_records()
        if not self.df.empty:
            self.df['DT'] = pd.to_datetime(self.df['Yaratilgan sana'], errors='coerce')
        self.filtered_df = self.df.copy()

    def _classify(self, df):
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

        corruption_words = [
            'pora', 'tamagir', 'ta’magir', 'тамагир', 'таъмагир', 'порахоʻр', 'порахор',
            'korup', 'корруп', 'каруп', 'karup', 'pul talab', 'пул талаб', 
            'pora olish', 'pora berish', 'suiiste', 'суиисте'
        ]

        def get_cat(row):
            matn = str(row.get('Murojaat matni', '')).lower()
            if any(w in matn for w in corruption_words):
                return 'Korrupsiyaga oid'
            return 'Sohaviy/Umumiy'

        df['Aniq_Yonalish'] = df['Yoʻnalish'].apply(get_exact_yonalish)
        df['Kategoriya'] = df.apply(get_cat, axis=1)

    def filter_data(self, period='Barchasi', yonalish='Barchasi', category='Barchasi', masul='Barchasi'):
        temp = self.df.copy()
        if temp.empty:
            self.filtered_df = temp
            return temp

        if 'DT' in temp.columns and temp['DT'].notnull().any():
            max_date = temp['DT'].max()
            if period == 'Joriy hafta':
                start_week = max_date - timedelta(days=7)
                temp = temp[temp['DT'] >= start_week]
            elif period == 'Joriy oy':
                temp = temp[(temp['DT'].dt.year == max_date.year) & (temp['DT'].dt.month == max_date.month)]
            elif period == 'Joriy yil':
                temp = temp[temp['DT'].dt.year == max_date.year]

        if yonalish != 'Barchasi':
            temp = temp[temp['Aniq_Yonalish'] == yonalish]

        if category == 'Korrupsiyaga oid':
            temp = temp[temp['Kategoriya'] == 'Korrupsiyaga oid']
        elif category == 'Sohaviy/Umumiy':
            temp = temp[temp['Kategoriya'] == 'Sohaviy/Umumiy']

        if masul != 'Barchasi':
            temp = temp[temp['Masul_Komplayens'] == masul]

        self.filtered_df = temp
        return temp

    def get_kpi_stats(self):
        d = self.filtered_df
        total = len(d)
        if total == 0:
            return {
                "total": 0, "korrupsiya": 0, 
                "agentlik_organish": 0, "palata_organish": 0, 
                "natija_kiritilgan": 0, "asossiz": 0
            }

        korrupsiya_count = len(d[d['Kategoriya'] == 'Korrupsiyaga oid'])
        
        # Agentlik va Palata komplayenslarida alohida o'rganishda turganlar
        is_organish = d['Ijro_Holati'].astype(str).str.contains("O‘rganishga yuborilgan|O'rganishda", case=False, na=False)
        agentlik_org = len(d[is_organish & d['Masul_Komplayens'].astype(str).str.contains("agentligi", case=False, na=False)])
        palata_org = len(d[is_organish & d['Masul_Komplayens'].astype(str).str.contains("palata", case=False, na=False)])

        # Natijasi o'rganib chiqilganlar
        natija_count = len(d[d['Ijro_Holati'].astype(str).str.contains("Bartaraf etildi|Ijobiy hal etildi|Intizomiy chora|O‘rganib chiqildi", case=False, na=False)])
        asossiz_count = len(d[d['Ijro_Holati'].astype(str).str.contains("Asossiz", case=False, na=False)])

        return {
            "total": total,
            "korrupsiya": korrupsiya_count,
            "agentlik_organish": agentlik_org,
            "palata_organish": palata_org,
            "natija_kiritilgan": natija_count,
            "asossiz": asossiz_count
        }

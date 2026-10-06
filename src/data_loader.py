import pandas as pd
import os
from datetime import datetime, timedelta
from src.db_manager import DatabaseManager

class DataLoader:
    def __init__(self, excel_path=None):
        self.db = DatabaseManager()
        self.df = pd.DataFrame()
        self.filtered_df = pd.DataFrame()
        
        # Boshlang'ich Excel mavjud bo'lsa yuklaymiz
        if excel_path and os.path.exists(excel_path):
            self.load_from_excel(excel_path)
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
            self.df['Yaratilgan_DT'] = pd.to_datetime(self.df['Yaratilgan sana'], errors='coerce')
        self.filtered_df = self.df.copy()

    def _classify(self, df):
        def get_org(y):
            s = str(y).lower()
            if 'palata' in s:
                return 'Davlat kadastrlari palatasi'
            elif 'agentlik' in s:
                return 'Kadastr agentligi'
            return 'Boshqa tashkilot'

        corruption_words = [
            'pora', 'tamagir', 'ta’magir', 'korup', 'korrup', 'karup', 
            'til biriktir', 'noqonuniy yer', 'mansab', 'pul talab', 'poraxoʻr', 'aldov'
        ]
        test_words = ['test', 'тест', 'lorem', 'фыва', 'alo', 'yangilash', '123']

        def get_cat(row):
            t = str(row.get('Murojaat matni', '')).lower()
            n = str(row.get('F.I.Sh.', '')).lower()
            if any(w in t for w in test_words) or any(w in n for w in ['test', 'nnn', 'ааа']):
                return 'Test/Texnik'
            elif any(w in t for w in corruption_words):
                return 'Korrupsiyaga oid'
            return 'Sohaviy/Umumiy'

        df['Tashkilot_Turi'] = df['Yoʻnalish'].apply(get_org)
        df['1097_Yuborilgan'] = df['Javob'].astype(str).str.contains('1097')
        df['Kategoriya'] = df.apply(get_cat, axis=1)

    def filter_data(self, period='Barchasi', region='Barchasi', org='Barchasi', category='Barchasi'):
        temp = self.df.copy()
        if temp.empty:
            self.filtered_df = temp
            return temp

        # Vaqt filtri
        now = datetime.now()
        if period == 'Joriy hafta' and 'Yaratilgan_DT' in temp.columns:
            start_week = now - timedelta(days=now.weekday())
            temp = temp[temp['Yaratilgan_DT'] >= start_week.replace(hour=0, minute=0, second=0)]
        elif period == 'Joriy oy' and 'Yaratilgan_DT' in temp.columns:
            temp = temp[(temp['Yaratilgan_DT'].dt.year == now.year) & (temp['Yaratilgan_DT'].dt.month == now.month)]
        elif period == 'Joriy yil' and 'Yaratilgan_DT' in temp.columns:
            temp = temp[temp['Yaratilgan_DT'].dt.year == now.year]

        # Hudud filtri
        if region != 'Barchasi':
            temp = temp[temp['Viloyat'] == region]

        # Tashkilot filtri
        if org != 'Barchasi':
            temp = temp[temp['Tashkilot_Turi'] == org]

        # Kategoriya filtri
        if category == 'Korrupsiyaga oid':
            temp = temp[temp['Kategoriya'] == 'Korrupsiyaga oid']
        elif category == '1097 ga yo‘naltirilgan':
            temp = temp[temp['1097_Yuborilgan'] == True]
        elif category == 'Sohaviy/Umumiy':
            temp = temp[temp['Kategoriya'] == 'Sohaviy/Umumiy']

        self.filtered_df = temp
        return temp

    def get_kpi_stats(self):
        d = self.filtered_df
        total = len(d)
        if total == 0:
            return {"total": 0, "korrupsiya": 0, "sent_1097": 0, "organishda": 0, "bartaraf": 0}

        return {
            "total": total,
            "korrupsiya": len(d[d['Kategoriya'] == 'Korrupsiyaga oid']),
            "sent_1097": len(d[d['1097_Yuborilgan'] == True]),
            "organishda": len(d[d['Ijro_Holati'].str.contains("O'rganishda|Yangi", case=False, na=False)]),
            "bartaraf": len(d[d['Ijro_Holati'].str.contains("Bartaraf|Ijobiy|Chora", case=False, na=False)])
        }

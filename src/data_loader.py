import pandas as pd
import os
from src.db_manager import DatabaseManager

class DataLoader:
    def __init__(self, excel_path=None):
        self.excel_path = excel_path
        self.db = DatabaseManager()
        self.df = pd.DataFrame()
        self.load_data()

    def load_data(self):
        # 1. Agar Excel mavjud bo'lsa, o'qib bazaga saqlaydi
        if self.excel_path and os.path.exists(self.excel_path):
            new_df = pd.read_excel(self.excel_path)
            new_df.columns = [col.strip() for col in new_df.columns]
            self._process_and_classify(new_df)
            self.db.sync_dataframe(new_df)

        # 2. Bazadan to'liq ma'lumotni yuklaydi
        self.df = self.db.get_all_records_df()

    def append_new_file(self, new_file_path):
        if not os.path.exists(new_file_path):
            raise FileNotFoundError(f"Fayl topilmadi: {new_file_path}")

        incoming_df = pd.read_excel(new_file_path)
        incoming_df.columns = [col.strip() for col in incoming_df.columns]
        self._process_and_classify(incoming_df)
        self.db.sync_dataframe(incoming_df)
        self.df = self.db.get_all_records_df()

    def _process_and_classify(self, target_df):
        # 1. Tashkilot turi
        def get_org_type(yonalish):
            y = str(yonalish).lower()
            if 'palata' in y:
                return 'Davlat kadastrlari palatasi'
            elif 'agentlik' in y:
                return 'Kadastr agentligi'
            return 'Boshqa tashkilot'

        # 2. 1097 yo'naltirilganlik
        def is_1097(javob):
            return '1097' in str(javob)

        # 3. Kategoriya
        corruption_keywords = [
            'pora', 'tamagir', 'ta’magir', 'korup', 'korrup', 'karup', 
            'til biriktir', 'noqonuniy yer sot', 'mansab', 
            'pul talab', 'poraxoʻr', 'poraxor', 'aldov', 'shaxsimizni sir saqlasa'
        ]
        test_keywords = ['test', 'тест', 'lorem', 'фыва', 'alo', 'yangilash', '123']

        def get_category(row):
            matn = str(row.get('Murojaat matni', '')).lower()
            name = str(row.get('F.I.Sh.', '')).lower()
            if any(t in matn for t in test_keywords) or any(t in name for t in ['test', 'nnn', 'ааа']):
                return 'Test/Texnik'
            elif any(c in matn for c in corruption_keywords):
                return 'Korrupsiyaga oid'
            else:
                return 'Sohaviy/Boshqa'

        # 4. Ijro vaqti (soatda)
        def calc_response_hours(row):
            try:
                t1 = pd.to_datetime(row.get('Yaratilgan sana'))
                t2 = pd.to_datetime(row.get('Javob sanasi'))
                diff = (t2 - t1).total_seconds() / 3600.0
                return round(max(diff, 0), 1)
            except Exception:
                return 0.0

        target_df['Tashkilot_Turi'] = target_df['Yoʻnalish'].apply(get_org_type)
        target_df['1097_Yuborilgan'] = target_df['Javob'].apply(is_1097)
        target_df['Kategoriya'] = target_df.apply(get_category, axis=1)
        target_df['Ijro_Vaqti_Soat'] = target_df.apply(calc_response_hours, axis=1)

    def get_summary_stats(self):
        total = len(self.df)
        if total == 0:
            return {"total": 0, "agentlik": 0, "palata": 0, "korrupsiya": 0, "sent_1097": 0, "javob_berilgan": 0, "avg_time": 0}

        agentlik = len(self.df[self.df['Tashkilot_Turi'] == 'Kadastr agentligi'])
        palata = len(self.df[self.df['Tashkilot_Turi'] == 'Davlat kadastrlari palatasi'])
        korrupsiya = len(self.df[self.df['Kategoriya'] == 'Korrupsiyaga oid'])
        sent_1097 = len(self.df[self.df['1097_Yuborilgan'] == True])
        javob_berilgan = len(self.df[self.df['Holat'].astype(str).str.lower().str.contains('javob')])
        avg_time = round(self.df['Ijro_Vaqti_Soat'].mean(), 1) if 'Ijro_Vaqti_Soat' in self.df.columns else 0.0

        return {
            "total": total,
            "agentlik": agentlik,
            "palata": palata,
            "korrupsiya": korrupsiya,
            "sent_1097": sent_1097,
            "javob_berilgan": javob_berilgan,
            "avg_time": avg_time
        }

    def get_region_stats(self):
        if self.df.empty:
            return pd.Series(dtype=int)
        return self.df['Viloyat'].value_counts()

    def get_top_risk_tumans(self, top_n=5):
        """Eng ko'p murojaat va korrupsiya xavfi yuqori bo'lgan tumanlar"""
        if self.df.empty:
            return pd.DataFrame()
        tuman_counts = self.df['Tuman'].value_counts().head(top_n).reset_index()
        tuman_counts.columns = ['Tuman', 'Jami']
        return tuman_counts

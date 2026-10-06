import pandas as pd
import os

class DataLoader:
    def __init__(self, excel_path):
        self.excel_path = excel_path
        self.df = None
        self.load_data()

    def load_data(self):
        if not os.path.exists(self.excel_path):
            raise FileNotFoundError(f"Fayl topilmadi: {self.excel_path}")
            
        self.df = pd.read_excel(self.excel_path)
        self.df.columns = [col.strip() for col in self.df.columns]
        
        # Kategoriyalarni aniqlash
        self._classify_murojaatlar()

    def _classify_murojaatlar(self):
        # 1. Tashkilot turi (Agentlik, Palata, Boshqa)
        def get_org_type(yonalish):
            y = str(yonalish).lower()
            if 'palata' in y:
                return 'Davlat kadastrlari palatasi'
            elif 'agentlik' in y or 'kadastr agentligi' in y:
                return 'Kadastr agentligi'
            return 'Boshqa tashkilot'

        # 2. 1097 ga yo'naltirilganligi
        def is_1097(javob):
            return '1097' in str(javob)

        # 3. Korrupsiyaga oidligi
        corruption_keywords = [
            'pora', 'tamagir', 'ta’magir', 'korup', 'korrup', 'karup', 
            'til biriktir', 'noqonuniy yer sot', 'mansab', 
            'pul talab', 'poraxoʻr', 'poraxor', 'aldov', 'shaxsimizni sir saqlasa'
        ]
        test_keywords = [
            'test', 'тест', 'lorem', 'фыва', 'alo', 'yangilash', '123'
        ]

        def get_category(row):
            matn = str(row.get('Murojaat matni', '')).lower()
            name = str(row.get('F.I.Sh.', '')).lower()

            if any(t in matn for t in test_keywords) or any(t in name for t in ['test', 'nnn', 'ааа']):
                return 'Test/Texnik'
            elif any(c in matn for c in corruption_keywords):
                return 'Korrupsiyaga oid'
            else:
                return 'Sohaviy/Boshqa'

        self.df['Tashkilot_Turi'] = self.df['Yoʻnalish'].apply(get_org_type)
        self.df['1097_Yuborilgan'] = self.df['Javob'].apply(is_1097)
        self.df['Kategoriya'] = self.df.apply(get_category, axis=1)

    def get_summary_stats(self):
        total = len(self.df)
        agentlik = len(self.df[self.df['Tashkilot_Turi'] == 'Kadastr agentligi'])
        palata = len(self.df[self.df['Tashkilot_Turi'] == 'Davlat kadastrlari palatasi'])
        korrupsiya = len(self.df[self.df['Kategoriya'] == 'Korrupsiyaga oid'])
        sent_1097 = len(self.df[self.df['1097_Yuborilgan'] == True])
        javob_berilgan = len(self.df[self.df['Holat'].astype(str).str.lower().str.contains('javob')])

        return {
            "total": total,
            "agentlik": agentlik,
            "palata": palata,
            "korrupsiya": korrupsiya,
            "sent_1097": sent_1097,
            "javob_berilgan": javob_berilgan
        }

    def get_region_stats(self):
        return self.df['Viloyat'].value_counts()

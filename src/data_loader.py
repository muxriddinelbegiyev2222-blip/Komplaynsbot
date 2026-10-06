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
            if 'palata' in s.lower():
                return 'Davlat kadastrlari palatasi hududiy boshqarmasi'
            return 'Kadastr agentligi hududiy boshqarmasi'

        df['Aniq_Yonalish'] = df['Yoʻnalish'].apply(get_exact_yonalish)

    def get_available_periods(self):
        """Barcha yillarni (2025, 2026, 2027 va kelgusi) dinamik shakllantirish"""
        periods = ["Barchasi", "Joriy hafta", "Joriy oy", "I-chorak", "II-chorak", "III-chorak", "IV-chorak"]
        if not self.df.empty and 'DT' in self.df.columns and self.df['DT'].notnull().any():
            years = sorted(self.df['DT'].dropna().dt.year.unique(), reverse=True)
            for y in years:
                periods.append(f"{y}-yil")
        else:
            periods.extend(["2027-yil", "2026-yil", "2025-yil"])
        return periods

    def filter_data(self, period='Barchasi', masul='Barchasi', search_query=''):
        temp = self.df.copy()
        if temp.empty:
            self.filtered_df = temp
            return temp

        # Davr filtrlari
        if 'DT' in temp.columns and temp['DT'].notnull().any():
            max_date = temp['DT'].max()
            if period == 'Joriy hafta':
                start_week = max_date - timedelta(days=7)
                temp = temp[temp['DT'] >= start_week]
            elif period == 'Joriy oy':
                temp = temp[(temp['DT'].dt.year == max_date.year) & (temp['DT'].dt.month == max_date.month)]
            elif period == 'I-chorak':
                temp = temp[temp['DT'].dt.quarter == 1]
            elif period == 'II-chorak':
                temp = temp[temp['DT'].dt.quarter == 2]
            elif period == 'III-chorak':
                temp = temp[temp['DT'].dt.quarter == 3]
            elif period == 'IV-chorak':
                temp = temp[temp['DT'].dt.quarter == 4]
            elif '-yil' in str(period):
                try:
                    y = int(str(period).replace('-yil', '').strip())
                    temp = temp[temp['DT'].dt.year == y]
                except Exception:
                    pass

        # Mas'ul komplayens filtri
        if masul != 'Barchasi':
            temp = temp[temp['Masul_Komplayens'] == masul]

        # Global poisk
        if search_query:
            q = str(search_query).strip().lower()
            temp = temp[
                temp['F.I.Sh.'].astype(str).str.lower().str.contains(q) |
                temp['Telefon'].astype(str).str.lower().str.contains(q) |
                temp['Viloyat'].astype(str).str.lower().str.contains(q) |
                temp['Tuman'].astype(str).str.lower().str.contains(q) |
                temp['Murojaat matni'].astype(str).str.lower().str.contains(q) |
                temp['Organish_Natijasi'].astype(str).str.lower().str.contains(q)
            ]

        self.filtered_df = temp
        return temp

    def get_kpi_stats(self):
        d = self.filtered_df
        total = len(d)
        if total == 0:
            return {
                "total": 0, "agentlik_organish": 0, "palata_organish": 0,
                "natija_kiritilgan": 0, "asossiz": 0,
                "muddati_otgan_15": 0, "ogohlantirish_10": 0,
                "takroriy_soni": 0, "chora_krilgan_soni": 0,
                "chorak_taqsimot": {"I": 0, "II": 0, "III": 0, "IV": 0}
            }

        is_organish = d['Ijro_Holati'].astype(str).str.contains("O‘rganishga yuborilgan|O'rganishda", case=False, na=False)
        agentlik_org = len(d[is_organish & d['Masul_Komplayens'].astype(str).str.contains("agentligi", case=False, na=False)])
        palata_org = len(d[is_organish & d['Masul_Komplayens'].astype(str).str.contains("palata", case=False, na=False)])

        natija_count = len(d[d['Ijro_Holati'].astype(str).str.contains("Bartaraf etildi|Ijobiy hal etildi|Intizomiy chora|O‘rganib chiqildi", case=False, na=False)])
        asossiz_count = len(d[d['Ijro_Holati'].astype(str).str.contains("Asossiz", case=False, na=False)])

        # 1-BLOK ANALITIKASI: SLA (Muddatlar)
        now_date = datetime.now()
        org_df = d[is_organish].copy()
        muddati_otgan_15 = 0
        ogohlantirish_10 = 0
        if not org_df.empty and 'DT' in org_df.columns:
            days_diff = (now_date - org_df['DT']).dt.days
            muddati_otgan_15 = len(days_diff[days_diff > 15])
            ogohlantirish_10 = len(days_diff[(days_diff >= 10) & (days_diff <= 15)])

        # 2-BLOK ANALITIKASI: Takroriy murojaatlar (1 dan ortiq yozgan fuqarolar)
        clean_phones = d['Telefon'].astype(str).str.strip()
        dup_counts = clean_phones.value_counts()
        takroriy_soni = len(d[d['Telefon'].isin(dup_counts[dup_counts > 1].index)])

        # 3-BLOK ANALITIKASI: Ko'rilgan choralar hisobi
        chora_mask = d['Chora_Turi'].astype(str).str.contains("Xayfsan|Lavozimidan ozod|Prokuratura|Jarima", case=False, na=False)
        chora_krilgan_soni = len(d[chora_mask])

        # 4-BLOK ANALITIKASI: Kvartal (Choraklar)
        choraklar = {"I": 0, "II": 0, "III": 0, "IV": 0}
        if 'DT' in d.columns and d['DT'].notnull().any():
            q_counts = d['DT'].dt.quarter.value_counts()
            choraklar["I"] = int(q_counts.get(1, 0))
            choraklar["II"] = int(q_counts.get(2, 0))
            choraklar["III"] = int(q_counts.get(3, 0))
            choraklar["IV"] = int(q_counts.get(4, 0))

        return {
            "total": total,
            "agentlik_organish": agentlik_org,
            "palata_organish": palata_org,
            "natija_kiritilgan": natija_count,
            "asossiz": asossiz_count,
            "muddati_otgan_15": muddati_otgan_15,
            "ogohlantirish_10": ogohlantirish_10,
            "takroriy_soni": takroriy_soni,
            "chora_krilgan_soni": chora_krilgan_soni,
            "chorak_taqsimot": choraklar
        }

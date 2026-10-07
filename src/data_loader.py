import pandas as pd
import os
import re
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

    def _clean_phone(self, phone):
        """Telefon raqamlarini tozalash va standart formatga keltirish"""
        ph = str(phone).strip()
        ph = re.sub(r'[^\d+]', '', ph)
        if len(ph) == 9: ph = "+998" + ph
        elif len(ph) == 12 and ph.startswith("998"): ph = "+" + ph
        elif not ph.startswith("+"): ph = "+" + ph
        return ph

    def _mark_risk(self, text):
        """Matnda korrupsiyaviy xavf so'zlari borligini aniqlash"""
        t = str(text).lower()
        danger_words = ["pora", "pul so'radi", "tamagirlik", "dollar", "berdim", "pul talab", "tanish-bilish", "soqqa"]
        return any(w in t for w in danger_words)

    def refresh_data(self):
        self.df = self.db.get_all_records()
        if not self.df.empty:
            self.df['DT'] = pd.to_datetime(self.df['Yaratilgan sana'], errors='coerce')
            self.df['Toza_Telefon'] = self.df['Telefon'].apply(self._clean_phone)
            self.df['Yuqori_Xavf'] = self.df['Murojaat matni'].apply(self._mark_risk)
        self.filtered_df = self.df.copy()

    def _classify(self, df):
        def get_exact_yonalish(val):
            s = str(val).strip()
            if 'palata' in s.lower(): return 'Davlat kadastrlari palatasi hududiy boshqarmasi'
            return 'Kadastr agentligi hududiy boshqarmasi'
        df['Aniq_Yonalish'] = df['Yoʻnalish'].apply(get_exact_yonalish)

    def get_available_periods(self):
        periods = ["Barchasi", "Joriy hafta", "Joriy oy", "I-chorak", "II-chorak", "III-chorak", "IV-chorak"]
        if not self.df.empty and 'DT' in self.df.columns and self.df['DT'].notnull().any():
            years = sorted(self.df['DT'].dropna().dt.year.unique(), reverse=True)
            for y in years:
                periods.append(f"{y}-yil")
        else:
            periods.extend(["2027-yil", "2026-yil", "2025-yil"])
        return periods

    def filter_data(self, period='Barchasi', masul='Barchasi', manba='Barchasi', search_query=''):
        temp = self.df.copy()
        if temp.empty:
            self.filtered_df = temp; return temp

        if 'DT' in temp.columns and temp['DT'].notnull().any():
            max_date = temp['DT'].max()
            if period == 'Joriy hafta':
                start_week = max_date - timedelta(days=7)
                temp = temp[temp['DT'] >= start_week]
            elif period == 'Joriy oy':
                temp = temp[(temp['DT'].dt.year == max_date.year) & (temp['DT'].dt.month == max_date.month)]
            elif period == 'I-chorak': temp = temp[temp['DT'].dt.quarter == 1]
            elif period == 'II-chorak': temp = temp[temp['DT'].dt.quarter == 2]
            elif period == 'III-chorak': temp = temp[temp['DT'].dt.quarter == 3]
            elif period == 'IV-chorak': temp = temp[temp['DT'].dt.quarter == 4]
            elif '-yil' in str(period):
                try: temp = temp[temp['DT'].dt.year == int(str(period).replace('-yil', '').strip())]
                except: pass

        if masul != 'Barchasi': temp = temp[temp['Masul_Komplayens'] == masul]

        if manba == 'Telegram bot': temp = temp[temp['Manba'].astype(str).str.contains('Telegram', case=False, na=False)]
        elif 'Telefon' in manba: temp = temp[temp['Manba'].astype(str).str.contains('Telefon|273-19-66', case=False, na=False)]

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
            return {"total":0, "tg_total":0, "phone_total":0, "agentlik_organish":0, "palata_organish":0, 
                    "natija_kiritilgan":0, "asossiz":0, "muddati_otgan_15":0, "ogohlantirish_10":0, 
                    "takroriy_soni":0, "chora_krilgan_soni":0, "chorak_taqsimot":{"I":0, "II":0, "III":0, "IV":0}}

        tg_total = len(d[d['Manba'].astype(str).str.contains('Telegram', case=False, na=False)])
        phone_total = len(d[d['Manba'].astype(str).str.contains('Telefon|273-19-66', case=False, na=False)])

        is_org = d['Ijro_Holati'].astype(str).str.contains("O‘rganishga yuborilgan|O'rganishda", case=False, na=False)
        agentlik_org = len(d[is_org & d['Masul_Komplayens'].astype(str).str.contains("agentligi", case=False, na=False)])
        palata_org = len(d[is_org & d['Masul_Komplayens'].astype(str).str.contains("palata", case=False, na=False)])

        # MANTIQIY YECHIM: "Asossiz" ham o'rganib chiqilganlar qatoriga qo'shildi
        is_hal = d['Ijro_Holati'].astype(str).str.contains("Bartaraf etildi|Ijobiy hal etildi|Intizomiy chora|O‘rganib chiqildi|Asossiz", case=False, na=False)
        natija_count = len(d[is_hal])
        
        asossiz_count = len(d[d['Ijro_Holati'].astype(str).str.contains("Asossiz", case=False, na=False)])

        muddati_otgan_15 = 0; ogohlantirish_10 = 0
        if not d[is_org].empty and 'DT' in d[is_org].columns:
            days_diff = (datetime.now() - d[is_org]['DT']).dt.days
            muddati_otgan_15 = len(days_diff[days_diff > 15])
            ogohlantirish_10 = len(days_diff[(days_diff >= 10) & (days_diff <= 15)])

        dup_counts = d['Toza_Telefon'].value_counts()
        takroriy_soni = len(d[d['Toza_Telefon'].isin(dup_counts[dup_counts > 1].index)])

        chora_krilgan_soni = len(d[d['Chora_Turi'].astype(str).str.contains("Xayfsan|Lavozimidan ozod|Prokuratura|Jarima", case=False, na=False)])

        choraklar = {"I":0, "II":0, "III":0, "IV":0}
        if 'DT' in d.columns and d['DT'].notnull().any():
            q_counts = d['DT'].dt.quarter.value_counts()
            choraklar.update({k: int(q_counts.get(k, 0)) for k in [1, 2, 3, 4]})
            choraklar = {"I": choraklar[1], "II": choraklar[2], "III": choraklar[3], "IV": choraklar[4]}

        return {
            "total": total, "tg_total": tg_total, "phone_total": phone_total,
            "agentlik_organish": agentlik_org, "palata_organish": palata_org,
            "natija_kiritilgan": natija_count, "asossiz": asossiz_count,
            "muddati_otgan_15": muddati_otgan_15, "ogohlantirish_10": ogohlantirish_10,
            "takroriy_soni": takroriy_soni, "chora_krilgan_soni": chora_krilgan_soni,
            "chorak_taqsimot": choraklar
        }

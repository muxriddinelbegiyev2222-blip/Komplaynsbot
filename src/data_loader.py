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
        ph = str(phone).strip()
        ph = re.sub(r'[^\d+]', '', ph)
        if len(ph) == 9:
            ph = "+998" + ph
        elif len(ph) == 12 and ph.startswith("998"):
            ph = "+" + ph
        elif not ph.startswith("+"):
            ph = "+" + ph
        return ph

    def _mark_risk(self, text):
        t = str(text).lower()
        return any(w in t for w in ["pora", "pul so'radi", "tamagirlik", "dollar", "berdim", "pul talab", "tanish-bilish", "soqqa", "noqonuniy"])

    def refresh_data(self):
        self.df = self.db.get_all_records()
        if not self.df.empty:
            self.df['DT'] = pd.to_datetime(self.df['Yaratilgan sana'], errors='coerce')
            self.df['Toza_Telefon'] = self.df['Telefon'].apply(self._clean_phone)
            self.df['Yuqori_Xavf'] = self.df['Murojaat matni'].apply(self._mark_risk)
        self.filtered_df = self.df.copy()

    def _classify(self, df):
        df['Aniq_Yonalish'] = df['Yoʻnalish'].apply(
            lambda s: 'Davlat kadastrlari palatasi hududiy boshqarmasi' if 'palata' in str(s).lower() else 'Kadastr agentligi hududiy boshqarmasi'
        )

    def get_available_periods(self):
        periods = ["Barchasi", "Joriy hafta", "Joriy oy", "I-chorak", "II-chorak", "III-chorak", "IV-chorak"]
        if not self.df.empty and 'DT' in self.df.columns and self.df['DT'].notnull().any():
            for y in sorted(self.df['DT'].dropna().dt.year.unique(), reverse=True):
                periods.append(f"{y}-yil")
        else:
            periods.extend([f"{datetime.now().year}-yil", f"{datetime.now().year-1}-yil"])
        return periods

    def filter_data(self, period='Barchasi', masul='Barchasi', manba='Barchasi', search_query=''):
        temp = self.df.copy()
        if temp.empty:
            self.filtered_df = temp
            return temp

        if 'DT' in temp.columns and temp['DT'].notnull().any():
            max_date = temp['DT'].max()
            if period == 'Joriy hafta':
                temp = temp[temp['DT'] >= max_date - timedelta(days=7)]
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
                    target_year = int(str(period).replace('-yil', '').strip())
                    temp = temp[temp['DT'].dt.year == target_year]
                except:
                    pass

        if masul != 'Barchasi':
            temp = temp[temp['Masul_Komplayens'] == masul]
        
        if manba == 'Telegram bot':
            temp = temp[temp['Manba'].astype(str).str.contains('Telegram', case=False, na=False)]
        elif 'Telefon' in manba:
            temp = temp[temp['Manba'].astype(str).str.contains('Telefon|273-19-66', case=False, na=False)]

        if search_query:
            q = str(search_query).strip().lower()
            mask = (
                temp['F.I.Sh.'].astype(str).str.lower().str.contains(q) | 
                temp['Telefon'].astype(str).str.lower().str.contains(q) | 
                temp['Viloyat'].astype(str).str.lower().str.contains(q) | 
                temp['Tuman'].astype(str).str.lower().str.contains(q) | 
                temp['Murojaat matni'].astype(str).str.lower().str.contains(q) | 
                temp['Organish_Natijasi'].astype(str).str.lower().str.contains(q)
            )
            temp = temp[mask]

        self.filtered_df = temp
        return temp

    def get_kpi_stats(self):
        d = self.filtered_df
        total = len(d)
        
        # Birlamchi sozlamalarni olish (SLA Kunlar)
        sets = self.db.get_settings()
        try:
            sla_limit = int(sets.get("sla_days", "2"))
        except:
            sla_limit = 2
            
        if total == 0:
            return {
                "total": 0, "tg_total": 0, "phone_total": 0, 
                "agentlik_organish": 0, "palata_organish": 0, 
                "natija_kiritilgan": 0, "asossiz": 0, 
                "muddati_otgan": 0, "ogohlantirish": 0, 
                "takroriy_soni": 0, "chora_krilgan_soni": 0, 
                "chorak_taqsimot": {"I": 0, "II": 0, "III": 0, "IV": 0}, 
                "sla_days": sla_limit
            }

        tg_total = len(d[d['Manba'].astype(str).str.contains('Telegram', case=False, na=False)])
        phone_total = len(d[d['Manba'].astype(str).str.contains('Telefon|273-19-66', case=False, na=False)])

        is_org = d['Ijro_Holati'].astype(str).str.contains("O‘rganishga yuborilgan|O'rganishda", case=False, na=False)
        agentlik_org = len(d[is_org & d['Masul_Komplayens'].astype(str).str.contains("agentligi", case=False, na=False)])
        palata_org = len(d[is_org & d['Masul_Komplayens'].astype(str).str.contains("palata", case=False, na=False)])

        is_hal = d['Ijro_Holati'].astype(str).str.contains("Bartaraf etildi|Ijobiy hal etildi|Intizomiy chora|O‘rganib chiqildi|Asossiz", case=False, na=False) | d['Chora_Turi'].astype(str).str.contains("Asossiz", case=False, na=False)
        natija_count = len(d[is_hal])
        asossiz_count = len(d[d['Ijro_Holati'].astype(str).str.contains("Asossiz", case=False, na=False) | d['Chora_Turi'].astype(str).str.contains("Asossiz", case=False, na=False)])

        muddati_otgan = 0
        ogohlantirish = 0
        if not d[is_org].empty and 'DT' in d[is_org].columns:
            days_diff = (datetime.now() - d[is_org]['DT']).dt.days
            muddati_otgan = len(days_diff[days_diff > sla_limit])
            ogohlantirish = len(days_diff[(days_diff >= max(1, sla_limit - 1)) & (days_diff <= sla_limit)])

        dup_counts = d['Toza_Telefon'].value_counts()
        takroriy_soni = len(d[d['Toza_Telefon'].isin(dup_counts[dup_counts > 1].index)])
        chora_krilgan_soni = len(d[d['Chora_Turi'].astype(str).str.contains("Xayfsan|Lavozimidan ozod|Prokuratura|Jarima", case=False, na=False)])

        choraklar = {"I": 0, "II": 0, "III": 0, "IV": 0}
        if 'DT' in d.columns and d['DT'].notnull().any():
            q_counts = d['DT'].dt.quarter.value_counts()
            choraklar = {
                "I": int(q_counts.get(1, 0)), 
                "II": int(q_counts.get(2, 0)), 
                "III": int(q_counts.get(3, 0)), 
                "IV": int(q_counts.get(4, 0))
            }

        return {
            "total": total, "tg_total": tg_total, "phone_total": phone_total,
            "agentlik_organish": agentlik_org, "palata_organish": palata_org,
            "natija_kiritilgan": natija_count, "asossiz": asossiz_count,
            "muddati_otgan": muddati_otgan, "ogohlantirish": ogohlantirish,
            "takroriy_soni": takroriy_soni, "chora_krilgan_soni": chora_krilgan_soni,
            "chorak_taqsimot": choraklar, "sla_days": sla_limit
        }

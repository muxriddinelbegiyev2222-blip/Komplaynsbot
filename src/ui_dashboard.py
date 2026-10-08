import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import customtkinter as ctk
import pandas as pd
from datetime import datetime

from src.db_manager import DatabaseManager

try:
    from src.ui_details import DetailsWindow
except ImportError:
    DetailsWindow = None

try:
    from src.report_generator import ReportGenerator
except ImportError:
    ReportGenerator = None


class DashboardApp(ctk.CTk):
    def __init__(self, data_loader=None, username="admin", role="admin", db=None):
        super().__init__()

        self.data_loader = data_loader
        self.username = str(username)
        self.role = str(role).lower()
        self.db = db if db else DatabaseManager()

        self.title("KADASTR AGENTLIGI — KORRUPSIYAGA QARSHI KOMPLAYENS MONITORING TIZIMI")
        self.geometry("1420x860")
        self.minsize(1200, 750)

        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        self.df_data = pd.DataFrame()
        self.filtered_df = pd.DataFrame()

        self.regions_list = [
            "Buxoro viloyati", "Farg'ona viloyati", "Jizzax viloyati", "Namangan viloyati",
            "Navoiy viloyati", "Qashqadaryo viloyati", "Qoraqalpog'iston Respublikasi",
            "Samarqand viloyati", "Sirdaryo viloyati", "Surxondaryo viloyati",
            "Toshkent shahri", "Toshkent viloyati", "Xorazm viloyati"
        ]

        self._build_ui()
        self.load_data()

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        # -------------------------------------------------------------
        # 1. KO'K SHAPKA
        # -------------------------------------------------------------
        header_frame = ctk.CTkFrame(self, height=36, corner_radius=0, fg_color="#0b1e36")
        header_frame.grid(row=0, column=0, sticky="ew")
        header_frame.grid_columnconfigure(0, weight=1)

        lbl_top = ctk.CTkLabel(
            header_frame,
            text="  KADASTR AGENTLIGI — KORRUPSIYAGA QARSHI KOMPLAYENS MONITORING TIZIMI",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#cbd5e1"
        )
        lbl_top.grid(row=0, column=0, sticky="w", padx=10, pady=4)

        # -------------------------------------------------------------
        # 2. NAVIGATSIYA VA TUGMALAR (PODSHAPKA)
        # -------------------------------------------------------------
        nav_frame = ctk.CTkFrame(self, height=52, corner_radius=0, fg_color="#0f2744")
        nav_frame.grid(row=1, column=0, sticky="ew")
        nav_frame.grid_columnconfigure(2, weight=1)

        btn_back = ctk.CTkButton(
            nav_frame, text="⬅ Orqaga", width=80, height=30,
            fg_color="#1e293b", hover_color="#334155",
            command=self.destroy
        )
        btn_back.grid(row=0, column=0, padx=(15, 10), pady=10)

        # Foydalanuvchi ismini va rolini ko'rsatish
        lbl_nav_title = ctk.CTkLabel(
            nav_frame,
            text=f"Asosiy oyna  /  Tahliliy Dashboard  —  👤 {self.username.upper()} ({'ADMIN' if self.role == 'admin' else 'KUZATUVCHI'})",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color="white"
        )
        lbl_nav_title.grid(row=0, column=1, padx=5, pady=10)

        actions_frame = ctk.CTkFrame(nav_frame, fg_color="transparent")
        actions_frame.grid(row=0, column=3, padx=15, pady=8, sticky="e")

        # =======================================================
        # RAHBAR UCHUN CHEKLOVLAR SHU YERDA QO'YILGAN
        # =======================================================
        if self.role == "admin":
            btn_import = ctk.CTkButton(
                actions_frame, text="📁 Yangi Excel yuklash", height=32,
                fg_color="#1d4ed8", hover_color="#1e40af", command=self.import_excel
            )
            btn_import.pack(side="left", padx=4)

            btn_phone = ctk.CTkButton(
                actions_frame, text="📞 + Telefon orqali qabul", height=32,
                fg_color="#15803d", hover_color="#166534", command=self.open_add_phone_murojaat
            )
            btn_phone.pack(side="left", padx=4)

            btn_audit = ctk.CTkButton(
                actions_frame, text="👁 Audit Log", height=32,
                fg_color="#d97706", hover_color="#b45309", command=self.open_audit_window
            )
            btn_audit.pack(side="left", padx=4)

        btn_xod = ctk.CTkButton(
            actions_frame, text="👥 Hududiy xodimlar", height=32,
            fg_color="#7e22ce", hover_color="#6b21a8", command=self.open_xodimlar_window
        )
        btn_xod.pack(side="left", padx=4)

        btn_excel_view = ctk.CTkButton(
            actions_frame, text="📊 Excel Jadval", height=32,
            fg_color="#0f766e", hover_color="#115e59", command=self.open_all_records_window
        )
        btn_excel_view.pack(side="left", padx=4)

        btn_word = ctk.CTkButton(
            actions_frame, text="📄 Word Ma'lumotnoma", height=32,
            fg_color="#b45309", hover_color="#92400e", command=self.generate_word_report
        )
        btn_word.pack(side="left", padx=4)

        # -------------------------------------------------------------
        # 3. FILTRLAR PANELI
        # -------------------------------------------------------------
        filter_bar = ctk.CTkFrame(self, height=48, fg_color="transparent")
        filter_bar.grid(row=2, column=0, sticky="ew", padx=15, pady=(8, 4))

        ctk.CTkLabel(filter_bar, text="🔍 Qidiruv:", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=(5, 4))
        self.e_search = ctk.CTkEntry(filter_bar, width=200, height=30, placeholder_text="F.I.Sh, tel, tuman...")
        self.e_search.pack(side="left", padx=4)
        self.e_search.bind("<Return>", lambda e: self.apply_filters())

        btn_search = ctk.CTkButton(filter_bar, text="Topish", width=70, height=30, fg_color="#0f172a", hover_color="#1e293b", command=self.apply_filters)
        btn_search.pack(side="left", padx=(2, 10))

        ctk.CTkLabel(filter_bar, text="📅 Davr:", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=(5, 4))
        self.cb_davr = ctk.CTkComboBox(filter_bar, values=["Barchasi", "Bugun", "Shu hafta", "Shu oy", "I-Chorak", "II-Chorak", "III-Chorak", "IV-Chorak"], width=130, height=30, command=lambda v: self.apply_filters())
        self.cb_davr.set("Barchasi")
        self.cb_davr.pack(side="left", padx=4)

        ctk.CTkLabel(filter_bar, text="📡 Manba:", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=(10, 4))
        self.cb_manba = ctk.CTkComboBox(filter_bar, values=["Barchasi", "Telegram bot", "Ishonch telefoni"], width=140, height=30, command=lambda v: self.apply_filters())
        self.cb_manba.set("Barchasi")
        self.cb_manba.pack(side="left", padx=4)

        ctk.CTkLabel(filter_bar, text="👤 Mas'ul:", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=(10, 4))
        self.cb_masul = ctk.CTkComboBox(filter_bar, values=["Barchasi", "Kadastr agentligi", "Davlat kadastrlari palatasi"], width=170, height=30, command=lambda v: self.apply_filters())
        self.cb_masul.set("Barchasi")
        self.cb_masul.pack(side="left", padx=4)

        btn_reset = ctk.CTkButton(filter_bar, text="Tozalash", width=80, height=30, fg_color="#475569", hover_color="#334155", command=self.reset_filters)
        btn_reset.pack(side="left", padx=10)

        # -------------------------------------------------------------
        # 4. KPI KARTALAR VA ASOSIY JADVAL
        # -------------------------------------------------------------
        self.body_scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.body_scroll.grid(row=3, column=0, sticky="nsew", padx=15, pady=(0, 10))
        self.body_scroll.grid_columnconfigure(0, weight=1)

        kpi_container = ctk.CTkFrame(self.body_scroll, fg_color="transparent")
        kpi_container.pack(fill="x", pady=(4, 10))
        for i in range(5):
            kpi_container.grid_columnconfigure(i, weight=1)

        self.kpi_cards = {}
        cards_specs = [
            ("jami", "JAMI MUROJAATLAR", "#0a2540", "#00d4ff"),
            ("agentlik", "AGENTLIKDA O‘RGANISHDA", "#1e3a8a", "#60a5fa"),
            ("palata", "PALATADA O‘RGANISHDA", "#312e81", "#a5b4fc"),
            ("organilgan", "O‘RGANIB CHIQILGAN", "#14532d", "#4ade80"),
            ("asossiz", "ASOSSIZ DEB TOPILGAN", "#374151", "#9ca3af")
        ]

        for idx, (cid, title, bg_color, accent) in enumerate(cards_specs):
            card = ctk.CTkFrame(kpi_container, fg_color=bg_color, corner_radius=8, height=95)
            card.grid(row=0, column=idx, padx=4, sticky="ew")
            card.pack_propagate(False)

            ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=10, weight="bold"), text_color="#cbd5e1").pack(pady=(6, 0))
            lbl_val = ctk.CTkLabel(card, text="0", font=ctk.CTkFont(size=22, weight="bold"), text_color="white")
            lbl_val.pack(pady=(0, 2))

            btn_open = ctk.CTkButton(
                card, text="Ochish ➔", width=70, height=20,
                font=ctk.CTkFont(size=10), fg_color="#0f172a", hover_color="#1e293b",
                command=lambda c=cid: self.open_filtered_by_card(c)
            )
            btn_open.pack(pady=(0, 6))
            self.kpi_cards[cid] = lbl_val

        # ASOSIY JADVAL
        table_label_frame = ctk.CTkFrame(self.body_scroll, fg_color="transparent")
        table_label_frame.pack(fill="x", pady=(5, 4))
        ctk.CTkLabel(
            table_label_frame,
            text="Viloyatlar kesimida murojaatlar nazorati:",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#f8fafc"
        ).pack(side="left")

        self.table_box = ctk.CTkFrame(self.body_scroll, corner_radius=6, fg_color="#0b1329")
        self.table_box.pack(fill="x", pady=(0, 15))

        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Region.Treeview",
            background="#0f172a",
            foreground="#f8fafc",
            rowheight=26,
            fieldbackground="#0f172a",
            font=("Segoe UI", 10)
        )
        style.configure(
            "Region.Treeview.Heading",
            background="#020617",
            foreground="#38bdf8",
            font=("Segoe UI", 10, "bold")
        )
        style.map("Region.Treeview", background=[("selected", "#0369a1")])

        cols = ("hudud", "jami", "tg", "tel", "agentlik", "palata", "organilgan", "asossiz")
        self.tree_reg = ttk.Treeview(self.table_box, columns=cols, show="headings", height=13, style="Region.Treeview")

        headers = [
            ("hudud", "Hudud nomi (Viloyat)", 200, "w"),
            ("jami", "Jami", 90, "center"),
            ("tg", "Telegram bot", 110, "center"),
            ("tel", "Ishonch telefoni", 120, "center"),
            ("agentlik", "Agentlikda", 100, "center"),
            ("palata", "Palatada", 100, "center"),
            ("organilgan", "O'rganilgan", 110, "center"),
            ("asossiz", "Asossiz deb topilgan", 140, "center")
        ]

        for col_id, col_text, col_w, col_anc in headers:
            self.tree_reg.heading(col_id, text=col_text)
            self.tree_reg.column(col_id, width=col_w, anchor=col_anc)

        self.tree_reg.pack(fill="both", expand=True, padx=2, pady=2)
        self.tree_reg.bind("<Double-1>", self.on_double_click_region)

        # PASTKI KARTALAR
        bottom_cards_frame = ctk.CTkFrame(self.body_scroll, fg_color="transparent")
        bottom_cards_frame.pack(fill="x", pady=(0, 10))
        for i in range(4):
            bottom_cards_frame.grid_columnconfigure(i, weight=1)

        c1 = ctk.CTkFrame(bottom_cards_frame, fg_color="#fff1f2", corner_radius=8, height=85)
        c1.grid(row=0, column=0, padx=4, sticky="ew")
        c1.pack_propagate(False)
        ctk.CTkLabel(c1, text="⏰ IJRO MUDDATI NAZORATI", font=ctk.CTkFont(size=11, weight="bold"), text_color="#881337").pack(pady=(4, 2))
        self.lbl_sla_15 = ctk.CTkLabel(c1, text="🔴 Muddati o'tgan (>15 kun): 0 ta ➔", font=ctk.CTkFont(size=11, weight="bold"), text_color="#be123c")
        self.lbl_sla_15.pack()
        self.lbl_sla_10 = ctk.CTkLabel(c1, text="🟡 Ogohlantirish (10-15 kun): 0 ta ➔", font=ctk.CTkFont(size=11, weight="bold"), text_color="#b45309")
        self.lbl_sla_10.pack()

        c2 = ctk.CTkFrame(bottom_cards_frame, fg_color="#eff6ff", corner_radius=8, height=85)
        c2.grid(row=0, column=1, padx=4, sticky="ew")
        c2.pack_propagate(False)
        ctk.CTkLabel(c2, text="📄 TAKRORIY MUROJAATLAR", font=ctk.CTkFont(size=11, weight="bold"), text_color="#1e3a8a").pack(pady=(6, 6))
        self.lbl_takroriy = ctk.CTkLabel(c2, text="Takroriy kelganlar: 0 ta ➔", font=ctk.CTkFont(size=12, weight="bold"), text_color="#2563eb")
        self.lbl_takroriy.pack()

        c3 = ctk.CTkFrame(bottom_cards_frame, fg_color="#f0fdf4", corner_radius=8, height=85)
        c3.grid(row=0, column=2, padx=4, sticky="ew")
        c3.pack_propagate(False)
        ctk.CTkLabel(c3, text="⚖ INTIZOMIY CHORALAR", font=ctk.CTkFont(size=11, weight="bold"), text_color="#14532d").pack(pady=(6, 6))
        self.lbl_chora = ctk.CTkLabel(c3, text="Ko'rilgan choralar: 0 ta ➔", font=ctk.CTkFont(size=12, weight="bold"), text_color="#16a34a")
        self.lbl_chora.pack()

        c4 = ctk.CTkFrame(bottom_cards_frame, fg_color="#f8fafc", corner_radius=8, height=85)
        c4.grid(row=0, column=3, padx=4, sticky="ew")
        c4.pack_propagate(False)
        ctk.CTkLabel(c4, text="📊 CHORAKLAR (KVARTAL)", font=ctk.CTkFont(size=11, weight="bold"), text_color="#0f172a").pack(pady=(6, 6))
        self.lbl_chorak = ctk.CTkLabel(c4, text="I-ch: 0 | II-ch: 0 | III-ch: 0 | IV-ch: 0", font=ctk.CTkFont(size=11, weight="bold"), text_color="#334155")
        self.lbl_chorak.pack()

    def load_data(self):
        try:
            self.df_data = self.db.get_all_records()
            self.apply_filters()
        except Exception as e:
            messagebox.showerror("Xatolik", f"Ma'lumotlarni yuklashda xato: {e}")

    def apply_filters(self):
        if self.df_data.empty:
            self.filtered_df = pd.DataFrame()
            self._update_all_views()
            return

        df = self.df_data.copy()

        search_txt = self.e_search.get().strip().lower()
        if search_txt:
            mask = (
                df['F.I.Sh.'].astype(str).str.lower().str.contains(search_txt, na=False) |
                df['Telefon'].astype(str).str.lower().str.contains(search_txt, na=False) |
                df['Viloyat'].astype(str).str.lower().str.contains(search_txt, na=False) |
                df['Tuman'].astype(str).str.lower().str.contains(search_txt, na=False) |
                df['Murojaat matni'].astype(str).str.lower().str.contains(search_txt, na=False) |
                df['#'].astype(str).str.contains(search_txt, na=False)
            )
            df = df[mask]

        manba = self.cb_manba.get()
        if manba != "Barchasi":
            df = df[df['Manba'].astype(str).str.lower().str.contains(manba.lower())]

        masul = self.cb_masul.get()
        if masul != "Barchasi":
            if "palata" in masul.lower():
                df = df[df['Yoʻnalish'].astype(str).str.lower().str.contains("palata")]
            else:
                df = df[~df['Yoʻnalish'].astype(str).str.lower().str.contains("palata")]

        self.filtered_df = df
        self._update_all_views()

    def reset_filters(self):
        self.e_search.delete(0, "end")
        self.cb_davr.set("Barchasi")
        self.cb_manba.set("Barchasi")
        self.cb_masul.set("Barchasi")
        self.apply_filters()

    def _update_all_views(self):
        df = self.filtered_df

        jami = len(df)
        if jami > 0:
            yon = df['Yoʻnalish'].astype(str).str.lower()
            palata_mask = yon.str.contains('palata')
            agentlik_mask = ~palata_mask

            ijro = df['Ijro_Holati'].astype(str).str.lower()
            organilgan_cnt = ijro.str.contains('ijobiy|bajarildi|organildi|o‘rganildi').sum()
            asossiz_cnt = ijro.str.contains('rad|asossiz').sum()

            agentlik_org = (agentlik_mask & ~ijro.str.contains('ijobiy|bajarildi|rad|asossiz')).sum()
            palata_org = (palata_mask & ~ijro.str.contains('ijobiy|bajarildi|rad|asossiz')).sum()
        else:
            agentlik_org = palata_org = organilgan_cnt = asossiz_cnt = 0

        self.kpi_cards["jami"].configure(text=str(jami))
        self.kpi_cards["agentlik"].configure(text=str(agentlik_org))
        self.kpi_cards["palata"].configure(text=str(palata_org))
        self.kpi_cards["organilgan"].configure(text=str(organilgan_cnt))
        self.kpi_cards["asossiz"].configure(text=str(asossiz_cnt))

        self.tree_reg.delete(*self.tree_reg.get_children())
        for reg in self.regions_list:
            if not df.empty:
                r_df = df[df['Viloyat'].astype(str).str.strip() == reg]
                r_jami = len(r_df)
                r_manba = r_df['Manba'].astype(str).str.lower()
                r_tg = r_manba.str.contains('bot|telegram').sum()
                r_tel = r_manba.str.contains('telefon|ishonch').sum()

                r_yon = r_df['Yoʻnalish'].astype(str).str.lower()
                r_pal = r_yon.str.contains('palata').sum()
                r_ag = r_jami - r_pal

                r_ijro = r_df['Ijro_Holati'].astype(str).str.lower()
                r_org = r_ijro.str.contains('ijobiy|bajarildi|organildi|o‘rganildi').sum()
                r_as = r_ijro.str.contains('rad|asossiz').sum()
            else:
                r_jami = r_tg = r_tel = r_ag = r_pal = r_org = r_as = 0

            self.tree_reg.insert("", "end", values=(
                reg, f"{r_jami} ta", f"{r_tg} ta", f"{r_tel} ta",
                f"{r_ag} ta", f"{r_pal} ta", f"{r_org} ta", f"{r_as} ta"
            ))

        if not df.empty:
            now = datetime.now()
            cnt_15 = 0
            cnt_10 = 0
            for _, r in df.iterrows():
                ij = str(r.get('Ijro_Holati', '')).lower()
                if 'ijobiy' in ij or 'bajarildi' in ij or 'rad' in ij:
                    continue
                s_str = str(r.get('Yaratilgan sana', ''))[:10]
                try:
                    dt = datetime.strptime(s_str, "%Y-%m-%d")
                    diff = (now - dt).days
                    if diff >= 15:
                        cnt_15 += 1
                    elif diff >= 10:
                        cnt_10 += 1
                except:
                    pass

            fish_counts = df['F.I.Sh.'].astype(str).value_counts()
            takroriy_cnt = fish_counts[fish_counts > 1].sum() if not fish_counts.empty else 0

            chora_col = df['Chora_Turi'].astype(str).str.lower()
            chora_cnt = ((chora_col != 'chora ko‘rilmagan') & (chora_col != '') & (chora_col != 'nan')).sum()

            q1 = q2 = q3 = q4 = 0
            for _, r in df.iterrows():
                s_str = str(r.get('Yaratilgan sana', ''))
                try:
                    m = datetime.strptime(s_str[:10], "%Y-%m-%d").month
                    if m in [1, 2, 3]: q1 += 1
                    elif m in [4, 5, 6]: q2 += 1
                    elif m in [7, 8, 9]: q3 += 1
                    elif m in [10, 11, 12]: q4 += 1
                except:
                    pass
        else:
            cnt_15 = cnt_10 = takroriy_cnt = chora_cnt = q1 = q2 = q3 = q4 = 0

        self.lbl_sla_15.configure(text=f"🔴 Muddati o'tgan (>15 kun): {cnt_15} ta ➔")
        self.lbl_sla_10.configure(text=f"🟡 Ogohlantirish (10-15 kun): {cnt_10} ta ➔")
        self.lbl_takroriy.configure(text=f"Takroriy kelganlar: {takroriy_cnt} ta ➔")
        self.lbl_chora.configure(text=f"Ko'rilgan choralar: {chora_cnt} ta ➔")
        self.lbl_chorak.configure(text=f"I-ch: {q1} | II-ch: {q2} | III-ch: {q3} | IV-ch: {q4}")

    def on_double_click_region(self, event):
        sel = self.tree_reg.selection()
        if not sel: return
        reg_name = self.tree_reg.item(sel[0], "values")[0]
        self.open_all_records_window(filter_region=reg_name)

    def open_filtered_by_card(self, card_type):
        self.open_all_records_window(filter_card=card_type)

    def open_all_records_window(self, filter_region=None, filter_card=None):
        win = ctk.CTkToplevel(self)
        title_txt = "Murojaatlar umumiy reyestri"
        if filter_region: title_txt += f" — {filter_region}"
        win.title(title_txt)
        win.geometry("1180x620")
        win.grab_set()

        lbl = ctk.CTkLabel(win, text=title_txt, font=ctk.CTkFont(size=16, weight="bold"))
        lbl.pack(pady=10)

        t_box = ctk.CTkFrame(win)
        t_box.pack(padx=15, pady=5, fill="both", expand=True)

        cols = ("#", "sana", "fish", "telefon", "viloyat", "tuman", "yonalish", "ijro", "masul", "chora")
        tree = ttk.Treeview(t_box, columns=cols, show="headings", height=18)
        tree.heading("#", text="№")
        tree.heading("sana", text="Sana")
        tree.heading("fish", text="Fuqaro F.I.Sh.")
        tree.heading("telefon", text="Telefon")
        tree.heading("viloyat", text="Viloyat")
        tree.heading("tuman", text="Tuman")
        tree.heading("yonalish", text="Yo'nalish")
        tree.heading("ijro", text="Ijro holati")
        tree.heading("masul", text="Mas'ul xodim")
        tree.heading("chora", text="Chora")

        tree.column("#", width=50, anchor="center")
        tree.column("sana", width=95, anchor="center")
        tree.column("fish", width=160)
        tree.column("telefon", width=110, anchor="center")
        tree.column("viloyat", width=130)
        tree.column("tuman", width=110)
        tree.column("yonalish", width=150)
        tree.column("ijro", width=130, anchor="center")
        tree.column("masul", width=140)
        tree.column("chora", width=120, anchor="center")

        sy = ttk.Scrollbar(t_box, orient="vertical", command=tree.yview)
        sx = ttk.Scrollbar(t_box, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)
        tree.pack(side="left", fill="both", expand=True)
        sy.pack(side="right", fill="y")
        sx.pack(side="bottom", fill="x")

        df = self.df_data.copy()
        if filter_region:
            df = df[df['Viloyat'].astype(str).str.strip() == filter_region]

        if filter_card:
            yon = df['Yoʻnalish'].astype(str).str.lower()
            ij = df['Ijro_Holati'].astype(str).str.lower()
            if filter_card == "agentlik":
                df = df[~yon.str.contains('palata') & ~ij.str.contains('ijobiy|bajarildi|rad')]
            elif filter_card == "palata":
                df = df[yon.str.contains('palata') & ~ij.str.contains('ijobiy|bajarildi|rad')]
            elif filter_card == "organilgan":
                df = df[ij.str.contains('ijobiy|bajarildi|organildi|o‘rganildi')]
            elif filter_card == "asossiz":
                df = df[ij.str.contains('rad|asossiz')]

        for _, r in df.iterrows():
            tree.insert("", "end", values=(
                r.get('#', ''), str(r.get('Yaratilgan sana', ''))[:10],
                r.get('F.I.Sh.', ''), r.get('Telefon', ''),
                r.get('Viloyat', ''), r.get('Tuman', ''),
                r.get('Yoʻnalish', ''), r.get('Ijro_Holati', ''),
                r.get('Masul_Komplayens', ''), r.get('Chora_Turi', '')
            ))

        def on_open_detail(e):
            sel = tree.selection()
            if not sel: return
            mid = int(tree.item(sel[0], "values")[0])
            if DetailsWindow:
                try:
                    DetailsWindow(win, mid, self.db, self.load_data, role=self.role)
                except TypeError:
                    DetailsWindow(win, mid, self.db, self.load_data)

        tree.bind("<Double-1>", on_open_detail)

    def open_audit_window(self):
        win = ctk.CTkToplevel(self)
        win.title("Tizimga kirishlar tarixi (Audit Log)")
        win.geometry("820x500")
        win.grab_set()

        ctk.CTkLabel(win, text="👥 Tizimga kirishlar tarixi va faollik nazorati", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)

        t_box = ctk.CTkFrame(win)
        t_box.pack(padx=15, pady=5, fill="both", expand=True)

        cols = ("#", "user", "role", "time", "comp")
        tree = ttk.Treeview(t_box, columns=cols, show="headings", height=15)
        tree.heading("#", text="№")
        tree.heading("user", text="Foydalanuvchi logini")
        tree.heading("role", text="Roli")
        tree.heading("time", text="Kirgan vaqti")
        tree.heading("comp", text="Kompyuter nomi")

        tree.column("#", width=50, anchor="center")
        tree.column("user", width=150, anchor="center")
        tree.column("role", width=140, anchor="center")
        tree.column("time", width=180, anchor="center")
        tree.column("comp", width=180, anchor="center")
        tree.pack(fill="both", expand=True)

        df_logs = self.db.get_audit_logs()
        for _, r in df_logs.iterrows():
            r_str = "Kuzatuvchi (Rahbar)" if str(r.get('Rol', '')).lower() == 'kuzatuvchi' else "Administrator"
            tree.insert("", "end", values=(r.get('#', ''), r.get('Foydalanuvchi', ''), r_str, r.get('Kirish vaqti', ''), r.get('Kompyuter', '')))

    def open_xodimlar_window(self):
        win = ctk.CTkToplevel(self)
        win.title("Hududiy mas'ul xodimlar kontaktlari")
        win.geometry("800x480")
        win.grab_set()

        ctk.CTkLabel(win, text="📋 Hududiy komplayens xodimlari ro'yxati", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)

        tree = ttk.Treeview(win, columns=("id", "vil", "tash", "fish", "tel", "tg"), show="headings", height=14)
        tree.heading("id", text="ID")
        tree.heading("vil", text="Hudud")
        tree.heading("tash", text="Tashkilot")
        tree.heading("fish", text="Xodim F.I.Sh.")
        tree.heading("tel", text="Telefon")
        tree.heading("tg", text="Telegram")

        tree.column("id", width=40, anchor="center")
        tree.column("vil", width=150)
        tree.column("tash", width=170)
        tree.column("fish", width=180)
        tree.column("tel", width=120, anchor="center")
        tree.column("tg", width=120, anchor="center")
        tree.pack(padx=15, pady=10, fill="both", expand=True)

        df_x = self.db.get_xodimlar()
        for _, r in df_x.iterrows():
            tree.insert("", "end", values=(r['id'], r['viloyat'], r['tashkilot_turi'], r['fish'], r['telefon'], r['telegram_username']))

    def open_add_phone_murojaat(self):
        w = ctk.CTkToplevel(self)
        w.title("Yangi murojaat (Ishonch telefoni)")
        w.geometry("500x560")
        w.grab_set()

        ctk.CTkLabel(w, text="Yangi murojaatni qayd etish", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)

        e_fish = ctk.CTkEntry(w, placeholder_text="Fuqaro F.I.Sh.", width=400)
        e_fish.pack(pady=5)
        e_tel = ctk.CTkEntry(w, placeholder_text="Telefon raqami", width=400)
        e_tel.pack(pady=5)

        cb_vil = ctk.CTkComboBox(w, values=self.regions_list, width=400)
        cb_vil.set("Toshkent shahri")
        cb_vil.pack(pady=5)

        e_tum = ctk.CTkEntry(w, placeholder_text="Tuman / Shahar", width=400)
        e_tum.pack(pady=5)

        cb_yon = ctk.CTkComboBox(w, values=["Kadastr agentligi faoliyati yuzasidan", "Davlat kadastrlari palatasi faoliyati yuzasidan"], width=400)
        cb_yon.set("Kadastr agentligi faoliyati yuzasidan")
        cb_yon.pack(pady=5)

        txt_m = ctk.CTkTextbox(w, width=400, height=120)
        txt_m.insert("0.0", "Murojaat matni...")
        txt_m.pack(pady=5)

        def save():
            f = e_fish.get().strip()
            t = e_tel.get().strip()
            v = cb_vil.get().strip()
            tm = e_tum.get().strip()
            y = cb_yon.get().strip()
            m = txt_m.get("0.0", "end").strip()
            if f and m:
                mas = "Kadastr agentligi hududiy komplayens xodimi" if "agentlik" in y.lower() else "Davlat kadastrlari palatasi hududiy komplayens xodimi"
                nid = self.db.insert_phone_murojaat(f, t, v, tm, y, m, mas)
                messagebox.showinfo("Saqlandi", f"Murojaat № {nid} qabul qilindi!")
                w.destroy()
                self.load_data()

        ctk.CTkButton(w, text="💾 Saqlash", command=save, fg_color="#15803d", width=400).pack(pady=15)

    def import_excel(self):
        p = filedialog.askopenfilename(filetypes=[("Excel", "*.xlsx *.xls")])
        if not p: return
        try:
            df = pd.read_excel(p)
            self.db.sync_excel_data(df)
            messagebox.showinfo("Muvaffaqiyatli", "Excel ma'lumotlari yuklandi!")
            self.load_data()
        except Exception as e:
            messagebox.showerror("Xatolik", f"Excel yuklashda xato: {e}")

    def generate_word_report(self):
        if ReportGenerator:
            try:
                rg = ReportGenerator(self.db)
                out = rg.generate_word_report()
                if out:
                    messagebox.showinfo("Hisobot", f"Word hisoboti saqlandi:\n{out}")
            except Exception as e:
                messagebox.showerror("Xato", f"Hisobot yaratishda xato: {e}")
        else:
            p = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")])
            if p:
                self.filtered_df.to_excel(p, index=False)
                messagebox.showinfo("Saqlandi", f"Fayl saqlandi: {p}")


if __name__ == "__main__":
    app = DashboardApp()
    app.mainloop()

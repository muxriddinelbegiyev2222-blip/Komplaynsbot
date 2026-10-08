import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import customtkinter as ctk
import pandas as pd
from datetime import datetime, timedelta

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
    def __init__(self, username="admin", role="admin", db=None):
        super().__init__()

        self.username = str(username)
        self.role = str(role).lower()
        self.db = db if db else DatabaseManager()

        self.title("Kadastr agentligi — Korrupsiyaga qarshi komplayens nazorat tizimi")
        self.geometry("1380x820")
        self.minsize(1150, 700)

        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        self.df_data = pd.DataFrame()
        self.filtered_df = pd.DataFrame()

        self._build_ui()
        self.load_data()

    def _build_ui(self):
        # Asosiy to'r
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # -------------------------------------------------------------
        # 1. YUQORI SARLAVHA PANELI (HEADER)
        # -------------------------------------------------------------
        self.header_frame = ctk.CTkFrame(self, height=65, corner_radius=0, fg_color="#1a365d")
        self.header_frame.grid(row=0, column=0, sticky="ew")
        self.header_frame.grid_columnconfigure(1, weight=1)

        # Logotip va Nom
        lbl_brand = ctk.CTkLabel(
            self.header_frame,
            text="🛡 O‘ZBEKISTON RESPUBLIKASI KADASTR AGENTLIGI\nKORRUPSIYAGA QARSHI KOMPLAYENS MONITORING TIZIMI",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="white",
            justify="left"
        )
        lbl_brand.grid(row=0, column=0, padx=20, pady=10, sticky="w")

        # Foydalanuvchi ma'lumoti va roli
        user_badge_text = f"👤 {self.username} ({'Administrator' if self.role == 'admin' else 'Kuzatuvchi (Rahbar)'})"
        badge_bg = "#2b6cb0" if self.role == "admin" else "#b7791f"

        self.user_badge = ctk.CTkLabel(
            self.header_frame,
            text=user_badge_text,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=badge_bg,
            corner_radius=8,
            text_color="white",
            padx=12,
            pady=6
        )
        self.user_badge.grid(row=0, column=2, padx=15, pady=12, sticky="e")

        btn_exit = ctk.CTkButton(
            self.header_frame,
            text="🚪 Chiqish",
            width=90,
            command=self.destroy,
            fg_color="#c53030",
            hover_color="#9b2c2c"
        )
        btn_exit.grid(row=0, column=3, padx=(0, 20), pady=12, sticky="e")

        # -------------------------------------------------------------
        # 2. ASOSIY TABVIEW (Barcha bo'limlar jamlangan)
        # -------------------------------------------------------------
        self.tabview = ctk.CTkTabview(self, corner_radius=10)
        self.tabview.grid(row=1, column=0, padx=15, pady=10, sticky="nsew")

        # Vkladkalar
        self.tab_murojaatlar = self.tabview.add("📋 Murojaatlar bazasi")
        self.tab_statistika = self.tabview.add("📊 Hududiy tahlil")
        self.tab_sla = self.tabview.add("⏰ SLA (Muddati o'tganlar)")
        self.tab_xodimlar = self.tabview.add("👥 Mas'ul xodimlar")
        self.tab_hisobot = self.tabview.add("📑 Hisobot tayyorlash")

        if self.role == "admin":
            self.tab_audit = self.tabview.add("👁 Kirishlar tarixi (Audit)")
            self.tab_sozlamalar = self.tabview.add("⚙️ Sozlamalar va Foydalanuvchilar")

        # Vkladkalarni to'ldirish
        self._setup_tab_murojaatlar()
        self._setup_tab_statistika()
        self._setup_tab_sla()
        self._setup_tab_xodimlar()
        self._setup_tab_hisobot()

        if self.role == "admin":
            self._setup_tab_audit()
            self._setup_tab_sozlamalar()

    # =========================================================================
    # TAB 1: MUROJAATLAR BAZASI
    # =========================================================================
    def _setup_tab_murojaatlar(self):
        tab = self.tab_murojaatlar
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(2, weight=1)

        # 1. KPI Kartochkalari
        self.kpi_frame = ctk.CTkFrame(tab, fg_color="transparent")
        self.kpi_frame.grid(row=0, column=0, sticky="ew", pady=(5, 10))
        for i in range(5):
            self.kpi_frame.grid_columnconfigure(i, weight=1)

        self.kpi_labels = {}
        cards = [
            ("jami", "Jami murojaatlar", "#2b6cb0"),
            ("yangi", "O'rganilmoqda / Yangi", "#d69e2e"),
            ("ijobiy", "Bajarildi (Ijobiy)", "#38a169"),
            ("chora", "Chora ko'rilgan", "#805ad5"),
            ("sla_out", "Muddati o'tgan (SLA)", "#e53e3e")
        ]
        for idx, (cid, title, col) in enumerate(cards):
            card = ctk.CTkFrame(self.kpi_frame, fg_color=col, corner_radius=8)
            card.grid(row=0, column=idx, padx=4, sticky="ew")
            ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=11, weight="bold"), text_color="white").pack(pady=(6, 0))
            lbl_v = ctk.CTkLabel(card, text="0", font=ctk.CTkFont(size=20, weight="bold"), text_color="white")
            lbl_v.pack(pady=(0, 6))
            self.kpi_labels[cid] = lbl_v

        # 2. Filtrlar va Amallar paneli
        filter_box = ctk.CTkFrame(tab)
        filter_box.grid(row=1, column=0, sticky="ew", pady=(0, 10))

        lbl_s = ctk.CTkLabel(filter_box, text="🔍 Qidirish:")
        lbl_s.pack(side="left", padx=(12, 4), pady=8)
        self.e_search = ctk.CTkEntry(filter_box, width=180, placeholder_text="F.I.Sh, tel, mazmun...")
        self.e_search.pack(side="left", padx=4, pady=8)
        self.e_search.bind("<KeyRelease>", lambda e: self.apply_filters())

        lbl_r = ctk.CTkLabel(filter_box, text="📍 Hudud:")
        lbl_r.pack(side="left", padx=(10, 4), pady=8)
        regions = ["Barchasi", "Buxoro viloyati", "Farg'ona viloyati", "Jizzax viloyati", "Namangan viloyati", "Navoiy viloyati", "Qashqadaryo viloyati", "Qoraqalpog'iston Respublikasi", "Samarqand viloyati", "Sirdaryo viloyati", "Surxondaryo viloyati", "Toshkent shahri", "Toshkent viloyati", "Xorazm viloyati"]
        self.cb_region = ctk.CTkComboBox(filter_box, values=regions, width=150, command=lambda v: self.apply_filters())
        self.cb_region.set("Barchasi")
        self.cb_region.pack(side="left", padx=4, pady=8)

        lbl_h = ctk.CTkLabel(filter_box, text="📌 Holat:")
        lbl_h.pack(side="left", padx=(10, 4), pady=8)
        holatlar = ["Barchasi", "O‘rganishga yuborilgan", "O‘rganilmoqda", "Bajarildi (Ijobiy)", "Tushuntirish berildi", "Rad etildi"]
        self.cb_status = ctk.CTkComboBox(filter_box, values=holatlar, width=160, command=lambda v: self.apply_filters())
        self.cb_status.set("Barchasi")
        self.cb_status.pack(side="left", padx=4, pady=8)

        btn_rst = ctk.CTkButton(filter_box, text="Tozalash", width=70, fg_color="#718096", command=self.reset_filters)
        btn_rst.pack(side="left", padx=6, pady=8)

        # Tugmalar (Admin / Kuzatuvchi)
        btn_rf = ctk.CTkButton(filter_box, text="🔄 Yangilash", width=90, command=self.load_data)
        btn_rf.pack(side="right", padx=10, pady=8)

        if self.role == "admin":
            btn_add = ctk.CTkButton(filter_box, text="➕ Yangi murojaat", width=120, fg_color="#2b6cb0", command=self.open_add_window)
            btn_add.pack(side="right", padx=5, pady=8)

            btn_imp = ctk.CTkButton(filter_box, text="📥 Excel yuklash", width=110, fg_color="#2f855a", hover_color="#22543d", command=self.import_excel)
            btn_imp.pack(side="right", padx=5, pady=8)

        # 3. Murojaatlar jadvali (Treeview)
        t_box = ctk.CTkFrame(tab)
        t_box.grid(row=2, column=0, sticky="nsew")
        t_box.grid_columnconfigure(0, weight=1)
        t_box.grid_rowconfigure(0, weight=1)

        cols = ("#", "sana", "fish", "telefon", "viloyat", "tuman", "yonalish", "ijro", "masul", "chora")
        self.tree_m = ttk.Treeview(t_box, columns=cols, show="headings", selectmode="browse")

        self.tree_m.heading("#", text="№")
        self.tree_m.heading("sana", text="Sana")
        self.tree_m.heading("fish", text="Fuqaro F.I.Sh.")
        self.tree_m.heading("telefon", text="Telefon")
        self.tree_m.heading("viloyat", text="Hudud")
        self.tree_m.heading("tuman", text="Tuman")
        self.tree_m.heading("yonalish", text="Yo'nalish")
        self.tree_m.heading("ijro", text="Ijro holati")
        self.tree_m.heading("masul", text="Mas'ul xodim")
        self.tree_m.heading("chora", text="Chora turi")

        self.tree_m.column("#", width=50, anchor="center")
        self.tree_m.column("sana", width=95, anchor="center")
        self.tree_m.column("fish", width=160)
        self.tree_m.column("telefon", width=105, anchor="center")
        self.tree_m.column("viloyat", width=130)
        self.tree_m.column("tuman", width=110)
        self.tree_m.column("yonalish", width=150)
        self.tree_m.column("ijro", width=140, anchor="center")
        self.tree_m.column("masul", width=150)
        self.tree_m.column("chora", width=130, anchor="center")

        sy = ttk.Scrollbar(t_box, orient="vertical", command=self.tree_m.yview)
        sx = ttk.Scrollbar(t_box, orient="horizontal", command=self.tree_m.xview)
        self.tree_m.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)

        self.tree_m.grid(row=0, column=0, sticky="nsew")
        sy.grid(row=0, column=1, sticky="ns")
        sx.grid(row=1, column=0, sticky="ew")

        self.tree_m.bind("<Double-1>", self.on_double_click)

        # Pastki status satri
        self.lbl_status = ctk.CTkLabel(tab, text="Murojaatlar soni: 0 ta", font=ctk.CTkFont(size=12))
        self.lbl_status.grid(row=3, column=0, sticky="w", pady=(5, 0), padx=5)

    # =========================================================================
    # TAB 2: HUDUDIY TAHLIL VA STATISTIKA
    # =========================================================================
    def _setup_tab_statistika(self):
        tab = self.tab_statistika
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=1)

        bar = ctk.CTkFrame(tab)
        bar.grid(row=0, column=0, sticky="ew", pady=(5, 10))
        ctk.CTkLabel(bar, text="📊 Respublika hududlari kesimida tahliliy hisobot", font=ctk.CTkFont(size=14, weight="bold")).pack(side="left", padx=15, pady=8)
        ctk.CTkButton(bar, text="🔄 Tahlilni yangilash", command=self.update_stats, width=130).pack(side="right", padx=10, pady=8)

        cols = ("vil", "jami", "agentlik", "palata", "ijobiy", "organishda", "chora")
        self.tree_st = ttk.Treeview(tab, columns=cols, show="headings", height=16)
        self.tree_st.heading("vil", text="Hudud nomi")
        self.tree_st.heading("jami", text="Jami murojaat")
        self.tree_st.heading("agentlik", text="Kadastr agentligi")
        self.tree_st.heading("palata", text="Davlat kadastrlari palatasi")
        self.tree_st.heading("ijobiy", text="Ijobiy hal etilgan")
        self.tree_st.heading("organishda", text="O‘rganilmoqda")
        self.tree_st.heading("chora", text="Chora ko‘rilgan")

        for c in cols[1:]:
            self.tree_st.column(c, width=120, anchor="center")
        self.tree_st.column("vil", width=220)

        self.tree_st.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

    def update_stats(self):
        self.tree_st.delete(*self.tree_st.get_children())
        if self.df_data.empty:

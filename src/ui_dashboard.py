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
            return

        regions = [
            "Qoraqalpog'iston Respublikasi", "Andijon viloyati", "Buxoro viloyati", "Jizzax viloyati", 
            "Qashqadaryo viloyati", "Navoiy viloyati", "Namangan viloyati", "Samarqand viloyati", 
            "Surxondaryo viloyati", "Sirdaryo viloyati", "Toshkent viloyati", "Farg'ona viloyati", 
            "Xorazm viloyati", "Toshkent shahri"
        ]

        df = self.df_data
        for r in regions:
            sub = df[df['Viloyat'].astype(str).str.strip() == r]
            jami = len(sub)
            yon = sub['Yoʻnalish'].astype(str).str.lower()
            palata = yon.str.contains('palata').sum()
            agentlik = jami - palata

            ijro = sub['Ijro_Holati'].astype(str).str.lower()
            ijobiy = ijro.str.contains('ijobiy|bajarildi').sum()
            org = ijro.str.contains('yuborilgan|organilmoqda|o‘rganilmoqda|yangi').sum()

            chora_col = sub['Chora_Turi'].astype(str).str.lower()
            chora = ((chora_col != 'chora ko‘rilmagan') & (chora_col != '') & (chora_col != 'nan')).sum()

            self.tree_st.insert("", "end", values=(r, jami, agentlik, palata, ijobiy, org, chora))

    # =========================================================================
    # TAB 3: SLA NAZORATI (MUDDATI O'TGANLAR)
    # =========================================================================
    def _setup_tab_sla(self):
        tab = self.tab_sla
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=1)

        bar = ctk.CTkFrame(tab)
        bar.grid(row=0, column=0, sticky="ew", pady=(5, 10))
        ctk.CTkLabel(bar, text="🚨 Muddat buzilishi xavfi mavjud bo‘lgan murojaatlar (SLA Nazorati)", font=ctk.CTkFont(size=14, weight="bold"), text_color="#e53e3e").pack(side="left", padx=15, pady=8)

        cols = ("#", "sana", "kun", "fish", "viloyat", "yonalish", "ijro", "masul")
        self.tree_sla = ttk.Treeview(tab, columns=cols, show="headings", height=15)
        self.tree_sla.heading("#", text="№")
        self.tree_sla.heading("sana", text="Kelgan sana")
        self.tree_sla.heading("kun", text="O‘tgan kun")
        self.tree_sla.heading("fish", text="Fuqaro F.I.Sh.")
        self.tree_sla.heading("viloyat", text="Hudud")
        self.tree_sla.heading("yonalish", text="Yo'nalish")
        self.tree_sla.heading("ijro", text="Hozirgi holati")
        self.tree_sla.heading("masul", text="Mas'ul inspektor")

        self.tree_sla.column("#", width=50, anchor="center")
        self.tree_sla.column("sana", width=100, anchor="center")
        self.tree_sla.column("kun", width=90, anchor="center")
        self.tree_sla.column("fish", width=160)
        self.tree_sla.column("viloyat", width=140)
        self.tree_sla.column("yonalish", width=160)
        self.tree_sla.column("ijro", width=140, anchor="center")
        self.tree_sla.column("masul", width=160)

        self.tree_sla.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        self.tree_sla.bind("<Double-1>", self.on_double_click_sla)

    def update_sla_tab(self):
        self.tree_sla.delete(*self.tree_sla.get_children())
        if self.df_data.empty:
            return

        settings = self.db.get_settings()
        try:
            sla_days = int(settings.get("sla_days", 2))
        except:
            sla_days = 2

        count = 0
        now = datetime.now()

        for _, row in self.df_data.iterrows():
            ijro = str(row.get('Ijro_Holati', '')).lower()
            if 'ijobiy' in ijro or 'bajarildi' in ijro or 'rad' in ijro or 'tushuntirish' in ijro:
                continue

            sana_str = str(row.get('Yaratilgan sana', ''))[:10]
            try:
                dt = datetime.strptime(sana_str, "%Y-%m-%d")
                passed = (now - dt).days
                if passed >= sla_days:
                    count += 1
                    self.tree_sla.insert("", "end", values=(
                        row.get('#', ''),
                        sana_str,
                        f"{passed} kun",
                        row.get('F.I.Sh.', ''),
                        row.get('Viloyat', ''),
                        row.get('Yoʻnalish', ''),
                        row.get('Ijro_Holati', ''),
                        row.get('Masul_Komplayens', '')
                    ))
            except:
                pass

        if "sla_out" in self.kpi_labels:
            self.kpi_labels["sla_out"].configure(text=str(count))

    def on_double_click_sla(self, e):
        sel = self.tree_sla.selection()
        if not sel: return
        vals = self.tree_sla.item(sel[0], "values")
        if vals and DetailsWindow:
            DetailsWindow(self, int(vals[0]), self.db, self.load_data, role=self.role)

    # =========================================================================
    # TAB 4: MAS'UL XODIMLAR
    # =========================================================================
    def _setup_tab_xodimlar(self):
        tab = self.tab_xodimlar
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=1)

        bar = ctk.CTkFrame(tab)
        bar.grid(row=0, column=0, sticky="ew", pady=(5, 10))
        ctk.CTkLabel(bar, text="📋 Hududiy komplayens nazorat inspektorlari kontaktlari", font=ctk.CTkFont(size=14, weight="bold")).pack(side="left", padx=15, pady=8)

        cols = ("id", "vil", "tash", "fish", "tel", "tg")
        self.tree_xod = ttk.Treeview(tab, columns=cols, show="headings", height=15)
        self.tree_xod.heading("id", text="ID")
        self.tree_xod.heading("vil", text="Hudud")
        self.tree_xod.heading("tash", text="Tashkilot")
        self.tree_xod.heading("fish", text="Mas'ul xodim F.I.Sh.")
        self.tree_xod.heading("tel", text="Telefon")
        self.tree_xod.heading("tg", text="Telegram")

        self.tree_xod.column("id", width=50, anchor="center")
        self.tree_xod.column("vil", width=150)
        self.tree_xod.column("tash", width=170)
        self.tree_xod.column("fish", width=180)
        self.tree_xod.column("tel", width=130, anchor="center")
        self.tree_xod.column("tg", width=130, anchor="center")

        self.tree_xod.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

        if self.role == "admin":
            f_edit = ctk.CTkFrame(tab)
            f_edit.grid(row=2, column=0, sticky="ew", pady=(10, 5))

            self.e_x_fish = ctk.CTkEntry(f_edit, placeholder_text="F.I.Sh.", width=200)
            self.e_x_fish.pack(side="left", padx=5, pady=8)

            self.e_x_tel = ctk.CTkEntry(f_edit, placeholder_text="Telefon", width=130)
            self.e_x_tel.pack(side="left", padx=5, pady=8)

            self.e_x_tg = ctk.CTkEntry(f_edit, placeholder_text="Telegram (@username)", width=150)
            self.e_x_tg.pack(side="left", padx=5, pady=8)

            def save_x():
                sel = self.tree_xod.selection()
                if not sel:
                    messagebox.showwarning("Tanlang", "O'zgartirish uchun ro'yxatdan xodimni tanlang!")
                    return
                x_id = self.tree_xod.item(sel[0], "values")[0]
                self.db.save_xodim(x_id, self.e_x_fish.get().strip(), self.e_x_tel.get().strip(), self.e_x_tg.get().strip())
                messagebox.showinfo("Saqlandi", "Xodim ma'lumotlari yangilandi!")
                self.load_xodimlar()

            ctk.CTkButton(f_edit, text="💾 Saqlash", command=save_x, fg_color="#2f855a").pack(side="left", padx=10, pady=8)

    def load_xodimlar(self):
        self.tree_xod.delete(*self.tree_xod.get_children())
        df_x = self.db.get_xodimlar()
        for _, r in df_x.iterrows():
            self.tree_xod.insert("", "end", values=(r['id'], r['viloyat'], r['tashkilot_turi'], r['fish'], r['telefon'], r['telegram_username']))

    # =========================================================================
    # TAB 5: HISOBOT TAYYORLASH
    # =========================================================================
    def _setup_tab_hisobot(self):
        tab = self.tab_hisobot
        f = ctk.CTkFrame(tab)
        f.pack(padx=30, pady=30, fill="both", expand=True)

        ctk.CTkLabel(f, text="📑 Rasmiy komplayens tahliliy hisobotlarini shakllantirish", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(20, 15))

        btn_doc = ctk.CTkButton(
            f, text="📄 Word formatida tahliliy hisobot tayyorlash (.docx)", 
            height=45, width=350, font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#2b6cb0", hover_color="#2c5282", command=self.generate_word_report
        )
        btn_doc.pack(pady=15)

        btn_xls = ctk.CTkButton(
            f, text="📊 Hozirgi ko‘rinishdagi ma’lumotlarni Excelga yuklash (.xlsx)", 
            height=45, width=350, font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#2f855a", hover_color="#22543d", command=self.export_excel
        )
        btn_xls.pack(pady=10)

    def generate_word_report(self):
        if ReportGenerator:
            try:
                rg = ReportGenerator(self.db)
                out = rg.generate_word_report()
                if out:
                    messagebox.showinfo("Muvaffaqiyatli", f"Rasmiy Word hisoboti saqlandi:\n{out}")
            except Exception as e:
                messagebox.showerror("Xato", f"Hisobot yaratishda xato: {e}")
        else:
            self.export_excel()

    def export_excel(self):
        if self.filtered_df.empty:
            messagebox.showwarning("Bo'sh", "Eksport qilish uchun ma'lumot yo'q!")
            return
        p = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")])
        if p:
            self.filtered_df.to_excel(p, index=False)
            messagebox.showinfo("Muvaffaqiyatli", f"Fayl saqlandi: {p}")

    # =========================================================================
    # TAB 6: AUDIT LOG (KIRISHLAR TARIXI) — RAHBARLAR KELIB-KETISH NAZORATI
    # =========================================================================
    def _setup_tab_audit(self):
        tab = self.tab_audit
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=1)

        bar = ctk.CTkFrame(tab)
        bar.grid(row=0, column=0, sticky="ew", pady=(5, 10))
        ctk.CTkLabel(bar, text="👁 Tizimga kirishlar tarixi va faollik nazorati (Audit Log)", font=ctk.CTkFont(size=14, weight="bold")).pack(side="left", padx=15, pady=8)
        ctk.CTkButton(bar, text="🔄 Yangilash", command=self.load_audit_tab, width=110).pack(side="right", padx=10, pady=8)

        cols = ("#", "user", "role", "time", "comp")
        self.tree_aud = ttk.Treeview(tab, columns=cols, show="headings", height=16)
        self.tree_aud.heading("#", text="№")
        self.tree_aud.heading("user", text="Foydalanuvchi logini")
        self.tree_aud.heading("role", text="Tizimdagi roli")
        self.tree_aud.heading("time", text="Kirgan aniq vaqti")
        self.tree_aud.heading("comp", text="Kompyuter nomi")

        self.tree_aud.column("#", width=60, anchor="center")
        self.tree_aud.column("user", width=160, anchor="center")
        self.tree_aud.column("role", width=140, anchor="center")
        self.tree_aud.column("time", width=180, anchor="center")
        self.tree_aud.column("comp", width=180, anchor="center")

        self.tree_aud.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

    def load_audit_tab(self):
        if not hasattr(self, 'tree_aud'): return
        self.tree_aud.delete(*self.tree_aud.get_children())
        df = self.db.get_audit_logs()
        for _, r in df.iterrows():
            r_str = "Kuzatuvchi (Rahbar)" if str(r.get('Rol', '')).lower() == 'kuzatuvchi' else "Administrator"
            self.tree_aud.insert("", "end", values=(r.get('#', ''), r.get('Foydalanuvchi', ''), r_str, r.get('Kirish vaqti', ''), r.get('Kompyuter', '')))

    # =========================================================================
    # TAB 7: SOZLAMALAR VA FOYDALANUVCHILAR (ADMIN)
    # =========================================================================
    def _setup_tab_sozlamalar(self):
        tab = self.tab_sozlamalar
        tab.grid_columnconfigure((0, 1), weight=1)

        # 1. Sozlamalar qismi
        f_soz = ctk.CTkFrame(tab)
        f_soz.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        ctk.CTkLabel(f_soz, text="⚙️ Asosiy tizim sozlamalari", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(15, 10))
        sett = self.db.get_settings()

        ctk.CTkLabel(f_soz, text="Murojaatni ko'rib chiqish muddati (kunlarda):").pack(anchor="w", padx=15, pady=(5, 2))
        self.e_sla = ctk.CTkEntry(f_soz, width=280)
        self.e_sla.insert(0, sett.get("sla_days", "2"))
        self.e_sla.pack(anchor="w", padx=15, pady=(0, 10))

        ctk.CTkLabel(f_soz, text="Hisobot rasmiy shapkasi:").pack(anchor="w", padx=15, pady=(5, 2))
        self.txt_rep = ctk.CTkTextbox(f_soz, width=320, height=80)
        self.txt_rep.insert("0.0", sett.get("report_header", ""))
        self.txt_rep.pack(anchor="w", padx=15, pady=(0, 10))

        def save_sett():
            self.db.update_settings({
                "sla_days": self.e_sla.get().strip(),
                "report_header": self.txt_rep.get("0.0", "end").strip()
            })
            messagebox.showinfo("Saqlandi", "Sozlamalar saqlandi!")

        ctk.CTkButton(f_soz, text="💾 Saqlash", command=save_sett, fg_color="#2f855a").pack(padx=15, pady=10)

        # 2. Foydalanuvchilar qismi
        f_users = ctk.CTkFrame(tab)
        f_users.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

        ctk.CTkLabel(f_users, text="👥 Foydalanuvchilar (Admin / Rahbar)", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(15, 10))

        f_u_add = ctk.CTkFrame(f_users, fg_color="transparent")
        f_u_add.pack(padx=10, pady=5, fill="x")

        self.e_u_log = ctk.CTkEntry(f_u_add, placeholder_text="Login", width=100)
        self.e_u_log.pack(side="left", padx=2)
        self.e_u_pas = ctk.CTkEntry(f_u_add, placeholder_text="Parol", width=100)
        self.e_u_pas.pack(side="left", padx=2)
        self.cb_u_rol = ctk.CTkComboBox(f_u_add, values=["kuzatuvchi", "admin"], width=110)
        self.cb_u_rol.set("kuzatuvchi")
        self.cb_u_rol.pack(side="left", padx=2)

        def add_u():
            l = self.e_u_log.get().strip()
            p = self.e_u_pas.get().strip()
            r = self.cb_u_rol.get().strip()
            if l and p:
                if self.db.add_user(l, p, r):
                    messagebox.showinfo("Qo'shildi", f"Foydalanuvchi {l} qo'shildi!")
                    self.load_users_table()
                else:
                    messagebox.showerror("Xato", "Bu login mavjud!")

        ctk.CTkButton(f_u_add, text="+", width=40, command=add_u, fg_color="#2f855a").pack(side="left", padx=4)

        self.tree_u = ttk.Treeview(f_users, columns=("id", "log", "rol"), show="headings", height=8)
        self.tree_u.heading("id", text="ID")
        self.tree_u.heading("log", text="Login")
        self.tree_u.heading("rol", text="Roli")
        self.tree_u.column("id", width=40, anchor="center")
        self.tree_u.pack(padx=10, pady=10, fill="both", expand=True)

        def del_u():
            sel = self.tree_u.selection()
            if not sel: return
            uid = self.tree_u.item(sel[0], "values")[0]
            if str(uid) == "1":
                messagebox.showwarning("Xato", "Asosiy admin o'chirilmaydi!")
                return
            if messagebox.askyesno("O'chirish", "Haqiqatan ham o'chirilsinmi?"):
                self.db.delete_user(uid)
                self.load_users_table()

        ctk.CTkButton(f_users, text="O'chirish", command=del_u, fg_color="#c53030").pack(pady=5)

    def load_users_table(self):
        if not hasattr(self, 'tree_u'): return
        self.tree_u.delete(*self.tree_u.get_children())
        df = self.db.get_all_users()
        for _, r in df.iterrows():
            self.tree_u.insert("", "end", values=(r['id'], r['username'], r['role']))

    # =========================================================================
    # MA'LUMOTLARNI YUKLASH VA INTERFEYSNI YANGILASH
    # =========================================================================
    def load_data(self):
        try:
            self.df_data = self.db.get_all_records()
            self.apply_filters()
            self.update_kpi()
            self.update_stats()
            self.update_sla_tab()
            self.load_xodimlar()
            if self.role == "admin":
                self.load_audit_tab()
                self.load_users_table()
        except Exception as e:
            messagebox.showerror("Xatolik", f"Yuklashda xato: {e}")

    def update_kpi(self):
        if self.df_data.empty:
            for k in self.kpi_labels:
                self.kpi_labels[k].configure(text="0")
            return

        jami = len(self.df_data)
        holat = self.df_data['Ijro_Holati'].astype(str).str.lower()
        chora = self.df_data['Chora_Turi'].astype(str).str.lower()

        yangi = holat.str.contains('yuborilgan|organilmoqda|o‘rganilmoqda|yangi').sum()
        ijobiy = holat.str.contains('ijobiy|bajarildi').sum()
        chora_soni = ((chora != 'chora ko‘rilmagan') & (chora != '') & (chora != 'nan')).sum()

        self.kpi_labels["jami"].configure(text=str(jami))
        self.kpi_labels["yangi"].configure(text=str(yangi))
        self.kpi_labels["ijobiy"].configure(text=str(ijobiy))
        self.kpi_labels["chora"].configure(text=str(chora_soni))

    def apply_filters(self):
        if self.df_data.empty:
            self.tree_m.delete(*self.tree_m.get_children())
            self.lbl_status.configure(text="Murojaatlar soni: 0 ta")
            return

        df = self.df_data.copy()

        s = self.e_search.get().strip().lower()
        if s:
            mask = (
                df['F.I.Sh.'].astype(str).str.lower().str.contains(s, na=False) |
                df['Telefon'].astype(str).str.lower().str.contains(s, na=False) |
                df['Murojaat matni'].astype(str).str.lower().str.contains(s, na=False) |
                df['#'].astype(str).str.contains(s, na=False)
            )
            df = df[mask]

        reg = self.cb_region.get()
        if reg != "Barchasi":
            df = df[df['Viloyat'] == reg]

        st = self.cb_status.get()
        if st != "Barchasi":
            df = df[df['Ijro_Holati'] == st]

        self.filtered_df = df

        self.tree_m.delete(*self.tree_m.get_children())
        for _, row in df.iterrows():
            self.tree_m.insert("", "end", values=(
                row.get('#', ''),
                str(row.get('Yaratilgan sana', ''))[:10],
                row.get('F.I.Sh.', ''),
                row.get('Telefon', ''),
                row.get('Viloyat', ''),
                row.get('Tuman', ''),
                row.get('Yoʻnalish', ''),
                row.get('Ijro_Holati', ''),
                row.get('Masul_Komplayens', ''),
                row.get('Chora_Turi', '')
            ))

        self.lbl_status.configure(text=f"Ko'rsatilmoqda: {len(df)} ta (Jami bazada: {len(self.df_data)} ta)")

    def reset_filters(self):
        self.e_search.delete(0, "end")
        self.cb_region.set("Barchasi")
        self.cb_status.set("Barchasi")
        self.apply_filters()

    def on_double_click(self, event):
        sel = self.tree_m.selection()
        if not sel: return
        vals = self.tree_m.item(sel[0], "values")
        if not vals: return
        m_id = int(vals[0])

        if DetailsWindow:
            try:
                DetailsWindow(self, m_id, self.db, self.load_data, role=self.role)
            except TypeError:
                DetailsWindow(self, m_id, self.db, self.load_data)
        else:
            messagebox.showinfo("Murojaat", f"Murojaat № {m_id}")

    def import_excel(self):
        p = filedialog.askopenfilename(filetypes=[("Excel", "*.xlsx *.xls")])
        if not p: return
        try:
            df = pd.read_excel(p)
            self.db.sync_excel_data(df)
            messagebox.showinfo("Muvaffaqiyatli", "Excel murojaatlari bazaga qo'shildi!")
            self.load_data()
        except Exception as e:
            messagebox.showerror("Xato", f"Excel yuklashda xato: {e}")

    def open_add_window(self):
        w = ctk.CTkToplevel(self)
        w.title("Yangi murojaat (Ishonch telefoni)")
        w.geometry("500x560")
        w.grab_set()

        ctk.CTkLabel(w, text="Yangi murojaatni qayd etish", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)

        e_fish = ctk.CTkEntry(w, placeholder_text="Fuqaro F.I.Sh.", width=400)
        e_fish.pack(pady=5)
        e_tel = ctk.CTkEntry(w, placeholder_text="Telefon raqami", width=400)
        e_tel.pack(pady=5)

        cb_vil = ctk.CTkComboBox(w, values=["Toshkent shahri", "Toshkent viloyati", "Samarqand viloyati", "Farg'ona viloyati", "Andijon viloyati", "Namangan viloyati", "Buxoro viloyati", "Qashqadaryo viloyati", "Surxondaryo viloyati", "Jizzax viloyati", "Sirdaryo viloyati", "Navoiy viloyati", "Xorazm viloyati", "Qoraqalpog'iston Respublikasi"], width=400)
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

        ctk.CTkButton(w, text="💾 Saqlash", command=save, fg_color="#2f855a", width=400).pack(pady=15)


if __name__ == "__main__":
    app = DashboardApp()
    app.mainloop()

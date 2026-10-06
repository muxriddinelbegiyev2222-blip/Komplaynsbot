import customtkinter as ctk
from tkinter import ttk, filedialog, messagebox
import os
import shutil
from src.report_generator import ReportGenerator

class DashboardApp(ctk.CTk):
    def __init__(self, data_loader):
        super().__init__()
        self.loader = data_loader

        self.title("Kadastr Agentligi - Korrupsiyaga Qarshi Monitoring Tizimi")
        self.geometry("1400x880")
        self.minsize(1180, 700)
        ctk.set_appearance_mode("Light")
        self.configure(fg_color="#F4F7FC")

        self.view_stack = []

        self._build_top_navbar()
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(fill="both", expand=True, padx=20, pady=(0, 15))

        self.show_dashboard_view()

    def _build_top_navbar(self):
        nav = ctk.CTkFrame(self, fg_color="#1F497D", height=60, corner_radius=0)
        nav.pack(fill="x", side="top", pady=(0, 12))

        self.btn_back = ctk.CTkButton(
            nav, text="⬅ Orqaga", width=95, height=34,
            fg_color="#34495E", hover_color="#2C3E50",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._go_back
        )
        self.btn_back.pack(side="left", padx=15, pady=13)

        self.lbl_path = ctk.CTkLabel(
            nav, text="Asosiy oyna  /  Tahliliy Dashboard", 
            font=ctk.CTkFont(size=16, weight="bold"), text_color="white"
        )
        self.lbl_path.pack(side="left", padx=10, pady=13)

        btn_word = ctk.CTkButton(
            nav, text="📄 Word Ma'lumotnoma", width=145, height=34,
            fg_color="#D35400", hover_color="#B94A00", font=ctk.CTkFont(size=11, weight="bold"),
            command=self._export_word
        )
        btn_word.pack(side="right", padx=(5, 15), pady=13)

        btn_excel = ctk.CTkButton(
            nav, text="📊 Excel Jadval", width=115, height=34,
            fg_color="#27AE60", hover_color="#219150", font=ctk.CTkFont(size=11, weight="bold"),
            command=self._export_excel
        )
        btn_excel.pack(side="right", padx=5, pady=13)

        btn_import = ctk.CTkButton(
            nav, text="📥 Yangi Excel yuklash", width=145, height=34,
            fg_color="#2980B9", hover_color="#2471A3", font=ctk.CTkFont(size=11, weight="bold"),
            command=self._import_excel
        )
        btn_import.pack(side="right", padx=5, pady=13)

    def _clear_container(self):
        for widget in self.container.winfo_children():
            widget.destroy()

    def _go_back(self):
        if self.view_stack:
            prev_view = self.view_stack.pop()
            prev_view()
        else:
            self.show_dashboard_view()

    # ================= 1-POG'ONA: DASHBOARD =================
    def show_dashboard_view(self):
        self.view_stack.clear()
        self.btn_back.configure(state="disabled")
        self.lbl_path.configure(text="Asosiy oyna  /  Tahliliy Dashboard")
        self._clear_container()

        # Filtrlar paneli
        filter_box = ctk.CTkFrame(self.container, fg_color="white", corner_radius=8, height=48)
        filter_box.pack(fill="x", pady=(0, 10), padx=5)

        ctk.CTkLabel(filter_box, text="⏳ Davr:", font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=(12, 4), pady=8)
        self.cb_period = ctk.CTkComboBox(filter_box, values=["Barchasi", "Joriy hafta", "Joriy oy", "Joriy yil"], command=self._apply_filters, width=105, font=ctk.CTkFont(size=11))
        self.cb_period.set(getattr(self, 'selected_period', 'Barchasi'))
        self.cb_period.pack(side="left", padx=4, pady=8)

        ctk.CTkLabel(filter_box, text="🏢 Yoʻnalish:", font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=(10, 4), pady=8)
        yonalish_options = [
            "Barchasi",
            "Kadastr agentligi markaziy apparati",
            "Kadastr agentligi hududiy boshqarmasi",
            "Davlat kadastrlari palatasi markaziy apparati",
            "Davlat kadastrlari palatasi hududiy boshqarmasi",
            "Boshqa tizim tashkiloti"
        ]
        self.cb_yonalish = ctk.CTkComboBox(filter_box, values=yonalish_options, command=self._apply_filters, width=260, font=ctk.CTkFont(size=11))
        self.cb_yonalish.set(getattr(self, 'selected_yonalish', 'Barchasi'))
        self.cb_yonalish.pack(side="left", padx=4, pady=8)

        ctk.CTkLabel(filter_box, text="👤 Mas'ul komplayens:", font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=(10, 4), pady=8)
        masul_options = [
            "Barchasi",
            "Kadastr agentligi hududiy komplayens xodimi",
            "Davlat kadastrlari palatasi hududiy komplayens xodimi",
            "Agentlik markaziy apparati mas’ul xodimi"
        ]
        self.cb_masul = ctk.CTkComboBox(filter_box, values=masul_options, command=self._apply_filters, width=220, font=ctk.CTkFont(size=11))
        self.cb_masul.set(getattr(self, 'selected_masul', 'Barchasi'))
        self.cb_masul.pack(side="left", padx=4, pady=8)

        btn_reset = ctk.CTkButton(filter_box, text="Tozalash", width=65, height=28, fg_color="#95A5A6", hover_color="#7F8C8D", font=ctk.CTkFont(size=11), command=self._reset_filters)
        btn_reset.pack(side="left", padx=8, pady=8)

        # KPI Kartochkalari (Alohida Agentlik va Palata o'rganishi bilan)
        cards_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        cards_frame.pack(fill="x", pady=(0, 10))

        stats = self.loader.get_kpi_stats()
        cards = [
            ("JAMI MUROJAATLAR", stats['total'], "#1F497D", lambda: self.show_records_view("Barcha murojaatlar", self.loader.filtered_df)),
            ("KORRUPSIYA ALOMATI", stats['korrupsiya'], "#C0392B", lambda: self.show_records_view("Korrupsiyaga oid murojaatlar", self.loader.filtered_df[self.loader.filtered_df['Kategoriya'] == 'Korrupsiyaga oid'])),
            ("AGENTLIKDA O‘RGANISHDA", stats['agentlik_organish'], "#2980B9", lambda: self.show_records_view("Agentlik komplayensida o‘rganishdagi murojaatlar", self.loader.filtered_df[self.loader.filtered_df['Ijro_Holati'].astype(str).str.contains("O‘rganishga yuborilgan|O'rganishda", case=False, na=False) & self.loader.filtered_df['Masul_Komplayens'].astype(str).str.contains("agentligi", case=False, na=False)])),
            ("PALATADA O‘RGANISHDA", stats['palata_organish'], "#8E44AD", lambda: self.show_records_view("Palata komplayensida o‘rganishdagi murojaatlar", self.loader.filtered_df[self.loader.filtered_df['Ijro_Holati'].astype(str).str.contains("O‘rganishga yuborilgan|O'rganishda", case=False, na=False) & self.loader.filtered_df['Masul_Komplayens'].astype(str).str.contains("palata", case=False, na=False)])),
            ("O‘RGANIB CHIQILGAN", stats['natija_kiritilgan'], "#27AE60", lambda: self.show_records_view("O‘rganib chiqilgan va natijasi kiritilgan", self.loader.filtered_df[self.loader.filtered_df['Ijro_Holati'].astype(str).str.contains("Bartaraf etildi|Ijobiy hal etildi|Intizomiy chora|O‘rganib chiqildi", case=False, na=False)])),
            ("ASOSSIZ DEB TOPILGAN", stats['asossiz'], "#7F8C8D", lambda: self.show_records_view("Asossiz deb topilganlar", self.loader.filtered_df[self.loader.filtered_df['Ijro_Holati'].astype(str).str.contains("Asossiz", case=False, na=False)]))
        ]

        for i, (title, val, color, cmd) in enumerate(cards):
            card = ctk.CTkFrame(cards_frame, fg_color=color, corner_radius=8)
            card.grid(row=0, column=i, padx=3, sticky="nsew")
            cards_frame.grid_columnconfigure(i, weight=1)

            ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=9, weight="bold"), text_color="#E0E6ED").pack(pady=(6, 1))
            ctk.CTkLabel(card, text=str(val), font=ctk.CTkFont(size=22, weight="bold"), text_color="white").pack(pady=(0, 2))
            ctk.CTkButton(card, text="Ochish ➔", width=70, height=20, fg_color="transparent", border_width=1, border_color="white", font=ctk.CTkFont(size=9), command=cmd).pack(pady=(0, 6))

        # Asosiy jadval paneli (Yengil va silliq)
        content = ctk.CTkFrame(self.container, fg_color="white", corner_radius=8)
        content.pack(fill="both", expand=True, padx=5, pady=(0, 5))

        lbl_sec = ctk.CTkLabel(content, text="Viloyatlar kesimida o‘rganish holati (Viloyat ustiga 2 marta bosing):", font=ctk.CTkFont(size=12, weight="bold"), text_color="#1F497D")
        lbl_sec.pack(anchor="w", padx=15, pady=(10, 5))

        table_frame = ctk.CTkFrame(content, fg_color="transparent")
        table_frame.pack(fill="both", expand=True, padx=15, pady=(0, 10))

        cols = ("viloyat", "jami", "korrupsiya", "agentlik_org", "palata_org", "hal_etilgan")
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Dash.Treeview", rowheight=30, font=("Calibri", 11))
        style.configure("Dash.Treeview.Heading", font=("Calibri", 11, "bold"), background="#E4E9F2")

        self.dash_tree = ttk.Treeview(table_frame, columns=cols, show="headings", style="Dash.Treeview", selectmode="browse")
        self.dash_tree.heading("viloyat", text="Hudud nomi (Viloyat)")
        self.dash_tree.heading("jami", text="Jami murojaat")
        self.dash_tree.heading("korrupsiya", text="Korrupsiya alomati")
        self.dash_tree.heading("agentlik_org", text="Agentlikda o‘rganishda")
        self.dash_tree.heading("palata_org", text="Palatada o‘rganishda")
        self.dash_tree.heading("hal_etilgan", text="O‘rganib chiqilgan")

        self.dash_tree.column("viloyat", width=240)
        self.dash_tree.column("jami", width=110, anchor="center")
        self.dash_tree.column("korrupsiya", width=130, anchor="center")
        self.dash_tree.column("agentlik_org", width=150, anchor="center")
        self.dash_tree.column("palata_org", width=150, anchor="center")
        self.dash_tree.column("hal_etilgan", width=140, anchor="center")

        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.dash_tree.yview)
        self.dash_tree.configure(yscrollcommand=vsb.set)
        self.dash_tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        f_df = self.loader.filtered_df
        reg_groups = f_df.groupby('Viloyat') if not f_df.empty else []

        for reg, group in reg_groups:
            c_tot = len(group)
            c_kor = len(group[group['Kategoriya'] == 'Korrupsiyaga oid'])
            is_org = group['Ijro_Holati'].astype(str).str.contains("O‘rganishga yuborilgan|O'rganishda", case=False, na=False)
            c_ag = len(group[is_org & group['Masul_Komplayens'].astype(str).str.contains("agentligi", case=False, na=False)])
            c_pa = len(group[is_org & group['Masul_Komplayens'].astype(str).str.contains("palata", case=False, na=False)])
            c_hal = len(group[group['Ijro_Holati'].astype(str).str.contains("Bartaraf etildi|Ijobiy hal etildi|Intizomiy chora|O‘rganib chiqildi", case=False, na=False)])
            
            self.dash_tree.insert("", "end", values=(reg, f"{c_tot} ta", f"{c_kor} ta", f"{c_ag} ta", f"{c_pa} ta", f"{c_hal} ta"))

        def on_region_open(event):
            sel = self.dash_tree.selection()
            if not sel: return
            reg_name = self.dash_tree.item(sel[0], "values")[0]
            self._drill_down_region(reg_name)

        self.dash_tree.bind("<Double-1>", on_region_open)

    def _apply_filters(self, _=None):
        self.selected_period = self.cb_period.get()
        self.selected_yonalish = self.cb_yonalish.get()
        self.selected_masul = self.cb_masul.get()

        self.loader.filter_data(
            period=self.selected_period,
            yonalish=self.selected_yonalish,
            masul=self.selected_masul
        )
        self.show_dashboard_view()

    def _reset_filters(self):
        self.selected_period = "Barchasi"
        self.selected_yonalish = "Barchasi"
        self.selected_masul = "Barchasi"
        self.loader.filter_data("Barchasi", "Barchasi", "Barchasi", "Barchasi")
        self.show_dashboard_view()

    def _drill_down_region(self, reg_name):
        df_reg = self.loader.filtered_df[self.loader.filtered_df['Viloyat'] == reg_name]
        self.show_records_view(f"{reg_name} murojaatlari", df_reg)

    # ================= 2-POG'ONA: RO'YXAT =================
    def show_records_view(self, title, data_df):
        self.view_stack.append(self.show_dashboard_view)
        self.btn_back.configure(state="normal")
        self.lbl_path.configure(text=f"Asosiy oyna  /  Ro'yxat: {title}")
        self._clear_container()

        main_box = ctk.CTkFrame(self.container, fg_color="white", corner_radius=8)
        main_box.pack(fill="both", expand=True)

        top_bar = ctk.CTkFrame(main_box, fg_color="transparent")
        top_bar.pack(fill="x", padx=15, pady=10)

        ctk.CTkLabel(top_bar, text="🔍 Tezkor qidiruv:", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=(0, 5))
        entry_search = ctk.CTkEntry(top_bar, placeholder_text="F.I.Sh, Telefon, Tuman yoki Kalit so'z...", width=320, font=ctk.CTkFont(size=12))
        entry_search.pack(side="left", padx=5)

        lbl_count = ctk.CTkLabel(top_bar, text=f"Jami: {len(data_df)} ta", font=ctk.CTkFont(size=13, weight="bold"), text_color="#1F497D")
        lbl_count.pack(side="right", padx=10)

        tree_frame = ctk.CTkFrame(main_box, fg_color="transparent")
        tree_frame.pack(fill="both", expand=True, padx=15, pady=(0, 8))

        cols = ("#", "sana", "fish", "telefon", "viloyat", "tuman", "masul", "ijro")
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Rec.Treeview", rowheight=28, font=("Calibri", 11))
        style.configure("Rec.Treeview.Heading", font=("Calibri", 11, "bold"), background="#E4E9F2")

        tree = ttk.Treeview(tree_frame, columns=cols, show="headings", style="Rec.Treeview", selectmode="browse")
        tree.heading("#", text="#")
        tree.heading("sana", text="Sana")
        tree.heading("fish", text="F.I.Sh.")
        tree.heading("telefon", text="Telefon")
        tree.heading("viloyat", text="Viloyat")
        tree.heading("tuman", text="Tuman")
        tree.heading("masul", text="Mas’ul komplayens xodimi")
        tree.heading("ijro", text="Holati")

        tree.column("#", width=45, anchor="center")
        tree.column("sana", width=125, anchor="center")
        tree.column("fish", width=150)
        tree.column("telefon", width=105, anchor="center")
        tree.column("viloyat", width=115)
        tree.column("tuman", width=115)
        tree.column("masul", width=220)
        tree.column("ijro", width=130, anchor="center")

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        def populate(df_to_show):
            tree.delete(*tree.get_children())
            for _, r in df_to_show.iterrows():
                tree.insert("", "end", values=(
                    r.get('#'), str(r.get('Yaratilgan sana'))[:16], r.get('F.I.Sh.'),
                    r.get('Telefon'), r.get('Viloyat'), r.get('Tuman'),
                    r.get('Masul_Komplayens', 'Agentlik hududiy komplayens'), r.get('Ijro_Holati', 'O‘rganishga yuborilgan')
                ))

        populate(data_df)

        def on_search(event):
            q = entry_search.get().lower().strip()
            if not q:
                populate(data_df)
            else:
                m = data_df['F.I.Sh.'].astype(str).str.lower().str.contains(q) | \
                    data_df['Telefon'].astype(str).str.lower().str.contains(q) | \
                    data_df['Tuman'].astype(str).str.lower().str.contains(q) | \
                    data_df['Murojaat matni'].astype(str).str.lower().str.contains(q) | \
                    data_df['Masul_Komplayens'].astype(str).str.lower().str.contains(q)
                populate(data_df[m])

        entry_search.bind("<KeyRelease>", on_search)

        def on_open(event):
            sel = tree.selection()
            if not sel: return
            item_vals = tree.item(sel[0], "values")
            m_id = int(item_vals[0])
            self.show_detail_view(m_id, lambda: self.show_records_view(title, data_df))

        tree.bind("<Double-1>", on_open)
        ctk.CTkLabel(main_box, text="💡 Murojaat ichiga kirish, o'rganish natijasi va hujjat biriktirish uchun qator ustiga ikki marta bosing.", font=ctk.CTkFont(size=11, slant="italic")).pack(pady=4)

    # ================= 3-POG'ONA: KARTOCHKA =================
    def show_detail_view(self, m_id, return_callback):
        self.view_stack.append(return_callback)
        self.btn_back.configure(state="normal")
        self.lbl_path.configure(text=f"Asosiy oyna  /  Murojaatlar  /  Kartochka #{m_id}")
        self._clear_container()

        rec = self.loader.df[self.loader.df['#'] == m_id].iloc[0]

        main_scroll = ctk.CTkScrollableFrame(self.container, fg_color="white", corner_radius=8)
        main_scroll.pack(fill="both", expand=True, padx=5, pady=5)

        info_top = ctk.CTkFrame(main_scroll, fg_color="#F8FAFC", corner_radius=6)
        info_top.pack(fill="x", padx=15, pady=(12, 8))

        txt_info = f"👤 Fuqaro: {rec.get('F.I.Sh.')}   |   📞 Tel: {rec.get('Telefon')}   |   📍 Hudud: {rec.get('Viloyat')}, {rec.get('Tuman')}\n" \
                   f"🏢 Yo'nalish: {rec.get('Yoʻnalish')}\n🕒 Kelib tushgan sana: {rec.get('Yaratilgan sana')}"
        ctk.CTkLabel(info_top, text=txt_info, justify="left", font=ctk.CTkFont(size=13, weight="bold")).pack(padx=15, pady=8, anchor="w")

        # Katta va tiniq matn oynasi
        ctk.CTkLabel(main_scroll, text="📝 Murojaat matni (to‘liq shaklda):", font=ctk.CTkFont(size=13, weight="bold"), text_color="#1F497D").pack(padx=15, anchor="w")
        tb_m = ctk.CTkTextbox(main_scroll, height=220, wrap="word", font=ctk.CTkFont(size=13))
        tb_m.insert("1.0", str(rec.get('Murojaat matni', '')))
        tb_m.configure(state="disabled")
        tb_m.pack(fill="x", padx=15, pady=(4, 10))

        # Yuborilgan rasmiy javob
        ctk.CTkLabel(main_scroll, text="✉️ Bot orqali fuqaroga yuborilgan rasmiy javob:", font=ctk.CTkFont(size=12, weight="bold")).pack(padx=15, anchor="w")
        tb_j = ctk.CTkTextbox(main_scroll, height=65, wrap="word", font=ctk.CTkFont(size=12))
        rasmiy_javob_shablon = "Ассалому алайкум, ҳурматли фуқаро. Сизнинг мурожаатингиз бўйича ҳолатларга аниқлик киритиш мақсадида Коррупцияга қарши курашиш бўлими ходимлари телефон рақамингиз орқали Сиз билан боғланади."
        tb_j.insert("1.0", rasmiy_javob_shablon)
        tb_j.configure(state="disabled")
        tb_j.pack(fill="x", padx=15, pady=(4, 10))

        # CRM va Ijrochi tayinlash qismi
        action_frame = ctk.CTkFrame(main_scroll, fg_color="#EEF2F7", corner_radius=6)
        action_frame.pack(fill="x", padx=15, pady=(5, 12))

        ctk.CTkLabel(action_frame, text="⚙️ KOMPLAYENS NAZORAT, MAS’UL TAYINLASH VA O‘RGANISH NATIJASI:", font=ctk.CTkFont(size=12, weight="bold"), text_color="#1F497D").pack(padx=15, pady=(8, 4), anchor="w")

        # 1-qator: O'rganishga yuboriladigan mas'ul xodim / organ
        row_masul = ctk.CTkFrame(action_frame, fg_color="transparent")
        row_masul.pack(fill="x", padx=15, pady=3)

        ctk.CTkLabel(row_masul, text="O‘rganish yuklatilgan mas’ul:", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=(0, 10))
        cb_masul_item = ctk.CTkComboBox(
            row_masul, 
            values=[
                "Kadastr agentligi hududiy komplayens xodimi",
                "Davlat kadastrlari palatasi hududiy komplayens xodimi",
                "Agentlik markaziy apparati mas’ul xodimi",
                "Davlat kadastrlari palatasi markaziy apparati mas’ul xodimi"
            ], 
            width=320, 
            font=ctk.CTkFont(size=12)
        )
        cb_masul_item.set(str(rec.get('Masul_Komplayens', 'Kadastr agentligi hududiy komplayens xodimi')))
        cb_masul_item.pack(side="left")

        # 2-qator: Holati
        row_status = ctk.CTkFrame(action_frame, fg_color="transparent")
        row_status.pack(fill="x", padx=15, pady=4)

        ctk.CTkLabel(row_status, text="Murojaat ijro holati:", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=(0, 10))
        cb_status = ctk.CTkComboBox(
            row_status, 
            values=["O‘rganishga yuborilgan", "O‘rganib chiqildi / Bartaraf etildi", "Ijobiy hal etildi", "Intizomiy chora ko‘rildi", "Asossiz deb topildi"], 
            width=280, 
            font=ctk.CTkFont(size=12)
        )
        cb_status.set(str(rec.get('Ijro_Holati', 'O‘rganishga yuborilgan')))
        cb_status.pack(side="left")

        # 3-qator: O'rganish natijasi
        ctk.CTkLabel(action_frame, text="Hududiy komplayens xodimining o‘rganish xulosasi va ko‘rilgan choralar mazmuni:", font=ctk.CTkFont(size=12, weight="bold")).pack(padx=15, pady=(6, 2), anchor="w")
        tb_natija = ctk.CTkTextbox(action_frame, height=85, wrap="word", font=ctk.CTkFont(size=12))
        tb_natija.insert("1.0", str(rec.get('Organish_Natijasi', '')))
        tb_natija.pack(fill="x", padx=15, pady=(0, 8))

        # Fayl biriktirish bloki
        self.attached_file_path = str(rec.get('Biriktirilgan_Fayl', ''))

        file_box = ctk.CTkFrame(action_frame, fg_color="white", corner_radius=5)
        file_box.pack(fill="x", padx=15, pady=(0, 10))

        self.lbl_file_status = ctk.CTkLabel(
            file_box, 
            text=f"📁 Biriktirilgan hujjat: {os.path.basename(self.attached_file_path)}" if self.attached_file_path else "📁 Biriktirilgan hujjat: Yo'q",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#1F497D" if self.attached_file_path else "#7F8C8D"
        )
        self.lbl_file_status.pack(side="left", padx=12, pady=7)

        btn_attach = ctk.CTkButton(
            file_box, text="📎 Hujjat yuklash (PDF/Rasm)", width=160, height=28,
            fg_color="#2980B9", hover_color="#2471A3", font=ctk.CTkFont(size=11, weight="bold"),
            command=self._attach_file
        )
        btn_attach.pack(side="right", padx=8, pady=5)

        btn_open_file = ctk.CTkButton(
            file_box, text="👁 Ko'rish", width=75, height=28,
            fg_color="#34495E", hover_color="#2C3E50", font=ctk.CTkFont(size=11, weight="bold"),
            command=self._open_attached_file
        )
        btn_open_file.pack(side="right", padx=4, pady=5)

        def save_changes():
            st = cb_status.get()
            ms = cb_masul_item.get()
            nat = tb_natija.get("1.0", "end-1c")
            self.loader.db.update_murojaat_ijro(m_id, st, nat, self.attached_file_path, ms)
            self.loader.refresh_data()
            messagebox.showinfo("Saqlandi", f"#{m_id} sonli murojaat bo‘yicha mas’ul xodim, o‘rganish natijasi va hujjat saqlandi!")

        btn_save = ctk.CTkButton(action_frame, text="💾 Saqlash", fg_color="#27AE60", hover_color="#219150", width=130, height=32, font=ctk.CTkFont(size=12, weight="bold"), command=save_changes)
        btn_save.pack(pady=(0, 8))

    def _attach_file(self):
        fp = filedialog.askopenfilename(
            title="Hujjatni tanlang (PDF, Rasm, Word)",
            filetypes=[("Hujjatlar va Rasmlar", "*.pdf *.png *.jpg *.jpeg *.docx *.doc *.xlsx")]
        )
        if fp:
            attach_dir = os.path.join("data", "attachments")
            os.makedirs(attach_dir, exist_ok=True)
            dest = os.path.join(attach_dir, os.path.basename(fp))
            shutil.copy2(fp, dest)
            self.attached_file_path = dest
            self.lbl_file_status.configure(text=f"📁 Biriktirilgan hujjat: {os.path.basename(dest)}", text_color="#1F497D")
            messagebox.showinfo("Fayl tanlandi", "Hujjat biriktirildi. Saqlash uchun '💾 Saqlash' tugmasini bosing.")

    def _open_attached_file(self):
        if self.attached_file_path and os.path.exists(self.attached_file_path):
            try:
                os.startfile(self.attached_file_path)
            except Exception as e:
                messagebox.showerror("Xatolik", f"Faylni ochishda xato: {str(e)}")
        else:
            messagebox.showwarning("Fayl yo'q", "Ushbu murojaatga hali hech qanday hujjat biriktirilmagan!")

    # ================= EKSPORT VA YUKLASH =================
    def _import_excel(self):
        fp = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx *.xls")])
        if fp:
            try:
                self.loader.load_from_excel(fp)
                self.show_dashboard_view()
                messagebox.showinfo("Baza yangilandi", "Yangi murojaatlar muvaffaqiyatli yuklandi!")
            except Exception as e:
                messagebox.showerror("Xatolik", f"Yuklashda xato: {str(e)}")

    def _export_excel(self):
        fp = filedialog.asksaveasfilename(defaultextension=".xlsx", initialfile="Murojaatlar_Hisoboti.xlsx")
        if fp:
            ReportGenerator.export_excel(self.loader.filtered_df, fp)
            messagebox.showinfo("Tayyor", "Mas'ul komplayens xodimlari ko'rsatilgan professional Excel saqlandi!")

    def _export_word(self):
        fp = filedialog.asksaveasfilename(defaultextension=".docx", initialfile="Rahbariyatga_Malumotnoma.docx")
        if fp:
            stats = self.loader.get_kpi_stats()
            reg_stats = self.loader.filtered_df['Viloyat'].value_counts()
            ReportGenerator.export_word_report(stats, reg_stats, fp, self.cb_period.get())
            messagebox.showinfo("Tayyor", "Rasmiy Word ma'lumotnomasi saqlandi!")

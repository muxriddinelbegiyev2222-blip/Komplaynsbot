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
        self.geometry("1380x880")
        self.minsize(1200, 750)
        ctk.set_appearance_mode("Light")
        self.configure(fg_color="#F4F7FC")

        self.view_stack = []

        self._build_top_navbar()
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(fill="both", expand=True, padx=20, pady=(0, 15))

        self.show_dashboard_view()

    def _build_top_navbar(self):
        nav = ctk.CTkFrame(self, fg_color="#1F497D", height=65, corner_radius=0)
        nav.pack(fill="x", side="top", pady=(0, 15))

        self.btn_back = ctk.CTkButton(
            nav, text="⬅ Orqaga", width=100, height=36,
            fg_color="#34495E", hover_color="#2C3E50",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._go_back
        )
        self.btn_back.pack(side="left", padx=15, pady=14)

        self.lbl_path = ctk.CTkLabel(
            nav, text="Asosiy oyna  /  Tahliliy Dashboard", 
            font=ctk.CTkFont(size=17, weight="bold"), text_color="white"
        )
        self.lbl_path.pack(side="left", padx=10, pady=14)

        btn_word = ctk.CTkButton(
            nav, text="📄 Word Ma'lumotnoma", width=150, height=36,
            fg_color="#D35400", hover_color="#B94A00", font=ctk.CTkFont(size=12, weight="bold"),
            command=self._export_word
        )
        btn_word.pack(side="right", padx=(5, 15), pady=14)

        btn_excel = ctk.CTkButton(
            nav, text="📊 Excel Jadval", width=120, height=36,
            fg_color="#27AE60", hover_color="#219150", font=ctk.CTkFont(size=12, weight="bold"),
            command=self._export_excel
        )
        btn_excel.pack(side="right", padx=5, pady=14)

        btn_import = ctk.CTkButton(
            nav, text="📥 Yangi Excel yuklash", width=150, height=36,
            fg_color="#2980B9", hover_color="#2471A3", font=ctk.CTkFont(size=12, weight="bold"),
            command=self._import_excel
        )
        btn_import.pack(side="right", padx=5, pady=14)

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

        filter_box = ctk.CTkFrame(self.container, fg_color="white", corner_radius=10)
        filter_box.pack(fill="x", pady=(0, 12), padx=5)

        ctk.CTkLabel(filter_box, text="⏳ Davr:", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=(15, 5), pady=10)
        self.cb_period = ctk.CTkComboBox(filter_box, values=["Barchasi", "Joriy hafta", "Joriy oy", "Joriy yil"], command=self._apply_filters, width=120, font=ctk.CTkFont(size=12))
        self.cb_period.set(getattr(self, 'selected_period', 'Barchasi'))
        self.cb_period.pack(side="left", padx=4, pady=10)

        ctk.CTkLabel(filter_box, text="🏢 Yoʻnalish:", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=(15, 5), pady=10)
        yonalish_options = [
            "Barchasi",
            "Kadastr agentligi markaziy apparati",
            "Kadastr agentligi hududiy boshqarmasi",
            "Davlat kadastrlari palatasi markaziy apparati",
            "Davlat kadastrlari palatasi hududiy boshqarmasi",
            "Boshqa tizim tashkiloti"
        ]
        self.cb_yonalish = ctk.CTkComboBox(filter_box, values=yonalish_options, command=self._apply_filters, width=300, font=ctk.CTkFont(size=12))
        self.cb_yonalish.set(getattr(self, 'selected_yonalish', 'Barchasi'))
        self.cb_yonalish.pack(side="left", padx=4, pady=10)

        ctk.CTkLabel(filter_box, text="📌 Toifa:", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=(15, 5), pady=10)
        self.cb_cat = ctk.CTkComboBox(filter_box, values=["Barchasi", "Korrupsiyaga oid", "Sohaviy/Umumiy"], command=self._apply_filters, width=170, font=ctk.CTkFont(size=12))
        self.cb_cat.set(getattr(self, 'selected_cat', 'Barchasi'))
        self.cb_cat.pack(side="left", padx=4, pady=10)

        btn_reset = ctk.CTkButton(filter_box, text="Tozalash", width=80, fg_color="#95A5A6", hover_color="#7F8C8D", font=ctk.CTkFont(size=12), command=self._reset_filters)
        btn_reset.pack(side="left", padx=10, pady=10)

        self.cards_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        self.cards_frame.pack(fill="x", pady=(0, 12))
        self._render_kpi_cards()

        content = ctk.CTkFrame(self.container, fg_color="transparent")
        content.pack(fill="both", expand=True)

        # Chap panel: Hududlar bo'yicha yengil progress-bar (Titramasdan tez ishlaydi)
        chart_box = ctk.CTkFrame(content, fg_color="white", corner_radius=10)
        chart_box.pack(side="left", fill="both", expand=True, padx=(0, 10))
        ctk.CTkLabel(chart_box, text="Hududlar bo'yicha murojaatlar taqsimoti", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=10)

        scroll_chart = ctk.CTkScrollableFrame(chart_box, fg_color="transparent")
        scroll_chart.pack(fill="both", expand=True, padx=15, pady=(0, 10))

        reg_stats = self.loader.filtered_df['Viloyat'].value_counts()
        max_val = reg_stats.max() if not reg_stats.empty and reg_stats.max() > 0 else 1

        for reg, count in reg_stats.items():
            row_f = ctk.CTkFrame(scroll_chart, fg_color="transparent")
            row_f.pack(fill="x", pady=5)

            ctk.CTkLabel(row_f, text=reg, width=170, anchor="w", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left")
            pb = ctk.CTkProgressBar(row_f, height=16, progress_color="#1F497D", fg_color="#E2E8F0")
            pb.set(count / max_val)
            pb.pack(side="left", fill="x", expand=True, padx=10)
            ctk.CTkLabel(row_f, text=f"{count} ta", width=60, anchor="e", font=ctk.CTkFont(size=12, weight="bold"), text_color="#1F497D").pack(side="right")

        # O'ng panel: Viloyatlar papkalari
        folder_box = ctk.CTkFrame(content, fg_color="white", corner_radius=10, width=330)
        folder_box.pack(side="right", fill="both", padx=(5, 0))
        ctk.CTkLabel(folder_box, text="📁 Viloyat bo'yicha kirish:", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=10, padx=15, anchor="w")

        scroll = ctk.CTkScrollableFrame(folder_box, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        for reg, count in reg_stats.items():
            btn = ctk.CTkButton(
                scroll, text=f"📂  {reg} ({count} ta)", anchor="w",
                fg_color="#EEF2F7", text_color="#1F497D", hover_color="#D5E1F0", height=36,
                font=ctk.CTkFont(size=12, weight="bold"),
                command=lambda r=reg: self._drill_down_region(r)
            )
            btn.pack(fill="x", pady=3)

    def _render_kpi_cards(self):
        for w in self.cards_frame.winfo_children():
            w.destroy()

        stats = self.loader.get_kpi_stats()
        cards = [
            ("JAMI MUROJAATLAR", stats['total'], "#1F497D", lambda: self.show_records_view("Barcha murojaatlar", self.loader.filtered_df)),
            ("KORRUPSIYA ALOMATI", stats['korrupsiya'], "#C0392B", lambda: self.show_records_view("Korrupsiyaga oid murojaatlar", self.loader.filtered_df[self.loader.filtered_df['Kategoriya'] == 'Korrupsiyaga oid'])),
            ("HUDUDLARDA O‘RGANISHDA", stats['organishda'], "#2980B9", lambda: self.show_records_view("O'rganishdagi murojaatlar", self.loader.filtered_df[self.loader.filtered_df['Ijro_Holati'].astype(str).str.contains("O‘rganishga yuborilgan|O'rganishda", case=False, na=False)])),
            ("NATIJASI KIRITILGAN", stats['natija_kiritilgan'], "#27AE60", lambda: self.show_records_view("Natijasi kiritilgan / Bartaraf etilgan", self.loader.filtered_df[self.loader.filtered_df['Ijro_Holati'].astype(str).str.contains("Bartaraf etildi|Ijobiy hal etildi|Intizomiy chora", case=False, na=False)])),
            ("ASOSSIZ DEB TOPILGAN", stats['asossiz'], "#7F8C8D", lambda: self.show_records_view("Asossiz deb topilgan", self.loader.filtered_df[self.loader.filtered_df['Ijro_Holati'].astype(str).str.contains("Asossiz", case=False, na=False)]))
        ]

        for i, (title, val, color, cmd) in enumerate(cards):
            card = ctk.CTkFrame(self.cards_frame, fg_color=color, corner_radius=10)
            card.grid(row=0, column=i, padx=4, sticky="nsew")
            self.cards_frame.grid_columnconfigure(i, weight=1)

            ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=11, weight="bold"), text_color="#E0E6ED").pack(pady=(10, 2))
            ctk.CTkLabel(card, text=str(val), font=ctk.CTkFont(size=26, weight="bold"), text_color="white").pack(pady=(0, 4))
            ctk.CTkButton(card, text="Ochish ➔", width=85, height=24, fg_color="transparent", border_width=1, border_color="white", font=ctk.CTkFont(size=11), command=cmd).pack(pady=(0, 10))

    def _apply_filters(self, _=None):
        self.selected_period = self.cb_period.get()
        self.selected_yonalish = self.cb_yonalish.get()
        self.selected_cat = self.cb_cat.get()

        self.loader.filter_data(
            period=self.selected_period,
            yonalish=self.selected_yonalish,
            category=self.selected_cat
        )
        self.show_dashboard_view()

    def _reset_filters(self):
        self.selected_period = "Barchasi"
        self.selected_yonalish = "Barchasi"
        self.selected_cat = "Barchasi"
        self.loader.filter_data("Barchasi", "Barchasi", "Barchasi")
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

        main_box = ctk.CTkFrame(self.container, fg_color="white", corner_radius=10)
        main_box.pack(fill="both", expand=True)

        top_bar = ctk.CTkFrame(main_box, fg_color="transparent")
        top_bar.pack(fill="x", padx=15, pady=12)

        ctk.CTkLabel(top_bar, text="🔍 Tezkor qidiruv:", font=ctk.CTkFont(size=13, weight="bold")).pack(side="left", padx=(0, 5))
        entry_search = ctk.CTkEntry(top_bar, placeholder_text="F.I.Sh, Telefon, Tuman yoki Kalit so'z...", width=340, font=ctk.CTkFont(size=13))
        entry_search.pack(side="left", padx=5)

        lbl_count = ctk.CTkLabel(top_bar, text=f"Jami: {len(data_df)} ta", font=ctk.CTkFont(size=14, weight="bold"), text_color="#1F497D")
        lbl_count.pack(side="right", padx=10)

        tree_frame = ctk.CTkFrame(main_box, fg_color="transparent")
        tree_frame.pack(fill="both", expand=True, padx=15, pady=(0, 10))

        cols = ("#", "sana", "fish", "telefon", "viloyat", "tuman", "yonalish", "ijro")
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", rowheight=28, font=("Calibri", 11))
        style.configure("Treeview.Heading", font=("Calibri", 11, "bold"), background="#E4E9F2")

        tree = ttk.Treeview(tree_frame, columns=cols, show="headings", selectmode="browse")
        tree.heading("#", text="#")
        tree.heading("sana", text="Sana")
        tree.heading("fish", text="F.I.Sh.")
        tree.heading("telefon", text="Telefon")
        tree.heading("viloyat", text="Viloyat")
        tree.heading("tuman", text="Tuman")
        tree.heading("yonalish", text="Yoʻnalish")
        tree.heading("ijro", text="Holati")

        tree.column("#", width=45, anchor="center")
        tree.column("sana", width=125, anchor="center")
        tree.column("fish", width=160)
        tree.column("telefon", width=110, anchor="center")
        tree.column("viloyat", width=120)
        tree.column("tuman", width=120)
        tree.column("yonalish", width=200)
        tree.column("ijro", width=150, anchor="center")

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
                    r.get('Aniq_Yonalish', r.get('Yoʻnalish')), r.get('Ijro_Holati', 'O‘rganishga yuborilgan')
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
                    data_df['Murojaat matni'].astype(str).str.lower().str.contains(q)
                populate(data_df[m])

        entry_search.bind("<KeyRelease>", on_search)

        def on_open(event):
            sel = tree.selection()
            if not sel: return
            item_vals = tree.item(sel[0], "values")
            m_id = int(item_vals[0])
            self.show_detail_view(m_id, lambda: self.show_records_view(title, data_df))

        tree.bind("<Double-1>", on_open)
        ctk.CTkLabel(main_box, text="💡 Murojaat ichiga kirish, o'rganish natijasini va hujjatni kiritish uchun qator ustiga ikki marta bosing.", font=ctk.CTkFont(size=12, slant="italic")).pack(pady=5)

    # ================= 3-POG'ONA: KARTOCHKA (KATTA OYNA VA FAYL BIRIKTIRISH) =================
    def show_detail_view(self, m_id, return_callback):
        self.view_stack.append(return_callback)
        self.btn_back.configure(state="normal")
        self.lbl_path.configure(text=f"Asosiy oyna  /  Murojaatlar  /  Kartochka #{m_id}")
        self._clear_container()

        rec = self.loader.df[self.loader.df['#'] == m_id].iloc[0]

        # Butun kartochkani o'rab turuvchi Scrollable Frame
        main_scroll = ctk.CTkScrollableFrame(self.container, fg_color="white", corner_radius=10)
        main_scroll.pack(fill="both", expand=True, padx=5, pady=5)

        # 1. Fuqaro haqida ma'lumot bloki (Katta va tiniq)
        info_top = ctk.CTkFrame(main_scroll, fg_color="#F8FAFC", corner_radius=8)
        info_top.pack(fill="x", padx=15, pady=(15, 10))

        txt_info = f"👤 Fuqaro: {rec.get('F.I.Sh.')}   |   📞 Tel: {rec.get('Telefon')}   |   📍 Hudud: {rec.get('Viloyat')}, {rec.get('Tuman')}\n" \
                   f"🏢 Yo'nalish: {rec.get('Yoʻnalish')}\n🕒 Kelib tushgan sana: {rec.get('Yaratilgan sana')}"
        ctk.CTkLabel(info_top, text=txt_info, justify="left", font=ctk.CTkFont(size=13, weight="bold")).pack(padx=15, pady=10, anchor="w")

        # 2. MUROJAAT MATNI (Katta va qulay oyna - 14pt shrift)
        ctk.CTkLabel(main_scroll, text="📝 Murojaat matni (to‘liq shaklda):", font=ctk.CTkFont(size=14, weight="bold"), text_color="#1F497D").pack(padx=15, anchor="w")
        tb_m = ctk.CTkTextbox(main_scroll, height=220, wrap="word", font=ctk.CTkFont(size=13))
        tb_m.insert("1.0", str(rec.get('Murojaat matni', '')))
        tb_m.configure(state="disabled")
        tb_m.pack(fill="x", padx=15, pady=(4, 10))

        # 3. Yuborilgan rasmiy javob
        ctk.CTkLabel(main_scroll, text="✉️ Bot orqali fuqaroga yuborilgan rasmiy javob:", font=ctk.CTkFont(size=13, weight="bold")).pack(padx=15, anchor="w")
        tb_j = ctk.CTkTextbox(main_scroll, height=75, wrap="word", font=ctk.CTkFont(size=12))
        rasmiy_javob_shablon = "Ассалому алайкум, ҳурматли фуқаро. Сизнинг мурожаатингиз бўйича ҳолатларга аниқлик киритиш мақсадида Коррупцияга қарши курашиш бўлими ходимлари телефон рақамингиз орқали Сиз билан боғланади."
        tb_j.insert("1.0", rasmiy_javob_shablon)
        tb_j.configure(state="disabled")
        tb_j.pack(fill="x", padx=15, pady=(4, 12))

        # 4. KOMPLAYENS NAZORAT VA O‘RGANISH NATIJASI (CRM qismi)
        action_frame = ctk.CTkFrame(main_scroll, fg_color="#EEF2F7", corner_radius=8)
        action_frame.pack(fill="x", padx=15, pady=(5, 15))

        ctk.CTkLabel(action_frame, text="⚙️ KOMPLAYENS NAZORAT VA O‘RGANISH NATIJASI:", font=ctk.CTkFont(size=13, weight="bold"), text_color="#1F497D").pack(padx=15, pady=(10, 4), anchor="w")

        # Holat tanlash
        row_status = ctk.CTkFrame(action_frame, fg_color="transparent")
        row_status.pack(fill="x", padx=15, pady=4)

        ctk.CTkLabel(row_status, text="Murojaat ijro holati:", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=(0, 10))
        cb_status = ctk.CTkComboBox(row_status, values=["O‘rganishga yuborilgan", "Bartaraf etildi", "Ijobiy hal etildi", "Intizomiy chora ko‘rildi", "Asossiz deb topildi"], width=250, font=ctk.CTkFont(size=12))
        cb_status.set(str(rec.get('Ijro_Holati', 'O‘rganishga yuborilgan')))
        cb_status.pack(side="left")

        # Natija matni
        ctk.CTkLabel(action_frame, text="O‘rganish natijasi (Hududiy komplayens xulosasi, ko'rilgan chora, buyruq raqami):", font=ctk.CTkFont(size=12, weight="bold")).pack(padx=15, pady=(6, 2), anchor="w")
        tb_natija = ctk.CTkTextbox(action_frame, height=90, wrap="word", font=ctk.CTkFont(size=12))
        tb_natija.insert("1.0", str(rec.get('Organish_Natijasi', '')))
        tb_natija.pack(fill="x", padx=15, pady=(0, 8))

        # 5. FAYL BIRIKTIRISH (PDF / Rasm / Word)
        self.attached_file_path = str(rec.get('Biriktirilgan_Fayl', ''))

        file_box = ctk.CTkFrame(action_frame, fg_color="white", corner_radius=6)
        file_box.pack(fill="x", padx=15, pady=(0, 12))

        self.lbl_file_status = ctk.CTkLabel(
            file_box, 
            text=f"📁 Biriktirilgan hujjat: {os.path.basename(self.attached_file_path)}" if self.attached_file_path else "📁 Biriktirilgan hujjat: Yo'q",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#1F497D" if self.attached_file_path else "#7F8C8D"
        )
        self.lbl_file_status.pack(side="left", padx=12, pady=8)

        btn_attach = ctk.CTkButton(
            file_box, text="📎 Hujjat yuklash (PDF/Rasm)", width=170, height=28,
            fg_color="#2980B9", hover_color="#2471A3", font=ctk.CTkFont(size=11, weight="bold"),
            command=self._attach_file
        )
        btn_attach.pack(side="right", padx=10, pady=6)

        btn_open_file = ctk.CTkButton(
            file_box, text="👁 Ko'rish", width=80, height=28,
            fg_color="#34495E", hover_color="#2C3E50", font=ctk.CTkFont(size=11, weight="bold"),
            command=self._open_attached_file
        )
        btn_open_file.pack(side="right", padx=5, pady=6)

        # Saqlash tugmasi
        def save_changes():
            st = cb_status.get()
            nat = tb_natija.get("1.0", "end-1c")
            self.loader.db.update_murojaat_ijro(m_id, st, nat, self.attached_file_path)
            self.loader.refresh_data()
            messagebox.showinfo("Saqlandi", f"#{m_id} sonli murojaat bo‘yicha o‘rganish natijasi va hujjat saqlandi!")

        btn_save = ctk.CTkButton(action_frame, text="💾 Saqlash", fg_color="#27AE60", hover_color="#219150", width=140, height=34, font=ctk.CTkFont(size=13, weight="bold"), command=save_changes)
        btn_save.pack(pady=(0, 10))

    def _attach_file(self):
        fp = filedialog.askopenfilename(
            title="O'rganish natijasiga oid faylni tanlang (PDF, Rasm, Word)",
            filetypes=[("Hujjatlar va Rasmlar", "*.pdf *.png *.jpg *.jpeg *.docx *.doc *.xlsx")]
        )
        if fp:
            # Faylni data/attachments papkasiga nusxalab saqlaymiz
            attach_dir = os.path.join("data", "attachments")
            os.makedirs(attach_dir, exist_ok=True)
            
            dest = os.path.join(attach_dir, os.path.basename(fp))
            shutil.copy2(fp, dest)
            self.attached_file_path = dest
            self.lbl_file_status.configure(text=f"📁 Biriktirilgan hujjat: {os.path.basename(dest)}", text_color="#1F497D")
            messagebox.showinfo("Fayl tanlandi", f"Hujjat biriktirildi. Saqlash uchun '💾 Saqlash' tugmasini bosing.")

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
                messagebox.showinfo("Baza yangilandi", "Yangi murojaatlar muvaffaqiyatli yuklandi (test xabarlar filtrlandi)!")
            except Exception as e:
                messagebox.showerror("Xatolik", f"Yuklashda xato: {str(e)}")

    def _export_excel(self):
        fp = filedialog.asksaveasfilename(defaultextension=".xlsx", initialfile="Murojaatlar_Hisoboti.xlsx")
        if fp:
            ReportGenerator.export_excel(self.loader.filtered_df, fp)
            messagebox.showinfo("Tayyor", "Professional Excel fayl saqlandi!")

    def _export_word(self):
        fp = filedialog.asksaveasfilename(defaultextension=".docx", initialfile="Rahbariyatga_Malumotnoma.docx")
        if fp:
            stats = self.loader.get_kpi_stats()
            reg_stats = self.loader.filtered_df['Viloyat'].value_counts()
            ReportGenerator.export_word_report(stats, reg_stats, fp, self.cb_period.get())
            messagebox.showinfo("Tayyor", "Rasmiy Word ma'lumotnomasi saqlandi!")

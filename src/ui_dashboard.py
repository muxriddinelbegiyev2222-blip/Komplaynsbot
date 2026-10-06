import customtkinter as ctk
from tkinter import ttk, filedialog, messagebox
import os
import shutil
import urllib.parse
import webbrowser
from PIL import Image, ImageDraw
from src.report_generator import ReportGenerator

def ensure_app_logo():
    os.makedirs("assets", exist_ok=True)
    logo_path = os.path.join("assets", "compliance_logo.png")
    if not os.path.exists(logo_path):
        img = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.polygon([(64, 6), (118, 26), (118, 76), (64, 122), (10, 76), (10, 26)], fill="#0F2537", outline="#D4AF37", width=4)
        draw.polygon([(64, 16), (108, 32), (108, 72), (64, 110), (20, 72), (20, 32)], fill="#16324F")
        draw.line([(64, 38), (64, 92)], fill="#D4AF37", width=5)
        draw.line([(40, 48), (88, 48)], fill="#D4AF37", width=4)
        draw.arc([(32, 48), (48, 64)], 0, 180, fill="#FFFFFF", width=3)
        draw.arc([(80, 48), (96, 64)], 0, 180, fill="#FFFFFF", width=3)
        img.save(logo_path, format="PNG")
    return logo_path

class DashboardApp(ctk.CTk):
    def __init__(self, data_loader):
        super().__init__()
        self.loader = data_loader

        self.title("KADASTR AGENTLIGI — KORRUPSIYAGA QARSHI KOMPLAYENS MONITORING TIZIMI")
        self.geometry("1440x920")
        self.minsize(1220, 740)
        ctk.set_appearance_mode("Light")
        self.configure(fg_color="#ECEFF4")

        try:
            self.logo_path = ensure_app_logo()
            logo_img = Image.open(self.logo_path)
            self._icon_photo = ctk.CTkImage(logo_img, size=(32, 32))
        except Exception:
            self._icon_photo = None

        self.view_stack = []

        self._build_top_navbar()
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(fill="both", expand=True, padx=16, pady=(0, 12))

        self.show_dashboard_view()

    def _build_top_navbar(self):
        nav = ctk.CTkFrame(self, fg_color="#0F2537", height=65, corner_radius=0)
        nav.pack(fill="x", side="top", pady=(0, 10))

        if self._icon_photo:
            lbl_logo = ctk.CTkLabel(nav, image=self._icon_photo, text="")
            lbl_logo.pack(side="left", padx=(15, 5), pady=14)

        self.btn_back = ctk.CTkButton(
            nav, text="⬅ Orqaga", width=95, height=34,
            fg_color="#1E3A56", hover_color="#2A4D73",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._go_back
        )
        self.btn_back.pack(side="left", padx=8, pady=15)

        self.lbl_path = ctk.CTkLabel(
            nav, text="Asosiy oyna  /  Tahliliy Dashboard", 
            font=ctk.CTkFont(size=16, weight="bold"), text_color="#F8FAFC"
        )
        self.lbl_path.pack(side="left", padx=10, pady=15)

        # Xodimlar ma'lumotnomasi va eksportlar
        btn_word = ctk.CTkButton(
            nav, text="📄 Word Ma'lumotnoma", width=145, height=34,
            fg_color="#8B3A2B", hover_color="#A94442", font=ctk.CTkFont(size=11, weight="bold"),
            command=self._export_word
        )
        btn_word.pack(side="right", padx=(4, 15), pady=15)

        btn_excel = ctk.CTkButton(
            nav, text="📊 Excel Jadval", width=115, height=34,
            fg_color="#1E6B47", hover_color="#258357", font=ctk.CTkFont(size=11, weight="bold"),
            command=self._export_excel
        )
        btn_excel.pack(side="right", padx=4, pady=15)

        btn_xodimlar = ctk.CTkButton(
            nav, text="👥 Hududiy xodimlar", width=140, height=34,
            fg_color="#4B3869", hover_color="#5E4784", font=ctk.CTkFont(size=11, weight="bold"),
            command=self.show_xodimlar_view
        )
        btn_xodimlar.pack(side="right", padx=4, pady=15)

        btn_import = ctk.CTkButton(
            nav, text="📥 Yangi Excel yuklash", width=145, height=34,
            fg_color="#1F4E79", hover_color="#286090", font=ctk.CTkFont(size=11, weight="bold"),
            command=self._import_excel
        )
        btn_import.pack(side="right", padx=4, pady=15)

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
        filter_box = ctk.CTkFrame(self.container, fg_color="#FFFFFF", corner_radius=6, border_width=1, border_color="#CBD5E1")
        filter_box.pack(fill="x", pady=(0, 8), padx=2)

        ctk.CTkLabel(filter_box, text="🔍 Qidiruv (Poisk):", font=ctk.CTkFont(size=11, weight="bold"), text_color="#0F2537").pack(side="left", padx=(12, 4), pady=7)
        self.entry_dash_search = ctk.CTkEntry(filter_box, placeholder_text="F.I.Sh, telefon, tuman, kalit so'z...", width=230, font=ctk.CTkFont(size=11))
        self.entry_dash_search.pack(side="left", padx=4, pady=7)
        self.entry_dash_search.bind("<Return>", self._apply_filters)

        btn_search = ctk.CTkButton(filter_box, text="Topish", width=60, height=28, fg_color="#0F2537", hover_color="#1E3A56", font=ctk.CTkFont(size=11, weight="bold"), command=self._apply_filters)
        btn_search.pack(side="left", padx=4, pady=7)

        ctk.CTkLabel(filter_box, text="⏳ Davr / Yil:", font=ctk.CTkFont(size=11, weight="bold"), text_color="#0F2537").pack(side="left", padx=(12, 4), pady=7)
        period_values = self.loader.get_available_periods()
        self.cb_period = ctk.CTkComboBox(filter_box, values=period_values, command=self._apply_filters, width=125, font=ctk.CTkFont(size=11))
        current_selection = getattr(self, 'selected_period', 'Barchasi')
        if current_selection not in period_values:
            current_selection = 'Barchasi'
        self.cb_period.set(current_selection)
        self.cb_period.pack(side="left", padx=4, pady=7)

        ctk.CTkLabel(filter_box, text="🏢 Mas'ul organ:", font=ctk.CTkFont(size=11, weight="bold"), text_color="#0F2537").pack(side="left", padx=(12, 4), pady=7)
        masul_options = ["Barchasi", "Kadastr agentligi hududiy komplayens xodimi", "Davlat kadastrlari palatasi hududiy komplayens xodimi"]
        self.cb_masul = ctk.CTkComboBox(filter_box, values=masul_options, command=self._apply_filters, width=260, font=ctk.CTkFont(size=11))
        self.cb_masul.set(getattr(self, 'selected_masul', 'Barchasi'))
        self.cb_masul.pack(side="left", padx=4, pady=7)

        btn_reset = ctk.CTkButton(filter_box, text="Tozalash", width=65, height=28, fg_color="#64748B", hover_color="#475569", font=ctk.CTkFont(size=11), command=self._reset_filters)
        btn_reset.pack(side="left", padx=8, pady=7)

        # KPI Kartochkalari
        cards_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        cards_frame.pack(fill="x", pady=(0, 8))

        stats = self.loader.get_kpi_stats()
        cards = [
            ("JAMI MUROJAATLAR", stats['total'], "#0F2537", lambda: self.show_records_view("Barcha murojaatlar", self.loader.filtered_df)),
            ("AGENTLIKDA O‘RGANISHDA", stats['agentlik_organish'], "#1B4D7E", lambda: self.show_records_view("Agentlikda o'rganishdagi murojaatlar", self.loader.filtered_df[self.loader.filtered_df['Ijro_Holati'].astype(str).str.contains("O‘rganishga yuborilgan|O'rganishda", case=False, na=False) & self.loader.filtered_df['Masul_Komplayens'].astype(str).str.contains("agentligi", case=False, na=False)])),
            ("PALATADA O‘RGANISHDA", stats['palata_organish'], "#4B3869", lambda: self.show_records_view("Palatada o'rganishdagi murojaatlar", self.loader.filtered_df[self.loader.filtered_df['Ijro_Holati'].astype(str).str.contains("O‘rganishga yuborilgan|O'rganishda", case=False, na=False) & self.loader.filtered_df['Masul_Komplayens'].astype(str).str.contains("palata", case=False, na=False)])),
            ("O‘RGANIB CHIQILGAN", stats['natija_kiritilgan'], "#1B5E20", lambda: self.show_records_view("O'rganib chiqilganlar", self.loader.filtered_df[self.loader.filtered_df['Ijro_Holati'].astype(str).str.contains("Bartaraf etildi|Ijobiy hal etildi|Intizomiy chora|O‘rganib chiqildi", case=False, na=False)])),
            ("ASOSSIZ DEB TOPILGAN", stats['asossiz'], "#475569", lambda: self.show_records_view("Asossiz deb topilganlar", self.loader.filtered_df[self.loader.filtered_df['Ijro_Holati'].astype(str).str.contains("Asossiz", case=False, na=False)]))
        ]

        for i, (title, val, color, cmd) in enumerate(cards):
            card = ctk.CTkFrame(cards_frame, fg_color=color, corner_radius=6)
            card.grid(row=0, column=i, padx=3, sticky="nsew")
            cards_frame.grid_columnconfigure(i, weight=1)

            ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=10, weight="bold"), text_color="#E2E8F0").pack(pady=(6, 1))
            ctk.CTkLabel(card, text=str(val), font=ctk.CTkFont(size=22, weight="bold"), text_color="#FFFFFF").pack(pady=(0, 1))
            ctk.CTkButton(card, text="Ochish ➔", width=70, height=20, fg_color="transparent", border_width=1, border_color="#CBD5E1", font=ctk.CTkFont(size=9), command=cmd).pack(pady=(0, 6))

        # Viloyatlar jadvali (O'rtadagi asosiy jadval)
        table_container = ctk.CTkFrame(self.container, fg_color="#FFFFFF", corner_radius=6, border_width=1, border_color="#CBD5E1")
        table_container.pack(fill="both", expand=True, padx=2, pady=(0, 8))

        lbl_sec = ctk.CTkLabel(table_container, text="Viloyatlar kesimida murojaatlar nazorati (Kirish uchun viloyat ustiga 2 marta bosing):", font=ctk.CTkFont(size=12, weight="bold"), text_color="#0F2537")
        lbl_sec.pack(anchor="w", padx=12, pady=(6, 3))

        table_frame = ctk.CTkFrame(table_container, fg_color="transparent")
        table_frame.pack(fill="both", expand=True, padx=12, pady=(0, 8))

        cols = ("viloyat", "jami", "agentlik_org", "palata_org", "hal_etilgan", "asossiz")
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Dash.Treeview", rowheight=27, font=("Calibri", 11), bordercolor="#94A3B8", borderwidth=1)
        style.configure("Dash.Treeview.Heading", font=("Calibri", 11, "bold"), background="#0F2537", foreground="#FFFFFF", bordercolor="#475569", borderwidth=1)

        self.dash_tree = ttk.Treeview(table_frame, columns=cols, show="headings", style="Dash.Treeview", selectmode="browse")
        self.dash_tree.heading("viloyat", text="Hudud nomi (Viloyat)")
        self.dash_tree.heading("jami", text="Jami murojaat")
        self.dash_tree.heading("agentlik_org", text="Agentlikda o‘rganishda")
        self.dash_tree.heading("palata_org", text="Palatada o‘rganishda")
        self.dash_tree.heading("hal_etilgan", text="O‘rganib chiqilgan")
        self.dash_tree.heading("asossiz", text="Asossiz deb topilgan")

        self.dash_tree.column("viloyat", width=250)
        self.dash_tree.column("jami", width=110, anchor="center")
        self.dash_tree.column("agentlik_org", width=160, anchor="center")
        self.dash_tree.column("palata_org", width=160, anchor="center")
        self.dash_tree.column("hal_etilgan", width=150, anchor="center")
        self.dash_tree.column("asossiz", width=140, anchor="center")

        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.dash_tree.yview)
        self.dash_tree.configure(yscrollcommand=vsb.set)
        self.dash_tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        self.dash_tree.tag_configure('odd', background='#F1F5F9')
        self.dash_tree.tag_configure('even', background='#FFFFFF')

        f_df = self.loader.filtered_df
        reg_groups = f_df.groupby('Viloyat') if not f_df.empty else []

        for idx, (reg, group) in enumerate(reg_groups):
            c_tot = len(group)
            is_org = group['Ijro_Holati'].astype(str).str.contains("O‘rganishga yuborilgan|O'rganishda", case=False, na=False)
            c_ag = len(group[is_org & group['Masul_Komplayens'].astype(str).str.contains("agentligi", case=False, na=False)])
            c_pa = len(group[is_org & group['Masul_Komplayens'].astype(str).str.contains("palata", case=False, na=False)])
            c_hal = len(group[group['Ijro_Holati'].astype(str).str.contains("Bartaraf etildi|Ijobiy hal etildi|Intizomiy chora|O‘rganib chiqildi", case=False, na=False)])
            c_as = len(group[group['Ijro_Holati'].astype(str).str.contains("Asossiz", case=False, na=False)])

            tag = 'even' if idx % 2 == 0 else 'odd'
            self.dash_tree.insert("", "end", values=(reg, f"{c_tot} ta", f"{c_ag} ta", f"{c_pa} ta", f"{c_hal} ta", f"{c_as} ta"), tags=(tag,))

        def on_region_open(event):
            sel = self.dash_tree.selection()
            if not sel: return
            reg_name = self.dash_tree.item(sel[0], "values")[0]
            self._drill_down_region(reg_name)

        self.dash_tree.bind("<Double-1>", on_region_open)

        # ================= PASTKI 4 TA ANALITIK BLOK (SKRINSHOTDAGI BO'SH JOY) =================
        bottom_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        bottom_frame.pack(fill="x", pady=(0, 2))

        # 1-BLOK: SLA / Ijro muddati
        b1 = ctk.CTkFrame(bottom_frame, fg_color="#FFFFFF", corner_radius=6, border_width=1, border_color="#E2E8F0")
        b1.grid(row=0, column=0, padx=3, sticky="nsew")
        ctk.CTkLabel(b1, text="⏱ IJRO MUDDATI NAZORATI", font=ctk.CTkFont(size=11, weight="bold"), text_color="#0F2537").pack(pady=(6, 2))
        ctk.CTkLabel(b1, text=f"🔴 Muddati o‘tgan (>15 kun): {stats['muddati_otgan_15']} ta", font=ctk.CTkFont(size=12, weight="bold"), text_color="#C0392B").pack(anchor="w", padx=12, pady=1)
        ctk.CTkLabel(b1, text=f"🟡 Ogohlantirish (10-15 kun): {stats['ogohlantirish_10']} ta", font=ctk.CTkFont(size=11, weight="bold"), text_color="#D35400").pack(anchor="w", padx=12, pady=1)
        ctk.CTkLabel(b1, text="Qonuniy muddat: 15 kalendar kun", font=ctk.CTkFont(size=10, slant="italic"), text_color="#7F8C8D").pack(anchor="w", padx=12, pady=(1, 6))

        # 2-BLOK: Takroriy murojaatlar
        b2 = ctk.CTkFrame(bottom_frame, fg_color="#FFFFFF", corner_radius=6, border_width=1, border_color="#E2E8F0")
        b2.grid(row=0, column=1, padx=3, sticky="nsew")
        ctk.CTkLabel(b2, text="🔄 TAKRORIY MUROJAATLAR", font=ctk.CTkFont(size=11, weight="bold"), text_color="#0F2537").pack(pady=(6, 2))
        ctk.CTkLabel(b2, text=f"Takroriy kelganlar: {stats['takroriy_soni']} ta", font=ctk.CTkFont(size=13, weight="bold"), text_color="#2980B9").pack(pady=1)
        ctk.CTkLabel(b2, text="Bitta fuqaro/raqamdan qayta arizalar", font=ctk.CTkFont(size=10, slant="italic"), text_color="#7F8C8D").pack(pady=(1, 6))

        # 3-BLOK: Ko'rilgan choralar hisobi
        b3 = ctk.CTkFrame(bottom_frame, fg_color="#FFFFFF", corner_radius=6, border_width=1, border_color="#E2E8F0")
        b3.grid(row=0, column=2, padx=3, sticky="nsew")
        ctk.CTkLabel(b3, text="⚖️ INTIZOMIY CHORALAR", font=ctk.CTkFont(size=11, weight="bold"), text_color="#0F2537").pack(pady=(6, 2))
        ctk.CTkLabel(b3, text=f"Qo‘llanilgan choralar: {stats['chora_krilgan_soni']} ta", font=ctk.CTkFont(size=13, weight="bold"), text_color="#27AE60").pack(pady=1)
        ctk.CTkLabel(b3, text="Xayfsan, jarima, lavozimdan ozod va h.k.", font=ctk.CTkFont(size=10, slant="italic"), text_color="#7F8C8D").pack(pady=(1, 6))

        # 4-BLOK: Kvartal (Choraklar)
        b4 = ctk.CTkFrame(bottom_frame, fg_color="#FFFFFF", corner_radius=6, border_width=1, border_color="#E2E8F0")
        b4.grid(row=0, column=3, padx=3, sticky="nsew")
        ctk.CTkLabel(b4, text="📅 CHORAKLAR TAHLILI (KVARTAL)", font=ctk.CTkFont(size=11, weight="bold"), text_color="#0F2537").pack(pady=(6, 2))
        q = stats['chorak_taqsimot']
        ctk.CTkLabel(b4, text=f"I-ch: {q['I']} | II-ch: {q['II']} | III-ch: {q['III']} | IV-ch: {q['IV']}", font=ctk.CTkFont(size=12, weight="bold"), text_color="#1F4E79").pack(pady=1)
        ctk.CTkLabel(b4, text="Yil davomidagi davriy dinamika", font=ctk.CTkFont(size=10, slant="italic"), text_color="#7F8C8D").pack(pady=(1, 6))

        for col_idx in range(4):
            bottom_frame.grid_columnconfigure(col_idx, weight=1)

    def _apply_filters(self, _=None):
        self.selected_period = self.cb_period.get()
        self.selected_masul = self.cb_masul.get()
        search_txt = self.entry_dash_search.get().strip() if hasattr(self, 'entry_dash_search') else ""
        self.loader.filter_data(period=self.selected_period, masul=self.selected_masul, search_query=search_txt)
        self.show_dashboard_view()

    def _reset_filters(self):
        self.selected_period = "Barchasi"
        self.selected_masul = "Barchasi"
        if hasattr(self, 'entry_dash_search'):
            self.entry_dash_search.delete(0, 'end')
        self.loader.filter_data("Barchasi", "Barchasi", "")
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

        main_box = ctk.CTkFrame(self.container, fg_color="#FFFFFF", corner_radius=6, border_width=1, border_color="#CBD5E1")
        main_box.pack(fill="both", expand=True)

        top_bar = ctk.CTkFrame(main_box, fg_color="transparent")
        top_bar.pack(fill="x", padx=15, pady=8)

        ctk.CTkLabel(top_bar, text="🔍 Tezkor qidiruv:", font=ctk.CTkFont(size=12, weight="bold"), text_color="#0F2537").pack(side="left", padx=(0, 5))
        entry_search = ctk.CTkEntry(top_bar, placeholder_text="F.I.Sh, telefon, tuman, matn kalit so'zi...", width=320, font=ctk.CTkFont(size=12))
        entry_search.pack(side="left", padx=5)

        lbl_count = ctk.CTkLabel(top_bar, text=f"Jami: {len(data_df)} ta", font=ctk.CTkFont(size=13, weight="bold"), text_color="#0F2537")
        lbl_count.pack(side="right", padx=10)

        tree_frame = ctk.CTkFrame(main_box, fg_color="transparent")
        tree_frame.pack(fill="both", expand=True, padx=15, pady=(0, 6))

        cols = ("#", "sana", "fish", "telefon", "viloyat", "tuman", "masul", "ijro")
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Rec.Treeview", rowheight=28, font=("Calibri", 11), bordercolor="#94A3B8", borderwidth=1)
        style.configure("Rec.Treeview.Heading", font=("Calibri", 11, "bold"), background="#0F2537", foreground="#FFFFFF", bordercolor="#475569", borderwidth=1)

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
        tree.column("fish", width=160)
        tree.column("telefon", width=110, anchor="center")
        tree.column("viloyat", width=120)
        tree.column("tuman", width=120)
        tree.column("masul", width=250)
        tree.column("ijro", width=140, anchor="center")

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        tree.tag_configure('odd', background='#F1F5F9')
        tree.tag_configure('even', background='#FFFFFF')

        def populate(df_to_show):
            tree.delete(*tree.get_children())
            for idx, (_, r) in enumerate(df_to_show.iterrows()):
                tag = 'even' if idx % 2 == 0 else 'odd'
                tree.insert("", "end", values=(
                    r.get('#'), str(r.get('Yaratilgan sana'))[:16], r.get('F.I.Sh.'),
                    r.get('Telefon'), r.get('Viloyat'), r.get('Tuman'),
                    r.get('Masul_Komplayens', 'Kadastr agentligi hududiy komplayens xodimi'), r.get('Ijro_Holati', 'O‘rganishga yuborilgan')
                ), tags=(tag,))

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
        ctk.CTkLabel(main_box, text="💡 Murojaat ichiga kirish, o'rganish natijasi, hujjat va Telegramga yo'naltirish uchun qator ustiga ikki marta bosing.", font=ctk.CTkFont(size=11, slant="italic")).pack(pady=4)

    # ================= 3-POG'ONA: KARTOCHKA VA TELEGRAM =================
    def show_detail_view(self, m_id, return_callback):
        self.view_stack.append(return_callback)
        self.btn_back.configure(state="normal")
        self.lbl_path.configure(text=f"Asosiy oyna  /  Murojaatlar  /  Kartochka #{m_id}")
        self._clear_container()

        rec = self.loader.df[self.loader.df['#'] == m_id].iloc[0]

        main_scroll = ctk.CTkScrollableFrame(self.container, fg_color="#FFFFFF", corner_radius=6, border_width=1, border_color="#CBD5E1")
        main_scroll.pack(fill="both", expand=True, padx=4, pady=4)

        info_top = ctk.CTkFrame(main_scroll, fg_color="#F1F5F9", corner_radius=6, border_width=1, border_color="#CBD5E1")
        info_top.pack(fill="x", padx=15, pady=(10, 6))

        txt_info = f"👤 Fuqaro: {rec.get('F.I.Sh.')}   |   📞 Tel: {rec.get('Telefon')}   |   📍 Hudud: {rec.get('Viloyat')}, {rec.get('Tuman')}\n" \
                   f"🏢 Yo'nalish: {rec.get('Yoʻnalish')}\n🕒 Kelib tushgan sana: {rec.get('Yaratilgan sana')}"
        ctk.CTkLabel(info_top, text=txt_info, justify="left", font=ctk.CTkFont(size=13, weight="bold"), text_color="#0F2537").pack(padx=15, pady=8, anchor="w")

        ctk.CTkLabel(main_scroll, text="📝 Murojaat matni (to‘liq shaklda):", font=ctk.CTkFont(size=13, weight="bold"), text_color="#0F2537").pack(padx=15, anchor="w")
        tb_m = ctk.CTkTextbox(main_scroll, height=180, wrap="word", font=ctk.CTkFont(size=13))
        tb_m.insert("1.0", str(rec.get('Murojaat matni', '')))
        tb_m.configure(state="disabled")
        tb_m.pack(fill="x", padx=15, pady=(4, 8))

        ctk.CTkLabel(main_scroll, text="✉️ Bot orqali fuqaroga yuborilgan rasmiy javob:", font=ctk.CTkFont(size=12, weight="bold"), text_color="#0F2537").pack(padx=15, anchor="w")
        tb_j = ctk.CTkTextbox(main_scroll, height=55, wrap="word", font=ctk.CTkFont(size=12))
        rasmiy_javob_shablon = "Ассалому алайкум, ҳурматли фуқаро. Сизнинг мурожаатингиз бўйича ҳолатларга аниқлик киритиш мақсадида Коррупцияга қарши курашиш бўлими ходимлари телефон рақамингиз орқали Сиз билан боғланади."
        tb_j.insert("1.0", rasmiy_javob_shablon)
        tb_j.configure(state="disabled")
        tb_j.pack(fill="x", padx=15, pady=(4, 8))

        # Komplayens nazorat bo'limi
        action_frame = ctk.CTkFrame(main_scroll, fg_color="#F8FAFC", corner_radius=6, border_width=1, border_color="#CBD5E1")
        action_frame.pack(fill="x", padx=15, pady=(4, 10))

        ctk.CTkLabel(action_frame, text="⚙️ KOMPLAYENS NAZORAT, MAS’UL TAYINLASH VA O‘RGANISH NATIJASI:", font=ctk.CTkFont(size=12, weight="bold"), text_color="#0F2537").pack(padx=15, pady=(6, 2), anchor="w")

        # 1-qator: Mas'ul organ va TELEGRAM TUGMASI
        row_masul = ctk.CTkFrame(action_frame, fg_color="transparent")
        row_masul.pack(fill="x", padx=15, pady=3)

        ctk.CTkLabel(row_masul, text="O‘rganish yuklatilgan mas’ul:", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=(0, 8))
        cb_masul_item = ctk.CTkComboBox(
            row_masul, 
            values=["Kadastr agentligi hududiy komplayens xodimi", "Davlat kadastrlari palatasi hududiy komplayens xodimi"], 
            width=320, font=ctk.CTkFont(size=12)
        )
        cur_masul = str(rec.get('Masul_Komplayens', ''))
        cb_masul_item.set("Davlat kadastrlari palatasi hududiy komplayens xodimi" if 'palata' in cur_masul.lower() else "Kadastr agentligi hududiy komplayens xodimi")
        cb_masul_item.pack(side="left")

        # Telegramga yuborish tugmasi
        def send_to_telegram():
            v_name = rec.get('Viloyat')
            m_org = cb_masul_item.get()
            x_info = self.loader.db.find_xodim_for_region(v_name, m_org)
            
            tg_text = (
                f"⚡️ KORRUPSIYAGA QARSHI KOMPLAYENS MONITORING\n"
                f"📌 Murojaat #{m_id}\n"
                f"👤 Fuqaro: {rec.get('F.I.Sh.')}\n"
                f"📞 Tel: {rec.get('Telefon')}\n"
                f"📍 Hudud: {rec.get('Viloyat')}, {rec.get('Tuman')}\n"
                f"🕒 Sana: {rec.get('Yaratilgan sana')}\n\n"
                f"📝 Murojaat mazmuni:\n{str(rec.get('Murojaat matni'))[:500]}...\n\n"
                f"⚠️ O'rganish va bartaraf etish uchun qabul qiling!"
            )
            encoded = urllib.parse.quote(tg_text)
            
            u_name = str(x_info.get('username', '')).strip().replace('@', '')
            u_phone = str(x_info.get('telefon', '')).strip().replace('+', '')
            
            if u_name:
                url = f"https://t.me/{u_name}?text={encoded}"
            elif u_phone:
                url = f"https://t.me/+{u_phone}?text={encoded}"
            else:
                url = f"https://t.me/share/url?url={encoded}"
            webbrowser.open(url)

        btn_tg = ctk.CTkButton(
            row_masul, text="✈️ Xodimga Telegramdan yuborish", width=190, height=28,
            fg_color="#0088CC", hover_color="#0077B5", font=ctk.CTkFont(size=11, weight="bold"),
            command=send_to_telegram
        )
        btn_tg.pack(side="left", padx=10)

        # 2-qator: Holati va Ko'rilgan chora turi
        row_status = ctk.CTkFrame(action_frame, fg_color="transparent")
        row_status.pack(fill="x", padx=15, pady=3)

        ctk.CTkLabel(row_status, text="Murojaat holati:", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=(0, 8))
        cb_status = ctk.CTkComboBox(
            row_status, 
            values=["O‘rganishga yuborilgan", "O‘rganib chiqildi / Bartaraf etildi", "Ijobiy hal etildi", "Intizomiy chora ko‘rildi", "Asossiz deb topildi"], 
            width=240, font=ctk.CTkFont(size=12)
        )
        cb_status.set(str(rec.get('Ijro_Holati', 'O‘rganishga yuborilgan')))
        cb_status.pack(side="left", padx=(0, 15))

        ctk.CTkLabel(row_status, text="Ko‘rilgan chora turi:", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=(0, 8))
        cb_chora = ctk.CTkComboBox(
            row_status, 
            values=["Chora ko‘rilmagan", "Xayfsan e'lon qilindi", "Jarima qo‘llandi", "Lavozimidan ozod etildi", "Prokuraturaga yuborildi"], 
            width=200, font=ctk.CTkFont(size=12)
        )
        cb_chora.set(str(rec.get('Chora_Turi', 'Chora ko‘rilmagan')))
        cb_chora.pack(side="left")

        ctk.CTkLabel(action_frame, text="Hududiy komplayens xodimining o‘rganish xulosasi va ko‘rilgan choralar mazmuni:", font=ctk.CTkFont(size=12, weight="bold")).pack(padx=15, pady=(5, 1), anchor="w")
        tb_natija = ctk.CTkTextbox(action_frame, height=75, wrap="word", font=ctk.CTkFont(size=12))
        tb_natija.insert("1.0", str(rec.get('Organish_Natijasi', '')))
        tb_natija.pack(fill="x", padx=15, pady=(0, 6))

        self.attached_file_path = str(rec.get('Biriktirilgan_Fayl', ''))

        file_box = ctk.CTkFrame(action_frame, fg_color="#FFFFFF", corner_radius=5, border_width=1, border_color="#CBD5E1")
        file_box.pack(fill="x", padx=15, pady=(0, 8))

        self.lbl_file_status = ctk.CTkLabel(
            file_box, 
            text=f"📁 Biriktirilgan hujjat: {os.path.basename(self.attached_file_path)}" if self.attached_file_path else "📁 Biriktirilgan hujjat: Yo'q",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#0F2537" if self.attached_file_path else "#64748B"
        )
        self.lbl_file_status.pack(side="left", padx=12, pady=6)

        btn_attach = ctk.CTkButton(file_box, text="📎 Hujjat yuklash", width=130, height=26, fg_color="#1E3A56", hover_color="#2A4D73", font=ctk.CTkFont(size=11, weight="bold"), command=self._attach_file)
        btn_attach.pack(side="right", padx=8, pady=4)

        btn_open_file = ctk.CTkButton(file_box, text="👁 Ko'rish", width=70, height=26, fg_color="#475569", hover_color="#334155", font=ctk.CTkFont(size=11, weight="bold"), command=self._open_attached_file)
        btn_open_file.pack(side="right", padx=4, pady=4)

        def save_changes():
            st = cb_status.get()
            ms = cb_masul_item.get()
            ch = cb_chora.get()
            nat = tb_natija.get("1.0", "end-1c")
            self.loader.db.update_murojaat_ijro(m_id, st, nat, self.attached_file_path, ms, ch)
            self.loader.refresh_data()
            messagebox.showinfo("Saqlandi", f"#{m_id} sonli murojaat bo‘yicha mas’ul xodim, o‘rganish natijasi va ko'rilgan chora saqlandi!")

        btn_save = ctk.CTkButton(action_frame, text="💾 Saqlash", fg_color="#1B5E20", hover_color="#2E7D32", width=130, height=32, font=ctk.CTkFont(size=12, weight="bold"), command=save_changes)
        btn_save.pack(pady=(0, 6))

    def _attach_file(self):
        fp = filedialog.askopenfilename(title="Hujjatni tanlang", filetypes=[("Hujjatlar va Rasmlar", "*.pdf *.png *.jpg *.jpeg *.docx *.doc *.xlsx")])
        if fp:
            attach_dir = os.path.join("data", "attachments")
            os.makedirs(attach_dir, exist_ok=True)
            dest = os.path.join(attach_dir, os.path.basename(fp))
            shutil.copy2(fp, dest)
            self.attached_file_path = dest
            self.lbl_file_status.configure(text=f"📁 Biriktirilgan hujjat: {os.path.basename(dest)}", text_color="#0F2537")
            messagebox.showinfo("Fayl tanlandi", "Hujjat biriktirildi. Saqlash uchun '💾 Saqlash' tugmasini bosing.")

    def _open_attached_file(self):
        if self.attached_file_path and os.path.exists(self.attached_file_path):
            try:
                os.startfile(self.attached_file_path)
            except Exception as e:
                messagebox.showerror("Xatolik", f"Faylni ochishda xato: {str(e)}")
        else:
            messagebox.showwarning("Fayl yo'q", "Ushbu murojaatga hali hech qanday hujjat biriktirilmagan!")

    # ================= 4-POG'ONA: HUDUDIY XODIMLAR MA'LUMOTNOMASI =================
    def show_xodimlar_view(self):
        self.view_stack.append(self.show_dashboard_view)
        self.btn_back.configure(state="normal")
        self.lbl_path.configure(text="Asosiy oyna  /  Hududiy komplayens xodimlari ro‘yxati")
        self._clear_container()

        main_box = ctk.CTkFrame(self.container, fg_color="#FFFFFF", corner_radius=6, border_width=1, border_color="#CBD5E1")
        main_box.pack(fill="both", expand=True, padx=4, pady=4)

        lbl_title = ctk.CTkLabel(main_box, text="👥 Hududiy komplayens xodimlari va Telegram kontaktlari (O'zgartirish uchun qator ustiga bosing):", font=ctk.CTkFont(size=13, weight="bold"), text_color="#0F2537")
        lbl_title.pack(anchor="w", padx=15, pady=10)

        table_frame = ctk.CTkFrame(main_box, fg_color="transparent")
        table_frame.pack(fill="both", expand=True, padx=15, pady=(0, 10))

        cols = ("id", "viloyat", "tashkilot", "fish", "telefon", "telegram")
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Xod.Treeview", rowheight=30, font=("Calibri", 11), bordercolor="#94A3B8", borderwidth=1)
        style.configure("Xod.Treeview.Heading", font=("Calibri", 11, "bold"), background="#0F2537", foreground="#FFFFFF")

        tree = ttk.Treeview(table_frame, columns=cols, show="headings", style="Xod.Treeview", selectmode="browse")
        tree.heading("id", text="#")
        tree.heading("viloyat", text="Hudud (Viloyat)")
        tree.heading("tashkilot", text="Tashkilot tarmog'i")
        tree.heading("fish", text="Mas'ul xodim F.I.Sh.")
        tree.heading("telefon", text="Telefon raqami")
        tree.heading("telegram", text="Telegram Username / Raqam")

        tree.column("id", width=40, anchor="center")
        tree.column("viloyat", width=180)
        tree.column("tashkilot", width=220)
        tree.column("fish", width=200)
        tree.column("telefon", width=140, anchor="center")
        tree.column("telegram", width=180, anchor="center")

        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        def populate_x():
            tree.delete(*tree.get_children())
            x_df = self.loader.db.get_xodimlar()
            for _, r in x_df.iterrows():
                tree.insert("", "end", values=(r['id'], r['viloyat'], r['tashkilot_turi'], r['fish'], r['telefon'], r['telegram_username']))

        populate_x()

        # Tahrirlash paneli
        edit_frame = ctk.CTkFrame(main_box, fg_color="#F8FAFC", corner_radius=6, border_width=1, border_color="#CBD5E1")
        edit_frame.pack(fill="x", padx=15, pady=(0, 12))

        ctk.CTkLabel(edit_frame, text="Tanlangan xodimni tahrirlash:", font=ctk.CTkFont(size=12, weight="bold"), text_color="#0F2537").pack(anchor="w", padx=12, pady=(6, 4))

        row_inputs = ctk.CTkFrame(edit_frame, fg_color="transparent")
        row_inputs.pack(fill="x", padx=12, pady=4)

        ctk.CTkLabel(row_inputs, text="F.I.Sh:").pack(side="left", padx=4)
        e_fish = ctk.CTkEntry(row_inputs, width=200)
        e_fish.pack(side="left", padx=4)

        ctk.CTkLabel(row_inputs, text="Telefon:").pack(side="left", padx=4)
        e_tel = ctk.CTkEntry(row_inputs, width=140)
        e_tel.pack(side="left", padx=4)

        ctk.CTkLabel(row_inputs, text="Telegram (@user / raqam):").pack(side="left", padx=4)
        e_tg = ctk.CTkEntry(row_inputs, width=160)
        e_tg.pack(side="left", padx=4)

        selected_id = [None]

        def on_select(event):
            sel = tree.selection()
            if not sel: return
            vals = tree.item(sel[0], "values")
            selected_id[0] = vals[0]
            e_fish.delete(0, 'end'); e_fish.insert(0, vals[3])
            e_tel.delete(0, 'end'); e_tel.insert(0, vals[4])
            e_tg.delete(0, 'end'); e_tg.insert(0, vals[5])

        tree.bind("<<TreeviewSelect>>", on_select)

        def save_x():
            if not selected_id[0]:
                messagebox.showwarning("Diqqat", "Iltimos, avval jadvaldan biror xodimni tanlang!")
                return
            self.loader.db.save_xodim(selected_id[0], e_fish.get().strip(), e_tel.get().strip(), e_tg.get().strip())
            populate_x()
            messagebox.showinfo("Saqlandi", "Hududiy komplayens xodimi ma'lumotlari muvaffaqiyatli saqlandi!")

        btn_save_x = ctk.CTkButton(row_inputs, text="💾 Saqlash", width=100, height=28, fg_color="#1B5E20", hover_color="#2E7D32", font=ctk.CTkFont(size=11, weight="bold"), command=save_x)
        btn_save_x.pack(side="left", padx=10)

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

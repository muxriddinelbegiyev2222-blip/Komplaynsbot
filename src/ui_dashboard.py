import customtkinter as ctk
from tkinter import ttk, filedialog, messagebox
import tkinter as tk
import os
import shutil
import urllib.parse
import webbrowser
from datetime import datetime
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
        img.save(logo_path, format="PNG")
    return logo_path

class DashboardApp(ctk.CTk):
    def __init__(self, data_loader, current_role="admin"):
        super().__init__()
        self.loader = data_loader
        self.role = current_role 
        
        rol_matni = " (KUZATUVCHI REJIMI)" if self.role == "kuzatuvchi" else " (ADMINISTRATOR)"
        self.title("KADASTR AGENTLIGI — KORRUPSIYAGA QARSHI KOMPLAYENS MONITORING TIZIMI" + rol_matni)
        
        self.geometry("1440x920")
        self.minsize(1220, 740)
        ctk.set_appearance_mode("Light")
        self.configure(fg_color="#ECEFF4")
        self.view_stack = []
        
        try:
            self.logo_path = ensure_app_logo()
            self._icon_photo = ctk.CTkImage(Image.open(self.logo_path), size=(32, 32))
        except: 
            self._icon_photo = None
            
        self._build_top_navbar()
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(fill="both", expand=True, padx=16, pady=(0, 12))
        self.show_dashboard_view()

    def _build_top_navbar(self):
        nav = ctk.CTkFrame(self, fg_color="#0F2537", height=65, corner_radius=0)
        nav.pack(fill="x", side="top", pady=(0, 10))
        
        self.btn_back = ctk.CTkButton(
            nav, text="⬅ Orqaga", width=95, height=34, fg_color="#1E3A56", 
            hover_color="#2A4D73", font=ctk.CTkFont(size=12, weight="bold"), 
            command=self._go_back
        )
        self.btn_back.pack(side="left", padx=15, pady=15)
        
        self.lbl_path = ctk.CTkLabel(
            nav, text="Asosiy oyna  /  Tahliliy Dashboard", 
            font=ctk.CTkFont(size=16, weight="bold"), text_color="#F8FAFC"
        )
        self.lbl_path.pack(side="left", padx=10, pady=15)
        
        # Tugmalarni rolga qarab chiqarish
        ctk.CTkButton(
            nav, text="📄 Word Ma'lumotnoma", width=145, height=34, 
            fg_color="#8B3A2B", hover_color="#A94442", 
            font=ctk.CTkFont(size=11, weight="bold"), command=self._export_word
        ).pack(side="right", padx=4, pady=15)
        
        ctk.CTkButton(
            nav, text="📊 Excel Jadval", width=115, height=34, 
            fg_color="#1E6B47", hover_color="#258357", 
            font=ctk.CTkFont(size=11, weight="bold"), command=self._export_excel
        ).pack(side="right", padx=4, pady=15)
        
        if self.role == "admin":
            ctk.CTkButton(
                nav, text="⚙️ Sozlamalar", width=110, height=34, 
                fg_color="#7F8C8D", hover_color="#95A5A6", 
                font=ctk.CTkFont(size=11, weight="bold"), command=self.show_settings_view
            ).pack(side="right", padx=(4, 15), pady=15)
            
            ctk.CTkButton(
                nav, text="👥 Hududiy xodimlar", width=140, height=34, 
                fg_color="#4B3869", hover_color="#5E4784", 
                font=ctk.CTkFont(size=11, weight="bold"), command=self.show_xodimlar_view
            ).pack(side="right", padx=4, pady=15)
            
            ctk.CTkButton(
                nav, text="📞 + Telefon qabul", width=140, height=34, 
                fg_color="#27AE60", hover_color="#219150", 
                font=ctk.CTkFont(size=11, weight="bold"), command=self.show_add_phone_view
            ).pack(side="right", padx=4, pady=15)
            
            ctk.CTkButton(
                nav, text="📥 Yangi Excel yuklash", width=145, height=34, 
                fg_color="#1F4E79", hover_color="#286090", 
                font=ctk.CTkFont(size=11, weight="bold"), command=self._import_excel
            ).pack(side="right", padx=4, pady=15)
        else:
            # Rahbar uchun maxsus Cloud Yangilash tugmasi
            ctk.CTkButton(
                nav, text="🔄 Bazani bulutdan yangilash", width=180, height=34, 
                fg_color="#1F4E79", hover_color="#286090", 
                font=ctk.CTkFont(size=11, weight="bold"), 
                command=self._pull_from_cloud
            ).pack(side="right", padx=15, pady=15)

    def _pull_from_cloud(self):
        self.loader.db._sync_pull_from_cloud()
        self.loader.refresh_data()
        self.show_dashboard_view()
        messagebox.showinfo("Yangilandi", "Murojaatlar bulutdan olindi!")

    def _clear_container(self):
        for widget in self.container.winfo_children(): 
            widget.destroy()

    def _go_back(self):
        if self.view_stack: 
            prev_view = self.view_stack.pop()
            prev_view()
        else: 
            self.show_dashboard_view()

    # ================= DASHBOARD =================
    def show_dashboard_view(self):
        self.view_stack.clear()
        self.btn_back.configure(state="disabled")
        self.lbl_path.configure(text="Asosiy oyna  /  Tahliliy Dashboard")
        self._clear_container()

        filter_box = ctk.CTkFrame(self.container, fg_color="#FFFFFF", corner_radius=6, border_width=1, border_color="#CBD5E1")
        filter_box.pack(fill="x", pady=(0, 8), padx=2)
        
        ctk.CTkLabel(filter_box, text="🔍 Qidiruv:", font=ctk.CTkFont(size=11, weight="bold"), text_color="#0F2537").pack(side="left", padx=(10, 2), pady=7)
        
        self.entry_dash_search = ctk.CTkEntry(filter_box, placeholder_text="F.I.Sh, tel, tuman...", width=160, font=ctk.CTkFont(size=11))
        self.entry_dash_search.pack(side="left", padx=2, pady=7)
        self.entry_dash_search.bind("<Return>", self._apply_filters)
        
        ctk.CTkButton(filter_box, text="Topish", width=55, height=28, fg_color="#0F2537", hover_color="#1E3A56", font=ctk.CTkFont(size=11, weight="bold"), command=self._apply_filters).pack(side="left", padx=2, pady=7)

        ctk.CTkLabel(filter_box, text="⏳ Davr:", font=ctk.CTkFont(size=11, weight="bold"), text_color="#0F2537").pack(side="left", padx=(8, 2), pady=7)
        period_values = self.loader.get_available_periods()
        self.cb_period = ctk.CTkComboBox(filter_box, values=period_values, command=self._apply_filters, width=110, font=ctk.CTkFont(size=11))
        self.cb_period.set(getattr(self, 'selected_period', 'Barchasi'))
        self.cb_period.pack(side="left", padx=2, pady=7)

        ctk.CTkLabel(filter_box, text="📡 Manba:", font=ctk.CTkFont(size=11, weight="bold"), text_color="#0F2537").pack(side="left", padx=(8, 2), pady=7)
        self.cb_manba = ctk.CTkComboBox(filter_box, values=["Barchasi", "Telegram bot", "Ishonch telefoni (+998-71-273-19-66)"], command=self._apply_filters, width=220, font=ctk.CTkFont(size=11))
        self.cb_manba.set(getattr(self, 'selected_manba', 'Barchasi'))
        self.cb_manba.pack(side="left", padx=2, pady=7)

        ctk.CTkLabel(filter_box, text="🏢 Mas'ul:", font=ctk.CTkFont(size=11, weight="bold"), text_color="#0F2537").pack(side="left", padx=(8, 2), pady=7)
        self.cb_masul = ctk.CTkComboBox(filter_box, values=["Barchasi", "Kadastr agentligi hududiy komplayens xodimi", "Davlat kadastrlari palatasi hududiy komplayens xodimi"], command=self._apply_filters, width=240, font=ctk.CTkFont(size=11))
        self.cb_masul.set(getattr(self, 'selected_masul', 'Barchasi'))
        self.cb_masul.pack(side="left", padx=2, pady=7)

        ctk.CTkButton(filter_box, text="Tozalash", width=60, height=28, fg_color="#64748B", hover_color="#475569", font=ctk.CTkFont(size=11), command=self._reset_filters).pack(side="left", padx=6, pady=7)

        cards_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        cards_frame.pack(fill="x", pady=(0, 8))
        stats = self.loader.get_kpi_stats()
        
        cards = [
            ("JAMI MUROJAATLAR", stats['total'], "#0F2537", lambda: self.show_records_view("Barcha murojaatlar", self.loader.filtered_df)),
            ("AGENTLIKDA O‘RGANISHDA", stats['agentlik_organish'], "#1B4D7E", lambda: self.show_records_view("Agentlikda o'rganishdagi", self.loader.filtered_df[self.loader.filtered_df['Ijro_Holati'].astype(str).str.contains("O‘rganishga yuborilgan|O'rganishda", case=False, na=False) & self.loader.filtered_df['Masul_Komplayens'].astype(str).str.contains("agentligi", case=False, na=False)])),
            ("PALATADA O‘RGANISHDA", stats['palata_organish'], "#4B3869", lambda: self.show_records_view("Palatada o'rganishdagi", self.loader.filtered_df[self.loader.filtered_df['Ijro_Holati'].astype(str).str.contains("O‘rganishga yuborilgan|O'rganishda", case=False, na=False) & self.loader.filtered_df['Masul_Komplayens'].astype(str).str.contains("palata", case=False, na=False)])),
            ("O‘RGANIB CHIQILGAN", stats['natija_kiritilgan'], "#1B5E20", lambda: self.show_records_view("O'rganib chiqilganlar", self.loader.filtered_df[self.loader.filtered_df['Ijro_Holati'].astype(str).str.contains("Bartaraf etildi|Ijobiy hal etildi|Intizomiy chora|O‘rganib chiqildi|Asossiz", case=False, na=False) | self.loader.filtered_df['Chora_Turi'].astype(str).str.contains("Asossiz", case=False, na=False)])),
            ("ASOSSIZ DEB TOPILGAN", stats['asossiz'], "#7F8C8D", lambda: self.show_records_view("Asossiz deb topilganlar", self.loader.filtered_df[self.loader.filtered_df['Ijro_Holati'].astype(str).str.contains("Asossiz", case=False, na=False) | self.loader.filtered_df['Chora_Turi'].astype(str).str.contains("Asossiz", case=False, na=False)]))
        ]

        for i, (title, val, color, cmd) in enumerate(cards):
            card = ctk.CTkFrame(cards_frame, fg_color=color, corner_radius=6)
            card.grid(row=0, column=i, padx=3, sticky="nsew")
            cards_frame.grid_columnconfigure(i, weight=1)
            
            ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=10, weight="bold"), text_color="#E2E8F0").pack(pady=(6, 1))
            ctk.CTkLabel(card, text=str(val), font=ctk.CTkFont(size=22, weight="bold"), text_color="#FFFFFF").pack(pady=(0, 1))
            ctk.CTkButton(card, text="Ochish ➔", width=70, height=20, fg_color="transparent", border_width=1, border_color="#CBD5E1", font=ctk.CTkFont(size=9), command=cmd).pack(pady=(0, 6))

        table_container = ctk.CTkFrame(self.container, fg_color="#FFFFFF", corner_radius=6, border_width=1, border_color="#CBD5E1")
        table_container.pack(fill="both", expand=True, padx=2, pady=(0, 8))
        
        lbl_sec = ctk.CTkLabel(table_container, text="Viloyatlar kesimida murojaatlar nazorati:", font=ctk.CTkFont(size=12, weight="bold"), text_color="#0F2537")
        lbl_sec.pack(anchor="w", padx=12, pady=(6, 3))

        table_frame = ctk.CTkFrame(table_container, fg_color="transparent")
        table_frame.pack(fill="both", expand=True, padx=12, pady=(0, 8))
        
        cols = ("viloyat", "jami", "tg_m", "tel_m", "agentlik_org", "palata_org", "hal_etilgan", "asossiz")
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Dash.Treeview", rowheight=27, font=("Calibri", 11), bordercolor="#94A3B8", borderwidth=1)
        style.configure("Dash.Treeview.Heading", font=("Calibri", 11, "bold"), background="#0F2537", foreground="#FFFFFF")

        self.dash_tree = ttk.Treeview(table_frame, columns=cols, show="headings", style="Dash.Treeview", selectmode="browse")
        self.dash_tree.heading("viloyat", text="Hudud nomi (Viloyat)")
        self.dash_tree.heading("jami", text="Jami")
        self.dash_tree.heading("tg_m", text="Telegram bot")
        self.dash_tree.heading("tel_m", text="Ishonch telefoni")
        self.dash_tree.heading("agentlik_org", text="Agentlikda")
        self.dash_tree.heading("palata_org", text="Palatada")
        self.dash_tree.heading("hal_etilgan", text="O‘rganilgan")
        self.dash_tree.heading("asossiz", text="Asossiz deb topilgan")
        
        self.dash_tree.column("viloyat", width=200)
        self.dash_tree.column("jami", width=80, anchor="center")
        self.dash_tree.column("tg_m", width=100, anchor="center")
        self.dash_tree.column("tel_m", width=110, anchor="center")
        self.dash_tree.column("agentlik_org", width=110, anchor="center")
        self.dash_tree.column("palata_org", width=110, anchor="center")
        self.dash_tree.column("hal_etilgan", width=120, anchor="center")
        self.dash_tree.column("asossiz", width=150, anchor="center")

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
            c_tg = len(group[group['Manba'].astype(str).str.contains('Telegram', case=False, na=False)])
            c_tel = len(group[group['Manba'].astype(str).str.contains('Telefon|273-19-66', case=False, na=False)])
            is_org = group['Ijro_Holati'].astype(str).str.contains("O‘rganishga yuborilgan|O'rganishda", case=False, na=False)
            c_ag = len(group[is_org & group['Masul_Komplayens'].astype(str).str.contains("agentligi", case=False, na=False)])
            c_pa = len(group[is_org & group['Masul_Komplayens'].astype(str).str.contains("palata", case=False, na=False)])
            c_hal = len(group[group['Ijro_Holati'].astype(str).str.contains("Bartaraf etildi|Ijobiy hal etildi|Intizomiy chora|O‘rganib chiqildi|Asossiz", case=False, na=False) | group['Chora_Turi'].astype(str).str.contains("Asossiz", case=False, na=False)])
            c_as = len(group[group['Ijro_Holati'].astype(str).str.contains("Asossiz", case=False, na=False) | group['Chora_Turi'].astype(str).str.contains("Asossiz", case=False, na=False)])
            
            tag = 'even' if idx % 2 == 0 else 'odd'
            self.dash_tree.insert("", "end", values=(reg, f"{c_tot} ta", f"{c_tg} ta", f"{c_tel} ta", f"{c_ag} ta", f"{c_pa} ta", f"{c_hal} ta", f"{c_as} ta"), tags=(tag,))

        def on_region_double_click(e):
            selected = self.dash_tree.selection()
            if selected:
                reg_name = self.dash_tree.item(selected[0], 'values')[0]
                df_to_show = self.loader.filtered_df[self.loader.filtered_df['Viloyat'] == reg_name]
                self.show_records_view(f"{reg_name}", df_to_show)

        self.dash_tree.bind("<Double-1>", on_region_double_click)

        bottom_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        bottom_frame.pack(fill="x", pady=(0, 2))
        
        now_date = datetime.now()
        is_org_mask = f_df['Ijro_Holati'].astype(str).str.contains("O‘rganishga yuborilgan|O'rganishda", case=False, na=False)
        sla_d = int(stats.get('sla_days', 2))

        def open_muddati():
            if not f_df[is_org_mask].empty and 'DT' in f_df.columns:
                days_passed = (now_date - f_df[is_org_mask]['DT']).dt.days
                df_show = f_df[is_org_mask][days_passed > sla_d]
                self.show_records_view(f"Muddati o‘tgan (>{sla_d} kun)", df_show)
                
        def open_ogoh():
            if not f_df[is_org_mask].empty and 'DT' in f_df.columns:
                days_passed = (now_date - f_df[is_org_mask]['DT']).dt.days
                df_show = f_df[is_org_mask][(days_passed >= max(1, sla_d-1)) & (days_passed <= sla_d)]
                self.show_records_view("Ogohlantirish", df_show)

        b1 = ctk.CTkFrame(bottom_frame, fg_color="#FFFFFF", corner_radius=6, border_width=1, border_color="#E2E8F0")
        b1.grid(row=0, column=0, padx=3, sticky="nsew")
        ctk.CTkLabel(b1, text="⏱ IJRO MUDDATI NAZORATI", font=ctk.CTkFont(size=11, weight="bold"), text_color="#0F2537").pack(pady=(4, 2))
        ctk.CTkButton(b1, text=f"🔴 Muddati o‘tgan (>{sla_d} kun): {stats['muddati_otgan']} ta ➔", fg_color="#FDF2F2", text_color="#C0392B", hover_color="#FDE8E8", font=ctk.CTkFont(size=11, weight="bold"), height=24, anchor="w", command=open_muddati).pack(fill="x", padx=8, pady=2)
        ctk.CTkButton(b1, text=f"🟡 Ogohlantirish (1-{sla_d} kun): {stats['ogohlantirish']} ta ➔", fg_color="#FEF9E7", text_color="#D35400", hover_color="#FCF3CF", font=ctk.CTkFont(size=11, weight="bold"), height=24, anchor="w", command=open_ogoh).pack(fill="x", padx=8, pady=2)

        def open_takroriy():
            dup_idx = f_df['Toza_Telefon'].astype(str).str.strip().value_counts()
            dups = dup_idx[dup_idx > 1].index
            df_show = f_df[f_df['Toza_Telefon'].isin(dups)].sort_values(by='Toza_Telefon')
            self.show_records_view("Takroriy", df_show)

        b2 = ctk.CTkFrame(bottom_frame, fg_color="#FFFFFF", corner_radius=6, border_width=1, border_color="#E2E8F0")
        b2.grid(row=0, column=1, padx=3, sticky="nsew")
        ctk.CTkLabel(b2, text="🔄 TAKRORIY MUROJAATLAR", font=ctk.CTkFont(size=11, weight="bold"), text_color="#0F2537").pack(pady=(4, 2))
        ctk.CTkButton(b2, text=f"Takroriy kelganlar: {stats['takroriy_soni']} ta ➔", fg_color="#EBF5FB", text_color="#2980B9", hover_color="#D4E6F1", font=ctk.CTkFont(size=12, weight="bold"), height=30, command=open_takroriy).pack(fill="x", padx=12, pady=5)
        
        def open_intizomiy():
            df_show = f_df[f_df['Chora_Turi'].astype(str).str.contains("Xayfsan|Lavozimidan ozod|Prokuratura|Jarima", case=False, na=False)]
            self.show_records_view("Intizomiy", df_show)

        b3 = ctk.CTkFrame(bottom_frame, fg_color="#FFFFFF", corner_radius=6, border_width=1, border_color="#E2E8F0")
        b3.grid(row=0, column=2, padx=3, sticky="nsew")
        ctk.CTkLabel(b3, text="⚖️ INTIZOMIY CHORALAR", font=ctk.CTkFont(size=11, weight="bold"), text_color="#0F2537").pack(pady=(4, 2))
        ctk.CTkButton(b3, text=f"Ko‘rilgan choralar: {stats['chora_krilgan_soni']} ta ➔", fg_color="#EAFAF1", text_color="#27AE60", hover_color="#D5F5E3", font=ctk.CTkFont(size=12, weight="bold"), height=30, command=open_intizomiy).pack(fill="x", padx=12, pady=5)

        b4 = ctk.CTkFrame(bottom_frame, fg_color="#FFFFFF", corner_radius=6, border_width=1, border_color="#E2E8F0")
        b4.grid(row=0, column=3, padx=3, sticky="nsew")
        ctk.CTkLabel(b4, text="📅 CHORAKLAR (KVARTAL)", font=ctk.CTkFont(size=11, weight="bold"), text_color="#0F2537").pack(pady=(4, 2))
        
        q_frame = ctk.CTkFrame(b4, fg_color="transparent")
        q_frame.pack(fill="x", padx=6, pady=2)
        q = stats['chorak_taqsimot']
        ctk.CTkLabel(q_frame, text=f"I-ch: {q['I']} | II-ch: {q['II']} | III-ch: {q['III']} | IV-ch: {q['IV']}", font=ctk.CTkFont(size=12, weight="bold"), text_color="#1F4E79").pack(pady=4)

        for col_idx in range(4): 
            bottom_frame.grid_columnconfigure(col_idx, weight=1)

    def _apply_filters(self, _=None):
        self.selected_period = self.cb_period.get()
        self.selected_masul = self.cb_masul.get()
        self.selected_manba = self.cb_manba.get()
        self.loader.filter_data(
            period=self.selected_period, 
            masul=self.selected_masul, 
            manba=self.selected_manba, 
            search_query=self.entry_dash_search.get().strip()
        )
        self.show_dashboard_view()

    def _reset_filters(self):
        self.selected_period = "Barchasi"
        self.selected_masul = "Barchasi"
        self.selected_manba = "Barchasi"
        if hasattr(self, 'entry_dash_search'): 
            self.entry_dash_search.delete(0, 'end')
        self.loader.filter_data("Barchasi", "Barchasi", "Barchasi", "")
        self.show_dashboard_view()

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
        
        ctk.CTkLabel(top_bar, text="🔍 Qidiruv:", font=ctk.CTkFont(size=12, weight="bold"), text_color="#0F2537").pack(side="left", padx=(0, 5))
        entry_search = ctk.CTkEntry(top_bar, placeholder_text="F.I.Sh, telefon, tuman...", width=320, font=ctk.CTkFont(size=12))
        entry_search.pack(side="left", padx=5)
        
        ctk.CTkLabel(top_bar, text=f"Jami: {len(data_df)} ta", font=ctk.CTkFont(size=13, weight="bold"), text_color="#0F2537").pack(side="right", padx=10)

        tree_frame = ctk.CTkFrame(main_box, fg_color="transparent")
        tree_frame.pack(fill="both", expand=True, padx=15, pady=(0, 6))
        
        cols = ("#", "sana", "xavf", "fish", "telefon", "viloyat", "tuman", "masul", "ijro")
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Rec.Treeview", rowheight=28, font=("Calibri", 11), bordercolor="#94A3B8", borderwidth=1)
        style.configure("Rec.Treeview.Heading", font=("Calibri", 11, "bold"), background="#0F2537", foreground="#FFFFFF")
        
        tree = ttk.Treeview(tree_frame, columns=cols, show="headings", style="Rec.Treeview", selectmode="browse")
        
        def sort_col(col_idx, reverse):
            l = [(tree.set(k, col_idx), k) for k in tree.get_children('')]
            l.sort(reverse=reverse)
            for index, (val, k) in enumerate(l): 
                tree.move(k, '', index)
            tree.heading(col_idx, command=lambda _col=col_idx: sort_col(_col, not reverse))

        tree.heading("#", text="#", command=lambda: sort_col("#", False))
        tree.heading("sana", text="Sana", command=lambda: sort_col("sana", False))
        tree.heading("xavf", text="Xavf darajasi")
        tree.heading("fish", text="F.I.Sh.", command=lambda: sort_col("fish", False))
        tree.heading("telefon", text="Telefon")
        tree.heading("viloyat", text="Viloyat", command=lambda: sort_col("viloyat", False))
        tree.heading("tuman", text="Tuman")
        tree.heading("masul", text="Mas’ul komplayens")
        tree.heading("ijro", text="Holati", command=lambda: sort_col("ijro", False))

        tree.column("#", width=45, anchor="center")
        tree.column("sana", width=125, anchor="center")
        tree.column("xavf", width=120, anchor="center")
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
        
        tree.tag_configure('odd', background='#F1F5F9')
        tree.tag_configure('even', background='#FFFFFF')
        tree.tag_configure('danger', background='#FDEDEC')

        def populate(df_to_show):
            tree.delete(*tree.get_children())
            for idx, (_, r) in enumerate(df_to_show.iterrows()):
                is_danger = r.get('Yuqori_Xavf', False)
                tag = 'danger' if is_danger else ('even' if idx % 2 == 0 else 'odd')
                xavf_text = "🔴 Yuqori xavf" if is_danger else "O'rtacha"
                tree.insert("", "end", values=(
                    r.get('#'), 
                    str(r.get('Yaratilgan sana'))[:16], 
                    xavf_text, 
                    r.get('F.I.Sh.'), 
                    r.get('Telefon'), 
                    r.get('Viloyat'), 
                    r.get('Tuman'), 
                    r.get('Masul_Komplayens', 'Kadastr agentligi hududiy komplayens xodimi'), 
                    r.get('Ijro_Holati', 'O‘rganishga yuborilgan')
                ), tags=(tag,))

        populate(data_df)
        
        def on_search(event):
            q = entry_search.get().lower().strip()
            if not q: 
                populate(data_df)
            else: 
                mask = (
                    data_df['F.I.Sh.'].astype(str).str.lower().str.contains(q) | 
                    data_df['Telefon'].astype(str).str.lower().str.contains(q) | 
                    data_df['Viloyat'].astype(str).str.lower().str.contains(q)
                )
                populate(data_df[mask])
                
        entry_search.bind("<KeyRelease>", on_search)
        
        def on_double_click(e):
            selected = tree.selection()
            if selected:
                m_id = int(tree.item(selected[0], "values")[0])
                self.show_detail_view(m_id, lambda: self.show_records_view(title, data_df))
                
        tree.bind("<Double-1>", on_double_click)

    # ================= 3-POG'ONA: KARTOCHKA =================
    def show_detail_view(self, m_id, return_callback):
        self.view_stack.append(return_callback)
        self.btn_back.configure(state="normal")
        self.lbl_path.configure(text=f"Asosiy oyna  /  Murojaatlar  /  Kartochka #{m_id}")
        self._clear_container()
        
        rec = self.loader.df[self.loader.df['#'] == m_id].iloc[0]
        sets = self.loader.db.get_settings()

        main_scroll = ctk.CTkScrollableFrame(self.container, fg_color="#FFFFFF", corner_radius=6, border_width=1, border_color="#CBD5E1")
        main_scroll.pack(fill="both", expand=True, padx=4, pady=4)

        info_top = ctk.CTkFrame(main_scroll, fg_color="#F1F5F9", corner_radius=6, border_width=1, border_color="#CBD5E1")
        info_top.pack(fill="x", padx=15, pady=(10, 6))
        
        txt_info = (
            f"👤 Fuqaro: {rec.get('F.I.Sh.')}   |   📞 Tel: {rec.get('Telefon')}   |   📍 Hudud: {rec.get('Viloyat')}, {rec.get('Tuman')}\n"
            f"📡 Manba: {rec.get('Manba', 'Telegram bot')}   |   🏢 Yo'nalish: {rec.get('Yoʻnalish')}\n"
            f"🕒 Kelib tushgan sana: {rec.get('Yaratilgan sana')}"
        )
        ctk.CTkLabel(info_top, text=txt_info, justify="left", font=ctk.CTkFont(size=13, weight="bold"), text_color="#0F2537").pack(padx=15, pady=8, anchor="w")

        if rec.get('Yuqori_Xavf', False): 
            ctk.CTkLabel(main_scroll, text="⚠️ DIQQAT: MUROJAATDA KORRUPSIYAVIY XAVF ALOMATLARI MAVJUD!", font=ctk.CTkFont(size=12, weight="bold"), text_color="#C0392B").pack(padx=15, anchor="w")

        ctk.CTkLabel(main_scroll, text="📝 Murojaat matni (to‘liq shaklda):", font=ctk.CTkFont(size=13, weight="bold"), text_color="#0F2537").pack(padx=15, anchor="w")
        
        tb_m = ctk.CTkTextbox(main_scroll, height=140, wrap="word", font=ctk.CTkFont(size=13))
        tb_m.insert("1.0", str(rec.get('Murojaat matni', '')))
        tb_m.configure(state="disabled")
        tb_m.pack(fill="x", padx=15, pady=(4, 8))

        action_frame = ctk.CTkFrame(main_scroll, fg_color="#F8FAFC", corner_radius=6, border_width=1, border_color="#CBD5E1")
        action_frame.pack(fill="x", padx=15, pady=(4, 10))
        
        ctk.CTkLabel(action_frame, text="⚙️ KOMPLAYENS NAZORAT, MAS’UL TAYINLASH VA O‘RGANISH NATIJASI:", font=ctk.CTkFont(size=12, weight="bold"), text_color="#0F2537").pack(padx=15, pady=(6, 2), anchor="w")

        row_masul = ctk.CTkFrame(action_frame, fg_color="transparent")
        row_masul.pack(fill="x", padx=15, pady=3)
        ctk.CTkLabel(row_masul, text="O‘rganish yuklatilgan mas’ul:", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=(0, 8))
        
        cb_masul_item = ctk.CTkComboBox(row_masul, values=["Kadastr agentligi hududiy komplayens xodimi", "Davlat kadastrlari palatasi hududiy komplayens xodimi"], width=300, font=ctk.CTkFont(size=12))
        cb_masul_item.set("Davlat kadastrlari palatasi hududiy komplayens xodimi" if 'palata' in str(rec.get('Masul_Komplayens', '')).lower() else "Kadastr agentligi hududiy komplayens xodimi")
        cb_masul_item.pack(side="left")

        def send_to_telegram():
            x_info = self.loader.db.find_xodim_for_region(rec.get('Viloyat'), cb_masul_item.get())
            raw_matn = str(rec.get('Murojaat matni', ''))
            short_matn = raw_matn if len(raw_matn) < 600 else raw_matn[:600] + "..."
            tmpl = sets.get("tg_template", "Murojaat #{id}\nMatn: {matn}")
            tg_text = tmpl.replace("{id}", str(m_id)).replace("{manba}", str(rec.get('Manba', 'Telegram bot'))).replace("{fish}", str(rec.get('F.I.Sh.'))).replace("{tel}", str(rec.get('Telefon'))).replace("{viloyat}", str(rec.get('Viloyat'))).replace("{tuman}", str(rec.get('Tuman'))).replace("{sana}", str(rec.get('Yaratilgan sana'))[:16]).replace("{matn}", short_matn)
            encoded = urllib.parse.quote(tg_text)
            
            u_name = str(x_info.get('username', '')).strip().replace('@', '')
            u_phone = str(x_info.get('telefon', '')).strip().replace('+', '')
            
            if u_name:
                url = f"https://t.me/{u_name}?text={encoded}"
            elif u_phone:
                url = f"https://t.me/+{u_phone}?text={encoded}"
            else:
                url = f"https://t.me/share/url?url={encoded}"
                
            try: 
                webbrowser.open(url)
            except Exception as e: 
                messagebox.showerror("Xatolik", f"Telegramni ochishda xato: {str(e)}")

        btn_tg = ctk.CTkButton(row_masul, text="✈️ To'g'ridan-to'g'ri Telegramga yuborish", width=240, height=28, fg_color="#0088CC", hover_color="#0077B5", font=ctk.CTkFont(size=11, weight="bold"), command=send_to_telegram)
        btn_tg.pack(side="left", padx=10)

        row_status = ctk.CTkFrame(action_frame, fg_color="transparent")
        row_status.pack(fill="x", padx=15, pady=3)
        ctk.CTkLabel(row_status, text="Murojaat holati:", font=ctk.CTkFont(size=12, weight="bold")).pack(

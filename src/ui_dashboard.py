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

# ================= 10 XIL RANG VA MAVZULAR BAZASI =================
THEMES = {
    "Navy (Asl)": {"primary": "#0F2537", "btn": "#1E3A56", "hover": "#2A4D73"},
    "Qora (Dark)": {"primary": "#111827", "btn": "#1F2937", "hover": "#374151"},
    "Yashil (Emerald)": {"primary": "#064E3B", "btn": "#047857", "hover": "#059669"},
    "Tungi (Midnight)": {"primary": "#1E3A8A", "btn": "#1D4ED8", "hover": "#2563EB"},
    "Siyohrang (Purple)": {"primary": "#4C1D95", "btn": "#5B21B6", "hover": "#6D28D9"},
    "To'q Qizil (Crimson)": {"primary": "#7F1D1D", "btn": "#991B1B", "hover": "#B91C1C"},
    "Dengiz (Teal)": {"primary": "#134E4A", "btn": "#0F766E", "hover": "#0D9488"},
    "Indigo (Deep)": {"primary": "#312E81", "btn": "#4338CA", "hover": "#4F46E5"},
    "Kulrang (Slate)": {"primary": "#1E293B", "btn": "#334155", "hover": "#475569"},
    "Kofeyniy (Mocha)": {"primary": "#451A03", "btn": "#78350F", "hover": "#92400E"},
}

# ================= UNIVERSAL NUSXALASH VA QO'YISH =================
def enable_copy_paste(root):
    def copy(event):
        try:
            w = root.focus_get()
            if hasattr(w, 'selection_get'):
                text = w.selection_get()
                root.clipboard_clear()
                root.clipboard_append(text)
        except: pass
        return "break"

    def paste(event):
        try:
            w = root.focus_get()
            if hasattr(w, 'insert'):
                text = root.clipboard_get()
                try:
                    if isinstance(w, (tk.Entry, ctk.CTkEntry)) and w.select_present():
                        w.delete("sel.first", "sel.last")
                    elif isinstance(w, (tk.Text, ctk.CTkTextbox)) and w.tag_ranges("sel"):
                        w.delete("sel.first", "sel.last")
                except: pass
                w.insert("insert", text)
        except: pass
        return "break"

    def cut(event):
        try:
            w = root.focus_get()
            if hasattr(w, 'selection_get'):
                text = w.selection_get()
                root.clipboard_clear()
                root.clipboard_append(text)
                try:
                    if isinstance(w, (tk.Entry, ctk.CTkEntry)) and w.select_present():
                        w.delete("sel.first", "sel.last")
                    elif isinstance(w, (tk.Text, ctk.CTkTextbox)) and w.tag_ranges("sel"):
                        w.delete("sel.first", "sel.last")
                except: pass
        except: pass
        return "break"

    # DASTURNI QULATMASLIGI UCHUN FAQAT STANDART TUGMALAR QOLDIRILDI
    for key in ["<Control-c>", "<Control-C>"]: root.bind_all(key, copy)
    for key in ["<Control-v>", "<Control-V>"]: root.bind_all(key, paste)
    for key in ["<Control-x>", "<Control-X>"]: root.bind_all(key, cut)

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
        
        # Holat o'zgaruvchilari
        self.current_theme = "Navy (Asl)"
        self.is_cyrillic = False
        
        self.geometry("1440x920")
        self.minsize(1220, 740)
        ctk.set_appearance_mode("Light")
        self.configure(fg_color="#ECEFF4")
        self.view_stack = []
        self.current_view_func = None
        
        try:
            self.logo_path = ensure_app_logo()
            self._icon_photo = ctk.CTkImage(Image.open(self.logo_path), size=(32, 32))
        except: 
            self._icon_photo = None
            
        enable_copy_paste(self)
        
        # Barcha qismlarni o'z ichiga oluvchi asosiy konteyner
        self.main_wrapper = ctk.CTkFrame(self, fg_color="transparent")
        self.main_wrapper.pack(fill="both", expand=True)
        
        self._redraw_entire_ui(initial=True)

    # ================= TARJIMA FUNKSIYALARI (LOTIN <-> KRILL) =================
    def _t(self, text):
        """Interfeys uchun Lotin -> Krill tarjimoni"""
        if not self.is_cyrillic or not text:
            return text
        text = str(text)
        mapping = {
            "Sh": "Ш", "sh": "ш", "Ch": "Ч", "ch": "ч", 
            "O'": "Ў", "O‘": "Ў", "o'": "ў", "o‘": "ў",
            "G'": "Ғ", "G‘": "Ғ", "g'": "ғ", "g‘": "ғ",
            "Yo": "Ё", "yo": "ё", "Yu": "Ю", "yu": "ю", "Ya": "Я", "ya": "я",
            "Ye": "Е", "ye": "е", "Ts": "Ц", "ts": "ц",
            "A": "А", "a": "а", "B": "Б", "b": "б", "D": "Д", "d": "д", "E": "Е", "e": "е",
            "F": "Ф", "f": "ф", "G": "Г", "g": "г", "H": "Ҳ", "h": "ҳ", "I": "И", "i": "и",
            "J": "Ж", "j": "ж", "K": "К", "k": "к", "L": "Л", "l": "л", "M": "М", "m": "м",
            "N": "Н", "n": "н", "O": "О", "o": "о", "P": "П", "p": "п", "Q": "Қ", "q": "қ",
            "R": "Р", "r": "р", "S": "С", "s": "с", "T": "Т", "t": "т", "U": "У", "u": "у",
            "V": "В", "v": "в", "X": "Х", "x": "х", "Y": "Й", "y": "й", "Z": "З", "z": "з"
        }
        for k, v in mapping.items():
            text = text.replace(k, v)
        return text

    def _to_latin(self, text):
        """Ma'lumotlar bazasi bilan ishlash uchun Krill -> Lotin tarjimoni"""
        if not self.is_cyrillic or not text:
            return text
        text = str(text)
        rev_mapping = {
            "Ш": "Sh", "ш": "sh", "Ч": "Ch", "ч": "ch", "Ў": "O'", "ў": "o'",
            "Ғ": "G'", "ғ": "g'", "Ё": "Yo", "ё": "yo", "Ю": "Yu", "ю": "yu", 
            "Я": "Ya", "я": "ya", "Е": "E", "е": "e", "Ц": "Ts", "ц": "ts",
            "А": "A", "а": "a", "Б": "B", "б": "b", "Д": "D", "д": "d", "Ф": "F", "ф": "f",
            "Г": "G", "г": "g", "Ҳ": "H", "ҳ": "h", "И": "I", "и": "i", "Ж": "J", "ж": "j",
            "К": "K", "к": "k", "Л": "L", "л": "l", "М": "M", "м": "m", "Н": "N", "н": "n",
            "О": "O", "о": "o", "П": "P", "п": "p", "Қ": "Q", "қ": "q", "Р": "R", "р": "r",
            "С": "S", "с": "s", "Т": "T", "т": "t", "У": "U", "у": "u", "В": "V", "в": "v",
            "Х": "X", "х": "x", "Й": "Y", "й": "y", "З": "Z", "з": "z"
        }
        for k, v in rev_mapping.items():
            text = text.replace(k, v)
        return text

    # ================= MAVZU VA TILNI YANGILASH Dvigateli =================
    def _redraw_entire_ui(self, initial=False):
        rol_matni = self._t(" (KUZATUVCHI REJIMI)") if self.role == "kuzatuvchi" else self._t(" (ADMINISTRATOR)")
        self.title(self._t("KADASTR AGENTLIGI — KORRUPSIYAGA QARSHI KOMPLAYENS MONITORING TIZIMI") + rol_matni)
        
        for w in self.main_wrapper.winfo_children():
            w.destroy()
            
        self.t_colors = THEMES[self.current_theme]
        self._build_top_navbar()
        self.container = ctk.CTkFrame(self.main_wrapper, fg_color="transparent")
        self.container.pack(fill="both", expand=True, padx=16, pady=(0, 12))
        
        if initial:
            self.current_view_func = self.show_dashboard_view
            
        if self.current_view_func:
            self.current_view_func()

    def change_theme(self, choice):
        for k in THEMES.keys():
            if self._t(k) == choice:
                self.current_theme = k
                break
        self._redraw_entire_ui()

    def toggle_lang(self):
        self.is_cyrillic = not self.is_cyrillic
        self._redraw_entire_ui()

    def _build_top_navbar(self):
        nav = ctk.CTkFrame(self.main_wrapper, fg_color=self.t_colors["primary"], height=65, corner_radius=0)
        nav.pack(fill="x", side="top", pady=(0, 10))
        
        self.btn_back = ctk.CTkButton(
            nav, text=self._t("⬅ Orqaga"), width=95, height=34, fg_color=self.t_colors["btn"], 
            hover_color=self.t_colors["hover"], font=ctk.CTkFont(size=12, weight="bold"), 
            command=self._go_back
        )
        self.btn_back.pack(side="left", padx=15, pady=15)
        
        self.lbl_path = ctk.CTkLabel(
            nav, text=self._t("Asosiy oyna  /  Tahliliy Dashboard"), 
            font=ctk.CTkFont(size=16, weight="bold"), text_color="#F8FAFC"
        )
        self.lbl_path.pack(side="left", padx=10, pady=15)

        # ---------------- TIL VA MAVZU TUGMALARI ----------------
        btn_lang = ctk.CTkButton(
            nav, text="🌐 " + ("Lotin" if self.is_cyrillic else "Krill"), 
            width=80, height=34, fg_color=self.t_colors["btn"], hover_color=self.t_colors["hover"],
            font=ctk.CTkFont(size=12, weight="bold"), command=self.toggle_lang
        )
        btn_lang.pack(side="right", padx=10, pady=15)

        cb_theme = ctk.CTkComboBox(
            nav, values=[self._t(k) for k in THEMES.keys()], width=130, height=34,
            font=ctk.CTkFont(size=11, weight="bold"), command=self.change_theme
        )
        cb_theme.set(self._t(self.current_theme))
        cb_theme.pack(side="right", padx=4, pady=15)
        
        # ---------------- HARAKAT TUGMALARI ----------------
        ctk.CTkButton(
            nav, text=self._t("📄 Word Ma'lumotnoma"), width=145, height=34, 
            fg_color="#8B3A2B", hover_color="#A94442", 
            font=ctk.CTkFont(size=11, weight="bold"), command=self._export_word
        ).pack(side="right", padx=4, pady=15)
        
        ctk.CTkButton(
            nav, text=self._t("📊 Excel Jadval"), width=115, height=34, 
            fg_color="#1E6B47", hover_color="#258357", 
            font=ctk.CTkFont(size=11, weight="bold"), command=self._export_excel
        ).pack(side="right", padx=4, pady=15)
        
        if self.role == "admin":
            # KIRISHLAR TARIXI (AUDIT LOG)
            ctk.CTkButton(
                nav, text=self._t("👁 Kirishlar tarixi"), width=140, height=34, 
                fg_color="#D35400", hover_color="#A04000", 
                font=ctk.CTkFont(size=11, weight="bold"), command=self.show_audit_view
            ).pack(side="right", padx=4, pady=15)

            ctk.CTkButton(
                nav, text=self._t("⚙️ Sozlamalar"), width=110, height=34, 
                fg_color="#7F8C8D", hover_color="#95A5A6", 
                font=ctk.CTkFont(size=11, weight="bold"), command=self.show_settings_view
            ).pack(side="right", padx=(4, 15), pady=15)
            
            ctk.CTkButton(
                nav, text=self._t("👥 Hududiy xodimlar"), width=140, height=34, 
                fg_color="#4B3869", hover_color="#5E4784", 
                font=ctk.CTkFont(size=11, weight="bold"), command=self.show_xodimlar_view
            ).pack(side="right", padx=4, pady=15)
            
            ctk.CTkButton(
                nav, text=self._t("📞 + Telefon qabul"), width=140, height=34, 
                fg_color="#27AE60", hover_color="#219150", 
                font=ctk.CTkFont(size=11, weight="bold"), command=self.show_add_phone_view
            ).pack(side="right", padx=4, pady=15)
            
            ctk.CTkButton(
                nav, text=self._t("📥 Yangi Excel yuklash"), width=145, height=34, 
                fg_color=self.t_colors["btn"], hover_color=self.t_colors["hover"], 
                font=ctk.CTkFont(size=11, weight="bold"), command=self._import_excel
            ).pack(side="right", padx=4, pady=15)
        else:
            ctk.CTkButton(
                nav, text=self._t("🔄 Bazani bulutdan yangilash"), width=180, height=34, 
                fg_color=self.t_colors["btn"], hover_color=self.t_colors["hover"], 
                font=ctk.CTkFont(size=11, weight="bold"), 
                command=self._pull_from_cloud
            ).pack(side="right", padx=15, pady=15)

    def _pull_from_cloud(self):
        self.loader.db._sync_pull_from_cloud()
        self.loader.refresh_data()
        self._redraw_entire_ui()
        messagebox.showinfo(self._t("Yangilandi"), self._t("Murojaatlar bulutdan olindi!"))

    def _clear_container(self):
        for widget in self.container.winfo_children(): 
            widget.destroy()

    def _go_back(self):
        if self.view_stack: 
            prev_view = self.view_stack.pop()
            prev_view()
        else: 
            self._redraw_entire_ui(initial=True)

    # ================= DASHBOARD =================
    def show_dashboard_view(self):
        self.current_view_func = self.show_dashboard_view
        if self.current_view_func not in self.view_stack:
            self.view_stack.clear()
            
        self.btn_back.configure(state="disabled")
        self.lbl_path.configure(text=self._t("Asosiy oyna  /  Tahliliy Dashboard"))
        self._clear_container()

        filter_box = ctk.CTkFrame(self.container, fg_color="#FFFFFF", corner_radius=6, border_width=1, border_color="#CBD5E1")
        filter_box.pack(fill="x", pady=(0, 8), padx=2)
        
        ctk.CTkLabel(filter_box, text=self._t("🔍 Qidiruv:"), font=ctk.CTkFont(size=11, weight="bold"), text_color="#0F2537").pack(side="left", padx=(10, 2), pady=7)
        
        self.entry_dash_search = ctk.CTkEntry(filter_box, placeholder_text=self._t("F.I.Sh, tel, tuman..."), width=160, font=ctk.CTkFont(size=11))
        self.entry_dash_search.pack(side="left", padx=2, pady=7)
        self.entry_dash_search.bind("<Return>", self._apply_filters)
        
        ctk.CTkButton(filter_box, text=self._t("Topish"), width=55, height=28, fg_color=self.t_colors["primary"], hover_color=self.t_colors["hover"], font=ctk.CTkFont(size=11, weight="bold"), command=self._apply_filters).pack(side="left", padx=2, pady=7)

        ctk.CTkLabel(filter_box, text=self._t("⏳ Davr:"), font=ctk.CTkFont(size=11, weight="bold"), text_color="#0F2537").pack(side="left", padx=(8, 2), pady=7)
        period_values = self.loader.get_available_periods()
        self.cb_period = ctk.CTkComboBox(filter_box, values=[self._t(v) for v in period_values], command=self._apply_filters, width=110, font=ctk.CTkFont(size=11))
        self.cb_period.set(self._t(getattr(self, 'selected_period', 'Barchasi')))
        self.cb_period.pack(side="left", padx=2, pady=7)

        ctk.CTkLabel(filter_box, text=self._t("📡 Manba:"), font=ctk.CTkFont(size=11, weight="bold"), text_color="#0F2537").pack(side="left", padx=(8, 2), pady=7)
        self.cb_manba = ctk.CTkComboBox(filter_box, values=[self._t(v) for v in ["Barchasi", "Telegram bot", "Ishonch telefoni (+998-71-273-19-66)"]], command=self._apply_filters, width=220, font=ctk.CTkFont(size=11))
        self.cb_manba.set(self._t(getattr(self, 'selected_manba', 'Barchasi')))
        self.cb_manba.pack(side="left", padx=2, pady=7)

        ctk.CTkLabel(filter_box, text=self._t("🏢 Mas'ul:"), font=ctk.CTkFont(size=11, weight="bold"), text_color="#0F2537").pack(side="left", padx=(8, 2), pady=7)
        self.cb_masul = ctk.CTkComboBox(filter_box, values=[self._t(v) for v in ["Barchasi", "Kadastr agentligi hududiy komplayens xodimi", "Davlat kadastrlari palatasi hududiy komplayens xodimi"]], command=self._apply_filters, width=240, font=ctk.CTkFont(size=11))
        self.cb_masul.set(self._t(getattr(self, 'selected_masul', 'Barchasi')))
        self.cb_masul.pack(side="left", padx=2, pady=7)

        ctk.CTkButton(filter_box, text=self._t("Tozalash"), width=60, height=28, fg_color="#64748B", hover_color="#475569", font=ctk.CTkFont(size=11), command=self._reset_filters).pack(side="left", padx=6, pady=7)

        cards_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        cards_frame.pack(fill="x", pady=(0, 8))
        stats = self.loader.get_kpi_stats()
        
        cards = [
            (self._t("JAMI MUROJAATLAR"), stats['total'], self.t_colors["primary"], lambda: self.show_records_view(self._t("Barcha murojaatlar"), self.loader.filtered_df)),
            (self._t("AGENTLIKDA O‘RGANISHDA"), stats['agentlik_organish'], "#1B4D7E", lambda: self.show_records_view(self._t("Agentlikda o'rganishdagi"), self.loader.filtered_df[self.loader.filtered_df['Ijro_Holati'].astype(str).str.contains("O‘rganishga yuborilgan|O'rganishda", case=False, na=False) & self.loader.filtered_df['Masul_Komplayens'].astype(str).str.contains("agentligi", case=False, na=False)])),
            (self._t("PALATADA O‘RGANISHDA"), stats['palata_organish'], "#4B3869", lambda: self.show_records_view(self._t("Palatada o'rganishdagi"), self.loader.filtered_df[self.loader.filtered_df['Ijro_Holati'].astype(str).str.contains("O‘rganishga yuborilgan|O'rganishda", case=False, na=False) & self.loader.filtered_df['Masul_Komplayens'].astype(str).str.contains("palata", case=False, na=False)])),
            (self._t("O‘RGANIB CHIQILGAN"), stats['natija_kiritilgan'], "#1B5E20", lambda: self.show_records_view(self._t("O'rganib chiqilganlar"), self.loader.filtered_df[self.loader.filtered_df['Ijro_Holati'].astype(str).str.contains("Bartaraf etildi|Ijobiy hal etildi|Intizomiy chora|O‘rganib chiqildi|Asossiz", case=False, na=False) | self.loader.filtered_df['Chora_Turi'].astype(str).str.contains("Asossiz", case=False, na=False)])),
            (self._t("ASOSSIZ DEB TOPILGAN"), stats['asossiz'], "#7F8C8D", lambda: self.show_records_view(self._t("Asossiz deb topilganlar"), self.loader.filtered_df[self.loader.filtered_df['Ijro_Holati'].astype(str).str.contains("Asossiz", case=False, na=False) | self.loader.filtered_df['Chora_Turi'].astype(str).str.contains("Asossiz", case=False, na=False)]))
        ]

        for i, (title, val, color, cmd) in enumerate(cards):
            card = ctk.CTkFrame(cards_frame, fg_color=color, corner_radius=6)
            card.grid(row=0, column=i, padx=3, sticky="nsew")
            cards_frame.grid_columnconfigure(i, weight=1)
            
            ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=10, weight="bold"), text_color="#E2E8F0").pack(pady=(6, 1))
            ctk.CTkLabel(card, text=str(val), font=ctk.CTkFont(size=22, weight="bold"), text_color="#FFFFFF").pack(pady=(0, 1))
            ctk.CTkButton(card, text=self._t("Ochish ➔"), width=70, height=20, fg_color="transparent", border_width=1, border_color="#CBD5E1", font=ctk.CTkFont(size=9), command=cmd).pack(pady=(0, 6))

        table_container = ctk.CTkFrame(self.container, fg_color="#FFFFFF", corner_radius=6, border_width=1, border_color="#CBD5E1")
        table_container.pack(fill="both", expand=True, padx=2, pady=(0, 8))
        
        lbl_sec = ctk.CTkLabel(table_container, text=self._t("Viloyatlar kesimida murojaatlar nazorati:"), font=ctk.CTkFont(size=12, weight="bold"), text_color="#0F2537")
        lbl_sec.pack(anchor="w", padx=12, pady=(6, 3))

        table_frame = ctk.CTkFrame(table_container, fg_color="transparent")
        table_frame.pack(fill="both", expand=True, padx=12, pady=(0, 8))
        
        cols = ("viloyat", "jami", "tg_m", "tel_m", "agentlik_org", "palata_org", "hal_etilgan", "asossiz")
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Dash.Treeview", rowheight=27, font=("Calibri", 11), bordercolor="#94A3B8", borderwidth=1)
        style.configure("Dash.Treeview.Heading", font=("Calibri", 11, "bold"), background=self.t_colors["primary"], foreground="#FFFFFF")

        self.dash_tree = ttk.Treeview(table_frame, columns=cols, show="headings", style="Dash.Treeview", selectmode="browse")
        self.dash_tree.heading("viloyat", text=self._t("Hudud nomi (Viloyat)"))
        self.dash_tree.heading("jami", text=self._t("Jami"))
        self.dash_tree.heading("tg_m", text=self._t("Telegram bot"))
        self.dash_tree.heading("tel_m", text=self._t("Ishonch telefoni"))
        self.dash_tree.heading("agentlik_org", text=self._t("Agentlikda"))
        self.dash_tree.heading("palata_org", text=self._t("Palatada"))
        self.dash_tree.heading("hal_etilgan", text=self._t("O‘rganilgan"))
        self.dash_tree.heading("asossiz", text=self._t("Asossiz deb topilgan"))
        
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
            self.dash_tree.insert("", "end", values=(self._t(reg), self._t(f"{c_tot} ta"), self._t(f"{c_tg} ta"), self._t(f"{c_tel} ta"), self._t(f"{c_ag} ta"), self._t(f"{c_pa} ta"), self._t(f"{c_hal} ta"), self._t(f"{c_as} ta")), tags=(tag,))

        def on_region_double_click(e):
            selected = self.dash_tree.selection()
            if selected:
                reg_name_translated = self.dash_tree.item(selected[0], 'values')[0]
                reg_name = self._to_latin(reg_name_translated.replace(self._t(" ta"), "").strip())
                df_to_show = self.loader.filtered_df[self.loader.filtered_df['Viloyat'] == reg_name]
                self.show_records_view(self._t(f"{reg_name}"), df_to_show)

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
                self.show_records_view(self._t(f"Muddati o‘tgan (>{sla_d} kun)"), df_show)
                
        def open_ogoh():
            if not f_df[is_org_mask].empty and 'DT' in f_df.columns:
                days_passed = (now_date - f_df[is_org_mask]['DT']).dt.days
                df_show = f_df[is_org_mask][(days_passed >= max(1, sla_d-1)) & (days_passed <= sla_d)]
                self.show_records_view(self._t("Ogohlantirish"), df_show)

        b1 = ctk.CTkFrame(bottom_frame, fg_color="#FFFFFF", corner_radius=6, border_width=1, border_color="#E2E8F0")
        b1.grid(row=0, column=0, padx=3, sticky="nsew")
        ctk.CTkLabel(b1, text=self._t("⏱ IJRO MUDDATI NAZORATI"), font=ctk.CTkFont(size=11, weight="bold"), text_color="#0F2537").pack(pady=(4, 2))
        ctk.CTkButton(b1, text=self._t(f"🔴 Muddati o‘tgan (>{sla_d} kun): {stats['muddati_otgan']} ta ➔"), fg_color="#FDF2F2", text_color="#C0392B", hover_color="#FDE8E8", font=ctk.CTkFont(size=11, weight="bold"), height=24, anchor="w", command=open_muddati).pack(fill="x", padx=8, pady=2)
        ctk.CTkButton(b1, text=self._t(f"🟡 Ogohlantirish (1-{sla_d} kun): {stats['ogohlantirish']} ta ➔"), fg_color="#FEF9E7", text_color="#D35400", hover_color="#FCF3CF", font=ctk.CTkFont(size=11, weight="bold"), height=24, anchor="w", command=open_ogoh).pack(fill="x", padx=8, pady=2)

        def open_takroriy():
            dup_idx = f_df['Toza_Telefon'].astype(str).str.strip().value_counts()
            dups = dup_idx[dup_idx > 1].index
            df_show = f_df[f_df['Toza_Telefon'].isin(dups)].sort_values(by='Toza_Telefon')
            self.show_records_view(self._t("Takroriy"), df_show)

        b2 = ctk.CTkFrame(bottom_frame, fg_color="#FFFFFF", corner_radius=6, border_width=1, border_color="#E2E8F0")
        b2.grid(row=0, column=1, padx=3, sticky="nsew")
        ctk.CTkLabel(b2, text=self._t("🔄 TAKRORIY MUROJAATLAR"), font=ctk.CTkFont(size=11, weight="bold"), text_color="#0F2537").pack(pady=(4, 2))
        ctk.CTkButton(b2, text=self._t(f"Takroriy kelganlar: {stats['takroriy_soni']} ta ➔"), fg_color="#EBF5FB", text_color="#2980B9", hover_color="#D4E6F1", font=ctk.CTkFont(size=12, weight="bold"), height=30, command=open_takroriy).pack(fill="x", padx=12, pady=5)
        
        def open_intizomiy():
            df_show = f_df[f_df['Chora_Turi'].astype(str).str.contains("Xayfsan|Lavozimidan ozod|Prokuratura|Jarima", case=False, na=False)]
            self.show_records_view(self._t("Intizomiy"), df_show)

        b3 = ctk.CTkFrame(bottom_frame, fg_color="#FFFFFF", corner_radius=6, border_width=1, border_color="#E2E8F0")
        b3.grid(row=0, column=2, padx=3, sticky="nsew")
        ctk.CTkLabel(b3, text=self._t("⚖️ INTIZOMIY CHORALAR"), font=ctk.CTkFont(size=11, weight="bold"), text_color="#0F2537").pack(pady=(4, 2))
        ctk.CTkButton(b3, text=self._t(f"Ko‘rilgan choralar: {stats['chora_krilgan_soni']} ta ➔"), fg_color="#EAFAF1", text_color="#27AE60", hover_color="#D5F5E3", font=ctk.CTkFont(size=12, weight="bold"), height=30, command=open_intizomiy).pack(fill="x", padx=12, pady=5)

        b4 = ctk.CTkFrame(bottom_frame, fg_color="#FFFFFF", corner_radius=6, border_width=1, border_color="#E2E8F0")
        b4.grid(row=0, column=3, padx=3, sticky="nsew")
        ctk.CTkLabel(b4, text=self._t("📅 CHORAKLAR (KVARTAL)"), font=ctk.CTkFont(size=11, weight="bold"), text_color="#0F2537").pack(pady=(4, 2))
        
        q_frame = ctk.CTkFrame(b4, fg_color="transparent")
        q_frame.pack(fill="x", padx=6, pady=2)
        q = stats['chorak_taqsimot']
        ctk.CTkLabel(q_frame, text=self._t(f"I-ch: {q['I']} | II-ch: {q['II']} | III-ch: {q['III']} | IV-ch: {q['IV']}"), font=ctk.CTkFont(size=12, weight="bold"), text_color="#1F4E79").pack(pady=4)

        for col_idx in range(4): 
            bottom_frame.grid_columnconfigure(col_idx, weight=1)

    def _apply_filters(self, _=None):
        self.selected_period = self._to_latin(self.cb_period.get())
        self.selected_masul = self._to_latin(self.cb_masul.get())
        self.selected_manba = self._to_latin(self.cb_manba.get())
        search_q = self._to_latin(self.entry_dash_search.get().strip())
        
        self.loader.filter_data(
            period=self.selected_period, 
            masul=self.selected_masul, 
            manba=self.selected_manba, 
            search_query=search_q
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
        self.current_view_func = lambda: self.show_records_view(title, data_df)
        if self.show_dashboard_view not in self.view_stack:
            self.view_stack.append(self.show_dashboard_view)
            
        self.btn_back.configure(state="normal")
        self.lbl_path.configure(text=self._t(f"Asosiy oyna  /  Ro'yxat: {title}"))
        self._clear_container()

        main_box = ctk.CTkFrame(self.container, fg_color="#FFFFFF", corner_radius=6, border_width=1, border_color="#CBD5E1")
        main_box.pack(fill="both", expand=True)

        top_bar = ctk.CTkFrame(main_box, fg_color="transparent")
        top_bar.pack(fill="x", padx=15, pady=8)
        
        ctk.CTkLabel(top_bar, text=self._t("🔍 Qidiruv:"), font=ctk.CTkFont(size=12, weight="bold"), text_color="#0F2537").pack(side="left", padx=(0, 5))
        entry_search = ctk.CTkEntry(top_bar, placeholder_text=self._t("F.I.Sh, telefon, tuman..."), width=320, font=ctk.CTkFont(size=12))
        entry_search.pack(side="left", padx=5)
        
        ctk.CTkLabel(top_bar, text=self._t(f"Jami: {len(data_df)} ta"), font=ctk.CTkFont(size=13, weight="bold"), text_color="#0F2537").pack(side="right", padx=10)

        tree_frame = ctk.CTkFrame(main_box, fg_color="transparent")
        tree_frame.pack(fill="both", expand=True, padx=15, pady=(0, 6))
        
        cols = ("#", "sana", "xavf", "fish", "telefon", "viloyat", "tuman", "masul", "ijro")
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Rec.Treeview", rowheight=28, font=("Calibri", 11), bordercolor="#94A3B8", borderwidth=1)
        style.configure("Rec.Treeview.Heading", font=("Calibri", 11, "bold"), background=self.t_colors["primary"], foreground="#FFFFFF")
        
        tree = ttk.Treeview(tree_frame, columns=cols, show="headings", style="Rec.Treeview", selectmode="browse")
        
        def sort_col(col_idx, reverse):
            l = [(tree.set(k, col_idx), k) for k in tree.get_children('')]
            l.sort(reverse=reverse)
            for index, (val, k) in enumerate(l): 
                tree.move(k, '', index)
            tree.heading(col_idx, command=lambda _col=col_idx: sort_col(_col, not reverse))

        tree.heading("#", text="#", command=lambda: sort_col("#", False))
        tree.heading("sana", text=self._t("Sana"), command=lambda: sort_col("sana", False))
        tree.heading("xavf", text=self._t("Xavf darajasi"))
        tree.heading("fish", text=self._t("F.I.Sh."), command=lambda: sort_col("fish", False))
        tree.heading("telefon", text=self._t("Telefon"))
        tree.heading("viloyat", text=self._t("Viloyat"), command=lambda: sort_col("viloyat", False))
        tree.heading("tuman", text=self._t("Tuman"))
        tree.heading("masul", text=self._t("Mas’ul komplayens"))
        tree.heading("ijro", text=self._t("Holati"), command=lambda: sort_col("ijro", False))

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
                xavf_text = self._t("🔴 Yuqori xavf") if is_danger else self._t("O'rtacha")
                tree.insert("", "end", values=(
                    r.get('#'), 
                    str(r.get('Yaratilgan sana'))[:16], 
                    xavf_text, 
                    self._t(r.get('F.I.Sh.')), 
                    r.get('Telefon'), 
                    self._t(r.get('Viloyat')), 
                    self._t(r.get('Tuman')), 
                    self._t(r.get('Masul_Komplayens', 'Kadastr agentligi hududiy komplayens xodimi')), 
                    self._t(r.get('Ijro_Holati', 'O‘rganishga yuborilgan'))
                ), tags=(tag,))

        populate(data_df)
        
        def on_search(event):
            q = self._to_latin(entry_search.get().lower().strip())
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
        self.current_view_func = lambda: self.show_detail_view(m_id, return_callback)
        if return_callback not in self.view_stack:
            self.view_stack.append(return_callback)
            
        self.btn_back.configure(state="normal")
        self.lbl_path.configure(text=self._t(f"Asosiy oyna  /  Murojaatlar  /  Kartochka #{m_id}"))
        self._clear_container()
        
        rec = self.loader.df[self.loader.df['#'] == m_id].iloc[0]
        sets = self.loader.db.get_settings()

        main_scroll = ctk.CTkScrollableFrame(self.container, fg_color="#FFFFFF", corner_radius=6, border_width=1, border_color="#CBD5E1")
        main_scroll.pack(fill="both", expand=True, padx=4, pady=4)

        info_top = ctk.CTkFrame(main_scroll, fg_color="#F1F5F9", corner_radius=6, border_width=1, border_color="#CBD5E1")
        info_top.pack(fill="x", padx=15, pady=(10, 6))
        
        txt_info = (
            f"👤 {self._t('Fuqaro')}: {self._t(rec.get('F.I.Sh.'))}   |   📞 {self._t('Tel')}: {rec.get('Telefon')}   |   📍 {self._t('Hudud')}: {self._t(rec.get('Viloyat'))}, {self._t(rec.get('Tuman'))}\n"
            f"📡 {self._t('Manba')}: {self._t(rec.get('Manba', 'Telegram bot'))}   |   🏢 {self._t('Yoʻnalish')}: {self._t(rec.get('Yoʻnalish'))}\n"
            f"🕒 {self._t('Kelib tushgan sana')}: {rec.get('Yaratilgan sana')}"
        )
        ctk.CTkLabel(info_top, text=txt_info, justify="left", font=ctk.CTkFont(size=13, weight="bold"), text_color="#0F2537").pack(padx=15, pady=8, anchor="w")

        if rec.get('Yuqori_Xavf', False): 
            ctk.CTkLabel(main_scroll, text=self._t("⚠️ DIQQAT: MUROJAATDA KORRUPSIYAVIY XAVF ALOMATLARI MAVJUD!"), font=ctk.CTkFont(size=12, weight="bold"), text_color="#C0392B").pack(padx=15, anchor="w")

        ctk.CTkLabel(main_scroll, text=self._t("📝 Murojaat matni (to‘liq shaklda):"), font=ctk.CTkFont(size=13, weight="bold"), text_color="#0F2537").pack(padx=15, anchor="w")
        
        tb_m = ctk.CTkTextbox(main_scroll, height=140, wrap="word", font=ctk.CTkFont(size=13))
        tb_m.insert("1.0", self._t(str(rec.get('Murojaat matni', ''))))
        tb_m.configure(state="disabled")
        tb_m.pack(fill="x", padx=15, pady=(4, 8))

        action_frame = ctk.CTkFrame(main_scroll, fg_color="#F8FAFC", corner_radius=6, border_width=1, border_color="#CBD5E1")
        action_frame.pack(fill="x", padx=15, pady=(4, 10))
        
        ctk.CTkLabel(action_frame, text=self._t("⚙️ KOMPLAYENS NAZORAT, MAS’UL TAYINLASH VA O‘RGANISH NATIJASI:"), font=ctk.CTkFont(size=12, weight="bold"), text_color="#0F2537").pack(padx=15, pady=(6, 2), anchor="w")

        row_masul = ctk.CTkFrame(action_frame, fg_color="transparent")
        row_masul.pack(fill="x", padx=15, pady=3)
        ctk.CTkLabel(row_masul, text=self._t("O‘rganish yuklatilgan mas’ul:"), font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=(0, 8))
        
        cb_masul_item = ctk.CTkComboBox(row_masul, values=[self._t(v) for v in ["Kadastr agentligi hududiy komplayens xodimi", "Davlat kadastrlari palatasi hududiy komplayens xodimi"]], width=300, font=ctk.CTkFont(size=12))
        cb_masul_item.set(self._t("Davlat kadastrlari palatasi hududiy komplayens xodimi" if 'palata' in str(rec.get('Masul_Komplayens', '')).lower() else "Kadastr agentligi hududiy komplayens xodimi"))
        cb_masul_item.pack(side="left")

        def send_to_telegram():
            x_info = self.loader.db.find_xodim_for_region(rec.get('Viloyat'), self._to_latin(cb_masul_item.get()))
            raw_matn = str(rec.get('Murojaat matni', ''))
            short_matn = raw_matn if len(raw_matn) < 600 else raw_matn[:600] + "..."
            tmpl = sets.get("tg_template", "Murojaat #{id}\nMatn: {matn}")
            tg_text = tmpl.replace("{id}", str(m_id)).replace("{manba}", str(rec.get('Manba', 'Telegram bot'))).replace("{fish}", str(rec.get('F.I.Sh.'))).replace("{tel}", str(rec.get('Telefon'))).replace("{viloyat}", str(rec.get('Viloyat'))).replace("{tuman}", str(rec.get('Tuman'))).replace("{sana}", str(rec.get('Yaratilgan sana'))[:16]).replace("{matn}", short_matn)
            encoded = urllib.parse.quote(self._t(tg_text))
            
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
                messagebox.showerror(self._t("Xatolik"), self._t(f"Telegramni ochishda xato: {str(e)}"))

        btn_tg = ctk.CTkButton(row_masul, text=self._t("✈️ To'g'ridan-to'g'ri Telegramga yuborish"), width=240, height=28, fg_color="#0088CC", hover_color="#0077B5", font=ctk.CTkFont(size=11, weight="bold"), command=send_to_telegram)
        btn_tg.pack(side="left", padx=10)

        row_status = ctk.CTkFrame(action_frame, fg_color="transparent")
        row_status.pack(fill="x", padx=15, pady=3)
        ctk.CTkLabel(row_status, text=self._t("Murojaat holati:"), font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=(0, 8))
        
        cb_status = ctk.CTkComboBox(row_status, values=[self._t(v) for v in ["O‘rganishga yuborilgan", "O‘rganib chiqildi / Bartaraf etildi", "Ijobiy hal etildi", "Intizomiy chora ko‘rildi", "Asossiz deb topildi"]], width=230, font=ctk.CTkFont(size=12))
        cb_status.set(self._t(str(rec.get('Ijro_Holati', 'O‘rganishga yuborilgan'))))
        cb_status.pack(side="left", padx=(0, 15))

        ctk.CTkLabel(row_status, text=self._t("Ko‘rilgan chora:"), font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=(0, 8))
        
        cb_chora = ctk.CTkComboBox(row_status, values=[self._t(v) for v in ["Chora ko‘rilmagan", "Xayfsan e'lon qilindi", "Jarima qo‘llandi", "Lavozimidan ozod etildi", "Prokuraturaga yuborildi", "Asossiz deb topildi"]], width=190, font=ctk.CTkFont(size=12))
        cb_chora.set(self._t(str(rec.get('Chora_Turi', 'Chora ko‘rilmagan'))))
        cb_chora.pack(side="left")

        ctk.CTkLabel(action_frame, text=self._t("Hududiy komplayens xodimining o‘rganish xulosasi:"), font=ctk.CTkFont(size=12, weight="bold")).pack(padx=15, pady=(5, 1), anchor="w")
        
        tb_natija = ctk.CTkTextbox(action_frame, height=90, wrap="word", font=ctk.CTkFont(size=12))
        
        natija_text = str(rec.get('Organish_Natijasi', ''))
        tb_natija.insert("1.0", self._t(natija_text) if self.is_cyrillic else natija_text)
        tb_natija.pack(fill="x", padx=15, pady=(0, 6))

        self.attached_file_path = str(rec.get('Biriktirilgan_Fayl', ''))
        file_box = ctk.CTkFrame(action_frame, fg_color="#FFFFFF", corner_radius=5, border_width=1, border_color="#CBD5E1")
        file_box.pack(fill="x", padx=15, pady=(0, 8))
        
        status_text = f"📁 {self._t('Biriktirilgan hujjat:')} {os.path.basename(self.attached_file_path)}" if self.attached_file_path else f"📁 {self._t('Biriktirilgan hujjat: Yoq')}"
        color_text = "#0F2537" if self.attached_file_path else "#64748B"
        self.lbl_file_status = ctk.CTkLabel(file_box, text=status_text, font=ctk.CTkFont(size=12, weight="bold"), text_color=color_text)
        self.lbl_file_status.pack(side="left", padx=12, pady=6)
        
        btn_attach = ctk.CTkButton(file_box, text=self._t("📎 Hujjat yuklash"), width=120, height=26, fg_color=self.t_colors["btn"], hover_color=self.t_colors["hover"], font=ctk.CTkFont(size=11, weight="bold"), command=self._attach_file)
        btn_attach.pack(side="right", padx=8, pady=4)
        
        ctk.CTkButton(file_box, text=self._t("👁 Ko'rish"), width=70, height=26, fg_color="#475569", hover_color="#334155", font=ctk.CTkFont(size=11, weight="bold"), command=self._open_attached_file).pack(side="right", padx=4, pady=4)

        row_save = ctk.CTkFrame(action_frame, fg_color="transparent")
        row_save.pack(pady=(0, 10))

        def save_changes():
            st = self._to_latin(cb_status.get())
            ms = self._to_latin(cb_masul_item.get())
            ch = self._to_latin(cb_chora.get())
            
            nat_xom = tb_natija.get("1.0", "end-1c")
            nat = self._to_latin(nat_xom) if self.is_cyrillic else nat_xom
            
            if st in ["Ijobiy hal etildi", "Intizomiy chora ko‘rildi", "Asossiz deb topildi", "O‘rganib chiqildi / Bartaraf etildi"] or ch == "Asossiz deb topildi":
                if not self.attached_file_path or not os.path.exists(self.attached_file_path):
                    messagebox.showwarning(self._t("Fayl yo'q!"), self._t("Diqqat: Murojaat o'rganilganligini tasdiqlovchi hujjat (PDF/Rasm) biriktirilishi shart! Faylsiz saqlash mumkin emas."))
                    return
                    
            self.loader.db.update_murojaat_ijro(m_id, st, nat, self.attached_file_path, ms, ch)
            self.loader.refresh_data()
            messagebox.showinfo(self._t("Saqlandi"), self._t(f"#{m_id} sonli murojaat ijrosi saqlandi!"))

        def download_resolution():
            rec_updated = self.loader.df[self.loader.df['#'] == m_id].iloc[0].copy()
            
            nat_xom = tb_natija.get("1.0", "end-1c").strip()
            rec_updated['Organish_Natijasi'] = self._to_latin(nat_xom) if self.is_cyrillic else nat_xom
            rec_updated['Ijro_Holati'] = self._to_latin(cb_status.get())
            rec_updated['Chora_Turi'] = self._to_latin(cb_chora.get())
            rec_updated['Masul_Komplayens'] = self._to_latin(cb_masul_item.get())
            
            fp = filedialog.asksaveasfilename(defaultextension=".docx", initialfile=f"Xulosa_{m_id}.docx")
            if fp:
                ReportGenerator.generate_resolution_report(rec_updated, fp, self._t(sets.get("report_header", "O‘ZBEKISTON RESPUBLIKASI KADASTR AGENTLIGI\nKORRUPSIYAGA QARSHI KURASHISH BO‘LIMI")))
                messagebox.showinfo(self._t("Tayyor"), self._t("Rasmiy xulosa ma'lumotnomasi yuklab olindi!"))
                os.system(f'explorer /select,"{os.path.abspath(fp)}"')

        btn_save = ctk.CTkButton(row_save, text=self._t("💾 Saqlash"), fg_color="#1B5E20", hover_color="#2E7D32", width=130, height=32, font=ctk.CTkFont(size=12, weight="bold"), command=save_changes)
        btn_save.pack(side="left", padx=10)
        
        btn_word_res = ctk.CTkButton(row_save, text=self._t("📄 Xulosa ma'lumotnomasini yuklash (Word)"), fg_color="#8B3A2B", hover_color="#A94442", width=250, height=32, font=ctk.CTkFont(size=12, weight="bold"), command=download_resolution)
        btn_word_res.pack(side="left", padx=10)

        if self.role == "kuzatuvchi":
            cb_masul_item.configure(state="disabled")
            cb_status.configure(state="disabled")
            cb_chora.configure(state="disabled")
            tb_natija.configure(state="disabled")
            btn_tg.configure(state="disabled", fg_color="#95A5A6")
            btn_attach.configure(state="disabled", fg_color="#95A5A6")
            btn_save.configure(state="disabled", fg_color="#95A5A6")

    def _attach_file(self):
        fp = filedialog.askopenfilename(title=self._t("Hujjatni tanlang"), filetypes=[(self._t("Hujjatlar va Rasmlar"), "*.pdf *.png *.jpg *.jpeg *.docx *.doc *.xlsx")])
        if fp:
            attach_dir = os.path.join("data", "attachments")
            os.makedirs(attach_dir, exist_ok=True)
            dest = os.path.join(attach_dir, os.path.basename(fp))
            shutil.copy2(fp, dest)
            self.attached_file_path = dest
            self.lbl_file_status.configure(text=f"📁 {self._t('Biriktirilgan hujjat:')} {os.path.basename(dest)}", text_color="#0F2537")

    def _open_attached_file(self):
        if self.attached_file_path and os.path.exists(self.attached_file_path):
            try: 
                os.startfile(self.attached_file_path)
            except Exception as e: 
                messagebox.showerror(self._t("Xatolik"), self._t(f"Faylni ochishda xato: {str(e)}"))
        else: 
            messagebox.showwarning(self._t("Fayl yo'q"), self._t("Ushbu murojaatga hali hech qanday hujjat biriktirilmagan!"))

    # ================= 4-POG'ONA: TELEFON MUROJAAT QABUL QILISH =================
    def show_add_phone_view(self):
        self.current_view_func = self.show_add_phone_view
        if self.show_dashboard_view not in self.view_stack:
            self.view_stack.append(self.show_dashboard_view)
            
        self.btn_back.configure(state="normal")
        self.lbl_path.configure(text=self._t("Asosiy oyna  /  Ishonch telefoni orqali murojaat qabul qilish (+998-71-273-19-66)"))
        self._clear_container()

        main_box = ctk.CTkFrame(self.container, fg_color="#FFFFFF", corner_radius=6, border_width=1, border_color="#CBD5E1")
        main_box.pack(fill="both", expand=True, padx=4, pady=4)
        
        ctk.CTkLabel(main_box, text=self._t("📞 ISHONCH TELEFONI ORQALI MUROJAAT QABUL QILISH"), font=ctk.CTkFont(size=14, weight="bold"), text_color="#0F2537").pack(pady=(20, 5))
        ctk.CTkLabel(main_box, text=self._t("Ishonch raqami: +998-71-273-19-66 | Kelib tushgan vaqt: Avtomatik joriy vaqt"), font=ctk.CTkFont(size=11, slant="italic"), text_color="#64748B").pack(pady=(0, 15))

        form = ctk.CTkFrame(main_box, fg_color="#F8FAFC", corner_radius=6, border_width=1, border_color="#CBD5E1")
        form.pack(fill="x", padx=100, pady=10)
        
        ctk.CTkLabel(form, text=self._t("Fuqaro F.I.Sh.:"), font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=20, pady=(15, 2))
        e_fish = ctk.CTkEntry(form, placeholder_text=self._t("Familiyasi Ismi Otasining ismi"), width=500, font=ctk.CTkFont(size=12))
        e_fish.pack(anchor="w", padx=20)
        
        ctk.CTkLabel(form, text=self._t("Telefon raqami:"), font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=20, pady=(10, 2))
        e_tel = ctk.CTkEntry(form, placeholder_text="+998901234567", width=500, font=ctk.CTkFont(size=12))
        e_tel.insert(0, "+998")
        e_tel.pack(anchor="w", padx=20)

        row_geo = ctk.CTkFrame(form, fg_color="transparent")
        row_geo.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(row_geo, text=self._t("Viloyat:"), font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=(0, 5))
        cb_vil = ctk.CTkComboBox(row_geo, values=[self._t(v) for v in [
            "Toshkent shahri", "Toshkent viloyati", "Samarqand viloyati", "Buxoro viloyati", 
            "Farg'ona viloyati", "Andijon viloyati", "Namangan viloyati", "Qashqadaryo viloyati", 
            "Surxondaryo viloyati", "Jizzax viloyati", "Sirdaryo viloyati", "Navoiy viloyati", 
            "Xorazm viloyati", "Qoraqalpog'iston Respublikasi"
        ]], width=200, font=ctk.CTkFont(size=12))
        cb_vil.pack(side="left", padx=(0, 20))
        
        ctk.CTkLabel(row_geo, text=self._t("Tuman/Shahar:"), font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=(0, 5))
        e_tum = ctk.CTkEntry(row_geo, placeholder_text=self._t("Tuman nomi"), width=180, font=ctk.CTkFont(size=12))
        e_tum.pack(side="left")

        ctk.CTkLabel(form, text=self._t("Yo'nalish tarmog'i:"), font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=20, pady=(10, 2))
        cb_yon = ctk.CTkComboBox(form, values=[self._t(v) for v in [
            "Kadastr agentligi hududiy boshqarmasi xodimlarining xatti-harakatlari", 
            "Davlat kadastrlari palatasi hududiy boshqarmasi xodimlarining xatti-harakatlari"
        ]], width=500, font=ctk.CTkFont(size=12))
        cb_yon.pack(anchor="w", padx=20)
        
        ctk.CTkLabel(form, text=self._t("Murojaatning qisqacha mazmuni:"), font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=20, pady=(10, 2))
        tb_matn = ctk.CTkTextbox(form, height=140, wrap="word", font=ctk.CTkFont(size=12))
        tb_matn.pack(fill="x", padx=20, pady=(0, 15))

        def save_phone_entry():
            fish_val_xom = e_fish.get().strip()
            tel_val = e_tel.get().strip()
            vil_val_xom = cb_vil.get()
            tum_val_xom = e_tum.get().strip()
            yon_val_xom = cb_yon.get()
            matn_val_xom = tb_matn.get("1.0", "end-1c").strip()
            
            if not fish_val_xom or not tel_val or not matn_val_xom: 
                messagebox.showwarning(self._t("To'ldirish shart"), self._t("Iltimos, barcha maydonlarni to'liq kiriting!"))
                return
                
            fish_val = self._to_latin(fish_val_xom) if self.is_cyrillic else fish_val_xom
            vil_val = self._to_latin(vil_val_xom) if self.is_cyrillic else vil_val_xom
            tum_val = self._to_latin(tum_val_xom) if self.is_cyrillic else tum_val_xom
            yon_val = self._to_latin(yon_val_xom) if self.is_cyrillic else yon_val_xom
            matn_val = self._to_latin(matn_val_xom) if self.is_cyrillic else matn_val_xom
            
            masul = "Davlat kadastrlari palatasi hududiy komplayens xodimi" if "palata" in yon_val.lower() else "Kadastr agentligi hududiy komplayens xodimi"
            new_id = self.loader.db.insert_phone_murojaat(fish_val, tel_val, vil_val, tum_val, yon_val, matn_val, masul)
            
            self.loader.refresh_data()
            self._redraw_entire_ui()
            messagebox.showinfo(self._t("Qabul qilindi"), self._t(f"Murojaat muvaffaqiyatli ro'yxatga olindi!\nTartib raqami: #{new_id}"))

        ctk.CTkButton(main_box, text=self._t("💾 Murojaatni ro'yxatga olish"), height=38, width=250, fg_color="#1B5E20", hover_color="#2E7D32", font=ctk.CTkFont(size=13, weight="bold"), command=save_phone_entry).pack(pady=20)

    # ================= 5-POG'ONA: HUDUDIY XODIMLAR REYESTRI =================
    def show_xodimlar_view(self):
        self.current_view_func = self.show_xodimlar_view
        if self.show_dashboard_view not in self.view_stack:
            self.view_stack.append(self.show_dashboard_view)
            
        self.btn_back.configure(state="normal")
        self.lbl_path.configure(text=self._t("Asosiy oyna  /  Hududiy komplayens xodimlari"))
        self._clear_container()

        main_box = ctk.CTkFrame(self.container, fg_color="#FFFFFF", corner_radius=6, border_width=1, border_color="#CBD5E1")
        main_box.pack(fill="both", expand=True, padx=4, pady=4)
        
        ctk.CTkLabel(main_box, text=self._t("👥 Hududiy komplayens xodimlari (Tahrirlash uchun qator ustiga bosing):"), font=ctk.CTkFont(size=13, weight="bold"), text_color="#0F2537").pack(anchor="w", padx=15, pady=10)

        table_frame = ctk.CTkFrame(main_box, fg_color="transparent")
        table_frame.pack(fill="both", expand=True, padx=15, pady=(0, 10))
        
        cols = ("id", "viloyat", "tashkilot", "fish", "telefon", "telegram")
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Xod.Treeview", rowheight=30, font=("Calibri", 11), bordercolor="#94A3B8", borderwidth=1)
        style.configure("Xod.Treeview.Heading", font=("Calibri", 11, "bold"), background=self.t_colors["primary"], foreground="#FFFFFF")

        tree = ttk.Treeview(table_frame, columns=cols, show="headings", style="Xod.Treeview", selectmode="browse")
        tree.heading("id", text="#")
        tree.heading("viloyat", text=self._t("Hudud"))
        tree.heading("tashkilot", text=self._t("Tashkilot"))
        tree.heading("fish", text=self._t("F.I.Sh."))
        tree.heading("telefon", text=self._t("Telefon raqami"))
        tree.heading("telegram", text=self._t("Telegram Username"))
        
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
            for _, r in self.loader.db.get_xodimlar().iterrows(): 
                tree.insert("", "end", values=(r['id'], self._t(r['viloyat']), self._t(r['tashkilot_turi']), self._t(r['fish']), r['telefon'], r['telegram_username']))
                
        populate_x()

        edit_frame = ctk.CTkFrame(main_box, fg_color="#F8FAFC", corner_radius=6, border_width=1, border_color="#CBD5E1")
        edit_frame.pack(fill="x", padx=15, pady=(0, 12))
        
        ctk.CTkLabel(edit_frame, text=self._t("Tanlangan xodimni tahrirlash:"), font=ctk.CTkFont(size=12, weight="bold"), text_color="#0F2537").pack(anchor="w", padx=12, pady=(6, 4))
        
        row_inputs = ctk.CTkFrame(edit_frame, fg_color="transparent")
        row_inputs.pack(fill="x", padx=12, pady=4)
        
        ctk.CTkLabel(row_inputs, text=self._t("F.I.Sh:")).pack(side="left", padx=4)
        e_fish = ctk.CTkEntry(row_inputs, width=200)
        e_fish.pack(side="left", padx=4)
        
        ctk.CTkLabel(row_inputs, text=self._t("Telefon:")).pack(side="left", padx=4)
        e_tel = ctk.CTkEntry(row_inputs, width=140)
        e_tel.pack(side="left", padx=4)
        
        ctk.CTkLabel(row_inputs, text=self._t("Telegram:")).pack(side="left", padx=4)
        e_tg = ctk.CTkEntry(row_inputs, width=160)
        e_tg.pack(side="left", padx=4)

        selected_id = [None]
        def on_select(event):
            sel = tree.selection()
            if not sel: return
            vals = tree.item(sel[0], "values")
            selected_id[0] = vals[0]
            e_fish.delete(0, 'end')
            e_fish.insert(0, vals[3])
            e_tel.delete(0, 'end')
            e_tel.insert(0, vals[4])
            e_tg.delete(0, 'end')
            e_tg.insert(0, vals[5])
            
        tree.bind("<<TreeviewSelect>>", on_select)

        def save_x():
            if not selected_id[0]: 
                messagebox.showwarning(self._t("Diqqat"), self._t("Jadvaldan biror xodimni tanlang!"))
                return
            fish_v = self._to_latin(e_fish.get().strip()) if self.is_cyrillic else e_fish.get().strip()
            self.loader.db.save_xodim(selected_id[0], fish_v, e_tel.get().strip(), e_tg.get().strip())
            populate_x()
            messagebox.showinfo(self._t("Saqlandi"), self._t("Hududiy xodim ma'lumotlari muvaffaqiyatli saqlandi!"))

        ctk.CTkButton(row_inputs, text=self._t("💾 Saqlash"), width=100, height=28, fg_color="#1B5E20", hover_color="#2E7D32", font=ctk.CTkFont(size=11, weight="bold"), command=save_x).pack(side="left", padx=10)

    # ================= 6-POG'ONA: ADMIN PANEL (FOYDALANUVCHILARNI QO'SHIB) =================
    def show_settings_view(self):
        self.current_view_func = self.show_settings_view
        if self.show_dashboard_view not in self.view_stack:
            self.view_stack.append(self.show_dashboard_view)
            
        self.btn_back.configure(state="normal")
        self.lbl_path.configure(text=self._t("Asosiy oyna  /  Tizim sozlamalari (Admin Panel)"))
        self._clear_container()

        sets = self.loader.db.get_settings()

        main_box = ctk.CTkScrollableFrame(self.container, fg_color="#FFFFFF", corner_radius=6, border_width=1, border_color="#CBD5E1")
        main_box.pack(fill="both", expand=True, padx=4, pady=4)
        
        ctk.CTkLabel(main_box, text=self._t("⚙️ DASTUR SOZLAMALARI"), font=ctk.CTkFont(size=14, weight="bold"), text_color="#0F2537").pack(pady=(20, 15))

        form = ctk.CTkFrame(main_box, fg_color="#F8FAFC", corner_radius=6, border_width=1, border_color="#CBD5E1")
        form.pack(fill="x", padx=100, pady=10)

        row_sla = ctk.CTkFrame(form, fg_color="transparent")
        row_sla.pack(fill="x", padx=20, pady=(20, 10))
        
        ctk.CTkLabel(row_sla, text=self._t("Ijro muddati (SLA kun):"), font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=(0, 10))
        e_sla = ctk.CTkEntry(row_sla, width=80, font=ctk.CTkFont(size=12))
        e_sla.insert(0, sets.get("sla_days", "2"))
        e_sla.pack(side="left")
        ctk.CTkLabel(row_sla, text=self._t("kun (Asosiy ijro xavf chegarasi)"), font=ctk.CTkFont(size=12)).pack(side="left", padx=5)

        ctk.CTkLabel(form, text=self._t("Word Xulosa Ma'lumotnomasi Sarlavhasi (Shapka):"), font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=20, pady=(15, 2))
        tb_header = ctk.CTkTextbox(form, height=60, font=ctk.CTkFont(size=12))
        
        h_text = sets.get("report_header", "O‘ZBEKISTON RESPUBLIKASI KADASTR AGENTLIGI\nKORRUPSIYAGA QARSHI KURASHISH BO‘LIMI")
        tb_header.insert("1.0", self._t(h_text) if self.is_cyrillic else h_text)
        tb_header.pack(fill="x", padx=20)

        ctk.CTkLabel(form, text=self._t("Telegramga xabar yuborish shabloni:"), font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=20, pady=(15, 2))
        tb_tg = ctk.CTkTextbox(form, height=180, font=ctk.CTkFont(size=12))
        t_text = sets.get("tg_template", "Murojaat № {id}\nSana: {sana}\nMatn: {matn}")
        tb_tg.insert("1.0", self._t(t_text) if self.is_cyrillic else t_text)
        tb_tg.pack(fill="x", padx=20)

        def save_settings():
            new_sets = {
                "sla_days": e_sla.get().strip(), 
                "report_header": self._to_latin(tb_header.get("1.0", "end-1c").strip()) if self.is_cyrillic else tb_header.get("1.0", "end-1c").strip(), 
                "tg_template": self._to_latin(tb_tg.get("1.0", "end-1c").strip()) if self.is_cyrillic else tb_tg.get("1.0", "end-1c").strip()
            }
            self.loader.db.update_settings(new_sets)
            messagebox.showinfo(self._t("Saqlandi"), self._t("Sozlamalar muvaffaqiyatli saqlandi! O'zgarishlar darhol kuchga kirdi."))

        ctk.CTkButton(form, text=self._t("💾 Sozlamalarni saqlash"), height=32, width=200, fg_color="#1B5E20", hover_color="#2E7D32", font=ctk.CTkFont(size=12, weight="bold"), command=save_settings).pack(pady=15)

        ctk.CTkLabel(main_box, text=self._t("👥 FOYDALANUVCHILAR VA ROLLARI (LOGIN / PAROL)"), font=ctk.CTkFont(size=14, weight="bold"), text_color="#0F2537").pack(pady=(30, 10))
        
        u_frame = ctk.CTkFrame(main_box, fg_color="#F8FAFC", corner_radius=6, border_width=1, border_color="#CBD5E1")
        u_frame.pack(fill="x", padx=100, pady=10)
        
        tree_u = ttk.Treeview(u_frame, columns=("id", "user", "pass", "role"), show="headings", height=6)
        style = ttk.Style()
        style.configure("Treeview.Heading", font=("Calibri", 11, "bold"), background=self.t_colors["primary"], foreground="#FFFFFF")

        tree_u.heading("id", text="ID")
        tree_u.heading("user", text=self._t("Login"))
        tree_u.heading("pass", text=self._t("Parol"))
        tree_u.heading("role", text=self._t("Foydalanuvchi Roli"))
        
        tree_u.column("id", width=50, anchor="center")
        tree_u.column("user", width=200)
        tree_u.column("pass", width=200)
        tree_u.column("role", width=150, anchor="center")
        tree_u.pack(fill="x", padx=15, pady=(15, 10))
        
        def populate_users():
            tree_u.delete(*tree_u.get_children())
            for _, r in self.loader.db.get_all_users().iterrows(): 
                tree_u.insert("", "end", values=(r['id'], r['username'], r['password'], self._t(r['role'].upper())))
                
        populate_users()

        u_input = ctk.CTkFrame(u_frame, fg_color="transparent")
        u_input.pack(fill="x", padx=15, pady=10)
        
        ctk.CTkLabel(u_input, text=self._t("Login:")).pack(side="left", padx=5)
        e_u = ctk.CTkEntry(u_input, width=150)
        e_u.pack(side="left", padx=5)
        
        ctk.CTkLabel(u_input, text=self._t("Parol:")).pack(side="left", padx=5)
        e_p = ctk.CTkEntry(u_input, width=150)
        e_p.pack(side="left", padx=5)
        
        ctk.CTkLabel(u_input, text=self._t("Rol:")).pack(side="left", padx=5)
        cb_r = ctk.CTkComboBox(u_input, values=["admin", "kuzatuvchi"], width=120)
        cb_r.set("kuzatuvchi")
        cb_r.pack(side="left", padx=5)

        sel_uid = [None]
        def on_u_select(e):
            s = tree_u.selection()
            if not s: return
            v = tree_u.item(s[0], "values")
            sel_uid[0] = v[0]
            e_u.delete(0, 'end')
            e_u.insert(0, v[1])
            e_p.delete(0, 'end')
            e_p.insert(0, v[2])
            role_val = self._to_latin(v[3]).lower()
            cb_r.set(role_val if role_val in ["admin", "kuzatuvchi"] else "kuzatuvchi")
            
        tree_u.bind("<<TreeviewSelect>>", on_u_select)

        def add_u():
            if not e_u.get().strip() or not e_p.get().strip(): 
                messagebox.showwarning(self._t("Xato"), self._t("Login va parolni kiriting!"))
                return
            if self.loader.db.add_user(e_u.get().strip(), e_p.get().strip(), cb_r.get()):
                populate_users()
                messagebox.showinfo(self._t("Saqlandi"), self._t("Yangi foydalanuvchi tizimga qo'shildi."))
            else: 
                messagebox.showerror(self._t("Xato"), self._t("Bu login band! Boshqa login kiriting."))
        
        def upd_u():
            if not sel_uid[0]: 
                messagebox.showwarning(self._t("Xato"), self._t("Ro'yxatdan foydalanuvchini tanlang!"))
                return
            self.loader.db.update_user(sel_uid[0], e_u.get().strip(), e_p.get().strip(), cb_r.get())
            populate_users()
            messagebox.showinfo(self._t("Saqlandi"), self._t("Ma'lumot yangilandi."))
        
        def del_u():
            if not sel_uid[0]: 
                messagebox.showwarning(self._t("Xato"), self._t("Ro'yxatdan tanlang!"))
                return
            if str(sel_uid[0]) == "1": 
                messagebox.showerror(self._t("Xato"), self._t("Asosiy adminni o'chirib bo'lmaydi!"))
                return
            self.loader.db.delete_user(sel_uid[0])
            populate_users()
            messagebox.showinfo(self._t("O'chirildi"), self._t("Foydalanuvchi o'chirildi."))

        btn_row = ctk.CTkFrame(u_frame, fg_color="transparent")
        btn_row.pack(pady=10)
        
        ctk.CTkButton(btn_row, text=self._t("➕ Yangi qo'shish"), width=120, fg_color=self.t_colors["btn"], hover_color=self.t_colors["hover"], command=add_u).pack(side="left", padx=5)
        ctk.CTkButton(btn_row, text=self._t("💾 O'zgarishni saqlash"), width=130, fg_color="#27AE60", command=upd_u).pack(side="left", padx=5)
        ctk.CTkButton(btn_row, text=self._t("🗑 O'chirish"), width=100, fg_color="#C0392B", hover_color="#A93226", command=del_u).pack(side="left", padx=5)


    # ================= 7-POG'ONA: KIRISHLAR TARIXI (AUDIT LOG) =================
    def show_audit_view(self):
        win = ctk.CTkToplevel(self)
        win.title(self._t("Tizimga kirishlar tarixi (Audit Log)"))
        win.geometry("850x500")
        win.grab_set()

        ctk.CTkLabel(win, text=self._t("👥 Tizimga kim, qachon va qaysi kompyuterdan kirgani tarixi"), font=ctk.CTkFont(size=16, weight="bold"), text_color="#0F2537").pack(pady=15)

        t_box = ctk.CTkFrame(win, fg_color="#FFFFFF", border_width=1, border_color="#CBD5E1")
        t_box.pack(padx=15, pady=5, fill="both", expand=True)

        cols = ("#", "user", "role", "time", "comp")
        tree = ttk.Treeview(t_box, columns=cols, show="headings", height=15)
        
        style = ttk.Style()
        style.configure("Treeview.Heading", font=("Calibri", 11, "bold"), background=self.t_colors["primary"], foreground="#FFFFFF")
        
        tree.heading("#", text="№")
        tree.heading("user", text=self._t("Foydalanuvchi logini"))
        tree.heading("role", text=self._t("Roli"))
        tree.heading("time", text=self._t("Kirgan vaqti"))
        tree.heading("comp", text=self._t("Kompyuter nomi"))

        tree.column("#", width=50, anchor="center")
        tree.column("user", width=150, anchor="center")
        tree.column("role", width=140, anchor="center")
        tree.column("time", width=180, anchor="center")
        tree.column("comp", width=180, anchor="center")
        
        vsb = ttk.Scrollbar(t_box, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        try:
            df_logs = self.loader.db.get_audit_logs()
            for _, r in df_logs.iterrows():
                r_str = self._t("Kuzatuvchi (Rahbar)") if str(r.get('Rol', '')).lower() == 'kuzatuvchi' else self._t("Administrator")
                tree.insert("", "end", values=(r.get('#', ''), r.get('Foydalanuvchi', ''), r_str, r.get('Kirish vaqti', ''), self._t(r.get('Kompyuter', ''))))
        except Exception:
            pass

    # ================= EKSPORT VA YUKLASH =================
    def _import_excel(self):
        fp = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx *.xls")])
        if fp:
            try: 
                self.loader.load_from_excel(fp)
                self._redraw_entire_ui()
                messagebox.showinfo(self._t("Baza yangilandi"), self._t("Yangi murojaatlar muvaffaqiyatli yuklandi!"))
            except Exception as e: 
                messagebox.showerror(self._t("Xatolik"), self._t(f"Yuklashda xato: {str(e)}"))

    def _export_excel(self):
        manba = getattr(self, 'selected_manba', 'Barchasi')
        if 'Telegram' in manba: 
            fname = "Telegram_bot_murojaatlar.xlsx"
        elif 'Ishonch' in manba: 
            fname = "Ishonch_telefoni_murojaatlar.xlsx"
        else: 
            fname = "Barcha_murojaatlar_Umumiy.xlsx"
            
        fp = filedialog.asksaveasfilename(defaultextension=".xlsx", initialfile=fname)
        if fp: 
            ReportGenerator.export_excel(self.loader.filtered_df, fp)
            messagebox.showinfo(self._t("Tayyor"), self._t(f"{manba} ma'lumotlari saqlandi!"))

    def _export_word(self):
        fp = filedialog.asksaveasfilename(defaultextension=".docx", initialfile="Rahbariyatga_Malumotnoma.docx")
        if fp:
            sets = self.loader.db.get_settings()
            period_val = self._t(getattr(self, 'selected_period', 'Barchasi'))
            ReportGenerator.export_word_report(
                self.loader.get_kpi_stats(), 
                self.loader.filtered_df['Viloyat'].value_counts(), 
                fp, 
                period_val, 
                self._t(sets.get("report_header", "O‘ZBEKISTON RESPUBLIKASI KADASTR AGENTLIGI"))
            )
            messagebox.showinfo(self._t("Tayyor"), self._t("Rasmiy Word ma'lumotnomasi saqlandi!"))

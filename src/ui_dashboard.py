import customtkinter as ctk
from tkinter import ttk, filedialog, messagebox
import tkinter as tk
import os
import re
import sys
import subprocess
import shutil
import urllib.parse
import webbrowser
from datetime import datetime
import pandas as pd
from PIL import Image, ImageDraw
from src.report_generator import ReportGenerator

# ================= 10 XIL RANG VA MAVZULAR BAZASI =================
THEMES = {
    "Navy (Asl)": {"primary": "#0F2537", "btn": "#1E3A56", "hover": "#2A4D73"},
    "Tungi (Midnight)": {"primary": "#1E3A8A", "btn": "#2563EB", "hover": "#3B82F6"},
    "O'rmon (Forest)": {"primary": "#064E3B", "btn": "#059669", "hover": "#10B981"},
    "Bordo (Crimson)": {"primary": "#7F1D1D", "btn": "#B91C1C", "hover": "#DC2626"},
    "Binafsha (Purple)": {"primary": "#4C1D95", "btn": "#7C3AED", "hover": "#8B5CF6"},
    "Kofe (Mocha)": {"primary": "#451A03", "btn": "#92400E", "hover": "#B45309"},
    "Dengiz (Teal)": {"primary": "#134E4A", "btn": "#0F766E", "hover": "#14B8A6"},
    "Qora (Dark)": {"primary": "#111827", "btn": "#374151", "hover": "#4B5563"},
    "Kulrang (Slate)": {"primary": "#334155", "btn": "#475569", "hover": "#64748B"},
    "Bronza (Bronze)": {"primary": "#553C13", "btn": "#8B6B22", "hover": "#AA8833"},
}


def _is_null(value):
    if value is None:
        return True
    try:
        result = pd.isna(value)
        return bool(result) if not hasattr(result, "__len__") else False
    except (TypeError, ValueError):
        return False


def ensure_app_logo():
    os.makedirs("assets", exist_ok=True)
    logo_path = os.path.join("assets", "compliance_logo.png")
    if not os.path.exists(logo_path):
        img = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.polygon([(64, 6), (118, 26), (118, 76), (64, 122), (10, 76), (10, 26)],
                     fill="#0F2537", outline="#D4AF37", width=4)
        draw.polygon([(64, 16), (108, 32), (108, 72), (64, 110), (20, 72), (20, 32)],
                     fill="#16324F")
        draw.line([(64, 38), (64, 92)], fill="#D4AF37", width=5)
        draw.line([(40, 48), (88, 48)], fill="#D4AF37", width=4)
        img.save(logo_path, format="PNG")
    return logo_path


def reveal_in_file_manager(filepath):
    filepath = os.path.abspath(filepath)
    try:
        if sys.platform == "win32":
            subprocess.Popen(["explorer", "/select,", filepath])
        elif sys.platform == "darwin":
            subprocess.Popen(["open", "-R", filepath])
        else:
            subprocess.Popen(["xdg-open", os.path.dirname(filepath)])
    except (OSError, FileNotFoundError) as e:
        messagebox.showwarning("Diqqat", f"Fayl joyini ochib bo'lmadi: {e}")


def sanitize_telegram_username(name):
    return re.sub(r"[^a-zA-Z0-9_]", "", str(name or "").strip().lstrip("@"))


def sanitize_phone(phone):
    return re.sub(r"\D", "", str(phone or ""))


LAT_TO_CYR = [
    ("SH", "Ш"), ("Sh", "Ш"), ("sH", "ш"), ("sh", "ш"),
    ("CH", "Ч"), ("Ch", "Ч"), ("cH", "ч"), ("ch", "ч"),
    ("O'", "Ў"), ("O‘", "Ў"), ("O`", "Ў"), ("o'", "ў"), ("o‘", "ў"), ("o`", "ў"),
    ("G'", "Ғ"), ("G‘", "Ғ"), ("G`", "Ғ"), ("g'", "ғ"), ("g‘", "ғ"), ("g`", "ғ"),
    ("YO", "Ё"), ("Yo", "Ё"), ("yO", "ё"), ("yo", "ё"),
    ("YU", "Ю"), ("Yu", "Ю"), ("yU", "ю"), ("yu", "ю"),
    ("YA", "Я"), ("Ya", "Я"), ("yA", "я"), ("ya", "я"),
    ("TS", "Ц"), ("Ts", "Ц"), ("tS", "ц"), ("ts", "ц"),
    ("YE", "Е"), ("Ye", "Е"), ("yE", "е"), ("ye", "е"),
    ("A", "А"), ("a", "а"), ("B", "Б"), ("b", "б"), ("D", "Д"), ("d", "д"),
    ("E", "Е"), ("e", "е"), ("F", "Ф"), ("f", "ф"), ("G", "Г"), ("g", "г"),
    ("H", "Ҳ"), ("h", "ҳ"), ("I", "И"), ("i", "и"), ("J", "Ж"), ("j", "ж"),
    ("K", "К"), ("k", "к"), ("L", "Л"), ("l", "л"), ("M", "М"), ("m", "м"),
    ("N", "Н"), ("n", "н"), ("O", "О"), ("o", "о"), ("P", "П"), ("p", "п"),
    ("Q", "Қ"), ("q", "қ"), ("R", "Р"), ("r", "р"), ("S", "С"), ("s", "с"),
    ("T", "Т"), ("t", "т"), ("U", "У"), ("u", "у"), ("V", "В"), ("v", "в"),
    ("X", "Х"), ("x", "х"), ("Y", "Й"), ("y", "й"), ("Z", "З"), ("z", "з"),
    ("'", "ъ"), ("‘", "ъ"), ("`", "ъ"),
]

CYR_TO_LAT = [
    ("Ш", "Sh"), ("ш", "sh"),
    ("Ч", "Ch"), ("ч", "ch"),
    ("Ў", "O'"), ("ў", "o'"),
    ("Ғ", "G'"), ("ғ", "g'"),
    ("Ё", "Yo"), ("ё", "yo"),
    ("Ю", "Yu"), ("ю", "yu"),
    ("Я", "Ya"), ("я", "ya"),
    ("Ц", "Ts"), ("ц", "ts"),
    ("А", "A"), ("а", "a"), ("Б", "B"), ("б", "b"), ("Д", "D"), ("д", "d"),
    ("Е", "E"), ("е", "e"), ("Ф", "F"), ("ф", "f"), ("Г", "G"), ("г", "g"),
    ("Ҳ", "H"), ("ҳ", "h"), ("И", "I"), ("и", "i"), ("Ж", "J"), ("ж", "j"),
    ("К", "K"), ("к", "k"), ("Л", "L"), ("л", "l"), ("М", "M"), ("м", "m"),
    ("Н", "N"), ("н", "n"), ("О", "O"), ("о", "o"), ("П", "P"), ("п", "p"),
    ("Қ", "Q"), ("қ", "q"), ("Р", "R"), ("р", "r"), ("С", "S"), ("с", "s"),
    ("Т", "T"), ("т", "t"), ("У", "U"), ("у", "u"), ("В", "V"), ("в", "v"),
    ("Х", "X"), ("х", "x"), ("Й", "Y"), ("й", "y"), ("З", "Z"), ("з", "z"),
    ("Ъ", "'"), ("ъ", "'"),
]


class DashboardApp(ctk.CTk):
    def __init__(self, data_loader, current_role="admin"):
        super().__init__()
        self.loader = data_loader
        self.role = current_role

        self.current_theme = "Navy (Asl)"
        self.is_cyrillic = True

        self.geometry("1440x920")
        self.minsize(1220, 740)
        ctk.set_appearance_mode("Light")
        self.configure(fg_color="#ECEFF4")

        self.view_stack = []
        self._suppress_stack_push = False
        self.current_view_func = None

        self.attached_file_path = ""

        try:
            self.logo_path = ensure_app_logo()
            icon_img = tk.PhotoImage(file=self.logo_path)
            self.iconphoto(False, icon_img)
            self._icon_photo = ctk.CTkImage(Image.open(self.logo_path), size=(32, 32))
        except (OSError, tk.TclError):
            self._icon_photo = None

        self.main_wrapper = ctk.CTkFrame(self, fg_color="transparent")
        self.main_wrapper.pack(fill="both", expand=True)

        self._redraw_entire_ui(initial=True)

    def _t(self, text):
        if _is_null(text):
            return ""
        text = str(text)
        if not self.is_cyrillic:
            return text
        for eng, rus in LAT_TO_CYR:
            text = text.replace(eng, rus)
        return text

    def _to_latin(self, text):
        if _is_null(text):
            return ""
        text = str(text)
        if not self.is_cyrillic:
            return text
        for rus, eng in CYR_TO_LAT:
            text = text.replace(rus, eng)
        return text

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
            self.view_stack.clear()
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

        ctk.CTkButton(
            nav, text="🌐 " + ("Lotin" if self.is_cyrillic else "Krill"),
            width=80, height=34, fg_color=self.t_colors["btn"], hover_color=self.t_colors["hover"],
            font=ctk.CTkFont(size=12, weight="bold"), command=self.toggle_lang
        ).pack(side="right", padx=10, pady=15)

        cb_theme = ctk.CTkComboBox(
            nav, values=[self._t(k) for k in THEMES.keys()], width=130, height=34,
            font=ctk.CTkFont(size=11, weight="bold"), command=self.change_theme
        )
        cb_theme.set(self._t(self.current_theme))
        cb_theme.pack(side="right", padx=4, pady=15)

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
                fg_color=self.t_colors["btn"], hover_color=self.t_colors["hover"],
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
                font=ctk.CTkFont(size=11, weight="bold"), command=self._pull_from_cloud
            ).pack(side="right", padx=15, pady=15)

    def _pull_from_cloud(self):
        try:
            self.loader.db.sync_pull_from_cloud()
            self.loader.refresh_data()
            self._redraw_entire_ui()
            messagebox.showinfo(self._t("Yangilandi"), self._t("Murojaatlar bulutdan olindi!"))
        except Exception as e:
            messagebox.showerror(self._t("Xatolik"), self._t(f"Bulutdan olishda xato: {e}"))

    def _clear_container(self):
        for widget in self.container.winfo_children():
            widget.destroy()

    def _go_back(self):
        if self.view_stack:
            prev_view = self.view_stack.pop()
            self._suppress_stack_push = True
            try:
                prev_view()
            finally:
                self._suppress_stack_push = False
        else:
            self._redraw_entire_ui(initial=True)

    def _push_current_to_stack(self):
        if self._suppress_stack_push:
            return
        if self.current_view_func is not None:
            self.view_stack.append(self.current_view_func)

    def show_dashboard_view(self):
        self.current_view_func = self.show_dashboard_view
        self.view_stack.clear()
        self.btn_back.configure(state="disabled")
        self.lbl_path.configure(text=self._t("Asosiy oyna  /  Tahliliy Dashboard"))
        self._clear_container()

        filter_box = ctk.CTkFrame(self.container, fg_color="#FFFFFF", corner_radius=6,
                                  border_width=1, border_color="#CBD5E1")
        filter_box.pack(fill="x", pady=(0, 8), padx=2)

        ctk.CTkLabel(filter_box, text=self._t("🔍 Qidiruv:"),
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color="#0F2537").pack(side="left", padx=(10, 2), pady=7)

        self.entry_dash_search = ctk.CTkEntry(
            filter_box, placeholder_text=self._t("F.I.Sh, tel, tuman..."),
            width=160, font=ctk.CTkFont(size=11))
        self.entry_dash_search.pack(side="left", padx=2, pady=7)
        self.entry_dash_search.bind("<Return>", self._apply_filters)

        ctk.CTkButton(
            filter_box, text=self._t("Topish"), width=55, height=28,
            fg_color=self.t_colors["primary"], hover_color=self.t_colors["hover"],
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self._apply_filters
        ).pack(side="left", padx=2, pady=7)

        ctk.CTkLabel(filter_box, text=self._t("⏳ Davr:"),
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color="#0F2537").pack(side="left", padx=(8, 2), pady=7)
        period_values = self.loader.get_available_periods()
        self.cb_period = ctk.CTkComboBox(
            filter_box, values=[self._t(v) for v in period_values],
            command=self._apply_filters, width=110, font=ctk.CTkFont(size=11))
        self.cb_period.set(self._t(getattr(self, 'selected_period', 'Barchasi')))
        self.cb_period.pack(side="left", padx=2, pady=7)

        ctk.CTkLabel(filter_box, text=self._t("📡 Manba:"),
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color="#0F2537").pack(side="left", padx=(8, 2), pady=7)
        self.cb_manba = ctk.CTkComboBox(
            filter_box,
            values=[self._t(v) for v in ["Barchasi", "Telegram bot", "Ishonch telefoni (+998-71-273-19-66)"]],
            command=self._apply_filters, width=220, font=ctk.CTkFont(size=11))
        self.cb_manba.set(self._t(getattr(self, 'selected_manba', 'Barchasi')))
        self.cb_manba.pack(side="left", padx=2, pady=7)

        ctk.CTkLabel(filter_box, text=self._t("🏢 Mas'ul:"),
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color="#0F2537").pack(side="left", padx=(8, 2), pady=7)
        self.cb_masul = ctk.CTkComboBox(
            filter_box,
            values=[self._t(v) for v in ["Barchasi", "Kadastr agentligi hududiy komplayens xodimi",
                                          "Davlat kadastrlari palatasi hududiy komplayens xodimi"]],
            command=self._apply_filters, width=240, font=ctk.CTkFont(size=11))
        self.cb_masul.set(self._t(getattr(self, 'selected_masul', 'Barchasi')))
        self.cb_masul.pack(side="left", padx=2, pady=7)

        ctk.CTkButton(
            filter_box, text=self._t("Tozalash"), width=60, height=28,
            fg_color="#64748B", hover_color="#475569",
            font=ctk.CTkFont(size=11), command=self._reset_filters
        ).pack(side="left", padx=6, pady=7)

        cards_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        cards_frame.pack(fill="x", pady=(0, 8))
        stats = self.loader.get_kpi_stats()
        f_df = self.loader.filtered_df

        cards = [
            (self._t("JAMI MUROJAATLAR"), stats['total'], self.t_colors["primary"],
             lambda: self.show_records_view(self._t("Barcha murojaatlar"), f_df)),
            (self._t("AGENTLIKDA O‘RGANISHDA"), stats['agentlik_organish'], "#1B4D7E",
             lambda: self.show_records_view(
                 self._t("Agentlikda o'rganishdagi"),
                 f_df[f_df['Ijro_Holati'].astype(str).str.contains("O‘rganishga yuborilgan|O'rganishda", case=False, na=False)
                      & f_df['Masul_Komplayens'].astype(str).str.contains("agentligi", case=False, na=False)])),
            (self._t("PALATADA O‘RGANISHDA"), stats['palata_organish'], "#4B3869",
             lambda: self.show_records_view(
                 self._t("Palatada o'rganishdagi"),
                 f_df[f_df['Ijro_Holati'].astype(str).str.contains("O‘rganishga yuborilgan|O'rganishda", case=False, na=False)
                      & f_df['Masul_Komplayens'].astype(str).str.contains("palata", case=False, na=False)])),
            (self._t("O‘RGANIB CHIQILGAN"), stats['natija_kiritilgan'], "#1B5E20",
             lambda: self.show_records_view(
                 self._t("O'rganib chiqilganlar"),
                 f_df[f_df['Ijro_Holati'].astype(str).str.contains(
                     "Bartaraf etildi|Ijobiy hal etildi|Intizomiy chora|O‘rganib chiqildi|Asossiz", case=False, na=False)
                     | f_df['Chora_Turi'].astype(str).str.contains("Asossiz", case=False, na=False)])),
            (self._t("ASOSSIZ DEB TOPILGAN"), stats['asossiz'], "#7F8C8D",
             lambda: self.show_records_view(
                 self._t("Asossiz deb topilganlar"),
                 f_df[f_df['Ijro_Holati'].astype(str).str.contains("Asossiz", case=False, na=False)
                      | f_df['Chora_Turi'].astype(str).str.contains("Asossiz", case=False, na=False)])),
        ]

        for i, (title, val, color, cmd) in enumerate(cards):
            card = ctk.CTkFrame(cards_frame, fg_color=color, corner_radius=6)
            card.grid(row=0, column=i, padx=3, sticky="nsew")
            cards_frame.grid_columnconfigure(i, weight=1)

            ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=10, weight="bold"),
                         text_color="#E2E8F0").pack(pady=(6, 1))
            ctk.CTkLabel(card, text=str(val), font=ctk.CTkFont(size=22, weight="bold"),
                         text_color="#FFFFFF").pack(pady=(0, 1))
            ctk.CTkButton(card, text=self._t("Ochish ➔"), width=70, height=20,
                          fg_color="transparent", border_width=1, border_color="#CBD5E1",
                          font=ctk.CTkFont(size=9), command=cmd).pack(pady=(0, 6))

        table_container = ctk.CTkFrame(self.container, fg_color="#FFFFFF", corner_radius=6,
                                       border_width=1, border_color="#CBD5E1")
        table_container.pack(fill="both", expand=True, padx=2, pady=(0, 8))

        ctk.CTkLabel(table_container, text=self._t("Viloyatlar kesimida murojaatlar nazorati:"),
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color="#0F2537").pack(anchor="w", padx=12, pady=(6, 3))

        table_frame = ctk.CTkFrame(table_container, fg_color="transparent")
        table_frame.pack(fill="both", expand=True, padx=12, pady=(0, 8))

        cols = ("viloyat", "jami", "tg_m", "tel_m", "agentlik_org", "palata_org", "hal_etilgan", "asossiz")
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Dash.Treeview", rowheight=27, font=("Calibri", 11),
                        bordercolor="#94A3B8", borderwidth=1)
        style.configure("Dash.Treeview.Heading", font=("Calibri", 11, "bold"),
                        background=self.t_colors["primary"], foreground="#FFFFFF")

        self.dash_tree = ttk.Treeview(table_frame, columns=cols, show="headings",
                                      style="Dash.Treeview", selectmode="browse")
        headings = {
            "viloyat": "Hudud nomi (Viloyat)", "jami": "Jami", "tg_m": "Telegram bot",
            "tel_m": "Ishonch telefoni", "agentlik_org": "Agentlikda",
            "palata_org": "Palatada", "hal_etilgan": "O‘rganilgan",
            "asossiz": "Asossiz deb topilgan",
        }
        for col, txt in headings.items():
            self.dash_tree.heading(col, text=self._t(txt))

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

        reg_groups = f_df.groupby('Viloyat') if not f_df.empty else []
        for idx, (reg, group) in enumerate(reg_groups):
            c_tot = len(group)
            c_tg = len(group[group['Manba'].astype(str).str.contains('Telegram', case=False, na=False)])
            c_tel = len(group[group['Manba'].astype(str).str.contains('Telefon|273-19-66', case=False, na=False)])
            is_org = group['Ijro_Holati'].astype(str).str.contains("O‘rganishga yuborilgan|O'rganishda",
                                                                  case=False, na=False)
            c_ag = len(group[is_org & group['Masul_Komplayens'].astype(str).str.contains("agentligi", case=False, na=False)])
            c_pa = len(group[is_org & group['Masul_Komplayens'].astype(str).str.contains("palata", case=False, na=False)])
            c_hal = len(group[group['Ijro_Holati'].astype(str).str.contains(
                "Bartaraf etildi|Ijobiy hal etildi|Intizomiy chora|O‘rganib chiqildi|Asossiz", case=False, na=False)
                | group['Chora_Turi'].astype(str

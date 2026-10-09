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
from src.logger import log, log_error, log_info, log_warning

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
    ("Ш", "Sh"), ("ш", "sh"), ("Ч", "Ch"), ("ч", "ch"),
    ("Ў", "O'"), ("ў", "o'"), ("Ғ", "G'"), ("ғ", "g'"),
    ("Ё", "Yo"), ("ё", "yo"), ("Ю", "Yu"), ("ю", "yu"),
    ("Я", "Ya"), ("я", "ya"), ("Ц", "Ts"), ("ц", "ts"),
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

VILOYATLAR = [
    "Toshkent shahri", "Toshkent viloyati", "Samarqand viloyati",
    "Buxoro viloyati", "Farg'ona viloyati", "Andijon viloyati",
    "Namangan viloyati", "Qashqadaryo viloyati", "Surxondaryo viloyati",
    "Jizzax viloyati", "Sirdaryo viloyati", "Navoiy viloyati",
    "Xorazm viloyati", "Qoraqalpog'iston Respublikasi",
]

TASHKILOTLAR = [
    "Kadastr agentligi hududiy boshqarmasi",
    "Davlat kadastrlari palatasi hududiy boshqarmasi",
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

        self.bind("<F5>", lambda e: self._refresh_current_view())
        self.bind("<Escape>", lambda e: self._go_back())

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

    def _show_loading(self, message="⏳ Yuklanmoqda..."):
        try:
            pending = self.loader.db.get_pending_count()
            if pending > 0:
                message += f"\n\n📡 Kutilmoqda: {pending} ta o'zgarish"
        except Exception:
            pass
        self._loading_window = ctk.CTkToplevel(self)
        self._loading_window.title("")
        self._loading_window.geometry("350x130")
        self._loading_window.resizable(False, False)
        self._loading_window.transient(self)
        self._loading_window.grab_set()

        self._loading_window.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - 350) // 2
        y = self.winfo_y() + (self.winfo_height() - 130) // 2
        self._loading_window.geometry(f"+{x}+{y}")

        ctk.CTkLabel(self._loading_window, text=message,
                     font=ctk.CTkFont(size=12, weight="bold")).pack(pady=15)
        self._progress = ctk.CTkProgressBar(self._loading_window, width=280)
        self._progress.pack(pady=10)
        self._progress.configure(mode="indeterminate")
        self._progress.start()
        self.update()

    def _hide_loading(self):
        try:
            if hasattr(self, '_progress'):
                self._progress.stop()
            if hasattr(self, '_loading_window'):
                self._loading_window.grab_release()
                self._loading_window.destroy()
                del self._loading_window
            self.update()
        except (tk.TclError, AttributeError):
            pass

    def _refresh_current_view(self):
        try:
            if self.current_view_func:
                self.current_view_func()
        except Exception as e:
            log_error(e, "refresh_view")
            messagebox.showerror(self._t("Xatolik"), str(e))

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
            nav, text=self._t("⬅ Orqaga"), width=100, height=34, fg_color=self.t_colors["btn"],
            hover_color=self.t_colors["hover"], font=ctk.CTkFont(size=12, weight="bold"),
            command=self._go_back
        )
        self.btn_back.pack(side="left", padx=15, pady=15)

        self.lbl_path = ctk.CTkLabel(
            nav, text=self._t("Asosiy oyna  /  Tahliliy Dashboard"),
            font=ctk.CTkFont(size=15, weight="bold"), text_color="#F8FAFC"
        )
        self.lbl_path.pack(side="left", padx=10, pady=15)

        ctk.CTkButton(
            nav, text="🌐 " + ("Lotin" if self.is_cyrillic else "Krill"),
            width=80, height=34, fg_color=self.t_colors["btn"], hover_color=self.t_colors["hover"],
            font=ctk.CTkFont(size=11, weight="bold"), command=self.toggle_lang
        ).pack(side="right", padx=8, pady=15)

        cb_theme = ctk.CTkComboBox(
            nav, values=[self._t(k) for k in THEMES.keys()], width=120, height=34,
            font=ctk.CTkFont(size=10, weight="bold"), command=self.change_theme
        )
        cb_theme.set(self._t(self.current_theme))
        cb_theme.pack(side="right", padx=3, pady=15)

        ctk.CTkButton(
            nav, text=self._t("📈 Grafiklar"), width=105, height=34,
            fg_color="#8E44AD", hover_color="#7D3C98",
            font=ctk.CTkFont(size=11, weight="bold"), command=self.show_charts_view
        ).pack(side="right", padx=3, pady=15)

        ctk.CTkButton(
            nav, text=self._t("📄 Word"), width=90, height=34,
            fg_color="#8B3A2B", hover_color="#A94442",
            font=ctk.CTkFont(size=11, weight="bold"), command=self._export_word
        ).pack(side="right", padx=3, pady=15)

        ctk.CTkButton(
            nav, text=self._t("📊 Excel"), width=90, height=34,
            fg_color="#1E6B47", hover_color="#258357",
            font=ctk.CTkFont(size=11, weight="bold"), command=self._export_excel
        ).pack(side="right", padx=3, pady=15)

        if self.role == "admin":
            ctk.CTkButton(
                nav, text=self._t("👁 Tarix"), width=90, height=34,
                fg_color="#D35400", hover_color="#A04000",
                font=ctk.CTkFont(size=11, weight="bold"), command=self.show_audit_view
            ).pack(side="right", padx=3, pady=15)

            ctk.CTkButton(
                nav, text=self._t("⚙️"), width=50, height=34,
                fg_color="#7F8C8D", hover_color="#95A5A6",
                font=ctk.CTkFont(size=11, weight="bold"), command=self.show_settings_view
            ).pack(side="right", padx=(3, 12), pady=15)

            ctk.CTkButton(
                nav, text=self._t("👥 Xodimlar"), width=110, height=34,
                fg_color=self.t_colors["btn"], hover_color=self.t_colors["hover"],
                font=ctk.CTkFont(size=11, weight="bold"), command=self.show_xodimlar_view
            ).pack(side="right", padx=3, pady=15)

            ctk.CTkButton(
                nav, text=self._t("📞 Qabul"), width=95, height=34,
                fg_color="#27AE60", hover_color="#219150",
                font=ctk.CTkFont(size=11, weight="bold"), command=self.show_add_phone_view
            ).pack(side="right", padx=3, pady=15)

            ctk.CTkButton(
                nav, text=self._t("📥 Excel"), width=95, height=34,
                fg_color=self.t_colors["btn"], hover_color=self.t_colors["hover"],
                font=ctk.CTkFont(size=11, weight="bold"), command=self._import_excel
            ).pack(side="right", padx=3, pady=15)
        else:
            ctk.CTkButton(
                nav, text=self._t("🔄 Yangilash"), width=130, height=34,
                fg_color=self.t_colors["btn"], hover_color=self.t_colors["hover"],
                font=ctk.CTkFont(size=11, weight="bold"), command=self._pull_from_cloud
            ).pack(side="right", padx=12, pady=15)

    def _pull_from_cloud(self):
        self._show_loading("🔄 Bulutdan yangilanmoqda...")
        try:
            self.loader.db.sync_pull_from_cloud()
            self.loader.refresh_data()
            self._hide_loading()
            self._redraw_entire_ui()
            messagebox.showinfo(self._t("Yangilandi"), self._t("Murojaatlar bulutdan olindi!"))
        except Exception as e:
            log_error(e, "pull_from_cloud")
            self._hide_loading()
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

        ctk.CTkLabel(filter_box, text=self._t("🔍"), font=ctk.CTkFont(size=11, weight="bold"),
                     text_color="#0F2537").pack(side="left", padx=(10, 2), pady=7)

        self.entry_dash_search = ctk.CTkEntry(
            filter_box, placeholder_text=self._t("F.I.Sh, tel, tuman..."),
            width=150, font=ctk.CTkFont(size=11))
        self.entry_dash_search.pack(side="left", padx=2, pady=7)
        self.entry_dash_search.bind("<Return>", self._apply_filters)

        ctk.CTkButton(filter_box, text=self._t("Topish"), width=55, height=28,
                      fg_color=self.t_colors["primary"], hover_color=self.t_colors["hover"],
                      font=ctk.CTkFont(size=11, weight="bold"),
                      command=self._apply_filters).pack(side="left", padx=2, pady=7)

        ctk.CTkLabel(filter_box, text=self._t("⏳"), font=ctk.CTkFont(size=11, weight="bold"),
                     text_color="#0F2537").pack(side="left", padx=(6, 2), pady=7)
        period_values = self.loader.get_available_periods()
        self.cb_period = ctk.CTkComboBox(filter_box, values=[self._t(v) for v in period_values],
                                          command=self._apply_filters, width=100, font=ctk.CTkFont(size=11))
        self.cb_period.set(self._t(getattr(self, 'selected_period', 'Barchasi')))
        self.cb_period.pack(side="left", padx=2, pady=7)

        ctk.CTkLabel(filter_box, text=self._t("📡"), font=ctk.CTkFont(size=11, weight="bold"),
                     text_color="#0F2537").pack(side="left", padx=(6, 2), pady=7)
        self.cb_manba = ctk.CTkComboBox(filter_box,
                                         values=[self._t(v) for v in ["Barchasi", "Telegram bot", "Ishonch telefoni (+998-71-273-19-66)"]],
                                         command=self._apply_filters, width=200, font=ctk.CTkFont(size=11))
        self.cb_manba.set(self._t(getattr(self, 'selected_manba', 'Barchasi')))
        self.cb_manba.pack(side="left", padx=2, pady=7)

        ctk.CTkLabel(filter_box, text=self._t("🏢"), font=ctk.CTkFont(size=11, weight="bold"),
                     text_color="#0F2537").pack(side="left", padx=(6, 2), pady=7)
        self.cb_masul = ctk.CTkComboBox(filter_box,
                                         values=[self._t(v) for v in ["Barchasi", "Kadastr agentligi hududiy komplayens xodimi",
                                                                       "Davlat kadastrlari palatasi hududiy komplayens xodimi"]],
                                         command=self._apply_filters, width=220, font=ctk.CTkFont(size=11))
        self.cb_masul.set(self._t(getattr(self, 'selected_masul', 'Barchasi')))
        self.cb_masul.pack(side="left", padx=2, pady=7)

        ctk.CTkButton(filter_box, text=self._t("Tozalash"), width=60, height=28,
                      fg_color="#64748B", hover_color="#475569",
                      font=ctk.CTkFont(size=11), command=self._reset_filters).pack(side="left", padx=6, pady=7)

        # Offline queue ko'rsatkichi
        try:
            pending = self.loader.db.get_pending_count()
            if pending > 0:
                pending_card = ctk.CTkFrame(self.container, fg_color="#FFF4E5",
                                            corner_radius=6, border_width=1,
                                            border_color="#F39C12")
                pending_card.pack(fill="x", pady=(0, 8), padx=2)
                ctk.CTkLabel(pending_card,
                             text=self._t(f"📡 {pending} ta o'zgarish navbatda — internet qaytganda yuboriladi"),
                             font=ctk.CTkFont(size=12, weight="bold"),
                             text_color="#D35400").pack(anchor="w", padx=12, pady=8)
        except Exception as e:
            log_error(e, "pending indicator")

        cards_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        cards_frame.pack(fill="x", pady=(0, 8))
        stats = self.loader.get_kpi_stats()
        f_df = self.loader.filtered_df

        cards = [
            (self._t("JAMI"), stats['total'], self.t_colors["primary"],
             lambda: self.show_records_view(self._t("Barcha murojaatlar"), f_df)),
            (self._t("AGENTLIKDA"), stats['agentlik_organish'], "#1B4D7E",
             lambda: self.show_records_view(self._t("Agentlikda"),
                 f_df[f_df['Ijro_Holati'].astype(str).str.contains("O‘rganishga yuborilgan|O'rganishda", case=False, na=False)
                      & f_df['Masul_Komplayens'].astype(str).str.contains("agentligi", case=False, na=False)])),
            (self._t("PALATADA"), stats['palata_organish'], "#4B3869",
             lambda: self.show_records_view(self._t("Palatada"),
                 f_df[f_df['Ijro_Holati'].astype(str).str.contains("O‘rganishga yuborilgan|O'rganishda", case=False, na=False)
                      & f_df['Masul_Komplayens'].astype(str).str.contains("palata", case=False, na=False)])),
            (self._t("O‘RGANILGAN"), stats['natija_kiritilgan'], "#1B5E20",
             lambda: self.show_records_view(self._t("O'rganilgan"),
                 f_df[f_df['Ijro_Holati'].astype(str).str.contains(
                     "Bartaraf etildi|Ijobiy hal etildi|Intizomiy chora|O‘rganib chiqildi|Asossiz", case=False, na=False)
                     | f_df['Chora_Turi'].astype(str).str.contains("Asossiz", case=False, na=False)])),
            (self._t("ASOSSIZ"), stats['asossiz'], "#7F8C8D",
             lambda: self.show_records_view(self._t("Asossiz"),
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

        ctk.CTkLabel(table_container, text=self._t("Viloyatlar kesimida murojaatlar:"),
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
            "viloyat": "Hudud", "jami": "Jami", "tg_m": "Telegram",
            "tel_m": "Telefon", "agentlik_org": "Agentlikda",
            "palata_org": "Palatada", "hal_etilgan": "O‘rganilgan",
            "asossiz": "Asossiz",
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
                | group['Chora_Turi'].astype(str).str.contains("Asossiz", case=False, na=False)])
            c_as = len(group[group['Ijro_Holati'].astype(str).str.contains("Asossiz", case=False, na=False)
                            | group['Chora_Turi'].astype(str).str.contains("Asossiz", case=False, na=False)])

            tag = 'even' if idx % 2 == 0 else 'odd'
            self.dash_tree.insert("", "end", values=(
                self._t(reg), self._t(f"{c_tot}"), self._t(f"{c_tg}"),
                self._t(f"{c_tel}"), self._t(f"{c_ag}"), self._t(f"{c_pa}"),
                self._t(f"{c_hal}"), self._t(f"{c_as}")), tags=(tag,))

        def on_region_double_click(_event):
            selected = self.dash_tree.selection()
            if not selected:
                return
            reg_name_translated = self.dash_tree.item(selected[0], 'values')[0]
            reg_name = self._to_latin(reg_name_translated.replace(self._t(" ta"), "").strip())
            df_to_show = f_df[f_df['Viloyat'] == reg_name]
            self.show_records_view(self._t(f"{reg_name}"), df_to_show)

        self.dash_tree.bind("<Double-1>", on_region_double_click)

        # Trend kartasi
        trend = self.loader.db.get_trend_stats(days=30)
        trend_card = ctk.CTkFrame(self.container, fg_color="#FFFFFF", corner_radius=6,
                                  border_width=1, border_color="#CBD5E1")
        trend_card.pack(fill="x", pady=(0, 8), padx=2)

        arrow = "📈" if trend['change_abs'] > 0 else ("📉" if trend['change_abs'] < 0 else "➖")
        color = "#27AE60" if trend['change_abs'] > 0 else ("#C0392B" if trend['change_abs'] < 0 else "#7F8C8D")

        ctk.CTkLabel(trend_card,
                     text=self._t(f"  {arrow} So'nggi 30 kunlik trend: "
                                  f"hozir {trend['current']} ta, o'tgan davr {trend['previous']} ta, "
                                  f"o'zgarish: {trend['change_abs']:+d} ({trend['change_pct']:+.1f}%)"),
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=color).pack(anchor="w", padx=12, pady=8)

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

    def show_records_view(self, title, data_df):
        self._push_current_to_stack()
        self.current_view_func = lambda t=title, d=data_df: self.show_records_view(t, d)

        self.btn_back.configure(state="normal")
        self.lbl_path.configure(text=self._t(f"Asosiy oyna  /  Ro'yxat: {title}"))
        self._clear_container()

        main_box = ctk.CTkFrame(self.container, fg_color="#FFFFFF", corner_radius=6,
                                border_width=1, border_color="#CBD5E1")
        main_box.pack(fill="both", expand=True)

        top_bar = ctk.CTkFrame(main_box, fg_color="transparent")
        top_bar.pack(fill="x", padx=15, pady=8)

        ctk.CTkLabel(top_bar, text=self._t("🔍"), font=ctk.CTkFont(size=12, weight="bold"),
                     text_color="#0F2537").pack(side="left", padx=(0, 5))
        entry_search = ctk.CTkEntry(top_bar, placeholder_text=self._t("F.I.Sh, telefon, tuman..."),
                                    width=320, font=ctk.CTkFont(size=12))
        entry_search.pack(side="left", padx=5)

        if self.role == "admin":
            ctk.CTkButton(top_bar, text=self._t("⚡ Bulk"), width=90, height=28,
                          fg_color="#8E44AD", hover_color="#7D3C98",
                          font=ctk.CTkFont(size=11, weight="bold"),
                          command=lambda: self._bulk_actions_dialog(data_df)).pack(side="left", padx=5)

        ctk.CTkLabel(top_bar, text=self._t(f"Jami: {len(data_df)} ta"),
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color="#0F2537").pack(side="right", padx=10)

        tree_frame = ctk.CTkFrame(main_box, fg_color="transparent")
        tree_frame.pack(fill="both", expand=True, padx=15, pady=(0, 6))

        cols = ("#", "sana", "xavf", "fish", "telefon", "viloyat", "tuman", "masul", "ijro")
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Rec.Treeview", rowheight=28, font=("Calibri", 11),
                        bordercolor="#94A3B8", borderwidth=1)
        style.configure("Rec.Treeview.Heading", font=("Calibri", 11, "bold"),
                        background=self.t_colors["primary"], foreground="#FFFFFF")

        tree = ttk.Treeview(tree_frame, columns=cols, show="headings",
                            style="Rec.Treeview", selectmode="extended")

        def sort_col(col_idx, reverse):
            items = [(tree.set(k, col_idx), k) for k in tree.get_children('')]
            items.sort(reverse=reverse)
            for index, (_val, k) in enumerate(items):
                tree.move(k, '', index)
            tree.heading(col_idx, command=lambda _c=col_idx: sort_col(_c, not reverse))

        tree.heading("#", text="#", command=lambda: sort_col("#", False))
        tree.heading("sana", text=self._t("Sana"), command=lambda: sort_col("sana", False))
        tree.heading("xavf", text=self._t("Xavf"))
        tree.heading("fish", text=self._t("F.I.Sh."), command=lambda: sort_col("fish", False))
        tree.heading("telefon", text=self._t("Telefon"))
        tree.heading("viloyat", text=self._t("Viloyat"), command=lambda: sort_col("viloyat", False))
        tree.heading("tuman", text=self._t("Tuman"))
        tree.heading("masul", text=self._t("Mas'ul"))
        tree.heading("ijro", text=self._t("Holati"), command=lambda: sort_col("ijro", False))

        tree.column("#", width=45, anchor="center")
        tree.column("sana", width=125, anchor="center")
        tree.column("xavf", width=110, anchor="center")
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
                xavf_text = self._t("🔴 Yuqori") if is_danger else self._t("O'rtacha")
                tree.insert("", "end", values=(
                    r.get('#', ''),
                    str(r.get('Yaratilgan sana', ''))[:16],
                    xavf_text,
                    self._t(r.get('F.I.Sh.', '')),
                    r.get('Telefon', ''),
                    self._t(r.get('Viloyat', '')),
                    self._t(r.get('Tuman', '')),
                    self._t(r.get('Masul_Komplayens', 'Kadastr agentligi hududiy komplayens xodimi')),
                    self._t(r.get('Ijro_Holati', 'O‘rganishga yuborilgan'))
                ), tags=(tag,))

        populate(data_df)

        def on_search(_event):
            q = self._to_latin(entry_search.get().lower().strip())
            if not q:
                populate(data_df)
                return
            mask = (
                data_df['F.I.Sh.'].astype(str).str.lower().str.contains(q)
                | data_df['Telefon'].astype(str).str.lower().str.contains(q)
                | data_df['Viloyat'].astype(str).str.lower().str.contains(q)
            )
            populate(data_df[mask])

        entry_search.bind("<KeyRelease>", on_search)

        def on_double_click(_event):
            selected = tree.selection()
            if not selected:
                return
            try:
                m_id = int(tree.item(selected[0], "values")[0])
            except (ValueError, IndexError):
                return
            self.show_detail_view(m_id, lambda: self.show_records_view(title, data_df))

        tree.bind("<Double-1>", on_double_click)

    def _bulk_actions_dialog(self, data_df):
        win = ctk.CTkToplevel(self)
        win.title(self._t("Bulk amallar"))
        win.geometry("600x500")
        win.grab_set()
        win.transient(self)

        ctk.CTkLabel(win, text=self._t("⚡ BULK AMALLAR"),
                     font=ctk.CTkFont(size=14, weight="bold")).pack(pady=10)
        ctk.CTkLabel(win, text=self._t("ID larni kiriting (har bir yangi qatorda bittadan):"),
                     font=ctk.CTkFont(size=11, slant="italic")).pack(pady=(0, 5))

        tb_ids = ctk.CTkTextbox(win, height=120, font=ctk.CTkFont(size=12))
        tb_ids.pack(fill="x", padx=20, pady=5)

        all_ids = "\n".join([str(x) for x in data_df['#'].head(10).tolist()])
        tb_ids.insert("1.0", all_ids)

        form = ctk.CTkFrame(win, fg_color="#F8FAFC", corner_radius=6,
                            border_width=1, border_color="#CBD5E1")
        form.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(form, text=self._t("Yangi holat:"),
                     font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=15, pady=(10, 2))
        cb_status = ctk.CTkComboBox(form, values=[self._t(v) for v in [
            "O‘rganishga yuborilgan", "O‘rganib chiqildi / Bartaraf etildi",
            "Ijobiy hal etildi", "Intizomiy chora ko‘rildi", "Asossiz deb topildi"
        ]], width=400, font=ctk.CTkFont(size=12))
        cb_status.set(self._t("O‘rganib chiqildi / Bartaraf etildi"))
        cb_status.pack(anchor="w", padx=15)

        ctk.CTkLabel(form, text=self._t("Yangi chora:"),
                     font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=15, pady=(10, 2))
        cb_chora = ctk.CTkComboBox(form, values=[self._t(v) for v in [
            "Chora ko‘rilmagan", "Xayfsan e'lon qilindi", "Jarima qo‘llandi",
            "Lavozimidan ozod etildi", "Prokuraturaga yuborildi", "Asossiz deb topildi"
        ]], width=400, font=ctk.CTkFont(size=12))
        cb_chora.set(self._t("Chora ko‘rilmagan"))
        cb_chora.pack(anchor="w", padx=15)

        ctk.CTkLabel(form, text=self._t("Yangi mas'ul:"),
                     font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=15, pady=(10, 2))
        cb_masul = ctk.CTkComboBox(form, values=[self._t(v) for v in [
            "Kadastr agentligi hududiy komplayens xodimi",
            "Davlat kadastrlari palatasi hududiy komplayens xodimi"
        ]], width=400, font=ctk.CTkFont(size=12))
        cb_masul.set(self._t("Kadastr agentligi hududiy komplayens xodimi"))
        cb_masul.pack(anchor="w", padx=15, pady=(0, 15))

        def apply_bulk():
            ids_text = tb_ids.get("1.0", "end-1c").strip()
            if not ids_text:
                messagebox.showwarning(self._t("Xato"), self._t("ID larni kiriting!"))
                return
            try:
                id_list = [int(x.strip()) for x in ids_text.split("\n") if x.strip().isdigit()]
            except ValueError:
                messagebox.showerror(self._t("Xato"), self._t("ID lar noto'g'ri!"))
                return

            if not id_list:
                messagebox.showwarning(self._t("Xato"), self._t("Hech qanday ID topilmadi!"))
                return

            if not messagebox.askyesno(self._t("Tasdiqlash"),
                                       self._t(f"{len(id_list)} ta murojaatni yangilaysizmi?")):
                return

            st = self._to_latin(cb_status.get())
            ch = self._to_latin(cb_chora.get())
            ms = self._to_latin(cb_masul.get())

            updated = self.loader.db.bulk_update_status(id_list, st, ch, ms,
                                                         ozgartirgan='admin',
                                                         ozgartirgan_rol=self.role)
            self.loader.refresh_data()
            win.destroy()
            messagebox.showinfo(self._t("Tayyor"), self._t(f"{updated} ta murojaat yangilandi!"))
            self.show_records_view(self._t("Barcha murojaatlar"), self.loader.filtered_df)

        ctk.CTkButton(win, text=self._t("⚡ Qo'llash"), width=200, height=38,
                      fg_color="#8E44AD", hover_color="#7D3C98",
                      font=ctk.CTkFont(size=13, weight="bold"),
                      command=apply_bulk).pack(pady=15)

    def show_detail_view(self, m_id, return_callback):
        self._push_current_to_stack()
        self.current_view_func = lambda: self.show_detail_view(m_id, return_callback)

        self.btn_back.configure(state="normal")
        self.lbl_path.configure(text=self._t(f"Asosiy oyna  /  Kartochka #{m_id}"))
        self._clear_container()

        self.attached_file_path = ""

        try:
            rec = self.loader.df[self.loader.df['#'] == m_id].iloc[0]
        except (IndexError, KeyError):
            messagebox.showerror(self._t("Xatolik"), self._t(f"#{m_id} topilmadi!"))
            self._go_back()
            return

        sets = self.loader.db.get_settings()

        main_scroll = ctk.CTkScrollableFrame(self.container, fg_color="#FFFFFF", corner_radius=6,
                                             border_width=1, border_color="#CBD5E1")
        main_scroll.pack(fill="both", expand=True, padx=4, pady=4)

        info_top = ctk.CTkFrame(main_scroll, fg_color="#F1F5F9", corner_radius=6,
                                border_width=1, border_color="#CBD5E1")
        info_top.pack(fill="x", padx=15, pady=(10, 6))

        txt_info = (
            f"👤 {self._t('Fuqaro')}: {self._t(rec.get('F.I.Sh.'))}   |   "
            f"📞 {rec.get('Telefon')}   |   "
            f"📍 {self._t(rec.get('Viloyat'))}, {self._t(rec.get('Tuman'))}\n"
            f"📡 {self._t('Manba')}: {self._t(rec.get('Manba', 'Telegram bot'))}   |   "
            f"🕒 {rec.get('Yaratilgan sana')}"
        )
        ctk.CTkLabel(info_top, text=txt_info, justify="left",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color="#0F2537").pack(padx=15, pady=8, anchor="w")

        if rec.get('Yuqori_Xavf', False):
            ctk.CTkLabel(main_scroll, text=self._t("⚠️ KORRUPSIYAVIY XAVF ALOMATLARI!"),
                         font=ctk.CTkFont(size=12, weight="bold"),
                         text_color="#C0392B").pack(padx=15, anchor="w")

        ctk.CTkLabel(main_scroll, text=self._t("📝 Murojaat matni:"),
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color="#0F2537").pack(padx=15, anchor="w")

        tb_m = ctk.CTkTextbox(main_scroll, height=120, wrap="word", font=ctk.CTkFont(size=13))
        tb_m.insert("1.0", self._t(str(rec.get('Murojaat matni', ''))))
        tb_m.configure(state="disabled")
        tb_m.pack(fill="x", padx=15, pady=(4, 8))

        action_frame = ctk.CTkFrame(main_scroll, fg_color="#F8FAFC", corner_radius=6,
                                    border_width=1, border_color="#CBD5E1")
        action_frame.pack(fill="x", padx=15, pady=(4, 10))

        ctk.CTkLabel(action_frame, text=self._t("⚙️ NAZORAT VA O‘RGANISH:"),
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color="#0F2537").pack(padx=15, pady=(6, 2), anchor="w")

        row_masul = ctk.CTkFrame(action_frame, fg_color="transparent")
        row_masul.pack(fill="x", padx=15, pady=3)
        ctk.CTkLabel(row_masul, text=self._t("Mas'ul:"),
                     font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=(0, 8))

        cb_masul_item = ctk.CTkComboBox(row_masul, values=[self._t(v) for v in [
            "Kadastr agentligi hududiy komplayens xodimi",
            "Davlat kadastrlari palatasi hududiy komplayens xodimi"
        ]], width=300, font=ctk.CTkFont(size=12))
        cb_masul_item.set(self._t(
            "Davlat kadastrlari palatasi hududiy komplayens xodimi"
            if 'palata' in str(rec.get('Masul_Komplayens', '')).lower()
            else "Kadastr agentligi hududiy komplayens xodimi"))
        cb_masul_item.pack(side="left")

        def send_to_telegram():
            x_info = self.loader.db.find_xodim_for_region(
                rec.get('Viloyat'), self._to_latin(cb_masul_item.get()))
            raw_matn = str(rec.get('Murojaat matni', ''))
            short_matn = raw_matn if len(raw_matn) < 600 else raw_matn[:600] + "..."
            tmpl = sets.get("tg_template", "Murojaat #{id}\nMatn: {matn}")
            tg_text = (tmpl.replace("{id}", str(m_id))
                       .replace("{manba}", str(rec.get('Manba', 'Telegram bot')))
                       .replace("{fish}", str(rec.get('F.I.Sh.')))
                       .replace("{tel}", str(rec.get('Telefon')))
                       .replace("{viloyat}", str(rec.get('Viloyat')))
                       .replace("{tuman}", str(rec.get('Tuman')))
                       .replace("{sana}", str(rec.get('Yaratilgan sana'))[:16])
                       .replace("{matn}", short_matn))
            encoded = urllib.parse.quote(self._t(tg_text))

            u_name = sanitize_telegram_username(x_info.get('username', ''))
            u_phone = sanitize_phone(x_info.get('telefon', ''))

            if u_name:
                url = f"https://t.me/{u_name}?text={encoded}"
            elif u_phone:
                url = f"https://t.me/+{u_phone}?text={encoded}"
            else:
                url = f"https://t.me/share/url?url={encoded}"

            try:
                webbrowser.open(url)
            except webbrowser.Error as e:
                log_error(e, "telegram")
                messagebox.showerror(self._t("Xatolik"), str(e))

        ctk.CTkButton(row_masul, text=self._t("✈️ Telegram"),
                      width=120, height=28, fg_color="#0088CC", hover_color="#0077B5",
                      font=ctk.CTkFont(size=11, weight="bold"),
                      command=send_to_telegram).pack(side="left", padx=10)

        row_status = ctk.CTkFrame(action_frame, fg_color="transparent")
        row_status.pack(fill="x", padx=15, pady=3)
        ctk.CTkLabel(row_status, text=self._t("Holat:"),
                     font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=(0, 8))

        cb_status = ctk.CTkComboBox(row_status, values=[self._t(v) for v in [
            "O‘rganishga yuborilgan", "O‘rganib chiqildi / Bartaraf etildi",
            "Ijobiy hal etildi", "Intizomiy chora ko‘rildi", "Asossiz deb topildi"
        ]], width=230, font=ctk.CTkFont(size=12))
        cb_status.set(self._t(str(rec.get('Ijro_Holati', 'O‘rganishga yuborilgan'))))
        cb_status.pack(side="left", padx=(0, 15))

        ctk.CTkLabel(row_status, text=self._t("Chora:"),
                     font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=(0, 8))

        cb_chora = ctk.CTkComboBox(row_status, values=[self._t(v) for v in [
            "Chora ko‘rilmagan", "Xayfsan e'lon qilindi", "Jarima qo‘llandi",
            "Lavozimidan ozod etildi", "Prokuraturaga yuborildi", "Asossiz deb topildi"
        ]], width=190, font=ctk.CTkFont(size=12))
        cb_chora.set(self._t(str(rec.get('Chora_Turi', 'Chora ko‘rilmagan'))))
        cb_chora.pack(side="left")

        ctk.CTkLabel(action_frame, text=self._t("Xulosa:"),
                     font=ctk.CTkFont(size=12, weight="bold")).pack(padx=15, pady=(5, 1), anchor="w")

        tb_natija = ctk.CTkTextbox(action_frame, height=80, wrap="word", font=ctk.CTkFont(size=12))
        natija_text = str(rec.get('Organish_Natijasi', ''))
        tb_natija.insert("1.0", self._t(natija_text) if self.is_cyrillic else natija_text)
        tb_natija.pack(fill="x", padx=15, pady=(0, 6))

        self.attached_file_path = str(rec.get('Biriktirilgan_Fayl', '') or '')

        ctk.CTkLabel(action_frame, text=self._t("📎 Biriktirilgan fayllar:"),
                     font=ctk.CTkFont(size=12, weight="bold")).pack(padx=15, pady=(5, 1), anchor="w")

        fayllar_frame = ctk.CTkFrame(action_frame, fg_color="#FFFFFF", corner_radius=5,
                                     border_width=1, border_color="#CBD5E1")
        fayllar_frame.pack(fill="x", padx=15, pady=(0, 6))

        self.fayllar_container = ctk.CTkFrame(fayllar_frame, fg_color="transparent")
        self.fayllar_container.pack(fill="x", padx=10, pady=6)

        def refresh_files():
            for w in self.fayllar_container.winfo_children():
                w.destroy()
            try:
                df_f = self.loader.db.get_murojaat_fayllar(m_id)
                if df_f.empty:
                    ctk.CTkLabel(self.fayllar_container, text=self._t("(Hujjat yo'q)"),
                                 font=ctk.CTkFont(size=11, slant="italic"),
                                 text_color="#64748B").pack(anchor="w")
                    return
                for _, r in df_f.iterrows():
                    row = ctk.CTkFrame(self.fayllar_container, fg_color="transparent")
                    row.pack(fill="x", pady=2)
                    ctk.CTkLabel(row, text=f"📄 {r['fayl_nomi']}  ({r['Yuklangan']})",
                                 font=ctk.CTkFont(size=11)).pack(side="left")
                    ctk.CTkButton(row, text="👁", width=40, height=22,
                                  fg_color="#475569", hover_color="#334155",
                                  command=lambda p=r['fayl_yoli']: self._open_file(p)).pack(side="right", padx=2)
                    if self.role == "admin":
                        ctk.CTkButton(row, text="🗑", width=40, height=22,
                                      fg_color="#C0392B", hover_color="#A93226",
                                      command=lambda fid=r['id']: self._delete_file(fid, refresh_files)).pack(side="right", padx=2)
            except Exception as e:
                log_error(e, "refresh_files")
                ctk.CTkLabel(self.fayllar_container, text=f"⚠️ {e}",
                             font=ctk.CTkFont(size=11), text_color="#C0392B").pack(anchor="w")

        refresh_files()

        btn_attach = ctk.CTkButton(fayllar_frame, text=self._t("📎 Yangi fayl qo'shish"),
                                   width=180, height=28,
                                   fg_color=self.t_colors["btn"], hover_color=self.t_colors["hover"],
                                   font=ctk.CTkFont(size=11, weight="bold"),
                                   command=lambda: self._attach_multi_file(m_id, refresh_files))
        btn_attach.pack(pady=6)

        ctk.CTkButton(fayllar_frame, text=self._t("📜 O'zgarishlar tarixi"),
                      width=180, height=28, fg_color="#8E44AD", hover_color="#7D3C98",
                      font=ctk.CTkFont(size=11, weight="bold"),
                      command=lambda: self._show_history_dialog(m_id)).pack(pady=(0, 6))

        row_save = ctk.CTkFrame(action_frame, fg_color="transparent")
        row_save.pack(pady=(0, 10))

        def save_changes():
            st = self._to_latin(cb_status.get())
            ms = self._to_latin(cb_masul_item.get())
            ch = self._to_latin(cb_chora.get())
            nat_xom = tb_natija.get("1.0", "end-1c")
            nat = self._to_latin(nat_xom) if self.is_cyrillic else nat_xom

            if (st in ["Ijobiy hal etildi", "Intizomiy chora ko‘rildi",
                       "Asossiz deb topildi", "O‘rganib chiqildi / Bartaraf etildi"]
                    or ch == "Asossiz deb topildi"):
                df_f = self.loader.db.get_murojaat_fayllar(m_id)
                has_attach = (not df_f.empty) or (self.attached_file_path and os.path.exists(self.attached_file_path))
                if not has_attach:
                    messagebox.showwarning(
                        self._t("Fayl yo'q!"),
                        self._t("Tasdiqlovchi hujjat biriktirilishi shart!"))
                    return

            try:
                self.loader.db.update_murojaat_ijro(
                    m_id, st, nat, self.attached_file_path, ms, ch,
                    ozgartirgan='admin', ozgartirgan_rol=self.role)
                self.loader.refresh_data()
                messagebox.showinfo(self._t("Saqlandi"), self._t(f"#{m_id} saqlandi!"))
            except Exception as e:
                log_error(e, "save_changes")
                messagebox.showerror(self._t("Xatolik"), str(e))

        def download_resolution():
            rec_updated = self.loader.df[self.loader.df['#'] == m_id].iloc[0].copy()
            nat_xom = tb_natija.get("1.0", "end-1c").strip()
            rec_updated['Organish_Natijasi'] = self._to_latin(nat_xom) if self.is_cyrillic else nat_xom
            rec_updated['Ijro_Holati'] = self._to_latin(cb_status.get()) if self.is_cyrillic else cb_status.get()
            rec_updated['Chora_Turi'] = self._to_latin(cb_chora.get()) if self.is_cyrillic else cb_chora.get()
            rec_updated['Masul_Komplayens'] = (self._to_latin(cb_masul_item.get())
                                                if self.is_cyrillic else cb_masul_item.get())

            fp = filedialog.asksaveasfilename(defaultextension=".docx",
                                              initialfile=f"Xulosa_{m_id}.docx")
            if not fp:
                return
            self._show_loading("📄 Word tayyorlanmoqda...")
            try:
                ReportGenerator.generate_resolution_report(
                    rec_updated, fp,
                    self._t(sets.get("report_header",
                                     "O‘ZBEKISTON RESPUBLIKASI KADASTR AGENTLIGI\n"
                                     "KORRUPSIYAGA QARSHI KURASHISH BO‘LIMI")))
                self._hide_loading()
                messagebox.showinfo(self._t("Tayyor"), self._t("Word saqlandi!"))
                reveal_in_file_manager(fp)
            except Exception as e:
                log_error(e, "word xulosa")
                self._hide_loading()
                messagebox.showerror(self._t("Xatolik"), str(e))

        btn_save = ctk.CTkButton(row_save, text=self._t("💾 Saqlash (Ctrl+S)"),
                                 fg_color="#1B5E20", hover_color="#2E7D32",
                                 width=150, height=32, font=ctk.CTkFont(size=12, weight="bold"),
                                 command=save_changes)
        btn_save.pack(side="left", padx=10)

        ctk.CTkButton(row_save, text=self._t("📄 Word xulosa"),
                      fg_color="#8B3A2B", hover_color="#A94442",
                      width=180, height=32, font=ctk.CTkFont(size=12, weight="bold"),
                      command=download_resolution).pack(side="left", padx=10)

        self.bind("<Control-s>", lambda e: save_changes())
        self.bind("<Control-S>", lambda e: save_changes())

        if self.role == "kuzatuvchi":
            cb_masul_item.configure(state="disabled")
            cb_status.configure(state="disabled")
            cb_chora.configure(state="disabled")
            tb_natija.configure(state="disabled")
            try:
                btn_attach.configure(state="disabled", fg_color="#95A5A6")
                btn_save.configure(state="disabled", fg_color="#95A5A6")
            except tk.TclError:
                pass

    def _attach_multi_file(self, m_id, refresh_callback):
        fp = filedialog.askopenfilename(
            title=self._t("Hujjatni tanlang"),
            filetypes=[(self._t("Hujjatlar"), "*.pdf *.png *.jpg *.jpeg *.docx *.doc *.xlsx")])
        if not fp:
            return
        try:
            attach_dir = os.path.join(os.getcwd(), "data", "attachments", str(m_id))
            try:
                os.makedirs(attach_dir, exist_ok=True)
            except PermissionError:
                messagebox.showerror(self._t("Ruxsat yo'q!"),
                                     self._t("Papkaga yozish huquqi yo'q!"))
                return

            base_name = os.path.basename(fp)
            dest = os.path.join(attach_dir, base_name)
            counter = 1
            while os.path.exists(dest):
                name, ext = os.path.splitext(base_name)
                dest = os.path.join(attach_dir, f"{name}_{counter}{ext}")
                counter += 1

            shutil.copy2(fp, dest)

            self.loader.db.add_murojaat_fayl(m_id, os.path.basename(dest), dest, 'admin')
            if refresh_callback:
                refresh_callback()
            messagebox.showinfo(self._t("Tayyor"), self._t("Fayl qo'shildi!"))
        except Exception as e:
            log_error(e, "attach_multi")
            messagebox.showerror(self._t("Xatolik"), str(e))

    def _open_file(self, filepath):
        if filepath and os.path.exists(filepath):
            try:
                if sys.platform == "win32":
                    os.startfile(filepath)
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", filepath])
                else:
                    subprocess.Popen(["xdg-open", filepath])
            except (OSError, AttributeError) as e:
                log_error(e, "open_file")
                messagebox.showerror(self._t("Xatolik"), str(e))
        else:
            messagebox.showwarning(self._t("Fayl yo'q"), self._t("Fayl topilmadi!"))

    def _delete_file(self, file_id, refresh_callback):
        if not messagebox.askyesno(self._t("Tasdiqlash"),
                                   self._t("Faylni o'chirmoqchimisiz?")):
            return
        self.loader.db.delete_murojaat_fayl(file_id)
        if refresh_callback:
            refresh_callback()

    def _show_history_dialog(self, m_id):
        win = ctk.CTkToplevel(self)
        win.title(self._t(f"#{m_id} o'zgarishlar tarixi"))
        win.geometry("900x500")
        win.grab_set()

        ctk.CTkLabel(win, text=self._t(f"📜 #{m_id} — O'zgarishlar tarixi"),
                     font=ctk.CTkFont(size=14, weight="bold")).pack(pady=10)

        t_box = ctk.CTkFrame(win, fg_color="#FFFFFF", border_width=1, border_color="#CBD5E1")
        t_box.pack(padx=15, pady=5, fill="both", expand=True)

        cols = ("vaqt", "kim", "rol", "eski", "yangi", "chora")
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Hist.Treeview", rowheight=28, font=("Calibri", 11))
        style.configure("Hist.Treeview.Heading", font=("Calibri", 11, "bold"),
                        background=self.t_colors["primary"], foreground="#FFFFFF")

        tree = ttk.Treeview(t_box, columns=cols, show="headings", height=15, style="Hist.Treeview")
        tree.heading("vaqt", text=self._t("Vaqt"))
        tree.heading("kim", text=self._t("Kim"))
        tree.heading("rol", text=self._t("Rol"))
        tree.heading("eski", text=self._t("Eski holat"))
        tree.heading("yangi", text=self._t("Yangi holat"))
        tree.heading("chora", text=self._t("Yangi chora"))

        tree.column("vaqt", width=150, anchor="center")
        tree.column("kim", width=100, anchor="center")
        tree.column("rol", width=100, anchor="center")
        tree.column("eski", width=180)
        tree.column("yangi", width=180)
        tree.column("chora", width=180)

        vsb = ttk.Scrollbar(t_box, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        try:
            df_h = self.loader.db.get_murojaat_history(m_id)
            for _, r in df_h.iterrows():
                tree.insert("", "end", values=(
                    r.get('Vaqt', ''), r.get('Kim', ''), r.get('Rol', ''),
                    self._t(r.get('Eski holat', '')),
                    self._t(r.get('Yangi holat', '')),
                    self._t(r.get('Yangi chora', ''))))
        except Exception as e:
            log_error(e, "history dialog")
            messagebox.showerror(self._t("Xatolik"), str(e))

    def show_add_phone_view(self):
        self._push_current_to_stack()
        self.current_view_func = self.show_add_phone_view

        self.btn_back.configure(state="normal")
        self.lbl_path.configure(text=self._t("Asosiy oyna  /  Ishonch telefoni qabul"))
        self._clear_container()

        main_box = ctk.CTkFrame(self.container, fg_color="#FFFFFF", corner_radius=6,
                                border_width=1, border_color="#CBD5E1")
        main_box.pack(fill="both", expand=True, padx=4, pady=4)

        ctk.CTkLabel(main_box, text=self._t("📞 ISHONCH TELEFONI ORQALI QABUL"),
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color="#0F2537").pack(pady=(20, 5))

        form = ctk.CTkFrame(main_box, fg_color="#F8FAFC", corner_radius=6,
                            border_width=1, border_color="#CBD5E1")
        form.pack(fill="x", padx=100, pady=10)

        ctk.CTkLabel(form, text=self._t("Fuqaro F.I.Sh.:"),
                     font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=20, pady=(15, 2))
        e_fish = ctk.CTkEntry(form, placeholder_text=self._t("F.I.Sh"),
                              width=500, font=ctk.CTkFont(size=12))
        e_fish.pack(anchor="w", padx=20)

        ctk.CTkLabel(form, text=self._t("Telefon:"),
                     font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=20, pady=(10, 2))
        e_tel = ctk.CTkEntry(form, placeholder_text="+998901234567",
                             width=500, font=ctk.CTkFont(size=12))
        e_tel.insert(0, "+998")
        e_tel.pack(anchor="w", padx=20)

        row_geo = ctk.CTkFrame(form, fg_color="transparent")
        row_geo.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(row_geo, text=self._t("Viloyat:"),
                     font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=(0, 5))
        cb_vil = ctk.CTkComboBox(row_geo, values=[self._t(v) for v in VILOYATLAR],
                                  width=200, font=ctk.CTkFont(size=12))
        cb_vil.pack(side="left", padx=(0, 20))

        ctk.CTkLabel(row_geo, text=self._t("Tuman:"),
                     font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=(0, 5))
        e_tum = ctk.CTkEntry(row_geo, placeholder_text=self._t("Tuman"),
                             width=180, font=ctk.CTkFont(size=12))
        e_tum.pack(side="left")

        ctk.CTkLabel(form, text=self._t("Yo'nalish:"),
                     font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=20, pady=(10, 2))
        cb_yon = ctk.CTkComboBox(form, values=[self._t(v) for v in [
            "Kadastr agentligi hududiy boshqarmasi xodimlarining xatti-harakatlari",
            "Davlat kadastrlari palatasi hududiy boshqarmasi xodimlarining xatti-harakatlari"
        ]], width=500, font=ctk.CTkFont(size=12))
        cb_yon.pack(anchor="w", padx=20)

        ctk.CTkLabel(form, text=self._t("Murojaat mazmuni:"),
                     font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=20, pady=(10, 2))
        tb_matn = ctk.CTkTextbox(form, height=120, wrap="word", font=ctk.CTkFont(size=12))
        tb_matn.pack(fill="x", padx=20, pady=(0, 15))

        def save_phone_entry():
            fish_xom = e_fish.get().strip()
            tel_val = e_tel.get().strip()
            vil_xom = cb_vil.get()
            tum_xom = e_tum.get().strip()
            yon_xom = cb_yon.get()
            matn_xom = tb_matn.get("1.0", "end-1c").strip()

            if not fish_xom or not tel_val or not matn_xom:
                messagebox.showwarning(self._t("To'ldirish shart"),
                                       self._t("Barcha maydonlarni to'ldiring!"))
                return

            fish_val = self._to_latin(fish_xom) if self.is_cyrillic else fish_xom
            vil_val = self._to_latin(vil_xom) if self.is_cyrillic else vil_xom
            tum_val = self._to_latin(tum_xom) if self.is_cyrillic else tum_xom
            yon_val = self._to_latin(yon_xom) if self.is_cyrillic else yon_xom
            matn_val = self._to_latin(matn_xom) if self.is_cyrillic else matn_xom

            masul = ("Davlat kadastrlari palatasi hududiy komplayens xodimi"
                     if "palata" in yon_val.lower()
                     else "Kadastr agentligi hududiy komplayens xodimi")

            try:
                new_id = self.loader.db.insert_phone_murojaat(
                    fish_val, tel_val, vil_val, tum_val, yon_val, matn_val, masul)
                self.loader.refresh_data()
                self._redraw_entire_ui()
                messagebox.showinfo(self._t("Qabul qilindi"),
                                    self._t(f"#{new_id} ro'yxatga olindi!"))
            except Exception as e:
                log_error(e, "phone entry")
                messagebox.showerror(self._t("Xatolik"), str(e))

        ctk.CTkButton(main_box, text=self._t("💾 Ro'yxatga olish"),
                      height=38, width=250, fg_color="#1B5E20", hover_color="#2E7D32",
                      font=ctk.CTkFont(size=13, weight="bold"),
                      command=save_phone_entry).pack(pady=20)

    def show_xodimlar_view(self):
        self._push_current_to_stack()
        self.current_view_func = self.show_xodimlar_view

        self.btn_back.configure(state="normal")
        self.lbl_path.configure(text=self._t("Asosiy oyna  /  Xodimlar"))
        self._clear_container()

        main_box = ctk.CTkFrame(self.container, fg_color="#FFFFFF", corner_radius=6,
                                border_width=1, border_color="#CBD5E1")
        main_box.pack(fill="both", expand=True, padx=4, pady=4)

        header = ctk.CTkFrame(main_box, fg_color="transparent")
        header.pack(fill="x", padx=15, pady=10)
        ctk.CTkLabel(header, text=self._t("👥 Xodimlar:"),
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color="#0F2537").pack(side="left")
        ctk.CTkButton(header, text=self._t("➕ Yangi xodim"),
                      width=150, height=30, fg_color="#27AE60", hover_color="#219150",
                      font=ctk.CTkFont(size=11, weight="bold"),
                      command=self._add_xodim_dialog).pack(side="right")

        table_frame = ctk.CTkFrame(main_box, fg_color="transparent")
        table_frame.pack(fill="both", expand=True, padx=15, pady=(0, 10))

        cols = ("id", "viloyat", "tashkilot", "fish", "telefon", "telegram")
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Xod.Treeview", rowheight=30, font=("Calibri", 11),
                        bordercolor="#94A3B8", borderwidth=1)
        style.configure("Xod.Treeview.Heading", font=("Calibri", 11, "bold"),
                        background=self.t_colors["primary"], foreground="#FFFFFF")

        tree = ttk.Treeview(table_frame, columns=cols, show="headings",
                            style="Xod.Treeview", selectmode="browse")
        tree.heading("id", text="#")
        tree.heading("viloyat", text=self._t("Hudud"))
        tree.heading("tashkilot", text=self._t("Tashkilot"))
        tree.heading("fish", text=self._t("F.I.Sh."))
        tree.heading("telefon", text=self._t("Telefon"))
        tree.heading("telegram", text=self._t("Telegram"))

        tree.column("id", width=40, anchor="center")
        tree.column("viloyat", width=180)
        tree.column("tashkilot", width=260)
        tree.column("fish", width=200)
        tree.column("telefon", width=140, anchor="center")
        tree.column("telegram", width=180, anchor="center")

        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        def populate_x():
            tree.delete(*tree.get_children())
            try:
                df_x = self.loader.db.get_xodimlar()
            except Exception as e:
                log_error(e, "populate_xodimlar")
                messagebox.showerror(self._t("Xatolik"), str(e))
                return
            for _, r in df_x.iterrows():
                def _s(key):
                    v = r.get(key, '')
                    return '' if _is_null(v) else str(v)
                tree.insert("", "end", values=(
                    _s('id'), self._t(_s('viloyat')), self._t(_s('tashkilot_turi')),
                    self._t(_s('fish')), _s('telefon'), _s('telegram_username')))

        populate_x()

        edit_frame = ctk.CTkFrame(main_box, fg_color="#F8FAFC", corner_radius=6,
                                  border_width=1, border_color="#CBD5E1")
        edit_frame.pack(fill="x", padx=15, pady=(0, 12))

        ctk.CTkLabel(edit_frame, text=self._t("Tahrirlash:"),
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color="#0F2537").pack(anchor="w", padx=12, pady=(6, 4))

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

        def on_select(_event):
            sel = tree.selection()
            if not sel:
                return
            vals = tree.item(sel[0], "values")
            selected_id[0] = vals[0]
            for entry, val in ((e_fish, vals[3]), (e_tel, vals[4]), (e_tg, vals[5])):
                entry.delete(0, 'end')
                entry.insert(0, val)

        tree.bind("<<TreeviewSelect>>", on_select)

        def save_x():
            if not selected_id[0]:
                messagebox.showwarning(self._t("Diqqat"), self._t("Xodimni tanlang!"))
                return
            fish_v = self._to_latin(e_fish.get().strip()) if self.is_cyrillic else e_fish.get().strip()
            try:
                self.loader.db.save_xodim(selected_id[0], fish_v,
                                          e_tel.get().strip(), e_tg.get().strip())
                populate_x()
                messagebox.showinfo(self._t("Saqlandi"), self._t("Saqlandi!"))
            except Exception as e:
                log_error(e, "save_xodim")
                messagebox.showerror(self._t("Xatolik"), str(e))

        def delete_x():
            if not selected_id[0]:
                messagebox.showwarning(self._t("Diqqat"), self._t("Xodimni tanlang!"))
                return
            if not messagebox.askyesno(self._t("Tasdiqlash"), self._t("O'chirmoqchimisiz?")):
                return
            self.loader.db.delete_xodim(selected_id[0])
            populate_x()
            messagebox.showinfo(self._t("O'chirildi"), self._t("O'chirildi!"))

        ctk.CTkButton(row_inputs, text=self._t("💾 Saqlash"), width=100, height=28,
                      fg_color="#1B5E20", hover_color="#2E7D32",
                      font=ctk.CTkFont(size=11, weight="bold"),
                      command=save_x).pack(side="left", padx=10)
        ctk.CTkButton(row_inputs, text=self._t("🗑 O'chirish"), width=100, height=28,
                      fg_color="#C0392B", hover_color="#A93226",
                      font=ctk.CTkFont(size=11, weight="bold"),
                      command=delete_x).pack(side="left", padx=4)

    def _add_xodim_dialog(self):
        win = ctk.CTkToplevel(self)
        win.title(self._t("Yangi xodim"))
        win.geometry("550x450")
        win.grab_set()
        win.transient(self)

        ctk.CTkLabel(win, text=self._t("➕ YANGI XODIM"),
                     font=ctk.CTkFont(size=14, weight="bold")).pack(pady=15)

        form = ctk.CTkFrame(win, fg_color="#F8FAFC", corner_radius=6,
                            border_width=1, border_color="#CBD5E1")
        form.pack(fill="both", expand=True, padx=20, pady=10)

        ctk.CTkLabel(form, text=self._t("Viloyat:"),
                     font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=20, pady=(15, 2))
        cb_vil = ctk.CTkComboBox(form, values=[self._t(v) for v in VILOYATLAR],
                                  width=400, font=ctk.CTkFont(size=12))
        cb_vil.pack(anchor="w", padx=20)

        ctk.CTkLabel(form, text=self._t("Tashkilot:"),
                     font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=20, pady=(10, 2))
        cb_tash = ctk.CTkComboBox(form, values=[self._t(v) for v in TASHKILOTLAR],
                                   width=400, font=ctk.CTkFont(size=12))
        cb_tash.pack(anchor="w", padx=20)

        ctk.CTkLabel(form, text=self._t("F.I.Sh:"),
                     font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=20, pady=(10, 2))
        e_fish = ctk.CTkEntry(form, width=400, font=ctk.CTkFont(size=12))
        e_fish.pack(anchor="w", padx=20)

        ctk.CTkLabel(form, text=self._t("Telefon:"),
                     font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=20, pady=(10, 2))
        e_tel = ctk.CTkEntry(form, width=400, font=ctk.CTkFont(size=12))
        e_tel.pack(anchor="w", padx=20)

        ctk.CTkLabel(form, text=self._t("Telegram:"),
                     font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=20, pady=(10, 2))
        e_tg = ctk.CTkEntry(form, width=400, font=ctk.CTkFont(size=12))
        e_tg.pack(anchor="w", padx=20)

        def save_new():
            vil_xom = cb_vil.get()
            tash_xom = cb_tash.get()
            fish_xom = e_fish.get().strip()
            tel_val = e_tel.get().strip()
            tg_val = e_tg.get().strip()

            if not fish_xom or not tel_val:
                messagebox.showwarning(self._t("To'ldirish shart"), self._t("F.I.Sh va Tel shart!"))
                return

            vil_val = self._to_latin(vil_xom) if self.is_cyrillic else vil_xom
            tash_val = self._to_latin(tash_xom) if self.is_cyrillic else tash_xom
            fish_val = self._to_latin(fish_xom) if self.is_cyrillic else fish_xom

            ok = self.loader.db.add_xodim(vil_val, tash_val, fish_val, tel_val, tg_val)
            if ok:
                win.destroy()
                self.show_xodimlar_view()
                messagebox.showinfo(self._t("Saqlandi"), self._t("Qo'shildi!"))
            else:
                messagebox.showerror(self._t("Xatolik"), self._t("Xato!"))

        ctk.CTkButton(win, text=self._t("💾 Saqlash"), width=200, height=38,
                      fg_color="#1B5E20", hover_color="#2E7D32",
                      font=ctk.CTkFont(size=13, weight="bold"),
                      command=save_new).pack(pady=15)

    def show_settings_view(self):
        self._push_current_to_stack()
        self.current_view_func = self.show_settings_view

        self.btn_back.configure(state="normal")
        self.lbl_path.configure(text=self._t("Asosiy oyna  /  Sozlamalar"))
        self._clear_container()

        sets = self.loader.db.get_settings()

        main_box = ctk.CTkScrollableFrame(self.container, fg_color="#FFFFFF", corner_radius=6,
                                           border_width=1, border_color="#CBD5E1")
        main_box.pack(fill="both", expand=True, padx=4, pady=4)

        ctk.CTkLabel(main_box, text=self._t("⚙️ SOZLAMALAR"),
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color="#0F2537").pack(pady=(20, 15))

        form = ctk.CTkFrame(main_box, fg_color="#F8FAFC", corner_radius=6,
                            border_width=1, border_color="#CBD5E1")
        form.pack(fill="x", padx=100, pady=10)

        row_sla = ctk.CTkFrame(form, fg_color="transparent")
        row_sla.pack(fill="x", padx=20, pady=(20, 10))
        ctk.CTkLabel(row_sla, text=self._t("SLA kun:"),
                     font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=(0, 10))
        e_sla = ctk.CTkEntry(row_sla, width=80, font=ctk.CTkFont(size=12))
        e_sla.insert(0, str(sets.get("sla_days", "2")))
        e_sla.pack(side="left")

        ctk.CTkLabel(form, text=self._t("Word sarlavhasi:"),
                     font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=20, pady=(15, 2))
        tb_header = ctk.CTkTextbox(form, height=60, font=ctk.CTkFont(size=12))
        h_text = sets.get("report_header",
                          "O‘ZBEKISTON RESPUBLIKASI KADASTR AGENTLIGI\n"
                          "KORRUPSIYAGA QARSHI KURASHISH BO‘LIMI")
        tb_header.insert("1.0", self._t(h_text) if self.is_cyrillic else h_text)
        tb_header.pack(fill="x", padx=20)

        ctk.CTkLabel(form, text=self._t("Telegram shabloni:"),
                     font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=20, pady=(15, 2))
        tb_tg = ctk.CTkTextbox(form, height=120, font=ctk.CTkFont(size=12))
        t_text = sets.get("tg_template", "Murojaat № {id}\nSana: {sana}\nMatn: {matn}")
        tb_tg.insert("1.0", self._t(t_text) if self.is_cyrillic else t_text)
        tb_tg.pack(fill="x", padx=20)

        def save_settings():
            try:
                sla_val = e_sla.get().strip()
                int(sla_val)
            except ValueError:
                messagebox.showerror(self._t("Xatolik"), self._t("SLA butun son!"))
                return
            new_sets = {
                "sla_days": sla_val,
                "report_header": (self._to_latin(tb_header.get("1.0", "end-1c").strip())
                                  if self.is_cyrillic else tb_header.get("1.0", "end-1c").strip()),
                "tg_template": (self._to_latin(tb_tg.get("1.0", "end-1c").strip())
                                if self.is_cyrillic else tb_tg.get("1.0", "end-1c").strip()),
            }
            try:
                self.loader.db.update_settings(new_sets)
                messagebox.showinfo(self._t("Saqlandi"), self._t("Saqlandi!"))
            except Exception as e:
                log_error(e, "save_settings")
                messagebox.showerror(self._t("Xatolik"), str(e))

        ctk.CTkButton(form, text=self._t("💾 Saqlash"), height=32, width=200,
                      fg_color="#1B5E20", hover_color="#2E7D32",
                      font=ctk.CTkFont(size=12, weight="bold"),
                      command=save_settings).pack(pady=15)

        ctk.CTkLabel(main_box, text=self._t("👥 FOYDALANUVCHILAR"),
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color="#0F2537").pack(pady=(30, 10))

        u_frame = ctk.CTkFrame(main_box, fg_color="#F8FAFC", corner_radius=6,
                               border_width=1, border_color="#CBD5E1")
        u_frame.pack(fill="x", padx=100, pady=10)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Users.Treeview", rowheight=28, font=("Calibri", 11))
        style.configure("Users.Treeview.Heading", font=("Calibri", 11, "bold"),
                        background=self.t_colors["primary"], foreground="#FFFFFF")

        tree_u = ttk.Treeview(u_frame, columns=("id", "user", "pass", "role"),
                              show="headings", height=6, style="Users.Treeview")
        tree_u.heading("id", text="ID")
        tree_u.heading("user", text=self._t("Login"))
        tree_u.heading("pass", text=self._t("Parol"))
        tree_u.heading("role", text=self._t("Rol"))

        tree_u.column("id", width=50, anchor="center")
        tree_u.column("user", width=200)
        tree_u.column("pass", width=200)
        tree_u.column("role", width=150, anchor="center")
        tree_u.pack(fill="x", padx=15, pady=(15, 10))

        user_passwords = {}

        def populate_users():
            tree_u.delete(*tree_u.get_children())
            user_passwords.clear()
            try:
                df_u = self.loader.db.get_all_users()
            except Exception as e:
                log_error(e, "populate_users")
                messagebox.showerror(self._t("Xatolik"), str(e))
                return
            for _, r in df_u.iterrows():
                uid = r['id']
                user_passwords[uid] = r['password']
                tree_u.insert("", "end", values=(
                    uid, r['username'], "•" * 8, self._t(r['role'].upper())))

        populate_users()

        u_input = ctk.CTkFrame(u_frame, fg_color="transparent")
        u_input.pack(fill="x", padx=15, pady=10)

        ctk.CTkLabel(u_input, text=self._t("Login:")).pack(side="left", padx=5)
        e_u = ctk.CTkEntry(u_input, width=150)
        e_u.pack(side="left", padx=5)

        ctk.CTkLabel(u_input, text=self._t("Parol:")).pack(side="left", padx=5)
        e_p = ctk.CTkEntry(u_input, width=150, show="•")
        e_p.pack(side="left", padx=5)

        ctk.CTkLabel(u_input, text=self._t("Rol:")).pack(side="left", padx=5)
        cb_r = ctk.CTkComboBox(u_input, values=["admin", "kuzatuvchi"], width=120)
        cb_r.set("kuzatuvchi")
        cb_r.pack(side="left", padx=5)

        sel_uid = [None]

        def on_u_select(_event):
            s = tree_u.selection()
            if not s:
                return
            v = tree_u.item(s[0], "values")
            sel_uid[0] = v[0]
            e_u.delete(0, 'end')
            e_u.insert(0, v[1])
            e_p.delete(0, 'end')
            role_val = self._to_latin(v[3]).lower()
            cb_r.set(role_val if role_val in ["admin", "kuzatuvchi"] else "kuzatuvchi")

        tree_u.bind("<<TreeviewSelect>>", on_u_select)

        def add_u():
            login = e_u.get().strip()
            password = e_p.get().strip()
            if not login or not password:
                messagebox.showwarning(self._t("Xato"), self._t("Kiriting!"))
                return
            try:
                ok = self.loader.db.add_user(login, password, cb_r.get())
                if ok:
                    populate_users()
                    messagebox.showinfo(self._t("Saqlandi"), self._t("Qo'shildi!"))
                else:
                    messagebox.showerror(self._t("Xato"), self._t("Login band!"))
            except Exception as e:
                log_error(e, "add_user")
                messagebox.showerror(self._t("Xatolik"), str(e))

        def upd_u():
            if not sel_uid[0]:
                messagebox.showwarning(self._t("Xato"), self._t("Tanlang!"))
                return
            new_pass = e_p.get().strip()
            if not new_pass:
                new_pass = user_passwords.get(sel_uid[0], "")
            try:
                self.loader.db.update_user(sel_uid[0], e_u.get().strip(), new_pass, cb_r.get())
                populate_users()
                messagebox.showinfo(self._t("Saqlandi"), self._t("Yangilandi!"))
            except Exception as e:
                log_error(e, "upd_user")
                messagebox.showerror(self._t("Xatolik"), str(e))

        def del_u():
            if not sel_uid[0]:
                messagebox.showwarning(self._t("Xato"), self._t("Tanlang!"))
                return
            if str(sel_uid[0]) == "1":
                messagebox.showerror(self._t("Xato"), self._t("Admin o'chirilmaydi!"))
                return
            if not messagebox.askyesno(self._t("Tasdiqlash"), self._t("O'chirmoqchimisiz?")):
                return
            self.loader.db.delete_user(sel_uid[0])
            populate_users()
            messagebox.showinfo(self._t("O'chirildi"), self._t("O'chirildi!"))

        btn_row = ctk.CTkFrame(u_frame, fg_color="transparent")
        btn_row.pack(pady=10)

        ctk.CTkButton(btn_row, text=self._t("➕ Qo'shish"), width=120,
                      fg_color=self.t_colors["btn"], hover_color=self.t_colors["hover"],
                      command=add_u).pack(side="left", padx=5)
        ctk.CTkButton(btn_row, text=self._t("💾 Saqlash"), width=120,
                      fg_color="#27AE60", command=upd_u).pack(side="left", padx=5)
        ctk.CTkButton(btn_row, text=self._t("🗑 O'chirish"), width=100,
                      fg_color="#C0392B", hover_color="#A93226",
                      command=del_u).pack(side="left", padx=5)

    def show_charts_view(self):
        self._push_current_to_stack()
        self.current_view_func = self.show_charts_view

        self.btn_back.configure(state="normal")
        self.lbl_path.configure(text=self._t("Asosiy oyna  /  Grafiklar"))
        self._clear_container()

        main_box = ctk.CTkFrame(self.container, fg_color="#FFFFFF", corner_radius=6,
                                border_width=1, border_color="#CBD5E1")
        main_box.pack(fill="both", expand=True, padx=4, pady=4)

        ctk.CTkLabel(main_box, text=self._t("📈 GRAFIKALAR VA TAHLIL"),
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color="#0F2537").pack(pady=(10, 5))

        charts_frame = ctk.CTkScrollableFrame(main_box, fg_color="transparent")
        charts_frame.pack(fill="both", expand=True, padx=10, pady=5)

        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            HAS_MPL = True
        except ImportError:
            HAS_MPL = False

        if not HAS_MPL:
            ctk.CTkLabel(charts_frame,
                         text=self._t("⚠️ matplotlib o'rnatilmagan!\n\n"
                                      "Terminalda: pip install matplotlib"),
                         font=ctk.CTkFont(size=13), text_color="#C0392B").pack(pady=30)
            return

        f_df = self.loader.filtered_df
        if f_df.empty:
            ctk.CTkLabel(charts_frame, text=self._t("Ma'lumot yo'q"),
                         font=ctk.CTkFont(size=13)).pack(pady=30)
            return

        chart1_frame = ctk.CTkFrame(charts_frame, fg_color="#F8FAFC", corner_radius=6,
                                    border_width=1, border_color="#CBD5E1")
        chart1_frame.pack(fill="both", expand=True, padx=5, pady=5)

        ctk.CTkLabel(chart1_frame, text=self._t("🏙 Viloyatlar bo'yicha murojaatlar"),
                     font=ctk.CTkFont(size=12, weight="bold")).pack(pady=5)

        try:
            fig1, ax1 = plt.subplots(figsize=(10, 4), dpi=80)
            reg_counts = f_df['Viloyat'].value_counts().head(14)
            colors = plt.cm.Blues(range(50, 250, 200 // max(1, len(reg_counts))))
            ax1.barh(range(len(reg_counts)), reg_counts.values, color=colors)
            ax1.set_yticks(range(len(reg_counts)))
            ax1.set_yticklabels(reg_counts.index, fontsize=9)
            ax1.set_xlabel(self._t("Murojaatlar soni"), fontsize=9)
            ax1.invert_yaxis()
            ax1.grid(axis='x', alpha=0.3)
            fig1.tight_layout()

            canvas1 = FigureCanvasTkAgg(fig1, master=chart1_frame)
            canvas1.draw()
            canvas1.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=5)
            plt.close(fig1)
        except Exception as e:
            log_error(e, "chart1")
            ctk.CTkLabel(chart1_frame, text=f"⚠️ {e}").pack()

        chart2_frame = ctk.CTkFrame(charts_frame, fg_color="#F8FAFC", corner_radius=6,
                                    border_width=1, border_color="#CBD5E1")
        chart2_frame.pack(fill="both", expand=True, padx=5, pady=5)

        ctk.CTkLabel(chart2_frame, text=self._t("📊 Holat bo'yicha taqsimot"),
                     font=ctk.CTkFont(size=12, weight="bold")).pack(pady=5)

        try:
            fig2, ax2 = plt.subplots(figsize=(7, 5), dpi=80)
            status_counts = f_df['Ijro_Holati'].value_counts().head(6)
            colors2 = ['#3498DB', '#27AE60', '#E74C3C', '#F39C12', '#9B59B6', '#7F8C8D']
            wedges, texts, autotexts = ax2.pie(
                status_counts.values, labels=None, autopct='%1.1f%%',
                colors=colors2[:len(status_counts)], startangle=90)
            ax2.legend(wedges, [s[:30] for s in status_counts.index],
                       loc="center left", bbox_to_anchor=(1, 0, 0.5, 1), fontsize=8)
            for t in autotexts:
                t.set_fontsize(8)
            fig2.tight_layout()

            canvas2 = FigureCanvasTkAgg(fig2, master=chart2_frame)
            canvas2.draw()
            canvas2.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=5)
            plt.close(fig2)
        except Exception as e:
            log_error(e, "chart2")
            ctk.CTkLabel(chart2_frame, text=f"⚠️ {e}").pack()

        chart3_frame = ctk.CTkFrame(charts_frame, fg_color="#F8FAFC", corner_radius=6,
                                    border_width=1, border_color="#CBD5E1")
        chart3_frame.pack(fill="both", expand=True, padx=5, pady=5)

        ctk.CTkLabel(chart3_frame, text=self._t("📅 Kunlik trend (so'nggi 30 kun)"),
                     font=ctk.CTkFont(size=12, weight="bold")).pack(pady=5)

        try:
            if 'DT' in f_df.columns:
                df_t = f_df.copy()
                df_t['DT'] = pd.to_datetime(df_t['DT'], errors='coerce')
                df_t = df_t.dropna(subset=['DT'])
                df_t['date'] = df_t['DT'].dt.date
                daily = df_t.groupby('date').size().tail(30)

                if not daily.empty:
                    fig3, ax3 = plt.subplots(figsize=(10, 3.5), dpi=80)
                    ax3.plot(daily.index, daily.values, marker='o', color='#3498DB', linewidth=2)
                    ax3.fill_between(daily.index, daily.values, alpha=0.3, color='#3498DB')
                    ax3.set_xlabel(self._t("Sana"), fontsize=9)
                    ax3.set_ylabel(self._t("Soni"), fontsize=9)
                    ax3.grid(alpha=0.3)
                    ax3.tick_params(axis='x', rotation=45, labelsize=8)
                    fig3.tight_layout()

                    canvas3 = FigureCanvasTkAgg(fig3, master=chart3_frame)
                    canvas3.draw()
                    canvas3.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=5)
                    plt.close(fig3)
                else:
                    ctk.CTkLabel(chart3_frame, text=self._t("Ma'lumot yo'q")).pack()
        except Exception as e:
            log_error(e, "chart3")
            ctk.CTkLabel(chart3_frame, text=f"⚠️ {e}").pack()

    def show_audit_view(self):
        win = ctk.CTkToplevel(self)
        win.title(self._t("Kirishlar tarixi"))
        win.geometry("850x500")
        win.grab_set()

        ctk.CTkLabel(win, text=self._t("👥 Tizimga kirishlar tarixi"),
                     font=ctk.CTkFont(size=16, weight="bold"),
                     text_color="#0F2537").pack(pady=15)

        t_box = ctk.CTkFrame(win, fg_color="#FFFFFF", border_width=1, border_color="#CBD5E1")
        t_box.pack(padx=15, pady=5, fill="both", expand=True)

        cols = ("#", "user", "role", "time", "comp")
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Audit.Treeview", rowheight=26, font=("Calibri", 11))
        style.configure("Audit.Treeview.Heading", font=("Calibri", 11, "bold"),
                        background=self.t_colors["primary"], foreground="#FFFFFF")

        tree = ttk.Treeview(t_box, columns=cols, show="headings", height=15, style="Audit.Treeview")
        tree.heading("#", text="№")
        tree.heading("user", text=self._t("Login"))
        tree.heading("role", text=self._t("Rol"))
        tree.heading("time", text=self._t("Vaqt"))
        tree.heading("comp", text=self._t("Kompyuter"))

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
                r_str = (self._t("Kuzatuvchi")
                         if str(r.get('Rol', '')).lower() == 'kuzatuvchi'
                         else self._t("Administrator"))
                tree.insert("", "end", values=(
                    r.get('#', ''), r.get('Foydalanuvchi', ''), r_str,
                    r.get('Kirish vaqti', ''), self._t(r.get('Kompyuter', ''))))
        except Exception as e:
            log_error(e, "audit view")
            messagebox.showerror(self._t("Xatolik"), str(e))

    def _import_excel(self):
        fp = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx *.xls")])
        if not fp:
            return
        self._show_loading("📥 Excel yuklanmoqda...")
        try:
            self.loader.load_from_excel(fp)
            self._hide_loading()
            self._redraw_entire_ui()
            messagebox.showinfo(self._t("Baza yangilandi"), self._t("Yuklandi!"))
        except Exception as e:
            log_error(e, "import_excel")
            self._hide_loading()
            messagebox.showerror(self._t("Xatolik"), str(e))

    def _export_excel(self):
        manba = getattr(self, 'selected_manba', 'Barchasi')
        if 'Telegram' in manba:
            fname = "Telegram_bot_murojaatlar.xlsx"
        elif 'Ishonch' in manba:
            fname = "Ishonch_telefoni_murojaatlar.xlsx"
        else:
            fname = "Barcha_murojaatlar_Umumiy.xlsx"

        fp = filedialog.asksaveasfilename(defaultextension=".xlsx", initialfile=fname)
        if not fp:
            return
        self._show_loading("📊 Excel tayyorlanmoqda...")
        try:
            ReportGenerator.export_excel(self.loader.filtered_df, fp)
            self._hide_loading()
            messagebox.showinfo(self._t("Tayyor"), self._t(f"{manba} saqlandi!"))
            reveal_in_file_manager(fp)
        except Exception as e:
            log_error(e, "export_excel")
            self._hide_loading()
            messagebox.showerror(self._t("Xatolik"), str(e))

    def _export_word(self):
        fp = filedialog.asksaveasfilename(defaultextension=".docx",
                                          initialfile="Rahbariyatga_Malumotnoma.docx")
        if not fp:
            return
        sets = self.loader.db.get_settings()
        period_val = self._t(getattr(self, 'selected_period', 'Barchasi'))
        self._show_loading("📄 Word tayyorlanmoqda...")
        try:
            ReportGenerator.export_word_report(
                self.loader.get_kpi_stats(),
                self.loader.filtered_df['Viloyat'].value_counts(),
                fp, period_val,
                self._t(sets.get("report_header",
                                 "O‘ZBEKISTON RESPUBLIKASI KADASTR AGENTLIGI")))
            self._hide_loading()
            messagebox.showinfo(self._t("Tayyor"), self._t("Word saqlandi!"))
            reveal_in_file_manager(fp)
        except Exception as e:
            log_error(e, "export_word")
            self._hide_loading()
            messagebox.showerror(self._t("Xatolik"), str(e))

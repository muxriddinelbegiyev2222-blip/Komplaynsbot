import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import customtkinter as ctk
import pandas as pd
from datetime import datetime

from src.db_manager import DatabaseManager

# Tashqi modullarni xavfsiz yuklash
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

        # Oyna sozlamalari
        self.title("Kadastr agentligi — Korrupsiyaga qarshi komplayens monitoring tizimi")
        self.geometry("1300x760")
        self.minsize(1100, 650)

        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        self.df_data = pd.DataFrame()
        self.filtered_df = pd.DataFrame()

        self._build_layout()
        self.load_data()

    def _build_layout(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # =====================================================================
        # 1. CHAP BOSHQARUV PANELI (SIDEBAR)
        # =====================================================================
        self.sidebar_frame = ctk.CTkFrame(self, width=250, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(13, weight=1)

        # Logotip va sarlavha
        lbl_logo = ctk.CTkLabel(
            self.sidebar_frame, 
            text="🛡 KOMPLAYENS\nMONITORING", 
            font=ctk.CTkFont(size=18, weight="bold")
        )
        lbl_logo.grid(row=0, column=0, padx=20, pady=(20, 15))

        # Profil kartochkasi
        role_title = "👑 Administrator" if self.role == "admin" else "👁 Kuzatuvchi (Rahbar)"
        badge_color = "#1f538d" if self.role == "admin" else "#8d6e1f"

        self.user_frame = ctk.CTkFrame(self.sidebar_frame, fg_color=badge_color, corner_radius=8)
        self.user_frame.grid(row=1, column=0, padx=15, pady=(0, 15), sticky="ew")

        lbl_user = ctk.CTkLabel(
            self.user_frame, 
            text=f"👤 {self.username}", 
            font=ctk.CTkFont(size=14, weight="bold"), 
            text_color="white"
        )
        lbl_user.pack(padx=10, pady=(6, 2))

        lbl_role = ctk.CTkLabel(
            self.user_frame, 
            text=role_title, 
            font=ctk.CTkFont(size=12), 
            text_color="#e0e0e0"
        )
        lbl_role.pack(padx=10, pady=(0, 6))

        # Yangilash tugmasi
        btn_refresh = ctk.CTkButton(
            self.sidebar_frame, 
            text="🔄 Ma'lumotlarni yangilash", 
            command=self.load_data,
            fg_color="#2b5c8f", hover_color="#1d3f63"
        )
        btn_refresh.grid(row=2, column=0, padx=15, pady=6, sticky="ew")

        current_row = 3

        # Faqat ADMIN uchun ko'rinadigan tugmalar
        if self.role == "admin":
            btn_import = ctk.CTkButton(
                self.sidebar_frame, 
                text="📥 Excel fayl yuklash", 
                command=self.import_excel,
                fg_color="#2e7d32", hover_color="#1b5e20"
            )
            btn_import.grid(row=current_row, column=0, padx=15, pady=6, sticky="ew")
            current_row += 1

            btn_add = ctk.CTkButton(
                self.sidebar_frame, 
                text="➕ Yangi murojaat", 
                command=self.open_add_murojaat_window
            )
            btn_add.grid(row=current_row, column=0, padx=15, pady=6, sticky="ew")
            current_row += 1

            # RAHBARLAR KELIB-KETISHINI NAZORAT QILISH
            btn_audit = ctk.CTkButton(
                self.sidebar_frame, 
                text="📊 Kirishlar tarixi (Audit)", 
                command=self.open_audit_window,
                fg_color="#e65100", hover_color="#b23c00"
            )
            btn_audit.grid(row=current_row, column=0, padx=15, pady=6, sticky="ew")
            current_row += 1

            btn_users = ctk.CTkButton(
                self.sidebar_frame, 
                text="👥 Foydalanuvchilar", 
                command=self.open_users_window
            )
            btn_users.grid(row=current_row, column=0, padx=15, pady=6, sticky="ew")
            current_row += 1

            btn_xodimlar = ctk.CTkButton(
                self.sidebar_frame, 
                text="📋 Mas'ul xodimlar", 
                command=self.open_xodimlar_window
            )
            btn_xodimlar.grid(row=current_row, column=0, padx=15, pady=6, sticky="ew")
            current_row += 1

            btn_settings = ctk.CTkButton(
                self.sidebar_frame, 
                text="⚙️ Tizim sozlamalari", 
                command=self.open_settings_window
            )
            btn_settings.grid(row=current_row, column=0, padx=15, pady=6, sticky="ew")
            current_row += 1

        # Umumiy hisobot eksporti
        btn_report = ctk.CTkButton(
            self.sidebar_frame, 
            text="📑 Hisobot tayyorlash", 
            command=self.generate_report,
            fg_color="#455a64", hover_color="#263238"
        )
        btn_report.grid(row=current_row, column=0, padx=15, pady=6, sticky="ew")

        # Chiqish
        btn_exit = ctk.CTkButton(
            self.sidebar_frame, 
            text="🚪 Chiqish", 
            command=self.destroy,
            fg_color="#c62828", hover_color="#8e0000"
        )
        btn_exit.grid(row=14, column=0, padx=15, pady=20, sticky="ew")

        # =====================================================================
        # 2. ASOSIY OYNA (MAIN CONTENT)
        # =====================================================================
        self.main_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=15, pady=15)
        self.main_frame.grid_rowconfigure(2, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)

        # 2.1. KPI Vidjetlari (Statistika kartochkalari)
        self.kpi_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.kpi_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        for i in range(4):
            self.kpi_frame.grid_columnconfigure(i, weight=1)

        self.kpi_cards = {}
        cards_info = [
            ("jami", "Jami murojaatlar", "0", "#1976d2"),
            ("yangi", "O'rganilmoqda / Yangi", "0", "#f57c00"),
            ("ijobiy", "Bajarildi (Ijobiy)", "0", "#388e3c"),
            ("chora", "Chora ko'rilgan", "0", "#7b1fa2")
        ]

        for idx, (cid, title, val, col) in enumerate(cards_info):
            card = ctk.CTkFrame(self.kpi_frame, corner_radius=10, fg_color=col)
            card.grid(row=0, column=idx, padx=5, sticky="ew")
            lbl_t = ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=12, weight="bold"), text_color="white")
            lbl_t.pack(pady=(8, 0))
            lbl_v = ctk.CTkLabel(card, text=val, font=ctk.CTkFont(size=22, weight="bold"), text_color="white")
            lbl_v.pack(pady=(0, 8))
            self.kpi_cards[cid] = lbl_v

        # 2.2. Qidiruv va Filtrlar paneli
        self.filter_frame = ctk.CTkFrame(self.main_frame, corner_radius=10)
        self.filter_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10), padx=5)

        lbl_s = ctk.CTkLabel(self.filter_frame, text="🔍 Qidirish:")
        lbl_s.pack(side="left", padx=(15, 5), pady=10)

        self.entry_search = ctk.CTkEntry(self.filter_frame, width=220, placeholder_text="F.I.Sh., tel, mazmun...")
        self.entry_search.pack(side="left", padx=5, pady=10)
        self.entry_search.bind("<KeyRelease>", lambda e: self.apply_filters())

        lbl_reg = ctk.CTkLabel(self.filter_frame, text="📍 Hudud:")
        lbl_reg.pack(side="left", padx=(15, 5), pady=10)

        regions_list = [
            "Barchasi", "Buxoro viloyati", "Farg'ona viloyati", "Jizzax viloyati", 
            "Namangan viloyati", "Navoiy viloyati", "Qashqadaryo viloyati", 
            "Qoraqalpog'iston Respublikasi", "Samarqand viloyati", "Sirdaryo viloyati", 
            "Surxondaryo viloyati", "Toshkent shahri", "Toshkent viloyati", "Xorazm viloyati"
        ]
        self.combo_region = ctk.CTkComboBox(self.filter_frame, values=regions_list, width=170, command=lambda v: self.apply_filters())
        self.combo_region.set("Barchasi")
        self.combo_region.pack(side="left", padx=5, pady=10)

        lbl_st = ctk.CTkLabel(self.filter_frame, text="📌 Holat:")
        lbl_st.pack(side="left", padx=(15, 5), pady=10)

        status_list = ["Barchasi", "O‘rganishga yuborilgan", "O‘rganilmoqda", "Bajarildi (Ijobiy)", "Tushuntirish berildi", "Rad etildi", "Yangi"]
        self.combo_status = ctk.CTkComboBox(self.filter_frame, values=status_list, width=170, command=lambda v: self.apply_filters())
        self.combo_status.set("Barchasi")
        self.combo_status.pack(side="left", padx=5, pady=10)

        btn_reset = ctk.CTkButton(self.filter_frame, text="Tozalash", width=80, fg_color="#546e7a", command=self.reset_filters)
        btn_reset.pack(side="right", padx=15, pady=10)

        # 2.3. Murojaatlar jadvali (Treeview)
        self.table_frame = ctk.CTkFrame(self.main_frame, corner_radius=10)
        self.table_frame.grid(row=2, column=0, sticky="nsew", padx=5)
        self.table_frame.grid_rowconfigure(0, weight=1)
        self.table_frame.grid_columnconfigure(0, weight=1)

        columns = ("#", "sana", "fish", "telefon", "viloyat", "tuman", "yonalish", "ijro_holati", "masul", "chora")
        self.tree = ttk.Treeview(self.table_frame, columns=columns, show="headings", selectmode="browse")

        self.tree.heading("#", text="№")
        self.tree.heading("sana", text="Sana")
        self.tree.heading("fish", text="Fuqaro F.I.Sh.")
        self.tree.heading("telefon", text="Telefon")
        self.tree.heading("viloyat", text="Hudud")
        self.tree.heading("tuman", text="Tuman")
        self.tree.heading("yonalish", text="Yo'nalish")
        self.tree.heading("ijro_holati", text="Ijro holati")
        self.tree.heading("masul", text="Mas'ul xodim")
        self.tree.heading("chora", text="Chora turi")

        self.tree.column("#", width=50, anchor="center")
        self.tree.column("sana", width=100, anchor="center")
        self.tree.column("fish", width=160)
        self.tree.column("telefon", width=110, anchor="center")
        self.tree.column("viloyat", width=130)
        self.tree.column("tuman", width=110)
        self.tree.column("yonalish", width=150)
        self.tree.column("ijro_holati", width=140, anchor="center")
        self.tree.column("masul", width=150)
        self.tree.column("chora", width=130, anchor="center")

        scroll_y = ttk.Scrollbar(self.table_frame, orient="vertical", command=self.tree.yview)
        scroll_x = ttk.Scrollbar(self.table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        scroll_y.grid(row=0, column=1, sticky="ns")
        scroll_x.grid(row=1, column=0, sticky="ew")

        self.tree.bind("<Double-1>", self.on_double_click_row)

        # 2.4. Pastki status satri
        self.status_bar = ctk.CTkFrame(self.main_frame, height=28, fg_color="transparent")
        self.status_bar.grid(row=3, column=0, sticky="ew", pady=(8, 0))

        self.lbl_record_count = ctk.CTkLabel(self.status_bar, text="Murojaatlar soni: 0 ta", font=ctk.CTkFont(size=12))
        self.lbl_record_count.pack(side="left", padx=10)

        lbl_mode_info = ctk.CTkLabel(
            self.status_bar, 
            text="👁 Kuzatuvchi rejimi: Faqat ko'rish huquqi" if self.role == "kuzatuvchi" else "⚡️ Administrator rejimi: To'liq boshqaruv",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#ffb74d" if self.role == "kuzatuvchi" else "#81c784"
        )
        lbl_mode_info.pack(side="right", padx=10)

    # =====================================================================
    # MA'LUMOTLARNI YUKLASH VA FILTRLASH
    # =====================================================================
    def load_data(self):
        try:
            self.df_data = self.db.get_all_records()
            self.apply_filters()
            self._update_kpi_cards()
        except Exception as e:
            messagebox.showerror("Xatolik", f"Ma'lumotlarni yuklashda xatolik: {e}")

    def _update_kpi_cards(self):
        if self.df_data.empty:
            for k in self.kpi_cards:
                self.kpi_cards[k].configure(text="0")
            return

        jami = len(self.df_data)
        holatlar = self.df_data['Ijro_Holati'].astype(str).str.lower() if 'Ijro_Holati' in self.df_data.columns else pd.Series()
        choralar = self.df_data['Chora_Turi'].astype(str).str.lower() if 'Chora_Turi' in self.df_data.columns else pd.Series()

        yangi = holatlar.str.contains('yuborilgan|yangi|o‘rganilmoqda|organilmoqda', regex=True).sum()
        ijobiy = holatlar.str.contains('ijobiy|bajarildi', regex=True).sum()
        chora_soni = ((choralar != 'chora ko‘rilmagan') & (choralar != '') & (choralar != 'nan')).sum()

        self.kpi_cards["jami"].configure(text=str(jami))
        self.kpi_cards["yangi"].configure(text=str(yangi))
        self.kpi_cards["ijobiy"].configure(text=str(ijobiy))
        self.kpi_cards["chora"].configure(text=str(chora_soni))

    def apply_filters(self):
        if self.df_data.empty:
            self.tree.delete(*self.tree.get_children())
            self.lbl_record_count.configure(text="Murojaatlar soni: 0 ta")
            return

        df = self.df_data.copy()

        search_txt = self.entry_search.get().strip().lower()
        if search_txt:
            mask = (
                df['F.I.Sh.'].astype(str).str.lower().str.contains(search_txt, na=False) |
                df['Telefon'].astype(str).str.lower().str.contains(search_txt, na=False) |
                df['Murojaat matni'].astype(str).str.lower().str.contains(search_txt, na=False) |
                df['#'].astype(str).str.contains(search_txt, na=False)
            )
            df = df[mask]

        reg = self.combo_region.get()
        if reg != "Barchasi":
            df = df[df['Viloyat'] == reg]

        st = self.combo_status.get()
        if st != "Barchasi":
            df = df[df['Ijro_Holati'] == st]

        self.filtered_df = df

        self.tree.delete(*self.tree.get_children())
        for _, row in df.iterrows():
            self.tree.insert("", "end", values=(
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

        self.lbl_record_count.configure(text=f"Ko'rsatilmoqda: {len(df)} ta (Jami bazada: {len(self.df_data)} ta)")

    def reset_filters(self):
        self.entry_search.delete(0, "end")
        self.combo_region.set("Barchasi")
        self.combo_status.set("Barchasi")
        self.apply_filters()

    def on_double_click_row(self, event):
        item = self.tree.selection()
        if not item: return
        vals = self.tree.item(item[0], "values")
        if not vals: return
        m_id = int(vals[0])

        if DetailsWindow:
            try:
                DetailsWindow(self, m_id, self.db, self.load_data, role=self.role)
            except TypeError:
                DetailsWindow(self, m_id, self.db, self.load_data)
        else:
            messagebox.showinfo("Batafsil", f"Murojaat № {m_id}")

    # =====================================================================
    # POPUP OYNALAR (ADMIN FUNKSIYALARI)
    # =====================================================================
    def open_audit_window(self):
        audit_win = ctk.CTkToplevel(self)
        audit_win.title("Tizimga kirishlar tarixi (Audit Log)")
        audit_win.geometry("820x520")
        audit_win.grab_set()

        ctk.CTkLabel(
            audit_win, 
            text="👥 Foydalanuvchilarning dasturga kirish faolligi", 
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(pady=(15, 5))

        table_box = ctk.CTkFrame(audit_win)
        table_box.pack(padx=20, pady=10, fill="both", expand=True)

        cols = ("#", "user", "role", "time", "comp")
        tree_audit = ttk.Treeview(table_box, columns=cols, show="headings", height=15)
        tree_audit.heading("#", text="№")
        tree_audit.heading("user", text="Foydalanuvchi logini")
        tree_audit.heading("role", text="Tizimdagi roli")
        tree_audit.heading("time", text="Kirgan vaqti")
        tree_audit.heading("comp", text="Kompyuter nomi")

        tree_audit.column("#", width=60, anchor="center")
        tree_audit.column("user", width=160, anchor="center")
        tree_audit.column("role", width=140, anchor="center")
        tree_audit.column("time", width=200, anchor="center")
        tree_audit.column("comp", width=180, anchor="center")

        sb = ttk.Scrollbar(table_box, orient="vertical", command=tree_audit.yview)
        tree_audit.configure(yscrollcommand=sb.set)

        tree_audit.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        def load_audit():
            tree_audit.delete(*tree_audit.get_children())
            df_logs = self.db.get_audit_logs()
            if not df_logs.empty:
                for _, r in df_logs.iterrows():
                    u_role = str(r.get('Rol', '')).lower()
                    role_str = "Kuzatuvchi (Rahbar)" if u_role == "kuzatuvchi" else "Administrator"
                    tree_audit.insert("", "end", values=(
                        r.get('#', ''),
                        r.get('Foydalanuvchi', ''),
                        role_str,
                        r.get('Kirish vaqti', ''),
                        r.get('Kompyuter', '')
                    ))

        load_audit()
        ctk.CTkButton(audit_win, text="🔄 Yangilash", command=load_audit, width=120).pack(pady=(0, 15))

    def open_users_window(self):
        users_win = ctk.CTkToplevel(self)
        users_win.title("Foydalanuvchilarni boshqarish")
        users_win.geometry("650x450")
        users_win.grab_set()

        ctk.CTkLabel(users_win, text="Foydalanuvchilar va ularning rollari", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)

        form = ctk.CTkFrame(users_win)
        form.pack(padx=20, pady=5, fill="x")

        e_login = ctk.CTkEntry(form, placeholder_text="Login", width=130)
        e_login.pack(side="left", padx=5, pady=10)

        e_pass = ctk.CTkEntry(form, placeholder_text="Parol", width=130)
        e_pass.pack(side="left", padx=5, pady=10)

        cb_role = ctk.CTkComboBox(form, values=["kuzatuvchi", "admin"], width=130)
        cb_role.set("kuzatuvchi")
        cb_role.pack(side="left", padx=5, pady=10)

        tree_u = ttk.Treeview(users_win, columns=("id", "login", "pass", "role"), show="headings", height=8)
        tree_u.heading("id", text="ID")
        tree_u.heading("login", text="Login")
        tree_u.heading("pass", text="Parol")
        tree_u.heading("role", text="Roli")
        tree_u.column("id", width=40, anchor="center")
        tree_u.pack(padx=20, pady=10, fill="both", expand=True)

        def refresh_u():
            tree_u.delete(*tree_u.get_children())
            df_u = self.db.get_all_users()
            for _, r in df_u.iterrows():
                tree_u.insert("", "end", values=(r['id'], r['username'], r['password'], r['role']))

        def add_u():
            log = e_login.get().strip()
            pas = e_pass.get().strip()
            rol = cb_role.get().strip()
            if not log or not pas:
                messagebox.showwarning("Xato", "Login va parolni kiriting!")
                return
            if self.db.add_user(log, pas, rol):
                messagebox.showinfo("Muvaffaqiyatli", f"Foydalanuvchi '{log}' qo'shildi!")
                e_login.delete(0, "end")
                e_pass.delete(0, "end")
                refresh_u()
            else:
                messagebox.showerror("Xato", "Bunday login allaqachon mavjud!")

        def del_u():
            sel = tree_u.selection()
            if not sel: return
            u_id = tree_u.item(sel[0], "values")[0]
            if str(u_id) == "1":
                messagebox.showwarning("Xato", "Asosiy adminni o'chirib bo'lmaydi!")
                return
            if messagebox.askyesno("Tasdiqlash", "O'chirilsinmi?"):
                self.db.delete_user(u_id)
                refresh_u()

        ctk.CTkButton(form, text="Qo'shish", width=100, command=add_u, fg_color="#2e7d32").pack(side="left", padx=10, pady=10)
        ctk.CTkButton(users_win, text="Tanlanganni o'chirish", fg_color="#c62828", command=del_u).pack(pady=10)
        refresh_u()

    def open_add_murojaat_window(self):
        add_win = ctk.CTkToplevel(self)
        add_win.title("Yangi murojaat (Ishonch telefoni)")
        add_win.geometry("500x560")
        add_win.grab_set()

        ctk.CTkLabel(add_win, text="Yangi murojaatni qayd etish", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)

        e_fish = ctk.CTkEntry(add_win, placeholder_text="Fuqaro F.I.Sh.", width=400)
        e_fish.pack(pady=6)
        e_tel = ctk.CTkEntry(add_win, placeholder_text="Telefon raqami", width=400)
        e_tel.pack(pady=6)

        cb_vil = ctk.CTkComboBox(add_win, values=[
            "Toshkent shahri", "Toshkent viloyati", "Samarqand viloyati", "Farg'ona viloyati", 
            "Andijon viloyati", "Namangan viloyati", "Buxoro viloyati", "Qashqadaryo viloyati", 
            "Surxondaryo viloyati", "Jizzax viloyati", "Sirdaryo viloyati", "Navoiy viloyati", 
            "Xorazm viloyati", "Qoraqalpog'iston Respublikasi"
        ], width=400)
        cb_vil.set("Toshkent shahri")
        cb_vil.pack(pady=6)

        e_tum = ctk.CTkEntry(add_win, placeholder_text="Tuman / Shahar", width=400)
        e_tum.pack(pady=6)

        cb_yon = ctk.CTkComboBox(add_win, values=["Kadastr agentligi faoliyati yuzasidan", "Davlat kadastrlari palatasi faoliyati yuzasidan"], width=400)
        cb_yon.set("Kadastr agentligi faoliyati yuzasidan")
        cb_yon.pack(pady=6)

        txt_m = ctk.CTkTextbox(add_win, width=400, height=120)
        txt_m.insert("0.0", "Murojaat matni...")
        txt_m.pack(pady=6)

        def save_m():
            f = e_fish.get().strip()
            t = e_tel.get().strip()
            v = cb_vil.get().strip()
            tm = e_tum.get().strip()
            y = cb_yon.get().strip()
            m = txt_m.get("0.0", "end").strip()
            if not f or not m:
                messagebox.showwarning("Xato", "F.I.Sh. va matnni kiriting!")
                return
            mas = "Kadastr agentligi hududiy komplayens xodimi" if "agentlik" in y.lower() else "Davlat kadastrlari palatasi hududiy komplayens xodimi"
            nid = self.db.insert_phone_murojaat(f, t, v, tm, y, m, mas)
            messagebox.showinfo("Saqlandi", f"Murojaat № {nid} qabul qilindi!")
            add_win.destroy()
            self.load_data()

        ctk.CTkButton(add_win, text="💾 Saqlash", command=save_m, fg_color="#2e7d32", width=400).pack(pady=15)

    def open_xodimlar_window(self):
        x_win = ctk.CTkToplevel(self)
        x_win.title("Hududiy mas'ul xodimlar")
        x_win.geometry("750x450")
        x_win.grab_set()

        tree_x = ttk.Treeview(x_win, columns=("id", "vil", "tash", "fish", "tel", "tg"), show="headings")
        tree_x.heading("id", text="ID")
        tree_x.heading("vil", text="Viloyat")
        tree_x.heading("tash", text="Tashkilot")
        tree_x.heading("fish", text="Xodim F.I.Sh.")
        tree_x.heading("tel", text="Telefon")
        tree_x.heading("tg", text="Telegram")
        tree_x.column("id", width=40, anchor="center")
        tree_x.pack(padx=20, pady=20, fill="both", expand=True)

        df_x = self.db.get_xodimlar()
        for _, r in df_x.iterrows():
            tree_x.insert("", "end", values=(r['id'], r['viloyat'], r['tashkilot_turi'], r['fish'], r['telefon'], r['telegram_username']))

    def open_settings_window(self):
        s_win = ctk.CTkToplevel(self)
        s_win.title("Tizim sozlamalari")
        s_win.geometry("500x350")
        s_win.grab_set()

        curr = self.db.get_settings()

        ctk.CTkLabel(s_win, text="Murojaatni o'rganish muddati (kunlarda):").pack(pady=(20, 5))
        e_sla = ctk.CTkEntry(s_win, width=300)
        e_sla.insert(0, curr.get("sla_days", "2"))
        e_sla.pack(pady=5)

        ctk.CTkLabel(s_win, text="Hisobot sarlavhasi matni:").pack(pady=(15, 5))
        txt_rep = ctk.CTkTextbox(s_win, width=400, height=80)
        txt_rep.insert("0.0", curr.get("report_header", ""))
        txt_rep.pack(pady=5)

        def save_s():
            self.db.update_settings({
                "sla_days": e_sla.get().strip(),
                "report_header": txt_rep.get("0.0", "end").strip()
            })
            messagebox.showinfo("Saqlandi", "Sozlamalar saqlandi!")
            s_win.destroy()

        ctk.CTkButton(s_win, text="💾 Saqlash", command=save_s, fg_color="#2e7d32").pack(pady=20)

    def import_excel(self):
        fpath = filedialog.askopenfilename(filetypes=[("Excel fayllar", "*.xlsx *.xls")])
        if not fpath: return
        try:
            df = pd.read_excel(fpath)
            self.db.sync_excel_data(df)
            messagebox.showinfo("Muvaffaqiyatli", "Excel murojaatlari bazaga yuklandi!")
            self.load_data()
        except Exception as e:
            messagebox.showerror("Xatolik", f"Excel yuklashda xatolik: {e}")

    def generate_report(self):
        if ReportGenerator:
            try:
                rep = ReportGenerator(self.db)
                out_path = rep.generate_word_report()
                if out_path:
                    messagebox.showinfo("Muvaffaqiyatli", f"Hisobot tayyorlandi:\n{out_path}")
            except Exception as e:
                messagebox.showerror("Xato", f"Hisobot yaratishda xato: {e}")
        else:
            save_path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")])
            if save_path:
                self.filtered_df.to_excel(save_path, index=False)
                messagebox.showinfo("Hisobot", f"Ma'lumotlar saqlandi: {save_path}")


if __name__ == "__main__":
    app = DashboardApp()
    app.mainloop()

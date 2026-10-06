import customtkinter as ctk
from tkinter import filedialog, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from src.ui_details import DetailsWindow
import os

class DashboardApp(ctk.CTk):
    def __init__(self, data_loader):
        super().__init__()
        self.loader = data_loader
        
        self.title("Kadastr Tizimida Murojaatlar Monitoringi va Komplayens Nazorat")
        self.geometry("1300x780")
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        self._build_header()
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True)

        self._render_dashboard()

    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color="#1F497D", height=60, corner_radius=0)
        header.pack(fill="x", side="top")
        
        title = ctk.CTkLabel(
            header, 
            text="Tahliliy Dashboard: Korrupsiyaga Qarshi Nazorat Monitori", 
            font=ctk.CTkFont(size=19, weight="bold"),
            text_color="white"
        )
        title.pack(pady=15, padx=20, side="left")

        # Excel hisobot eksport tugmasi
        btn_report = ctk.CTkButton(
            header,
            text="📄 Rahbariyat Hisoboti",
            fg_color="#D35400",
            hover_color="#A04000",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._generate_management_report
        )
        btn_report.pack(pady=15, padx=(0, 10), side="right")

        # Yangi Excel yuklash tugmasi
        btn_upload = ctk.CTkButton(
            header,
            text="📂 Yangi Excel yuklash",
            fg_color="#27AE60",
            hover_color="#219150",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._load_new_file
        )
        btn_upload.pack(pady=15, padx=10, side="right")

    def _render_dashboard(self):
        for widget in self.main_container.winfo_children():
            widget.destroy()

        self._build_kpi_cards(self.main_container)
        self._build_analytics_section(self.main_container)

    def _load_new_file(self):
        file_path = filedialog.askopenfilename(
            title="Telegram botdan olingan yangi Excel faylni tanlang",
            filetypes=[("Excel files", "*.xlsx *.xls")]
        )
        if file_path:
            try:
                self.loader.append_new_file(file_path)
                self._render_dashboard()
                messagebox.showinfo("Muvaffaqiyatli", f"Baza yangilandi!\nJami yagona murojaatlar: {len(self.loader.df)} ta")
            except Exception as e:
                messagebox.showerror("Xatolik", f"Yuklashda xatolik yuz berdi:\n{str(e)}")

    def _build_kpi_cards(self, parent):
        stats = self.loader.get_summary_stats()
        card_frame = ctk.CTkFrame(parent, fg_color="transparent")
        card_frame.pack(fill="x", padx=20, pady=12)

        cards = [
            ("Jami murojaatlar", stats['total'], "#2B5C8F", lambda: self._open_details("Barcha murojaatlar", self.loader.df)),
            ("Kadastr Agentligi", stats['agentlik'], "#34495E", lambda: self._open_details("Kadastr Agentligi murojaatlari", self.loader.df[self.loader.df['Tashkilot_Turi'] == 'Kadastr agentligi'])),
            ("Kadastr Palatasi", stats['palata'], "#2980B9", lambda: self._open_details("Kadastr Palatasi murojaatlari", self.loader.df[self.loader.df['Tashkilot_Turi'] == 'Davlat kadastrlari palatasi'])),
            ("Korrupsiya alomatlari", stats['korrupsiya'], "#C0392B", lambda: self._open_details("Korrupsiya alomatlari keltirilgan murojaatlar", self.loader.df[self.loader.df['Kategoriya'] == 'Korrupsiyaga oid'])),
            ("1097 ga yo'naltirilgan", stats['sent_1097'], "#E67E22", lambda: self._open_details("1097 ga yo'naltirilgan murojaatlar", self.loader.df[self.loader.df['1097_Yuborilgan'] == True])),
            ("O'rtacha ijro vaqti", f"{stats['avg_time']} soat", "#16A085", lambda: self._open_details("Barcha ko'rib chiqilgan murojaatlar", self.loader.df))
        ]

        for idx, (title, val, color, cmd) in enumerate(cards):
            card = ctk.CTkFrame(card_frame, fg_color=color, corner_radius=10)
            card.grid(row=0, column=idx, padx=5, sticky="nsew")
            card_frame.grid_columnconfigure(idx, weight=1)

            ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=11), text_color="#ECEFF1").pack(pady=(8, 2), padx=5)
            ctk.CTkLabel(card, text=str(val), font=ctk.CTkFont(size=22, weight="bold"), text_color="white").pack(pady=(0, 4))
            ctk.CTkButton(card, text="Ko'rish ➔", fg_color="transparent", border_width=1, border_color="white", height=22, font=ctk.CTkFont(size=10), command=cmd).pack(pady=(0, 8), padx=15)

    def _build_analytics_section(self, parent):
        grid_frame = ctk.CTkFrame(parent, fg_color="transparent")
        grid_frame.pack(fill="both", expand=True, padx=20, pady=(0, 15))

        # 1. Chap panel: Viloyatlar grafikasi
        chart_frame = ctk.CTkFrame(grid_frame)
        chart_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))

        ctk.CTkLabel(chart_frame, text="Viloyatlar kesimida murojaatlar soni", font=ctk.CTkFont(size=13, weight="bold")).pack(pady=8)

        reg_stats = self.loader.get_region_stats()
        fig, ax = plt.subplots(figsize=(5.5, 4.2), dpi=100)
        if not reg_stats.empty:
            reg_stats.plot(kind='barh', ax=ax, color="#1F497D")
            ax.invert_yaxis()
            ax.set_xlabel("Soni")
        plt.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=8, pady=5)

        # 2. O'ng panel: Eng xavfli tumanlar va Viloyatlar tanlovi
        right_frame = ctk.CTkFrame(grid_frame, width=340)
        right_frame.pack(side="right", fill="both", padx=(5, 0))

        # Xavfli tumanlar (Top Risk)
        lbl_risk = ctk.CTkLabel(right_frame, text="⚠️ Eng ko'p shikoyat tushgan tumanlar:", font=ctk.CTkFont(size=12, weight="bold"), text_color="#C0392B")
        lbl_risk.pack(pady=(10, 5), padx=12, anchor="w")

        top_tumans = self.loader.get_top_risk_tumans(5)
        for _, r in top_tumans.iterrows():
            t_name = r['Tuman']
            t_count = r['Jami']
            btn_t = ctk.CTkButton(
                right_frame,
                text=f"{t_name} — {t_count} ta murojaat",
                anchor="w",
                fg_color="#FADBD8",
                text_color="#900C3F",
                hover_color="#F1948A",
                height=26,
                command=lambda tn=t_name: self._open_details(f"{tn} bo'yicha murojaatlar", self.loader.df[self.loader.df['Tuman'] == tn])
            )
            btn_t.pack(fill="x", padx=10, pady=2)

        # Viloyatlar ro'yxati
        lbl_v = ctk.CTkLabel(right_frame, text="Viloyatni tanlang (Batafsil):", font=ctk.CTkFont(size=12, weight="bold"))
        lbl_v.pack(pady=(12, 5), padx=12, anchor="w")

        scroll_regions = ctk.CTkScrollableFrame(right_frame)
        scroll_regions.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        for reg, count in reg_stats.items():
            btn_reg = ctk.CTkButton(
                scroll_regions,
                text=f"{reg}  ({count} ta)",
                anchor="w",
                fg_color="#34495E",
                hover_color="#1ABC9C",
                height=28,
                command=lambda r=reg: self._open_details(f"{r} bo'yicha murojaatlar", self.loader.df[self.loader.df['Viloyat'] == r])
            )
            btn_reg.pack(fill="x", pady=2, padx=4)

    def _generate_management_report(self):
        """Rahbariyat uchun umumiy hisobot ma'lumotnomasini Excel qilib berish"""
        if self.loader.df.empty:
            messagebox.showwarning("Xatolik", "Hisobot yaratish uchun ma'lumot mavjud emas!")
            return

        save_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            initialfile="Rahbariyatga_Murojaatlar_Hisoboti.xlsx",
            filetypes=[("Excel files", "*.xlsx")]
        )
        if save_path:
            with pd.ExcelWriter(save_path, engine='openpyxl') as writer:
                # 1. Umumiy statistika varag'i
                stats = self.loader.get_summary_stats()
                stats_df = pd.DataFrame(list(stats.items()), columns=['Ko\'rsatkich', 'Qiymat'])
                stats_df.to_excel(writer, sheet_name="Umumiy_Ko'rsatkichlar", index=False)

                # 2. Viloyatlar statistikasi
                reg_df = self.loader.get_region_stats().reset_index()
                reg_df.columns = ['Viloyat', 'Murojaatlar soni']
                reg_df.to_excel(writer, sheet_name="Hududlar", index=False)

                # 3. Korrupsiyaga oid ro'yxat
                corr_df = self.loader.df[self.loader.df['Kategoriya'] == 'Korrupsiyaga oid']
                corr_df.to_excel(writer, sheet_name="Korrupsiya_Alomatlari", index=False)

            messagebox.showinfo("Tayyor", "Rahbariyat uchun hisobot fayli muvaffaqiyatli saqlandi!")

    def _open_details(self, title, filtered_df):
        DetailsWindow(self, title, filtered_df)

import customtkinter as ctk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from src.ui_details import DetailsWindow

class DashboardApp(ctk.CTk):
    def __init__(self, data_loader):
        super().__init__()
        self.loader = data_loader
        
        self.title("Korrupsiyaga qarshi kurashish bo'limi - Murojaatlar Monitoring Tizimi")
        self.geometry("1280x760")
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        self._build_header()
        self._build_kpi_cards()
        self._build_charts_and_regions()

    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color="#1F497D", height=60, corner_radius=0)
        header.pack(fill="x", side="top")
        
        title = ctk.CTkLabel(
            header, 
            text="Tahliliy Dashboard: Telegram Bot Murojaatlari Nazorati", 
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="white"
        )
        title.pack(pady=15, padx=25, side="left")

    def _build_kpi_cards(self):
        stats = self.loader.get_summary_stats()
        card_frame = ctk.CTkFrame(self, fg_color="transparent")
        card_frame.pack(fill="x", padx=20, pady=15)

        cards = [
            ("Jami murojaatlar", stats['total'], "#2b5c8f", lambda: self._open_details("Barcha murojaatlar", self.loader.df)),
            ("Kadastr Agentligi", stats['agentlik'], "#34495E", lambda: self._open_details("Kadastr Agentligi murojaatlari", self.loader.df[self.loader.df['Tashkilot_Turi'] == 'Kadastr agentligi'])),
            ("Kadastr Palatasi", stats['palata'], "#2980B9", lambda: self._open_details("Kadastr Palatasi murojaatlari", self.loader.df[self.loader.df['Tashkilot_Turi'] == 'Davlat kadastrlari palatasi'])),
            ("Korrupsiya alomatlari", stats['korrupsiya'], "#C0392B", lambda: self._open_details("Korrupsiya alomatlari bor murojaatlar", self.loader.df[self.loader.df['Kategoriya'] == 'Korrupsiyaga oid'])),
            ("1097 ga yo'naltirilgan", stats['sent_1097'], "#E67E22", lambda: self._open_details("1097 ga yo'naltirilgan murojaatlar", self.loader.df[self.loader.df['1097_Yuborilgan'] == True])),
            ("Javob berilgan", stats['javob_berilgan'], "#27AE60", lambda: self._open_details("Javob berilgan murojaatlar", self.loader.df[self.loader.df['Holat'].astype(str).str.lower().str.contains('javob')]))
        ]

        for idx, (title, val, color, cmd) in enumerate(cards):
            card = ctk.CTkFrame(card_frame, fg_color=color, corner_radius=10, cursor="hand2")
            card.grid(row=0, column=idx, padx=6, sticky="nsew")
            card_frame.grid_columnconfigure(idx, weight=1)

            lbl_t = ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=12), text_color="#ECEFF1")
            lbl_t.pack(pady=(10, 2), padx=10)
            
            lbl_v = ctk.CTkLabel(card, text=str(val), font=ctk.CTkFont(size=24, weight="bold"), text_color="white")
            lbl_v.pack(pady=(0, 6))

            btn = ctk.CTkButton(card, text="Ko'rish ➔", fg_color="transparent", border_width=1, border_color="white", height=24, font=ctk.CTkFont(size=11), command=cmd)
            btn.pack(pady=(0, 10), padx=15)

    def _build_charts_and_regions(self):
        bottom_frame = ctk.CTkFrame(self, fg_color="transparent")
        bottom_frame.pack(fill="both", expand=True, padx=20, pady=(0, 15))

        # Chap panel: Viloyatlar bo'yicha grafik
        chart_frame = ctk.CTkFrame(bottom_frame)
        chart_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))

        lbl_chart = ctk.CTkLabel(chart_frame, text="Viloyatlar kesimida murojaatlar soni", font=ctk.CTkFont(size=14, weight="bold"))
        lbl_chart.pack(pady=10)

        reg_stats = self.loader.get_region_stats()
        fig, ax = plt.subplots(figsize=(6, 4.5), dpi=100)
        reg_stats.plot(kind='barh', ax=ax, color="#1F497D")
        ax.invert_yaxis()
        ax.set_xlabel("Soni")
        plt.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=5)

        # O'ng panel: Viloyatlar ro'yxati (bosganda o'sha viloyatning ichiga kiradi)
        list_frame = ctk.CTkFrame(bottom_frame, width=320)
        list_frame.pack(side="right", fill="both", padx=(10, 0))

        lbl_list = ctk.CTkLabel(list_frame, text="Hududni tanlang (Batafsil):", font=ctk.CTkFont(size=14, weight="bold"))
        lbl_list.pack(pady=10, padx=15, anchor="w")

        scroll_regions = ctk.CTkScrollableFrame(list_frame)
        scroll_regions.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        for reg, count in reg_stats.items():
            btn_reg = ctk.CTkButton(
                scroll_regions,
                text=f"{reg}  ({count} ta)",
                anchor="w",
                fg_color="#34495E",
                hover_color="#1ABC9C",
                height=32,
                command=lambda r=reg: self._open_details(f"{r} bo'yicha murojaatlar", self.loader.df[self.loader.df['Viloyat'] == r])
            )
            btn_reg.pack(fill="x", pady=3, padx=5)

    def _open_details(self, title, filtered_df):
        DetailsWindow(self, title, filtered_df)

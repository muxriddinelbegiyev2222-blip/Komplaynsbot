import customtkinter as ctk
from tkinter import ttk, messagebox

class DetailsWindow(ctk.CTkToplevel):
    def __init__(self, parent, title, filtered_df):
        super().__init__(parent)
        self.title(title)
        self.geometry("1100x650")
        self.filtered_df = filtered_df

        self.attributes('-topmost', True)
        self.after(100, lambda: self.attributes('-topmost', False))

        self._build_ui(title)

    def _build_ui(self, title):
        # Sarlavha paneli
        header_frame = ctk.CTkFrame(self, fg_color="#1F497D", corner_radius=0, height=50)
        header_frame.pack(fill="x", side="top")
        
        lbl_title = ctk.CTkLabel(
            header_frame, 
            text=f"{title} (Jami: {len(self.filtered_df)} ta)", 
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="white"
        )
        lbl_title.pack(pady=12, padx=20, side="left")

        # Asosiy konteyner
        content_frame = ctk.CTkFrame(self)
        content_frame.pack(fill="both", expand=True, padx=15, pady=15)

        # Jadval (Treeview)
        columns = ("id", "sana", "fish", "telefon", "viloyat", "tuman", "yonalish", "kategoriya")
        
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", rowheight=26, font=("Calibri", 10))
        style.configure("Treeview.Heading", font=("Calibri", 10, "bold"), background="#E1E6EB")

        self.tree = ttk.Treeview(content_frame, columns=columns, show="headings", selectmode="browse")
        
        self.tree.heading("id", text="#")
        self.tree.heading("sana", text="Sana")
        self.tree.heading("fish", text="F.I.Sh.")
        self.tree.heading("telefon", text="Telefon")
        self.tree.heading("viloyat", text="Viloyat")
        self.tree.heading("tuman", text="Tuman")
        self.tree.heading("yonalish", text="Yoʻnalish")
        self.tree.heading("kategoriya", text="Holat/Kategoriya")

        self.tree.column("id", width=40, anchor="center")
        self.tree.column("sana", width=120, anchor="center")
        self.tree.column("fish", width=160, anchor="w")
        self.tree.column("telefon", width=100, anchor="center")
        self.tree.column("viloyat", width=120, anchor="w")
        self.tree.column("tuman", width=110, anchor="w")
        self.tree.column("yonalish", width=200, anchor="w")
        self.tree.column("kategoriya", width=130, anchor="center")

        # Scrollbarlar
        vsb = ttk.Scrollbar(content_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(content_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        content_frame.grid_rowconfigure(0, weight=1)
        content_frame.grid_columnconfigure(0, weight=1)

        # Ma'lumotlarni to'ldirish
        for _, row in self.filtered_df.iterrows():
            self.tree.insert("", "end", values=(
                row.get('#', ''),
                str(row.get('Yaratilgan sana', ''))[:16],
                row.get('F.I.Sh.', ''),
                row.get('Telefon', ''),
                row.get('Viloyat', ''),
                row.get('Tuman', ''),
                row.get('Yoʻnalish', ''),
                row.get('Kategoriya', '')
            ))

        self.tree.bind("<Double-1>", self._on_item_double_click)

        lbl_hint = ctk.CTkLabel(self, text="💡 Murojaat matni va yuborilgan javobni to'liq ko'rish uchun qator ustiga sichqoncha bilan ikki marta bosing.", font=ctk.CTkFont(size=11, slant="italic"))
        lbl_hint.pack(pady=5)

    def _on_item_double_click(self, event):
        item = self.tree.selection()
        if not item:
            return
        vals = self.tree.item(item, "values")
        m_id = int(vals[0])

        m_data = self.filtered_df[self.filtered_df['#'] == m_id].iloc[0]

        detail_box = ctk.CTkToplevel(self)
        detail_box.title(f"Murojaat tafsiloti: #{m_id}")
        detail_box.geometry("700x550")
        detail_box.attributes('-topmost', True)

        txt_info = (
            f"F.I.Sh: {m_data.get('F.I.Sh.', '')}\n"
            f"Telefon: {m_data.get('Telefon', '')}\n"
            f"Hudud: {m_data.get('Viloyat', '')}, {m_data.get('Tuman', '')}\n"
            f"Yo'nalish: {m_data.get('Yoʻnalish', '')}\n"
            f"Kelib tushgan sana: {m_data.get('Yaratilgan sana', '')}\n"
            f"Javob bergan: {m_data.get('Javob bergan', '')} ({m_data.get('Javob sanasi', '')})\n"
        )
        lbl = ctk.CTkLabel(detail_box, text=txt_info, justify="left", font=ctk.CTkFont(size=12, weight="bold"))
        lbl.pack(padx=15, pady=10, anchor="w")

        lbl_m = ctk.CTkLabel(detail_box, text="Murojaat matni:", font=ctk.CTkFont(weight="bold"))
        lbl_m.pack(padx=15, anchor="w")
        tb_m = ctk.CTkTextbox(detail_box, height=140, wrap="word")
        tb_m.insert("1.0", str(m_data.get('Murojaat matni', '')))
        tb_m.configure(state="disabled")
        tb_m.pack(padx=15, pady=5, fill="x")

        lbl_j = ctk.CTkLabel(detail_box, text="Yuborilgan javob xati:", font=ctk.CTkFont(weight="bold"))
        lbl_j.pack(padx=15, anchor="w")
        tb_j = ctk.CTkTextbox(detail_box, height=120, wrap="word")
        tb_j.insert("1.0", str(m_data.get('Javob', '')))
        tb_j.configure(state="disabled")
        tb_j.pack(padx=15, pady=5, fill="x")

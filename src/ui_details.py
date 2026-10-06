import customtkinter as ctk
from tkinter import ttk, filedialog, messagebox
import pandas as pd

class DetailsWindow(ctk.CTkToplevel):
    def __init__(self, parent, title, filtered_df):
        super().__init__(parent)
        self.title(title)
        self.geometry("1180x680")
        self.original_df = filtered_df.copy()
        self.current_df = filtered_df.copy()

        self.attributes('-topmost', True)
        self.after(100, lambda: self.attributes('-topmost', False))

        self._build_ui(title)

    def _build_ui(self, title):
        # Sarlavha va eksport paneli
        header_frame = ctk.CTkFrame(self, fg_color="#1F497D", corner_radius=0, height=52)
        header_frame.pack(fill="x", side="top")
        
        self.lbl_title = ctk.CTkLabel(
            header_frame, 
            text=f"{title} (Jami: {len(self.current_df)} ta)", 
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="white"
        )
        self.lbl_title.pack(pady=12, padx=20, side="left")

        # Excelga eksport tugmasi
        btn_export = ctk.CTkButton(
            header_frame,
            text="📥 Excelga yuklash",
            fg_color="#27AE60",
            hover_color="#1E8449",
            width=130,
            command=self._export_to_excel
        )
        btn_export.pack(pady=10, padx=20, side="right")

        # Qidiruv va Filtrlash paneli
        filter_bar = ctk.CTkFrame(self, fg_color="#EBF0F5", height=45)
        filter_bar.pack(fill="x", padx=15, pady=(10, 0))

        lbl_s = ctk.CTkLabel(filter_bar, text="🔍 Tezkor qidiruv:", font=ctk.CTkFont(size=12, weight="bold"))
        lbl_s.pack(side="left", padx=(15, 5), pady=8)

        self.search_entry = ctk.CTkEntry(filter_bar, placeholder_text="F.I.Sh, telefon, tuman yoki kalit so'z...", width=320)
        self.search_entry.pack(side="left", padx=5, pady=8)
        self.search_entry.bind("<KeyRelease>", self._apply_search)

        btn_reset = ctk.CTkButton(filter_bar, text="Tozalash", width=80, fg_color="#7F8C8D", command=self._reset_search)
        btn_reset.pack(side="left", padx=10, pady=8)

        # Jadval qismi
        content_frame = ctk.CTkFrame(self)
        content_frame.pack(fill="both", expand=True, padx=15, pady=10)

        columns = ("id", "sana", "fish", "telefon", "viloyat", "tuman", "yonalish", "kategoriya", "ijro_vaqti")
        
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
        self.tree.heading("kategoriya", text="Kategoriya")
        self.tree.heading("ijro_vaqti", text="Ijro (soat)")

        self.tree.column("id", width=40, anchor="center")
        self.tree.column("sana", width=120, anchor="center")
        self.tree.column("fish", width=150, anchor="w")
        self.tree.column("telefon", width=100, anchor="center")
        self.tree.column("viloyat", width=110, anchor="w")
        self.tree.column("tuman", width=110, anchor="w")
        self.tree.column("yonalish", width=180, anchor="w")
        self.tree.column("kategoriya", width=120, anchor="center")
        self.tree.column("ijro_vaqti", width=80, anchor="center")

        vsb = ttk.Scrollbar(content_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(content_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        content_frame.grid_rowconfigure(0, weight=1)
        content_frame.grid_columnconfigure(0, weight=1)

        self.tree.bind("<Double-1>", self._on_item_double_click)
        self._populate_tree(self.current_df)

        lbl_hint = ctk.CTkLabel(self, text="💡 Murojaat matni va yuborilgan javobni to'liq ko'rish uchun qator ustiga sichqoncha bilan ikki marta bosing.", font=ctk.CTkFont(size=11, slant="italic"))
        lbl_hint.pack(pady=4)

    def _populate_tree(self, df):
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        for _, row in df.iterrows():
            self.tree.insert("", "end", values=(
                row.get('#', ''),
                str(row.get('Yaratilgan sana', ''))[:16],
                row.get('F.I.Sh.', ''),
                row.get('Telefon', ''),
                row.get('Viloyat', ''),
                row.get('Tuman', ''),
                row.get('Yoʻnalish', ''),
                row.get('Kategoriya', ''),
                row.get('Ijro_Vaqti_Soat', 0.0)
            ))
        self.lbl_title.configure(text=f"Jami saralangan murojaatlar: {len(df)} ta")

    def _apply_search(self, event=None):
        query = self.search_entry.get().strip().lower()
        if not query:
            self.current_df = self.original_df.copy()
        else:
            mask = (
                self.original_df['F.I.Sh.'].astype(str).str.lower().str.contains(query) |
                self.original_df['Telefon'].astype(str).str.lower().str.contains(query) |
                self.original_df['Tuman'].astype(str).str.lower().str.contains(query) |
                self.original_df['Viloyat'].astype(str).str.lower().str.contains(query) |
                self.original_df['Murojaat matni'].astype(str).str.lower().str.contains(query)
            )
            self.current_df = self.original_df[mask]
        self._populate_tree(self.current_df)

    def _reset_search(self):
        self.search_entry.delete(0, 'end')
        self.current_df = self.original_df.copy()
        self._populate_tree(self.current_df)

    def _export_to_excel(self):
        if self.current_df.empty:
            messagebox.showwarning("Ogohlantirish", "Eksport qilish uchun ma'lumot mavjud emas!")
            return
            
        path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel files", "*.xlsx")])
        if path:
            self.current_df.to_excel(path, index=False)
            messagebox.showinfo("Muvaffaqiyatli", "Jadval saqlandi!")

    def _on_item_double_click(self, event):
        item = self.tree.selection()
        if not item:
            return
        vals = self.tree.item(item, "values")
        m_id = int(vals[0])

        m_data = self.original_df[self.original_df['#'] == m_id].iloc[0]

        box = ctk.CTkToplevel(self)
        box.title(f"Murojaat tafsiloti: #{m_id}")
        box.geometry("720x560")
        box.attributes('-topmost', True)

        txt_info = (
            f"F.I.Sh: {m_data.get('F.I.Sh.', '')}\n"
            f"Telefon: {m_data.get('Telefon', '')}\n"
            f"Hudud: {m_data.get('Viloyat', '')}, {m_data.get('Tuman', '')}\n"
            f"Yo'nalish: {m_data.get('Yoʻnalish', '')}\n"
            f"Ijro vaqti: {m_data.get('Ijro_Vaqti_Soat', 0)} soat | Javob bergan: {m_data.get('Javob bergan', '')}\n"
        )
        ctk.CTkLabel(box, text=txt_info, justify="left", font=ctk.CTkFont(size=12, weight="bold")).pack(padx=15, pady=10, anchor="w")

        ctk.CTkLabel(box, text="Murojaat matni:", font=ctk.CTkFont(weight="bold")).pack(padx=15, anchor="w")
        tb_m = ctk.CTkTextbox(box, height=130, wrap="word")
        tb_m.insert("1.0", str(m_data.get('Murojaat matni', '')))
        tb_m.configure(state="disabled")
        tb_m.pack(padx=15, pady=5, fill="x")

        ctk.CTkLabel(box, text="Yuborilgan javob xati:", font=ctk.CTkFont(weight="bold")).pack(padx=15, anchor="w")
        tb_j = ctk.CTkTextbox(box, height=120, wrap="word")
        tb_j.insert("1.0", str(m_data.get('Javob', '')))
        tb_j.configure(state="disabled")
        tb_j.pack(padx=15, pady=5, fill="x")

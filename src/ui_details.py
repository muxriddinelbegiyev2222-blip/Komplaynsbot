import customtkinter as ctk
from tkinter import messagebox

class DetailsWindow(ctk.CTkToplevel):
    def __init__(self, parent, m_id, db, refresh_cb, role="admin"):
        super().__init__(parent)
        self.m_id = m_id
        self.db = db
        self.refresh_cb = refresh_cb
        self.role = str(role).lower()  # Rolni qabul qilamiz

        self.title(f"Murojaat kartochkasi - № {self.m_id}")
        self.geometry("700x750")
        self.grab_set()
        
        ctk.set_appearance_mode("Dark")

        self.row_data = self.db._get_row_by_id(self.m_id)
        if not self.row_data:
            messagebox.showerror("Xato", "Murojaat topilmadi!")
            self.destroy()
            return

        self._build_ui()
        self._populate_data()

    def _build_ui(self):
        # Asosiy ramka
        main_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(main_frame, text=f"📄 Murojaat № {self.m_id} tafsilotlari", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(0, 20))

        # 1. O'zgartirib bo'lmaydigan ma'lumotlar (Fuqaro va matn)
        info_frame = ctk.CTkFrame(main_frame, corner_radius=10)
        info_frame.pack(fill="x", pady=10)
        
        self.lbl_info = ctk.CTkLabel(info_frame, text="", justify="left", font=ctk.CTkFont(size=13))
        self.lbl_info.pack(padx=15, pady=15, anchor="w")

        self.txt_matn = ctk.CTkTextbox(info_frame, height=120)
        self.txt_matn.pack(padx=15, pady=(0, 15), fill="x")
        self.txt_matn.configure(state="disabled") # Asl matn doim qulfli

        # 2. Tahrirlanadigan qism (Holat, Natija, Chora)
        edit_frame = ctk.CTkFrame(main_frame, corner_radius=10, fg_color="#0f2744")
        edit_frame.pack(fill="x", pady=10)

        ctk.CTkLabel(edit_frame, text="Ijro holati:").grid(row=0, column=0, padx=15, pady=10, sticky="w")
        self.cb_ijro = ctk.CTkComboBox(edit_frame, values=["O‘rganishga yuborilgan", "O‘rganilmoqda", "Bajarildi (Ijobiy)", "Tushuntirish berildi", "Rad etildi", "Asossiz deb topildi"], width=350)
        self.cb_ijro.grid(row=0, column=1, padx=15, pady=10)

        ctk.CTkLabel(edit_frame, text="Mas'ul xodim:").grid(row=1, column=0, padx=15, pady=10, sticky="w")
        self.e_masul = ctk.CTkEntry(edit_frame, width=350, placeholder_text="Mas'ul ismini kiriting...")
        self.e_masul.grid(row=1, column=1, padx=15, pady=10)

        ctk.CTkLabel(edit_frame, text="Chora turi:").grid(row=2, column=0, padx=15, pady=10, sticky="w")
        self.cb_chora = ctk.CTkComboBox(edit_frame, values=["Chora ko‘rilmagan", "Hayfsan", "Jarima", "Vazifasidan ozod etildi", "Jinoiy ish qo'zg'atildi"], width=350)
        self.cb_chora.grid(row=2, column=1, padx=15, pady=10)

        ctk.CTkLabel(edit_frame, text="O'rganish natijasi:").grid(row=3, column=0, padx=15, pady=10, sticky="nw")
        self.txt_natija = ctk.CTkTextbox(edit_frame, height=80, width=350)
        self.txt_natija.grid(row=3, column=1, padx=15, pady=10)

        # -------------------------------------------------------------
        # RAHBAR UCHUN XAVFSIZLIK CHEKLOVI
        # -------------------------------------------------------------
        if self.role != "admin":
            # Rahbar kirsa, hamma kiritish maydonlari qulflanadi
            self.cb_ijro.configure(state="disabled")
            self.e_masul.configure(state="disabled")
            self.cb_chora.configure(state="disabled")
            self.txt_natija.configure(state="disabled")
            
            # Saqlash tugmasi o'rniga ogohlantirish yozuvi chiqadi
            lbl_warning = ctk.CTkLabel(main_frame, text="👁 Sizda faqat ko'rish huquqi mavjud", text_color="#f59e0b", font=ctk.CTkFont(weight="bold"))
            lbl_warning.pack(pady=20)
        else:
            # Admin kirsa, saqlash tugmasi chiqadi
            self.btn_save = ctk.CTkButton(main_frame, text="💾 O'zgarishlarni saqlash", height=40, fg_color="#15803d", hover_color="#166534", command=self._save_changes)
            self.btn_save.pack(pady=20)

    def _populate_data(self):
        r = self.row_data
        
        info_text = (
            f"Sana: {str(r[1])[:10]}\n"
            f"F.I.Sh: {r[2]}\n"
            f"Telefon: {r[3]}\n"
            f"Hudud: {r[4]}, {r[5]}\n"
            f"Yo'nalish: {r[6]}\n"
            f"Manba: {r[18]}"
        )
        self.lbl_info.configure(text=info_text)
        
        self.txt_matn.configure(state="normal")
        self.txt_matn.insert("0.0", str(r[9]))
        self.txt_matn.configure(state="disabled")

        self.cb_ijro.set(str(r[13]) if r[13] else "O‘rganishga yuborilgan")
        self.txt_natija.insert("0.0", str(r[14]) if r[14] else "")
        self.e_masul.insert(0, str(r[16]) if r[16] else "")
        self.cb_chora.set(str(r[17]) if r[17] else "Chora ko‘rilmagan")

    def _save_changes(self):
        ijro = self.cb_ijro.get()
        masul = self.e_masul.get().strip()
        chora = self.cb_chora.get()
        natija = self.txt_natija.get("0.0", "end").strip()

        try:
            self.db.update_murojaat_ijro(self.m_id, ijro, natija, '', masul, chora)
            messagebox.showinfo("Muvaffaqiyatli", "Murojaat holati saqlandi va bulutga yuborildi!")
            self.refresh_cb()
            self.destroy()
        except Exception as e:
            messagebox.showerror("Xato", f"Saqlashda xato: {e}")

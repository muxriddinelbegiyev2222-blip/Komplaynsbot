import os
import customtkinter as ctk
from tkinter import filedialog, messagebox

class DetailsWindow(ctk.CTkToplevel):
    def __init__(self, parent, m_id, db, on_save_callback=None, role="admin"):
        super().__init__(parent)

        self.m_id = m_id
        self.db = db
        self.on_save_callback = on_save_callback
        self.role = str(role).lower()

        self.title(f"Murojaat kartochkasi № {self.m_id}")
        self.geometry("750x680")
        self.grab_set()

        self.row_data = self.db._get_row_by_id(self.m_id)
        if not self.row_data:
            messagebox.showerror("Xatolik", "Murojaat topilmadi!")
            self.destroy()
            return

        self._build_ui()

    def _build_ui(self):
        # Ma'lumotlarni o'zgaruvchilarga olish
        (
            mid, sana, fish, tel, vil, tum, yon, aniq_y, hol, matn,
            javob, j_bergan, j_sana, ijro_holati, org_natijasi,
            fayl_path, masul, chora, manba
        ) = self.row_data

        scroll = ctk.CTkScrollableFrame(self, width=710, height=640)
        scroll.pack(padx=15, pady=15, fill="both", expand=True)

        # 1. Asosiy ma'lumotlar bloki
        top_frame = ctk.CTkFrame(scroll, fg_color="#1f538d", corner_radius=8)
        top_frame.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(top_frame, text=f"Murojaat № {mid} | {manba}", font=ctk.CTkFont(size=16, weight="bold"), text_color="white").pack(anchor="w", padx=15, pady=(8, 2))
        ctk.CTkLabel(top_frame, text=f"Fuqaro: {fish} | Tel: {tel} | Sana: {sana}", font=ctk.CTkFont(size=12), text_color="#e0e0e0").pack(anchor="w", padx=15, pady=(0, 8))

        # 2. Mazmun
        ctk.CTkLabel(scroll, text="Murojaat matni:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(5, 2))
        txt_matn = ctk.CTkTextbox(scroll, height=80, wrap="word")
        txt_matn.insert("0.0", str(matn))
        txt_matn.configure(state="disabled")
        txt_matn.pack(fill="x", pady=(0, 10))

        # 3. Ijro ma'lumotlari
        ctk.CTkLabel(scroll, text="Ijro holati:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(5, 2))
        holatlar = ["O‘rganishga yuborilgan", "O‘rganilmoqda", "Bajarildi (Ijobiy)", "Tushuntirish berildi", "Rad etildi"]
        self.cb_ijro = ctk.CTkComboBox(scroll, values=holatlar, width=400)
        self.cb_ijro.set(str(ijro_holati) if ijro_holati else "O‘rganishga yuborilgan")
        self.cb_ijro.pack(anchor="w", pady=(0, 10))

        ctk.CTkLabel(scroll, text="O‘rganish natijasi / Komplayens xulosasi:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(5, 2))
        self.txt_natija = ctk.CTkTextbox(scroll, height=100, wrap="word")
        self.txt_natija.insert("0.0", str(org_natijasi) if org_natijasi else "")
        self.txt_natija.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(scroll, text="Ko‘rilgan chora turi:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(5, 2))
        choralar = ["Chora ko‘rilmagan", "Intizomiy jazo", "Hayfsan", "Lavozimidan ozod etilgan", "Hujjatlar prokuraturaga yuborilgan"]
        self.cb_chora = ctk.CTkComboBox(scroll, values=choralar, width=400)
        self.cb_chora.set(str(chora) if chora else "Chora ko‘rilmagan")
        self.cb_chora.pack(anchor="w", pady=(0, 10))

        ctk.CTkLabel(scroll, text="Mas'ul komplayens xodimi:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(5, 2))
        self.e_masul = ctk.CTkEntry(scroll, width=400)
        self.e_masul.insert(0, str(masul) if masul else "")
        self.e_masul.pack(anchor="w", pady=(0, 10))

        # Fayl biriktirish qismi
        file_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        file_frame.pack(fill="x", pady=(0, 15))

        self.lbl_file = ctk.CTkLabel(file_frame, text=f"Biriktirilgan fayl: {fayl_path if fayl_path else 'Mavjud emas'}")
        self.lbl_file.pack(side="left", padx=(0, 10))
        self.current_file = str(fayl_path) if fayl_path else ""

        # Rahbar (kuzatuvchi) uchun cheklov
        if self.role == "kuzatuvchi":
            self.cb_ijro.configure(state="disabled")
            self.txt_natija.configure(state="disabled")
            self.cb_chora.configure(state="disabled")
            self.e_masul.configure(state="disabled")

            lbl_note = ctk.CTkLabel(
                scroll,
                text="👁 Siz kuzatuvchi rejimidagiz. Ma'lumotlarni tahrirlash huquqi yo'q.",
                font=ctk.CTkFont(weight="bold"),
                text_color="#f57c00"
            )
            lbl_note.pack(pady=10)
        else:
            def choose_file():
                f = filedialog.askopenfilename()
                if f:
                    self.current_file = f
                    self.lbl_file.configure(text=f"Biriktirilgan fayl: {os.path.basename(f)}")

            btn_f = ctk.CTkButton(file_frame, text="📎 Fayl tanlash", width=120, command=choose_file)
            btn_f.pack(side="left")

            btn_save = ctk.CTkButton(
                scroll,
                text="💾 O‘zgarishlarni saqlash",
                fg_color="#2e7d32",
                hover_color="#1b5e20",
                command=self.save_data,
                height=40
            )
            btn_save.pack(fill="x", pady=10)

    def save_data(self):
        ijro = self.cb_ijro.get()
        natija = self.txt_natija.get("0.0", "end").strip()
        chora = self.cb_chora.get()
        masul = self.e_masul.get().strip()

        self.db.update_murojaat_ijro(self.m_id, ijro, natija, self.current_file, masul, chora)
        messagebox.showinfo("Saqlandi", "Ma'lumotlar muvaffaqiyatli saqlandi va bulutga yuborildi!")
        if self.on_save_callback:
            self.on_save_callback()
        self.destroy()

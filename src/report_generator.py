import os
import pandas as pd
from datetime import datetime
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT

class ReportGenerator:
    @staticmethod
    def export_excel(df, file_path):
        """
        Excel eksporti:
        - T/r raqami 1 dan boshlab tartiblanadi (1, 2, 3...)
        - Eng oxirgi kelib tushgan murojaatlar tepada bo'ladi (saralangan)
        - Ustunlar kengligi, matn o'ralishi va avtofiltr to'liq sozlangan
        """
        export_df = df.copy()

        # Sanani to'g'ri saralash
        if 'DT' in export_df.columns and export_df['DT'].notnull().any():
            export_df = export_df.sort_values(by='DT', ascending=False)
        elif 'Yaratilgan sana' in export_df.columns:
            export_df = export_df.sort_values(by='Yaratilgan sana', ascending=False)

        # Kerakli ustunlar ro'yxati
        cols = [
            'Yaratilgan sana', 'F.I.Sh.', 'Telefon', 'Viloyat', 'Tuman', 
            'Yoʻnalish', 'Masul_Komplayens', 'Ijro_Holati', 
            'Organish_Natijasi', 'Murojaat matni'
        ]
        available = [c for c in cols if c in export_df.columns]
        sub_df = export_df[available].copy()

        # 1 dan boshlanuvchi ketma-ket T/r qo'yish
        sub_df.insert(0, 'T/r', range(1, len(sub_df) + 1))

        # Ustunlarga rasmiy o'zbekcha nom berish
        col_rename = {
            'Yaratilgan sana': 'Kelib tushgan sana',
            'Yoʻnalish': 'Yoʻnalish turi',
            'Masul_Komplayens': 'Mas’ul komplayens organi',
            'Ijro_Holati': 'Ijro holati',
            'Organish_Natijasi': 'O‘rganish natijasi va ko‘rilgan chora',
            'Murojaat matni': 'Murojaat mazmuni'
        }
        sub_df = sub_df.rename(columns=col_rename)

        with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
            sheet_name = "Murojaatlar_Reyestri"
            sub_df.to_excel(writer, sheet_name=sheet_name, index=False)
            ws = writer.sheets[sheet_name]
            ws.views.sheetView[0].showGridLines = True

            # Ranglar va ramkalar
            navy_header_fill = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
            zebra_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
            thin_border = Border(
                left=Side(style='thin', color='B0C4DE'),
                right=Side(style='thin', color='B0C4DE'),
                top=Side(style='thin', color='B0C4DE'),
                bottom=Side(style='thin', color='B0C4DE')
            )

            # Sarlavha qatori bezagi
            ws.row_dimensions[1].height = 32
            for col_idx in range(1, len(sub_df.columns) + 1):
                cell = ws.cell(row=1, column=col_idx)
                cell.fill = navy_header_fill
                cell.font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
                cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
                cell.border = thin_border

            # Ma'lumot qatorlari
            for row_idx in range(2, len(sub_df) + 2):
                ws.row_dimensions[row_idx].height = 28
                is_even = (row_idx % 2 == 0)
                for col_idx in range(1, len(sub_df.columns) + 1):
                    cell = ws.cell(row=row_idx, column=col_idx)
                    cell.font = Font(name="Calibri", size=10)
                    cell.border = thin_border
                    if is_even:
                        cell.fill = zebra_fill
                    
                    # Joylashuv (alignment)
                    col_name = sub_df.columns[col_idx - 1]
                    if col_name in ['T/r']:
                        cell.alignment = Alignment(horizontal="center", vertical="center")
                    elif col_name in ['Kelib tushgan sana', 'Telefon', 'Ijro holati']:
                        cell.alignment = Alignment(horizontal="center", vertical="center")
                    elif col_name in ['O‘rganish natijasi va ko‘rilgan chora', 'Murojaat mazmuni']:
                        cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
                    else:
                        cell.alignment = Alignment(horizontal="left", vertical="center")

            # Ustun kengliklarini matnga moslab optimal sozlash
            col_widths = {
                'T/r': 8,
                'Kelib tushgan sana': 19,
                'F.I.Sh.': 26,
                'Telefon': 16,
                'Viloyat': 22,
                'Tuman': 20,
                'Yoʻnalish turi': 32,
                'Mas’ul komplayens organi': 36,
                'Ijro holati': 20,
                'O‘rganish natijasi va ko‘rilgan chora': 45,
                'Murojaat mazmuni': 55
            }

            for col_idx, col_name in enumerate(sub_df.columns, 1):
                col_letter = get_column_letter(col_idx)
                width = col_widths.get(col_name, 22)
                ws.column_dimensions[col_letter].width = width

            # Avtomatik filtrlash (AutoFilter) qo'shish
            last_col_letter = get_column_letter(len(sub_df.columns))
            ws.auto_filter.ref = f"A1:{last_col_letter}{len(sub_df) + 1}"

    @staticmethod
    def export_word_report(stats, reg_stats, file_path, period_name="Barchasi"):
        """
        Word ma'lumotnomasi:
        - "(Barchasi bo'yicha tahlil)" olib tashlandi, o'rniga rasmiy sana yoziladi
        - Takrorlangan yozuvlar yo'qotildi, pastki imzo rasmiy holatga keltirildi
        """
        doc = Document()

        # Sahifa hoshiyalari
        section = doc.sections[0]
        section.top_margin = Inches(0.8)
        section.bottom_margin = Inches(0.8)
        section.left_margin = Inches(1.0)
        section.right_margin = Inches(0.8)

        # Rasmiy sarlavha
        p_head = doc.add_paragraph()
        p_head.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_head.paragraph_format.space_after = Pt(4)

        r1 = p_head.add_run("O‘ZBEKISTON RESPUBLIKASI KADASTR AGENTLIGI\n")
        r1.bold = True
        r1.font.name = 'Times New Roman'
        r1.font.size = Pt(13)

        r2 = p_head.add_run("KORRUPSIYAGA QARSHI KURASHISH BO‘LIMI\n\n")
        r2.bold = True
        r2.font.name = 'Times New Roman'
        r2.font.size = Pt(12)

        # Davr nomini rasmiylashtirish
        current_year = datetime.now().year
        if period_name == "Barchasi" or not period_name:
            davr_matni = f"{current_year}-yil umumiy tahlili"
        elif period_name == "Joriy oy":
            davr_matni = f"{current_year}-yil joriy oy holatiga ko‘ra"
        elif period_name == "Joriy hafta":
            davr_matni = f"Joriy hafta davomidagi holatga ko‘ra"
        elif period_name == "Joriy yil":
            davr_matni = f"{current_year}-yil davomidagi tahlil"
        else:
            davr_matni = f"{period_name} holatiga ko‘ra"

        r3 = p_head.add_run(f"MA’LUMOTNOMA\n({davr_matni})\n")
        r3.bold = True
        r3.font.name = 'Times New Roman'
        r3.font.size = Pt(14)
        r3.font.color.rgb = RGBColor(15, 37, 55)

        # Kirish qismi
        p_body = doc.add_paragraph()
        p_body.paragraph_format.line_spacing = 1.15
        p_body.paragraph_format.space_after = Pt(8)
        p_body.paragraph_format.first_line_indent = Inches(0.4)

        r_body = p_body.add_run(
            f"Kadastr tizimi korrupsiyaga qarshi kurashish rasmiy Telegram boti orqali "
            f"hisobot davrida jami {stats['total']} ta murojaat kelib tushgan. "
            f"Mazkur murojaatlarning hududiy komplayens xodimlari tomonidan o‘rganilishi "
            f"va ijrosi quyidagi tartibda taqsimlangan:"
        )
        r_body.font.name = 'Times New Roman'
        r_body.font.size = Pt(12)

        # Jadval
        table = doc.add_table(rows=1, cols=3)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.style = 'Table Grid'

        # Sarlavha kataklari
        hdr_cells = table.rows[0].cells
        hdr_titles = ["T/r", "Ko‘rsatkich nomi", "Soni (ta)"]
        for idx, title in enumerate(hdr_titles):
            hdr_cells[idx].text = title
            p = hdr_cells[idx].paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for r in p.runs:
                r.bold = True
                r.font.name = 'Times New Roman'
                r.font.size = Pt(11)

        data_rows = [
            ("1", "Jami ko‘rib chiqilayotgan murojaatlar", str(stats['total'])),
            ("2", "Agentlik hududiy komplayens xodimlarida o‘rganishda", str(stats['agentlik_organish'])),
            ("3", "Palata hududiy komplayens xodimlarida o‘rganishda", str(stats['palata_organish'])),
            ("4", "O‘rganib chiqilgan (bartaraf etilgan / chora ko‘rilgan)", str(stats['natija_kiritilgan'])),
            ("5", "O‘rganish natijasida asossiz deb topilgan", str(stats['asossiz']))
        ]

        for row in data_rows:
            row_cells = table.add_row().cells
            row_cells[0].text = row[0]
            row_cells[1].text = row[1]
            row_cells[2].text = row[2]

            row_cells[0].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            row_cells[1].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.LEFT
            row_cells[2].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

            for c in row_cells:
                for r in c.paragraphs[0].runs:
                    r.font.name = 'Times New Roman'
                    r.font.size = Pt(11)

        # Hududlar taqsimoti
        p_reg = doc.add_paragraph()
        p_reg.paragraph_format.space_before = Pt(12)
        p_reg.paragraph_format.space_after = Pt(4)
        
        r_reg_h = p_reg.add_run("Eng ko‘p murojaat kelib tushgan hududlar kesimi:")
        r_reg_h.bold = True
        r_reg_h.font.name = 'Times New Roman'
        r_reg_h.font.size = Pt(12)

        for reg, cnt in reg_stats.head(5).items():
            p_item = doc.add_paragraph()
            p_item.paragraph_format.space_after = Pt(2)
            p_item.paragraph_format.left_indent = Inches(0.2)
            r_item = p_item.add_run(f"• {reg}: {cnt} ta murojaat")
            r_item.font.name = 'Times New Roman'
            r_item.font.size = Pt(11)

        # Imzo qismi (Rasmiy idoraviy standart)
        p_sign = doc.add_paragraph()
        p_sign.paragraph_format.space_before = Pt(36)
        
        table_sign = doc.add_table(rows=1, cols=2)
        table_sign.alignment = WD_TABLE_ALIGNMENT.CENTER
        
        # Chegaralarni yashirish
        cell_left = table_sign.rows[0].cells[0]
        cell_right = table_sign.rows[0].cells[1]

        p_left = cell_left.paragraphs[0]
        p_left.alignment = WD_ALIGN_PARAGRAPH.LEFT
        r_sl = p_left.add_run("Korrupsiyaga qarshi kurashish\nbo‘limi bosh mutaxassisi")
        r_sl.bold = True
        r_sl.font.name = 'Times New Roman'
        r_sl.font.size = Pt(11)

        p_right = cell_right.paragraphs[0]
        p_right.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        r_sr = p_right.add_run("______________  (imzo)")
        r_sr.font.name = 'Times New Roman'
        r_sr.font.size = Pt(11)

        doc.save(file_path)

import os
import pandas as pd
from datetime import datetime
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

try:
    from docx import Document
    from docx.shared import Inches, Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.enum.table import WD_TABLE_ALIGNMENT
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False

class ReportGenerator:
    @staticmethod
    def generate_task_document(rec, output_path):
        """Hududiy komplayens xodimiga rasmiy Word Topshiriq Xati yaratish"""
        if not HAS_DOCX:
            return None

        doc = Document()
        section = doc.sections[0]
        section.top_margin = Inches(0.8)
        section.bottom_margin = Inches(0.8)
        section.left_margin = Inches(1.0)
        section.right_margin = Inches(0.8)

        p_h = doc.add_paragraph()
        p_h.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r1 = p_h.add_run("O‘ZBEKISTON RESPUBLIKASI KADASTR AGENTLIGI\n")
        r1.bold = True
        r1.font.name = 'Times New Roman'
        r1.font.size = Pt(13)

        r2 = p_h.add_run("KORRUPSIYAGA QARSHI KURASHISH BO‘LIMI\n")
        r2.bold = True
        r2.font.name = 'Times New Roman'
        r2.font.size = Pt(12)

        r_tel = p_h.add_run("Ishonch telefoni: +998-71-273-19-66\n\n")
        r_tel.font.name = 'Times New Roman'
        r_tel.font.size = Pt(10)
        r_tel.italic = True

        r_title = p_h.add_run(f"KOMPLAYENS O‘RGANISH TOPSHIRIQLAR XATI № {rec.get('#')}\n")
        r_title.bold = True
        r_title.font.name = 'Times New Roman'
        r_title.font.size = Pt(14)
        r_title.font.color.rgb = RGBColor(15, 37, 55)

        table = doc.add_table(rows=7, cols=2)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.style = 'Table Grid'

        rows_data = [
            ("Murojaat tartib raqami:", f"#{rec.get('#')}"),
            ("Kelib tushgan sana:", str(rec.get('Yaratilgan sana'))),
            ("Murojaat manbasi:", str(rec.get('Manba', 'Telegram bot'))),
            ("Fuqaro (F.I.Sh.):", str(rec.get('F.I.Sh.'))),
            ("Aloqa telefoni:", str(rec.get('Telefon'))),
            ("Hudud (Viloyat / Tuman):", f"{rec.get('Viloyat')}, {rec.get('Tuman')}"),
            ("Ijro yuklatilgan mas'ul:", str(rec.get('Masul_Komplayens')))
        ]

        for i, (k, v) in enumerate(rows_data):
            cell_k = table.rows[i].cells[0]
            cell_v = table.rows[i].cells[1]
            cell_k.width = Inches(2.2)
            cell_v.width = Inches(4.5)
            
            p_k = cell_k.paragraphs[0]
            r_k = p_k.add_run(k)
            r_k.bold = True
            r_k.font.name = 'Times New Roman'
            r_k.font.size = Pt(11)

            p_v = cell_v.paragraphs[0]
            r_v = p_v.add_run(v)
            r_v.font.name = 'Times New Roman'
            r_v.font.size = Pt(11)

        p_m = doc.add_paragraph()
        p_m.paragraph_format.space_before = Pt(12)
        r_m_title = p_m.add_run("Fuqaro murojaatining matni:")
        r_m_title.bold = True
        r_m_title.font.name = 'Times New Roman'
        r_m_title.font.size = Pt(12)

        p_m_text = doc.add_paragraph()
        p_m_text.paragraph_format.line_spacing = 1.15
        p_m_text.paragraph_format.space_after = Pt(12)
        r_txt = p_m_text.add_run(str(rec.get('Murojaat matni', '')))
        r_txt.font.name = 'Times New Roman'
        r_txt.font.size = Pt(11)

        p_req = doc.add_paragraph()
        p_req.paragraph_format.line_spacing = 1.15
        r_req = p_req.add_run(
            "TOPShIRIQ: Mazkur murojaatda keltirilgan vajlar belgilangan qonuniy muddatda (15 kun ichida) to‘liq "
            "va xolisona o‘rganilib, natijasi hamda ko‘rilgan ta’sir choralari bo‘yicha tegishli asoslovchi hujjatlar (xulosa, buyruq) "
            "bilan birga Korrupsiyaga qarshi kurashish bo‘limiga axborot kiritilishi ta’minlansin."
        )
        r_req.italic = True
        r_req.font.name = 'Times New Roman'
        r_req.font.size = Pt(11)

        p_sign = doc.add_paragraph()
        p_sign.paragraph_format.space_before = Pt(30)
        table_s = doc.add_table(rows=1, cols=2)
        table_s.alignment = WD_TABLE_ALIGNMENT.CENTER
        
        c_left = table_s.rows[0].cells[0]
        c_right = table_s.rows[0].cells[1]
        
        r_sl = c_left.paragraphs[0].add_run("Korrupsiyaga qarshi kurashish\nbo‘limi bosh mutaxassisi")
        r_sl.bold = True
        r_sl.font.name = 'Times New Roman'
        r_sl.font.size = Pt(11)
        
        r_sr = c_right.paragraphs[0].add_run("______________ (imzo)")
        r_sr.font.name = 'Times New Roman'
        r_sr.font.size = Pt(11)

        doc.save(output_path)
        return output_path

    @staticmethod
    def export_excel(df, file_path):
        export_df = df.copy()
        if 'DT' in export_df.columns and export_df['DT'].notnull().any():
            export_df = export_df.sort_values(by='DT', ascending=False)
        elif 'Yaratilgan sana' in export_df.columns:
            export_df = export_df.sort_values(by='Yaratilgan sana', ascending=False)

        cols = [
            'Yaratilgan sana', 'Manba', 'F.I.Sh.', 'Telefon', 'Viloyat', 'Tuman', 
            'Yoʻnalish', 'Masul_Komplayens', 'Ijro_Holati', 
            'Chora_Turi', 'Organish_Natijasi', 'Murojaat matni'
        ]
        available = [c for c in cols if c in export_df.columns]
        sub_df = export_df[available].copy()
        sub_df.insert(0, 'T/r', range(1, len(sub_df) + 1))

        col_rename = {
            'Yaratilgan sana': 'Kelib tushgan sana',
            'Manba': 'Murojaat manbasi',
            'Yoʻnalish': 'Yoʻnalish turi',
            'Masul_Komplayens': 'Mas’ul komplayens organi',
            'Ijro_Holati': 'Ijro holati',
            'Chora_Turi': 'Ko‘rilgan chora',
            'Organish_Natijasi': 'O‘rganish natijasi',
            'Murojaat matni': 'Murojaat mazmuni'
        }
        sub_df = sub_df.rename(columns=col_rename)

        with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
            sheet_name = "Murojaatlar_Reyestri"
            sub_df.to_excel(writer, sheet_name=sheet_name, index=False)
            ws = writer.sheets[sheet_name]
            ws.views.sheetView[0].showGridLines = True

            navy_fill = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
            zebra_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
            thin_border = Border(
                left=Side(style='thin', color='B0C4DE'), right=Side(style='thin', color='B0C4DE'),
                top=Side(style='thin', color='B0C4DE'), bottom=Side(style='thin', color='B0C4DE')
            )

            ws.row_dimensions[1].height = 32
            for col_idx in range(1, len(sub_df.columns) + 1):
                cell = ws.cell(row=1, column=col_idx)
                cell.fill = navy_fill
                cell.font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
                cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
                cell.border = thin_border

            for row_idx in range(2, len(sub_df) + 2):
                ws.row_dimensions[row_idx].height = 28
                is_even = (row_idx % 2 == 0)
                for col_idx in range(1, len(sub_df.columns) + 1):
                    cell = ws.cell(row=row_idx, column=col_idx)
                    cell.font = Font(name="Calibri", size=10)
                    cell.border = thin_border
                    if is_even: cell.fill = zebra_fill
                    cell.alignment = Alignment(vertical="center", wrap_text=True)

            col_widths = {
                'T/r': 8, 'Kelib tushgan sana': 19, 'Murojaat manbasi': 24,
                'F.I.Sh.': 26, 'Telefon': 16, 'Viloyat': 22, 'Tuman': 20,
                'Yoʻnalish turi': 32, 'Mas’ul komplayens organi': 36,
                'Ijro holati': 18, 'Ko‘rilgan chora': 22,
                'O‘rganish natijasi': 45, 'Murojaat mazmuni': 55
            }
            for col_idx, col_name in enumerate(sub_df.columns, 1):
                col_letter = get_column_letter(col_idx)
                ws.column_dimensions[col_letter].width = col_widths.get(col_name, 22)

            last_col = get_column_letter(len(sub_df.columns))
            ws.auto_filter.ref = f"A1:{last_col}{len(sub_df) + 1}"

    @staticmethod
    def export_word_report(stats, reg_stats, file_path, period_name="Barchasi"):
        if not HAS_DOCX:
            return None

        doc = Document()
        section = doc.sections[0]
        section.top_margin = Inches(0.8)
        section.bottom_margin = Inches(0.8)
        section.left_margin = Inches(1.0)
        section.right_margin = Inches(0.8)

        p_head = doc.add_paragraph()
        p_head.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r1 = p_head.add_run("O‘ZBEKISTON RESPUBLIKASI KADASTR AGENTLIGI\n")
        r1.bold = True
        r1.font.name = 'Times New Roman'
        r1.font.size = Pt(13)

        r2 = p_head.add_run("KORRUPSIYAGA QARSHI KURASHISH BO‘LIMI\n")
        r2.bold = True
        r2.font.name = 'Times New Roman'
        r2.font.size = Pt(12)

        r_tel = p_head.add_run("Ishonch telefoni: +998-71-273-19-66\n\n")
        r_tel.font.name = 'Times New Roman'
        r_tel.font.size = Pt(10)
        r_tel.italic = True

        current_year = datetime.now().year
        davr_matni = f"{current_year}-yil holatiga ko‘ra" if period_name in ["Barchasi", ""] else f"{period_name} holatiga ko‘ra"

        r3 = p_head.add_run(f"MA’LUMOTNOMA\n({davr_matni})\n")
        r3.bold = True
        r3.font.name = 'Times New Roman'
        r3.font.size = Pt(14)
        r3.font.color.rgb = RGBColor(15, 37, 55)

        p_body = doc.add_paragraph()
        p_body.paragraph_format.line_spacing = 1.15
        p_body.paragraph_format.first_line_indent = Inches(0.4)
        r_body = p_body.add_run(
            f"Kadastr tizimi korrupsiyaga qarshi kurashish kanallari (rasmiy Telegram bot hamda +998-71-273-19-66 ishonch telefoni) orqali "
            f"hisobot davrida jami {stats['total']} ta murojaat kelib tushgan (shundan Telegram bot orqali: {stats['tg_total']} ta, ishonch telefoni orqali: {stats['phone_total']} ta). "
            f"Mazkur murojaatlarning hududiy komplayens xodimlari tomonidan o‘rganilishi va ijro holati quyidagicha taqsimlangan:"
        )
        r_body.font.name = 'Times New Roman'
        r_body.font.size = Pt(12)

        table = doc.add_table(rows=1, cols=3)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.style = 'Table Grid'
        hdr_cells = table.rows[0].cells
        for idx, title in enumerate(["T/r", "Ko‘rsatkich nomi", "Soni (ta)"]):
            hdr_cells[idx].text = title
            p = hdr_cells[idx].paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for r in p.runs:
                r.bold = True
                r.font.name = 'Times New Roman'
                r.font.size = Pt(11)

        data_rows = [
            ("1", "Jami ko‘rib chiqilayotgan murojaatlar", str(stats['total'])),
            ("2", "— Shundan Telegram bot orqali", str(stats['tg_total'])),
            ("3", "— Shundan Ishonch telefoni orqali (+998-71-273-19-66)", str(stats['phone_total'])),
            ("4", "Agentlik hududiy komplayens xodimlarida o‘rganishda", str(stats['agentlik_organish'])),
            ("5", "Palata hududiy komplayens xodimlarida o‘rganishda", str(stats['palata_organish'])),
            ("6", "O‘rganib chiqilgan (bartaraf etilgan / chora ko‘rilgan)", str(stats['natija_kiritilgan'])),
            ("7", "O‘rganish natijasida asossiz deb topilgan", str(stats['asossiz']))
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

        p_reg = doc.add_paragraph()
        p_reg.paragraph_format.space_before = Pt(12)
        r_reg_h = p_reg.add_run("Eng ko‘p murojaat kelib tushgan hududlar kesimi:")
        r_reg_h.bold = True
        r_reg_h.font.name = 'Times New Roman'
        r_reg_h.font.size = Pt(12)

        for reg, cnt in reg_stats.head(5).items():
            p_item = doc.add_paragraph()
            p_item.paragraph_format.left_indent = Inches(0.2)
            r_item = p_item.add_run(f"• {reg}: {cnt} ta murojaat")
            r_item.font.name = 'Times New Roman'
            r_item.font.size = Pt(11)

        p_sign = doc.add_paragraph()
        p_sign.paragraph_format.space_before = Pt(36)
        table_s = doc.add_table(rows=1, cols=2)
        table_s.alignment = WD_TABLE_ALIGNMENT.CENTER
        c_left = table_s.rows[0].cells[0]
        c_right = table_s.rows[0].cells[1]
        r_sl = c_left.paragraphs[0].add_run("Korrupsiyaga qarshi kurashish\nbo‘limi bosh mutaxassisi")
        r_sl.bold = True
        r_sl.font.name = 'Times New Roman'
        r_sl.font.size = Pt(11)
        r_sr = c_right.paragraphs[0].add_run("______________ (imzo)")
        r_sr.font.name = 'Times New Roman'
        r_sr.font.size = Pt(11)

        doc.save(file_path)

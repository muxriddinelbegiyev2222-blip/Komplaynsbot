import os
import pandas as pd
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

class ReportGenerator:
    @staticmethod
    def export_excel(df, file_path):
        with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
            export_cols = ['#', 'Yaratilgan sana', 'F.I.Sh.', 'Telefon', 'Viloyat', 'Tuman', 'Yoʻnalish', 'Kategoriya', 'Ijro_Holati', 'Murojaat matni', 'Organish_Natijasi']
            available = [c for c in export_cols if c in df.columns]
            sub_df = df[available].copy()
            sub_df.to_excel(writer, sheet_name="Murojaatlar", index=False)
            ws = writer.sheets["Murojaatlar"]
            ws.views.sheetView[0].showGridLines = True

            navy_fill = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
            zebra_fill = PatternFill(start_color="F7F9FC", end_color="F7F9FC", fill_type="solid")
            thin_border = Border(
                left=Side(style='thin', color='D9D9D9'),
                right=Side(style='thin', color='D9D9D9'),
                top=Side(style='thin', color='D9D9D9'),
                bottom=Side(style='thin', color='D9D9D9')
            )

            ws.row_dimensions[1].height = 28
            for col_num in range(1, len(available) + 1):
                cell = ws.cell(row=1, column=col_num)
                cell.fill = navy_fill
                cell.font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
                cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
                cell.border = thin_border

            for r_idx in range(2, len(sub_df) + 2):
                ws.row_dimensions[r_idx].height = 24
                is_even = (r_idx % 2 == 0)
                for c_idx in range(1, len(available) + 1):
                    cell = ws.cell(row=r_idx, column=c_idx)
                    cell.font = Font(name="Calibri", size=10)
                    cell.border = thin_border
                    if is_even:
                        cell.fill = zebra_fill
                    cell.alignment = Alignment(vertical="center", wrap_text=True)

            for c_idx, col_name in enumerate(available, 1):
                col_letter = get_column_letter(c_idx)
                if col_name in ['#']:
                    ws.column_dimensions[col_letter].width = 7
                elif col_name in ['Telefon', 'Ijro_Holati', 'Kategoriya']:
                    ws.column_dimensions[col_letter].width = 16
                elif col_name in ['Yaratilgan sana', 'F.I.Sh.', 'Viloyat', 'Tuman']:
                    ws.column_dimensions[col_letter].width = 22
                else:
                    ws.column_dimensions[col_letter].width = 40

    @staticmethod
    def export_word_report(stats, reg_stats, file_path, period_name="Barcha davr"):
        doc = Document()

        section = doc.sections[0]
        section.top_margin = Inches(0.8)
        section.bottom_margin = Inches(0.8)
        section.left_margin = Inches(1.0)
        section.right_margin = Inches(0.8)

        p_title = doc.add_paragraph()
        p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r1 = p_title.add_run("O‘ZBEKISTON RESPUBLIKASI KADASTR AGENTLIGI\n")
        r1.bold = True
        r1.font.size = Pt(13)
        r2 = p_title.add_run("KORRUPSIYAGA QARSHI KURASHISH BO‘LIMI\n\n")
        r2.bold = True
        r2.font.size = Pt(12)

        r3 = p_title.add_run(f"MA’LUMOTNOMA\n({period_name} bo‘yicha tahlil)\n")
        r3.bold = True
        r3.font.size = Pt(14)
        r3.font.color.rgb = RGBColor(31, 73, 125)

        p_body = doc.add_paragraph()
        p_body.paragraph_format.line_spacing = 1.25
        p_body.add_run(
            f"Kadastr tizimi korrupsiyaga qarshi kurashish rasmiy Telegram boti orqali "
            f"hisobot davrida jami {stats['total']} ta murojaat kelib tushgan (sinov va test xabarlari chiqarib tashlangan holda). "
            f"Ushbu murojaatlarning mazmuni va ijrosi quyidagicha taqsimlangan:\n"
        )

        table = doc.add_table(rows=1, cols=3)
        table.style = 'Light Shading Accent 1'
        hdr_cells = table.rows[0].cells
        hdr_cells[0].text = "T/r"
        hdr_cells[1].text = "Ko‘rsatkich nomi"
        hdr_cells[2].text = "Soni (ta)"

        data_rows = [
            ("1", "Jami haqiqiy murojaatlar", str(stats['total'])),
            ("2", "Korrupsiya va ta’magirlik alomatlari keltirilgan", str(stats['korrupsiya'])),
            ("3", "Hududiy bo'linmalarda o‘rganishda bo‘lgan murojaatlar", str(stats['organishda'])),
            ("4", "Natijasi kiritilgan (bartaraf etilgan / chora ko'rilgan)", str(stats['natija_kiritilgan'])),
            ("5", "O'rganish natijasida asossiz deb topilgan", str(stats['asossiz']))
        ]

        for row in data_rows:
            row_cells = table.add_row().cells
            row_cells[0].text = row[0]
            row_cells[1].text = row[1]
            row_cells[2].text = row[2]

        doc.add_paragraph("\n")
        p_reg = doc.add_paragraph()
        p_reg.add_run("Eng ko‘p murojaat qayd etilgan hududlar:\n").bold = True
        for reg, cnt in reg_stats.head(5).items():
            p_reg.add_run(f"• {reg}: {cnt} ta murojaat\n")

        p_footer = doc.add_paragraph()
        p_footer.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        p_footer.add_run("\n\nBo‘lim mas’ul xodimi: _______________")

        doc.save(file_path)

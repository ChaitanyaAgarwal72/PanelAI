import re
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY

def markdown_to_pdf_bytes(md_text: str) -> bytes:
    """
    Converts a simple markdown string into a PDF and returns the raw bytes.
    Useful for providing a download button in Streamlit.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=18
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Justify', alignment=TA_JUSTIFY))

    md_text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', md_text)
    md_text = re.sub(r'(?<!\*)\*(?!\*)(.*?)(?<!\*)\*(?!\*)', r'<i>\1</i>', md_text)

    Story = []
    
    in_table = False
    table_data = []

    def flush_table():
        if table_data:
            from reportlab.platypus import Table, TableStyle
            from reportlab.lib import colors
            t = Table(table_data)
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            Story.append(t)
            Story.append(Spacer(1, 12))
            table_data.clear()

    for line in md_text.split('\n'):
        line = line.strip()
        
        if line.startswith('|') and line.endswith('|'):
            in_table = True
            if re.match(r'^\|[\s\-:|]+\|$', line):
                continue
            
            row = [cell.strip() for cell in line.split('|')[1:-1]]
            
            from reportlab.platypus import Paragraph
            row_paragraphs = [Paragraph(cell, styles["Normal"]) for cell in row]
            table_data.append(row_paragraphs)
            continue
        else:
            if in_table:
                flush_table()
                in_table = False
        
        if not line:
            Story.append(Spacer(1, 12))
            continue
            
        if line.startswith('### '):
            Story.append(Paragraph(line[4:], styles["Heading3"]))
        elif line.startswith('## '):
            Story.append(Paragraph(line[3:], styles["Heading2"]))
        elif line.startswith('# '):
            Story.append(Paragraph(line[2:], styles["Heading1"]))
        elif line.startswith('- '):
            Story.append(Paragraph("• " + line[2:], styles["Normal"]))
        else:
            Story.append(Paragraph(line, styles["Normal"]))
            
    if in_table:
        flush_table()
            
    doc.build(Story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    
    return pdf_bytes

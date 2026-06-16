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
    
    for line in md_text.split('\n'):
        line = line.strip()
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
            
    doc.build(Story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    
    return pdf_bytes

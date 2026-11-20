"""Render the technical Markdown and use cases as PDF. Requires reportlab."""
from pathlib import Path
from html import escape
import re
import textwrap
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Preformatted, Flowable

ROOT = Path(__file__).resolve().parents[1]
FONT, BOLD = 'Helvetica', 'Helvetica-Bold'
for directory, regular, bold in [(Path('C:/Windows/Fonts'), 'arial.ttf', 'arialbd.ttf'),
                                  (Path('/usr/share/fonts/truetype/dejavu'), 'DejaVuSans.ttf', 'DejaVuSans-Bold.ttf')]:
    if (directory / regular).is_file():
        pdfmetrics.registerFont(TTFont('Document', str(directory / regular)))
        pdfmetrics.registerFont(TTFont('Document-Bold', str(directory / bold)))
        pdfmetrics.registerFontFamily('Document', normal='Document', bold='Document-Bold', italic='Document', boldItalic='Document-Bold')
        FONT, BOLD = 'Document', 'Document-Bold'
        break
INK = colors.HexColor('#173442')
TEAL = colors.HexColor('#096c79')
STYLES = {
    'body': ParagraphStyle('body', fontName=FONT, fontSize=10, leading=14, textColor=INK, spaceAfter=7),
    'title': ParagraphStyle('title', fontName=BOLD, fontSize=25, leading=30, textColor=TEAL, spaceAfter=15),
    'h2': ParagraphStyle('h2', fontName=BOLD, fontSize=15, leading=19, textColor=TEAL, spaceBefore=14, spaceAfter=9, keepWithNext=True),
    'h3': ParagraphStyle('h3', fontName=BOLD, fontSize=11, leading=15, textColor=TEAL, spaceBefore=11, spaceAfter=8, keepWithNext=True),
    'cell': ParagraphStyle('cell', fontName=FONT, fontSize=9, leading=12, textColor=INK),
    'code': ParagraphStyle('code', fontName='Courier', fontSize=8, leading=11, textColor=INK, backColor=colors.HexColor('#eef4f5'), spaceBefore=8, spaceAfter=12),
}


def inline(text):
    text = escape(text)
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'\1', text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    return re.sub(r'`([^`]+)`', r'<font name="Courier" size="8">\1</font>', text)


class UseCases(Flowable):
    def __init__(self):
        super().__init__()
        self.width, self.height = 490, 210

    def draw(self):
        c = self.canv
        c.setStrokeColor(INK)
        c.setFillColor(INK)
        c.setFont(FONT, 9)
        c.rect(135, 20, 350, 180)
        c.drawCentredString(310, 182, 'Pluvia SCZ')
        for x, y, name in [(55, 145, 'Cliente'), (55, 55, 'Administrador')]:
            c.circle(x, y+10, 6)
            c.line(x, y+4, x, y-15)
            c.line(x-12, y-2, x+12, y-2)
            c.line(x, y-15, x-12, y-29)
            c.line(x, y-15, x+12, y-29)
            c.drawCentredString(x, y-41, name)
            c.line(x+12, y-2, 180, 140)
            c.line(x+12, y-2, 180, 70)
        for y, name in [(140, 'CU-01 · Simular'), (70, 'CU-02 · Consultar resultados')]:
            c.setFillColor(colors.HexColor('#edf5f6'))
            c.ellipse(180, y-23, 450, y+23, fill=1)
            c.setFillColor(INK)
            c.drawCentredString(315, y-3, name)


def export(source, destination, diagram=False):
    story, rows, code = [], [], None

    def flush_table():
        if not rows:
            return
        widths = [230, 265] if len(rows[0]) == 2 else [175, 100, 220]
        if len(rows[0]) == 3 and rows[0][1] == 'Cliente':
            widths = [275, 95, 125]
        table = Table([[Paragraph(inline(cell), STYLES['cell']) for cell in row] for row in rows], colWidths=widths, repeatRows=1, hAlign='LEFT')
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#dbecef')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f3f7f8')]),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'), ('LEFTPADDING', (0, 0), (-1, -1), 7),
            ('RIGHTPADDING', (0, 0), (-1, -1), 7), ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.extend([table, Spacer(1, 10)])
        rows.clear()

    for line in source.read_text(encoding='utf-8').splitlines():
        if line.startswith('```'):
            flush_table()
            if code is None:
                code = []
            else:
                story.append(Preformatted('\n'.join(code), STYLES['code']))
                code = None
            continue
        if code is not None:
            code.extend(textwrap.wrap(line, 98, replace_whitespace=False, drop_whitespace=False) or [''])
            continue
        if line.startswith('|'):
            cells = [s.strip() for s in line.strip().strip('|').split('|')]
            if not all(re.fullmatch(r'[-:]+', cell) for cell in cells):
                rows.append(cells)
            continue
        flush_table()
        if not line.strip():
            continue
        if line.startswith('### '):
            story.append(Paragraph(inline(line[4:]), STYLES['h3']))
        elif line.startswith('## '):
            story.append(Paragraph(inline(line[3:]), STYLES['h2']))
        elif line.startswith('# '):
            story.append(Paragraph(inline(line[2:]), STYLES['title']))
            if diagram:
                story.extend([UseCases(), Spacer(1, 10)])
        else:
            story.append(Paragraph(inline(line), STYLES['body']))
    flush_table()

    def footer(canvas, doc):
        canvas.setFillColor(INK)
        canvas.setFont(FONT, 8)
        canvas.drawString(50, 28, 'Pluvia SCZ · Documentación funcional y técnica')
        canvas.drawRightString(A4[0]-50, 28, str(doc.page))

    SimpleDocTemplate(str(destination), pagesize=A4, rightMargin=50, leftMargin=50,
                      topMargin=45, bottomMargin=50, title='Pluvia SCZ', author='Pluvia SCZ').build(story, onFirstPage=footer, onLaterPages=footer)
    print(destination)


def main():
    for name in ('PLUVIA_SCZ_SPRINT_1', 'CASOS_DE_USO'):
        export(ROOT / f'docs/{name}.md', ROOT / f'docs/{name}.pdf', diagram=name == 'CASOS_DE_USO')


if __name__ == '__main__':
    main()

"""
Purchase Order PDF Generation Service using ReportLab.
Generates professional PDF purchase orders with seller branding.
"""

import io
import urllib.request
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_RIGHT


def generate_po_pdf(po: dict, seller: dict, supplier: dict) -> bytes:
    """Generate a PDF purchase order and return bytes."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=20*mm, bottomMargin=20*mm, leftMargin=15*mm, rightMargin=15*mm)

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('POTitle', parent=styles['Title'], fontSize=22, textColor=colors.HexColor('#1a4d2e'), spaceAfter=6)
    normal_style = ParagraphStyle('Normal2', parent=styles['Normal'], fontSize=9, leading=13)
    small_style = ParagraphStyle('Small', parent=styles['Normal'], fontSize=8, textColor=colors.HexColor('#666'))

    elements = []

    # Try to load seller logo
    seller_logo_url = seller.get("sellerLogoUrl", "")
    logo_element = None
    if seller_logo_url:
        try:
            req = urllib.request.Request(seller_logo_url, headers={'User-Agent': 'Mozilla/5.0'})
            logo_data = urllib.request.urlopen(req, timeout=5).read()
            logo_buf = io.BytesIO(logo_data)
            logo_element = Image(logo_buf, width=30*mm, height=30*mm)
            logo_element.hAlign = 'LEFT'
        except Exception:
            logo_element = None

    # Header
    if logo_element:
        header_data = [[logo_element, Paragraph("PURCHASE ORDER", title_style)]]
        header_table = Table(header_data, colWidths=[35*mm, 140*mm])
        header_table.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('LEFTPADDING', (0, 0), (-1, -1), 0)]))
        elements.append(header_table)
    else:
        elements.append(Paragraph("PURCHASE ORDER", title_style))
    elements.append(Spacer(1, 4*mm))

    # PO Info Row
    po_number = po.get("poNumber", "N/A")
    po_date = po.get("createdAt", "")
    if isinstance(po_date, datetime):
        po_date = po_date.strftime("%d %b %Y")
    elif isinstance(po_date, str):
        try:
            po_date = datetime.fromisoformat(po_date.replace("Z", "+00:00")).strftime("%d %b %Y")
        except Exception:
            pass

    status = po.get("status", "draft").upper()

    info_data = [
        [Paragraph(f"<b>PO #:</b> {po_number}", normal_style),
         Paragraph(f"<b>Date:</b> {po_date}", normal_style),
         Paragraph(f"<b>Status:</b> {status}", normal_style)]
    ]
    info_table = Table(info_data, colWidths=[65*mm, 55*mm, 55*mm])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e8f5e9')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#333')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6), ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 6*mm))

    # Seller & Supplier Details
    seller_name = seller.get("businessName", seller.get("name", "Seller"))
    from_text = f"<b>From (Buyer):</b><br/>{seller_name}"
    for field, label in [("address", None), ("phone", "Phone"), ("email", "Email"), ("gstNumber", "GST")]:
        val = seller.get(field, "")
        if val:
            from_text += f"<br/>{label + ': ' if label else ''}{val}"

    supplier_name = supplier.get("supplierName", "Supplier")
    to_text = f"<b>To (Supplier):</b><br/>{supplier_name}"
    for field, label in [("contact", "Contact"), ("address", None), ("phone", "Phone"), ("email", "Email"), ("gstNumber", "GST")]:
        val = supplier.get(field, "")
        if val:
            to_text += f"<br/>{label + ': ' if label else ''}{val}"

    party_data = [[Paragraph(from_text, normal_style), Paragraph(to_text, normal_style)]]
    party_table = Table(party_data, colWidths=[87.5*mm, 87.5*mm])
    party_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 4), ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#ddd')),
        ('LINEAFTER', (0, 0), (0, -1), 0.5, colors.HexColor('#ddd')),
    ]))
    elements.append(party_table)
    elements.append(Spacer(1, 6*mm))

    # Items Table
    items = po.get("items", [])
    header = ['#', 'Product', 'Specification', 'Qty', 'Rate', 'Total']
    table_data = [header]

    for i, item in enumerate(items, 1):
        qty = item.get("quantity", 0)
        rate = item.get("rate", 0)
        total = item.get("total", qty * rate)
        product_text = str(item.get("productName", "Item"))
        if item.get("sku"):
            product_text += f"<br/><font size='7' color='#666'>SKU: {item['sku']}</font>"
        if item.get("description"):
            product_text += f"<br/><font size='7' color='#888'>{item['description'][:100]}</font>"

        spec_text = str(item.get("specification", "")) or "-"

        row = [
            str(i),
            Paragraph(product_text, normal_style),
            Paragraph(spec_text.replace('\n', '<br/>'), small_style),
            str(qty),
            f"{rate:,.2f}",
            f"{total:,.2f}"
        ]
        table_data.append(row)

    col_widths = [10*mm, 55*mm, 40*mm, 15*mm, 25*mm, 30*mm]
    items_table = Table(table_data, colWidths=col_widths, repeatRows=1)
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a4d2e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('ALIGN', (3, 0), (-1, -1), 'RIGHT'),
        ('TOPPADDING', (0, 0), (-1, -1), 5), ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 4), ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9fafb')]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
    ]))
    elements.append(items_table)
    elements.append(Spacer(1, 4*mm))

    # Total
    total_amount = po.get("totalAmount", 0)
    totals_data = [['', '', '', 'Total Amount:', f"{total_amount:,.2f}"]]
    totals_table = Table(totals_data, colWidths=[40*mm, 40*mm, 30*mm, 35*mm, 30*mm])
    totals_table.setStyle(TableStyle([
        ('ALIGN', (3, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (3, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (3, 0), (-1, 0), 11),
        ('LINEABOVE', (3, 0), (-1, 0), 1, colors.HexColor('#1a4d2e')),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(totals_table)

    # Delivery Notes
    notes = po.get("deliveryNotes")
    if notes:
        elements.append(Spacer(1, 6*mm))
        elements.append(Paragraph("<b>Delivery Instructions:</b>", normal_style))
        elements.append(Paragraph(notes, small_style))

    # Footer
    elements.append(Spacer(1, 12*mm))
    elements.append(Paragraph(f"Authorized by: {seller_name}", normal_style))
    elements.append(Spacer(1, 6*mm))
    elements.append(Paragraph("This is a computer-generated purchase order.", small_style))

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()

"""
Invoice PDF Generation Service using ReportLab
Enhanced with seller branding (email) and payment summary.
"""

import io
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER


def generate_invoice_pdf(invoice: dict, seller: dict, buyer: dict) -> bytes:
    """Generate a PDF invoice and return bytes."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=20*mm, bottomMargin=20*mm, leftMargin=15*mm, rightMargin=15*mm)

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('InvoiceTitle', parent=styles['Title'], fontSize=22, textColor=colors.HexColor('#1a1a2e'), spaceAfter=6)
    heading_style = ParagraphStyle('Heading', parent=styles['Heading2'], fontSize=11, textColor=colors.HexColor('#333'), spaceAfter=4)
    normal_style = ParagraphStyle('Normal2', parent=styles['Normal'], fontSize=9, leading=13)
    small_style = ParagraphStyle('Small', parent=styles['Normal'], fontSize=8, textColor=colors.HexColor('#666'))
    right_style = ParagraphStyle('Right', parent=styles['Normal'], fontSize=9, alignment=TA_RIGHT)

    elements = []

    # Header
    elements.append(Paragraph("INVOICE", title_style))
    elements.append(Spacer(1, 4*mm))

    # Invoice Info Row
    invoice_number = invoice.get("invoiceNumber", "N/A")
    invoice_date = invoice.get("date", invoice.get("createdAt", ""))
    if isinstance(invoice_date, datetime):
        invoice_date = invoice_date.strftime("%d %b %Y")
    elif isinstance(invoice_date, str):
        try:
            invoice_date = datetime.fromisoformat(invoice_date.replace("Z", "+00:00")).strftime("%d %b %Y")
        except Exception:
            pass

    status = invoice.get("status", "draft").upper().replace("_", " ")

    info_data = [
        [Paragraph(f"<b>Invoice #:</b> {invoice_number}", normal_style),
         Paragraph(f"<b>Date:</b> {invoice_date}", normal_style),
         Paragraph(f"<b>Status:</b> {status}", normal_style)]
    ]
    info_table = Table(info_data, colWidths=[65*mm, 55*mm, 55*mm])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f0f4f8')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#333')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 6*mm))

    # Seller & Buyer Details
    seller_name = seller.get("businessName", seller.get("name", "Seller"))
    seller_address = seller.get("address", "")
    seller_city = seller.get("city", "")
    seller_state = seller.get("state", "")
    seller_gst = seller.get("gstNumber", "")
    seller_phone = seller.get("phone", "")
    seller_email = seller.get("email", "")

    buyer_name = buyer.get("buyerName", buyer.get("name", "Buyer"))
    buyer_company = buyer.get("company", "")
    buyer_address = buyer.get("address", "")
    buyer_gst = buyer.get("gstNumber", "")
    buyer_phone = buyer.get("phone", "")

    from_text = f"<b>From:</b><br/>{seller_name}"
    if seller_address:
        from_text += f"<br/>{seller_address}"
    if seller_city or seller_state:
        from_text += f"<br/>{seller_city}, {seller_state}"
    if seller_gst:
        from_text += f"<br/>GST: {seller_gst}"
    if seller_phone:
        from_text += f"<br/>Phone: {seller_phone}"
    if seller_email:
        from_text += f"<br/>Email: {seller_email}"

    to_text = f"<b>To:</b><br/>{buyer_name}"
    if buyer_company:
        to_text += f"<br/>{buyer_company}"
    if buyer_address:
        to_text += f"<br/>{buyer_address}"
    if buyer_gst:
        to_text += f"<br/>GST: {buyer_gst}"
    if buyer_phone:
        to_text += f"<br/>Phone: {buyer_phone}"

    party_data = [[Paragraph(from_text, normal_style), Paragraph(to_text, normal_style)]]
    party_table = Table(party_data, colWidths=[87.5*mm, 87.5*mm])
    party_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#ddd')),
        ('LINEAFTER', (0, 0), (0, -1), 0.5, colors.HexColor('#ddd')),
    ]))
    elements.append(party_table)
    elements.append(Spacer(1, 6*mm))

    # Items Table
    items = invoice.get("items", [])
    header = ['#', 'Product', 'Qty', 'Price', 'GST %', 'GST Amt', 'Total']
    table_data = [header]

    for i, item in enumerate(items, 1):
        qty = item.get("quantity", 0)
        price = item.get("price", 0)
        gst_pct = item.get("gstPercent", 0)
        gst_amt = item.get("gstAmount", 0)
        total = item.get("total", 0)
        product_text = str(item.get("productName", "Item"))
        # Add specs in compact single line
        specs = item.get("selected_specifications", [])
        if specs:
            spec_parts = [f"{s.get('key', '')}: {s.get('value', '')}" for s in specs if s.get('key') and s.get('value')]
            if spec_parts:
                product_text += f"<br/><font size='7' color='#666'>{' | '.join(spec_parts)}</font>"
        row = [
            str(i),
            Paragraph(product_text, normal_style),
            str(qty),
            f"{price:,.2f}",
            f"{gst_pct}%",
            f"{gst_amt:,.2f}",
            f"{total:,.2f}"
        ]
        table_data.append(row)

    col_widths = [10*mm, 60*mm, 15*mm, 25*mm, 18*mm, 22*mm, 25*mm]
    items_table = Table(table_data, colWidths=col_widths, repeatRows=1)
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a1a2e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9fafb')]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
    ]))
    elements.append(items_table)
    elements.append(Spacer(1, 4*mm))

    # Totals with Payment Summary
    subtotal = invoice.get("subtotal", 0)
    gst_total = invoice.get("gst", 0)
    grand_total = invoice.get("total", 0)
    total_paid = invoice.get("totalPaid", 0)
    pending_amount = invoice.get("pendingAmount", grand_total)

    totals_data = [
        ['', '', 'Subtotal:', f"{subtotal:,.2f}"],
        ['', '', 'GST:', f"{gst_total:,.2f}"],
        ['', '', 'Grand Total:', f"{grand_total:,.2f}"],
    ]

    # Add payment summary if any payments made
    if total_paid > 0:
        totals_data.append(['', '', 'Amount Paid:', f"{total_paid:,.2f}"])
        totals_data.append(['', '', 'Pending Amount:', f"{pending_amount:,.2f}"])

    totals_table = Table(totals_data, colWidths=[60*mm, 50*mm, 35*mm, 30*mm])

    totals_style = [
        ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (2, 2), (-1, 2), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('FONTSIZE', (2, 2), (-1, 2), 11),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LINEABOVE', (2, 2), (-1, 2), 1, colors.HexColor('#1a1a2e')),
    ]

    if total_paid > 0:
        # Style for paid row (green)
        paid_row = 3
        pending_row = 4
        totals_style.append(('TEXTCOLOR', (2, paid_row), (-1, paid_row), colors.HexColor('#059669')))
        totals_style.append(('FONTNAME', (2, paid_row), (-1, paid_row), 'Helvetica-Bold'))
        totals_style.append(('TEXTCOLOR', (2, pending_row), (-1, pending_row), colors.HexColor('#d97706')))
        totals_style.append(('FONTNAME', (2, pending_row), (-1, pending_row), 'Helvetica-Bold'))
        totals_style.append(('FONTSIZE', (2, pending_row), (-1, pending_row), 10))
        totals_style.append(('LINEABOVE', (2, paid_row), (-1, paid_row), 0.5, colors.HexColor('#ddd')))

    totals_table.setStyle(TableStyle(totals_style))
    elements.append(totals_table)

    # Notes
    notes = invoice.get("notes")
    if notes:
        elements.append(Spacer(1, 6*mm))
        elements.append(Paragraph("<b>Notes:</b>", heading_style))
        elements.append(Paragraph(notes, small_style))

    # Footer
    elements.append(Spacer(1, 10*mm))
    elements.append(Paragraph("This is a computer-generated invoice.", small_style))

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()

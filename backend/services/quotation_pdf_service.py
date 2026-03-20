"""
Quotation PDF Generation Service
Generates A4 quotation documents with GST layout, matching the invoice style.
Supports a DRAFT (OFFLINE) watermark for offline-generated quotations.
"""

import io
from datetime import datetime, timedelta
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
import urllib.request

ONES = ['', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine',
        'Ten', 'Eleven', 'Twelve', 'Thirteen', 'Fourteen', 'Fifteen', 'Sixteen',
        'Seventeen', 'Eighteen', 'Nineteen']
TENS = ['', '', 'Twenty', 'Thirty', 'Forty', 'Fifty', 'Sixty', 'Seventy', 'Eighty', 'Ninety']


def number_to_words(n: float) -> str:
    if n == 0:
        return "Zero Only"
    rupees = int(n)
    paise = round((n - rupees) * 100)

    def _convert(num):
        if num == 0:
            return ''
        if num < 20:
            return ONES[num]
        if num < 100:
            return TENS[num // 10] + (' ' + ONES[num % 10] if num % 10 else '')
        if num < 1000:
            return ONES[num // 100] + ' Hundred' + (' and ' + _convert(num % 100) if num % 100 else '')
        if num < 100000:
            return _convert(num // 1000) + ' Thousand' + (' ' + _convert(num % 1000) if num % 1000 else '')
        if num < 10000000:
            return _convert(num // 100000) + ' Lakh' + (' ' + _convert(num % 100000) if num % 100000 else '')
        return _convert(num // 10000000) + ' Crore' + (' ' + _convert(num % 10000000) if num % 10000000 else '')

    words = _convert(rupees)
    if paise > 0:
        words += f" and {_convert(paise)} Paise"
    return words.strip() + " Only"


def _is_igst(seller_state: str, place_of_supply: str) -> bool:
    if not seller_state or not place_of_supply:
        return False
    return seller_state.strip().lower() != place_of_supply.strip().lower()


def generate_quotation_pdf(quotation: dict, seller: dict, buyer: dict, is_offline: bool = False) -> bytes:
    """Generate a professional quotation PDF. If is_offline=True, adds a DRAFT (OFFLINE) watermark."""
    buffer = io.BytesIO()

    def draw_watermark(canvas, doc):
        if is_offline:
            canvas.saveState()
            canvas.setFont("Helvetica-Bold", 60)
            canvas.setFillColor(colors.Color(0.85, 0.85, 0.85, alpha=0.5))
            canvas.translate(A4[0] / 2, A4[1] / 2)
            canvas.rotate(45)
            canvas.drawCentredString(0, 0, "DRAFT (OFFLINE)")
            canvas.restoreState()

    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=12 * mm, bottomMargin=12 * mm, leftMargin=12 * mm, rightMargin=12 * mm)

    styles = getSampleStyleSheet()
    s_title = ParagraphStyle('Title2', parent=styles['Title'], fontSize=14, textColor=colors.HexColor('#111'), spaceAfter=2, leading=16)
    s_normal = ParagraphStyle('N', parent=styles['Normal'], fontSize=8, leading=11)
    s_small = ParagraphStyle('S', parent=styles['Normal'], fontSize=7, textColor=colors.HexColor('#555'), leading=9)
    s_right = ParagraphStyle('R', parent=styles['Normal'], fontSize=8, alignment=TA_RIGHT)
    s_bold = ParagraphStyle('B', parent=styles['Normal'], fontSize=8, leading=11, fontName='Helvetica-Bold')

    elements = []
    page_w = A4[0] - 24 * mm

    # === HEADER ===
    logo_element = None
    seller_logo_url = seller.get("sellerLogoUrl", "")
    if seller_logo_url:
        try:
            req = urllib.request.Request(seller_logo_url, headers={'User-Agent': 'Mozilla/5.0'})
            logo_data = urllib.request.urlopen(req, timeout=5).read()
            logo_buf = io.BytesIO(logo_data)
            logo_element = Image(logo_buf, width=20 * mm, height=20 * mm)
        except Exception:
            pass

    title_block = Paragraph("<b>QUOTATION</b>", s_title)
    if logo_element:
        header_cells = [[logo_element, title_block]]
        header_table = Table(header_cells, colWidths=[24 * mm, page_w - 24 * mm])
    else:
        header_cells = [[title_block]]
        header_table = Table(header_cells, colWidths=[page_w])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))
    elements.append(header_table)
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#1a1a2e')))
    elements.append(Spacer(1, 3 * mm))

    # === QUOTATION INFO ===
    q_num = quotation.get("quotationNumber", "N/A")
    q_date = quotation.get("date", quotation.get("createdAt", ""))
    if isinstance(q_date, datetime):
        q_date_str = q_date.strftime("%d/%m/%Y")
    elif isinstance(q_date, str):
        try:
            q_date_str = datetime.fromisoformat(q_date.replace("Z", "+00:00")).strftime("%d/%m/%Y")
        except Exception:
            q_date_str = str(q_date)
    else:
        q_date_str = str(q_date)

    validity_days = quotation.get("validityDays", 15)
    try:
        if isinstance(q_date, datetime):
            valid_until = q_date + timedelta(days=validity_days)
        else:
            valid_until = datetime.fromisoformat(str(q_date).replace("Z", "+00:00")) + timedelta(days=validity_days)
        valid_str = valid_until.strftime("%d/%m/%Y")
    except Exception:
        valid_str = f"{validity_days} days from date"

    info_left = f"<b>Quotation No:</b> {q_num}<br/><b>Date:</b> {q_date_str}<br/><b>Valid Until:</b> {valid_str}"
    status = quotation.get("status", "draft").capitalize()
    info_right = f"<b>Status:</b> {status}"

    info_data = [[Paragraph(info_left, s_normal), Paragraph(info_right, s_normal)]]
    info_table = Table(info_data, colWidths=[page_w / 2, page_w / 2])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f7f8fa')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#ddd')),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 3 * mm))

    # === SELLER DETAILS ===
    seller_name = seller.get("businessName", seller.get("name", "Seller"))
    seller_gstin = seller.get("gstNumber", "")
    seller_text = f"<b>{seller_name}</b>"
    if seller.get("address"):
        seller_text += f"<br/>{seller['address']}"
    if seller.get("city") or seller.get("state"):
        seller_text += f"<br/>{', '.join(filter(None, [seller.get('city', ''), seller.get('state', '')]))}"
    if seller_gstin:
        seller_text += f"<br/><b>GSTIN:</b> {seller_gstin}"
    if seller.get("phone"):
        seller_text += f"<br/>Ph: {seller['phone']}"

    seller_row = [[Paragraph(seller_text, s_normal)]]
    seller_table = Table(seller_row, colWidths=[page_w])
    seller_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#ccc')),
    ]))
    elements.append(seller_table)
    elements.append(Spacer(1, 2 * mm))

    # === BUYER DETAILS ===
    buyer_name = buyer.get("buyerName", buyer.get("name", "Buyer"))
    buyer_gstin = buyer.get("gstNumber", "")
    place_of_supply = quotation.get("placeOfSupply", buyer.get("state", seller.get("state", "")))
    seller_state = seller.get("state", "")

    bill_to = f"<b>To</b><br/><b>{buyer_name}</b>"
    if buyer.get("company"):
        bill_to += f"<br/>{buyer['company']}"
    if buyer.get("address"):
        bill_to += f"<br/>{buyer['address']}"
    if buyer_gstin:
        bill_to += f"<br/><b>GSTIN:</b> {buyer_gstin}"
    if buyer.get("phone"):
        bill_to += f"<br/>Ph: {buyer['phone']}"
    if place_of_supply:
        bill_to += f"<br/><b>Place of Supply:</b> {place_of_supply}"

    party_data = [[Paragraph(bill_to, s_normal)]]
    party_table = Table(party_data, colWidths=[page_w])
    party_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#ccc')),
    ]))
    elements.append(party_table)
    elements.append(Spacer(1, 4 * mm))

    # === ITEMS TABLE ===
    items = quotation.get("items", [])
    is_igst = _is_igst(seller_state, place_of_supply)

    if is_igst:
        header = ['#', 'Product', 'HSN', 'Qty', 'Rate', 'Disc', 'Taxable', 'IGST %', 'IGST', 'Total']
        col_w = [7 * mm, 42 * mm, 16 * mm, 12 * mm, 18 * mm, 12 * mm, 20 * mm, 13 * mm, 16 * mm, 20 * mm]
    else:
        header = ['#', 'Product', 'HSN', 'Qty', 'Rate', 'Disc', 'Taxable', 'CGST', 'SGST', 'Total']
        col_w = [7 * mm, 42 * mm, 16 * mm, 12 * mm, 18 * mm, 12 * mm, 20 * mm, 14 * mm, 14 * mm, 20 * mm]

    table_data = [header]
    total_taxable = 0
    total_cgst = 0
    total_sgst = 0
    total_igst = 0

    for i, item in enumerate(items, 1):
        qty = item.get("quantity", 0)
        price = item.get("price", 0)
        discount = item.get("discount", 0)
        disc_type = item.get("discountType", "Rs")
        gst_pct = item.get("gstPercent", 0)
        hsn = item.get("hsnCode", "")
        base = round(qty * price, 2)
        disc_amt = item.get("discountAmount", round(base * discount / 100, 2) if disc_type == "%" else round(discount, 2))
        taxable = item.get("taxableAmount", max(round(base - disc_amt, 2), 0))
        gst_amt = item.get("gstAmount", round(taxable * gst_pct / 100, 2))
        line_total = item.get("total", round(taxable + gst_amt, 2))
        total_taxable += taxable

        disc_display = "-"
        if disc_amt > 0:
            if disc_type == "%":
                disc_display = f"{discount}%\n({disc_amt:,.2f})"
            else:
                disc_display = f"{disc_amt:,.2f}"

        product_text = f"<b>{str(item.get('productName', 'Item'))}</b>"
        description = item.get("description", "")
        if description:
            product_text += f"<br/><font size='6' color='#666'>({description})</font>"
        specs = item.get("selected_specifications", [])
        if specs:
            spec_parts = [f"{s.get('key', '')}: {s.get('value', '')}" for s in specs if s.get('key')]
            if spec_parts:
                product_text += f"<br/><font size='6' color='#666'>{' | '.join(spec_parts)}</font>"

        if is_igst:
            total_igst += gst_amt
            row = [str(i), Paragraph(product_text, s_small), str(hsn), str(qty),
                   f"{price:,.2f}", disc_display,
                   f"{taxable:,.2f}", f"{gst_pct}%", f"{gst_amt:,.2f}", f"{line_total:,.2f}"]
        else:
            half_gst = round(gst_amt / 2, 2)
            total_cgst += half_gst
            total_sgst += half_gst
            row = [str(i), Paragraph(product_text, s_small), str(hsn), str(qty),
                   f"{price:,.2f}", disc_display,
                   f"{taxable:,.2f}", f"{half_gst:,.2f}", f"{half_gst:,.2f}", f"{line_total:,.2f}"]
        table_data.append(row)

    items_table = Table(table_data, colWidths=col_w, repeatRows=1)
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a1a2e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTSIZE', (0, 0), (-1, 0), 7),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 1), (-1, -1), 7),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('ALIGN', (3, 0), (-1, -1), 'RIGHT'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#fafafa')]),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#ddd')),
    ]))
    elements.append(items_table)
    elements.append(Spacer(1, 3 * mm))

    # === TOTALS ===
    subtotal = quotation.get("subtotal", total_taxable)
    grand_total = quotation.get("total", 0)
    total_gst_amt = quotation.get("gst", total_cgst + total_sgst + total_igst)
    round_off = quotation.get("roundOff", 0)
    amount_words = number_to_words(grand_total)

    totals_rows = [['Taxable Amount:', f"{subtotal:,.2f}"]]
    if is_igst:
        totals_rows.append(['IGST:', f"{total_gst_amt:,.2f}"])
    else:
        totals_rows.append(['CGST:', f"{quotation.get('cgst', total_cgst):,.2f}"])
        totals_rows.append(['SGST:', f"{quotation.get('sgst', total_sgst):,.2f}"])
    if round_off != 0:
        sign = "+" if round_off > 0 else ""
        totals_rows.append(['Round Off:', f"{sign}{round_off:.2f}"])
    totals_rows.append(['Grand Total:', f"{grand_total:,.2f}"])

    words_block = Paragraph(f"<b>Amount in Words:</b><br/>{amount_words}", s_small)
    totals_right_data = [[Paragraph(f"<b>{r[0]}</b>", s_right), Paragraph(f"<b>{r[1]}</b>" if 'Grand' in r[0] else r[1], s_right)] for r in totals_rows]
    totals_right = Table(totals_right_data, colWidths=[30 * mm, 30 * mm])
    totals_right.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))

    summary_data = [[words_block, totals_right]]
    summary_table = Table(summary_data, colWidths=[page_w - 65 * mm, 65 * mm])
    summary_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#ccc')),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 4 * mm))

    # === TERMS & CONDITIONS ===
    terms = quotation.get("termsAndConditions", "") or seller.get("invoiceTerms", "")
    notes = quotation.get("notes", "")
    bank = seller.get("bankDetails", {})

    bank_text = "<b>Bank Details</b>"
    if bank.get("accountName"):
        bank_text += f"<br/>A/c Name: {bank['accountName']}"
    if bank.get("accountNumber"):
        bank_text += f"<br/>A/c No: {bank['accountNumber']}"
    if bank.get("ifscCode"):
        bank_text += f"<br/>IFSC: {bank['ifscCode']}"
    if bank.get("bankName"):
        bank_text += f"<br/>Bank: {bank['bankName']}"

    terms_text = "<b>Terms &amp; Conditions</b>"
    if terms:
        terms_text += f"<br/>{terms}"
    else:
        terms_text += "<br/>1. Prices valid for the stated period.<br/>2. GST as applicable.<br/>3. Subject to local jurisdiction."
    if notes:
        terms_text += f"<br/><br/><b>Notes:</b> {notes}"

    footer_data = [[Paragraph(bank_text, s_small), Paragraph(terms_text, s_small)]]
    footer_table = Table(footer_data, colWidths=[page_w / 2, page_w / 2])
    footer_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#ddd')),
        ('LINEAFTER', (0, 0), (0, -1), 0.5, colors.HexColor('#ddd')),
    ]))
    elements.append(footer_table)
    elements.append(Spacer(1, 8 * mm))

    # Authorised Signatory
    sig_data = [
        ['', Paragraph(f"For <b>{seller_name}</b>", s_right)],
        ['', ''],
        ['', Paragraph("Authorised Signatory", s_right)],
    ]
    sig_table = Table(sig_data, colWidths=[page_w - 50 * mm, 50 * mm], rowHeights=[6 * mm, 12 * mm, 6 * mm])
    sig_table.setStyle(TableStyle([
        ('ALIGN', (-1, 0), (-1, -1), 'RIGHT'),
        ('LINEBELOW', (-1, 1), (-1, 1), 0.5, colors.HexColor('#333')),
    ]))
    elements.append(sig_table)

    elements.append(Spacer(1, 3 * mm))
    elements.append(Paragraph("This is a computer-generated quotation and does not require a physical signature.", s_small))

    doc.build(elements, onFirstPage=draw_watermark, onLaterPages=draw_watermark)
    buffer.seek(0)
    return buffer.getvalue()

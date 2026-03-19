"""
GST-Compliant Invoice PDF Generation Service
Generates A4 tax invoices with multiple copy types and full GST layout.
"""

import io
import urllib.request
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER

COPY_TYPES = {
    "original": "Original for Recipient",
    "transporter": "Duplicate for Transporter",
    "supplier": "Triplicate for Supplier / CA",
    "office": "Office Copy",
}

ONES = ['', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine',
        'Ten', 'Eleven', 'Twelve', 'Thirteen', 'Fourteen', 'Fifteen', 'Sixteen',
        'Seventeen', 'Eighteen', 'Nineteen']
TENS = ['', '', 'Twenty', 'Thirty', 'Forty', 'Fifty', 'Sixty', 'Seventy', 'Eighty', 'Ninety']


def number_to_words(n: float) -> str:
    """Convert number to Indian numbering words."""
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


def generate_invoice_pdf(invoice: dict, seller: dict, buyer: dict, copy_type: str = "original") -> bytes:
    """Generate a GST-compliant PDF invoice."""
    buffer = io.BytesIO()

    # Background watermark callback
    bg_url = seller.get("invoiceBackgroundImage", "")
    bg_image_data = None
    if bg_url:
        try:
            req = urllib.request.Request(bg_url, headers={'User-Agent': 'Mozilla/5.0'})
            bg_image_data = urllib.request.urlopen(req, timeout=5).read()
        except Exception:
            pass

    def draw_background(canvas, doc):
        if bg_image_data:
            from reportlab.lib.utils import ImageReader
            canvas.saveState()
            canvas.setFillAlpha(0.08)
            img_reader = ImageReader(io.BytesIO(bg_image_data))
            canvas.drawImage(img_reader, 0, 0, width=A4[0], height=A4[1], preserveAspectRatio=True, anchor='c', mask='auto')
            canvas.restoreState()

    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=12 * mm, bottomMargin=12 * mm, leftMargin=12 * mm, rightMargin=12 * mm)

    styles = getSampleStyleSheet()
    s_title = ParagraphStyle('Title2', parent=styles['Title'], fontSize=14, textColor=colors.HexColor('#111'), spaceAfter=2, leading=16)
    s_copy = ParagraphStyle('Copy', parent=styles['Normal'], fontSize=8, textColor=colors.HexColor('#555'), alignment=TA_CENTER, spaceAfter=1)
    s_heading = ParagraphStyle('H2', parent=styles['Heading2'], fontSize=9, textColor=colors.HexColor('#333'), spaceAfter=2, spaceBefore=4)
    s_normal = ParagraphStyle('N', parent=styles['Normal'], fontSize=8, leading=11)
    s_small = ParagraphStyle('S', parent=styles['Normal'], fontSize=7, textColor=colors.HexColor('#555'), leading=9)
    s_right = ParagraphStyle('R', parent=styles['Normal'], fontSize=8, alignment=TA_RIGHT)
    s_center = ParagraphStyle('C', parent=styles['Normal'], fontSize=8, alignment=TA_CENTER)
    s_bold = ParagraphStyle('B', parent=styles['Normal'], fontSize=8, leading=11)
    s_bold.fontName = 'Helvetica-Bold'

    elements = []
    page_w = A4[0] - 24 * mm  # usable width

    # === HEADER: TAX INVOICE + Copy Type ===
    copy_label = COPY_TYPES.get(copy_type, "Original for Recipient")

    # Try to load seller logo
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

    inv_num = invoice.get("invoiceNumber", "N/A")
    seller_gstin = seller.get("gstNumber", "")
    buyer_gstin = buyer.get("gstNumber", "")
    grand_total = invoice.get("total", 0)
    inv_date = invoice.get("date", invoice.get("createdAt", ""))
    if isinstance(inv_date, datetime):
        inv_date_str = inv_date.strftime("%d/%m/%Y")
    elif isinstance(inv_date, str):
        try:
            inv_date_str = datetime.fromisoformat(inv_date.replace("Z", "+00:00")).strftime("%d/%m/%Y")
        except Exception:
            inv_date_str = str(inv_date)
    else:
        inv_date_str = str(inv_date)

    # Header row: Logo | Title + Copy (no QR code)
    title_block = Paragraph(f"<b>TAX INVOICE</b><br/><font size='7' color='#666'>{copy_label}</font>", s_title)
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

    # === INVOICE INFO ROW ===
    po_number = invoice.get("poNumber", "")
    challan_number = invoice.get("challanNumber", "")
    transport = invoice.get("transport", {})

    info_left = f"<b>Invoice No:</b> {inv_num}<br/><b>Date:</b> {inv_date_str}"
    if po_number:
        info_left += f"<br/><b>PO No:</b> {po_number}"
    if challan_number:
        info_left += f"<br/><b>Challan No:</b> {challan_number}"
    payment_terms = invoice.get("paymentTerms", "")
    if payment_terms:
        info_left += f"<br/><b>Payment Terms:</b> {payment_terms}"

    info_right = ""
    if transport.get("transporterName"):
        info_right += f"<b>Transporter:</b> {transport['transporterName']}<br/>"
    if transport.get("lrNumber"):
        info_right += f"<b>LR No:</b> {transport['lrNumber']}<br/>"
    if transport.get("vehicleNumber"):
        info_right += f"<b>Vehicle:</b> {transport['vehicleNumber']}<br/>"
    if transport.get("bookingLocation"):
        info_right += f"<b>Booking:</b> {transport['bookingLocation']}<br/>"
    if transport.get("numberOfPackages"):
        info_right += f"<b>Packages:</b> {transport['numberOfPackages']}"

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

    # === SELLER DETAILS (Full Width) ===
    seller_name = seller.get("businessName", seller.get("name", "Seller"))
    seller_addr = seller.get("address", "")
    seller_city = seller.get("city", "")
    seller_state = seller.get("state", "")
    seller_phone = seller.get("phone", "")
    seller_email = seller.get("email", "")
    bank = seller.get("bankDetails", {})

    seller_text = f"<b>{seller_name}</b>"
    if seller_addr:
        seller_text += f"<br/>{seller_addr}"
    if seller_city or seller_state:
        seller_text += f"<br/>{', '.join(filter(None, [seller_city, seller_state]))}"
    if seller_gstin:
        seller_text += f"<br/><b>GSTIN:</b> {seller_gstin}"
    if seller_phone:
        seller_text += f"<br/>Ph: {seller_phone}"
    if seller_email:
        seller_text += f"<br/>{seller_email}"

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

    # === BILLING ADDRESS (Left) + SHIPPING ADDRESS (Right) ===
    buyer_name = buyer.get("buyerName", buyer.get("name", "Buyer"))
    buyer_company = buyer.get("company", "")
    buyer_addr = buyer.get("address", "")
    buyer_phone = buyer.get("phone", "")
    place_of_supply = invoice.get("placeOfSupply", buyer.get("state", seller_state))

    bill_to = f"<b>Bill To</b><br/><b>{buyer_name}</b>"
    if buyer_company:
        bill_to += f"<br/>{buyer_company}"
    if buyer_addr:
        bill_to += f"<br/>{buyer_addr}"
    if buyer_gstin:
        bill_to += f"<br/><b>GSTIN:</b> {buyer_gstin}"
    if buyer_phone:
        bill_to += f"<br/>Ph: {buyer_phone}"
    if place_of_supply:
        bill_to += f"<br/><b>Place of Supply:</b> {place_of_supply}"

    # Determine shipping address
    ship_addr = invoice.get("shippingAddress", {}) or {}
    # Build a billing address string for comparison
    billing_str = buyer_addr.strip().lower() if buyer_addr else ""
    shipping_str = ""
    if ship_addr.get("addressLine1"):
        shipping_parts = [ship_addr.get("addressLine1", ""), ship_addr.get("addressLine2", ""),
                          ship_addr.get("city", ""), ship_addr.get("state", ""), ship_addr.get("pincode", "")]
        shipping_str = " ".join(filter(None, shipping_parts)).strip().lower()

    # Check if shipping is different from billing
    show_separate_shipping = bool(ship_addr.get("addressLine1")) and shipping_str != billing_str

    if show_separate_shipping:
        ship_to = "<b>Ship To</b>"
        if ship_addr.get("contactPerson"):
            ship_to += f"<br/><b>{ship_addr['contactPerson']}</b>"
        ship_to += f"<br/>{ship_addr.get('addressLine1', '')}"
        if ship_addr.get("addressLine2"):
            ship_to += f", {ship_addr['addressLine2']}"
        ship_to += f"<br/>{', '.join(filter(None, [ship_addr.get('city', ''), ship_addr.get('state', '')]))}"
        if ship_addr.get("pincode"):
            ship_to += f" - {ship_addr['pincode']}"
        if ship_addr.get("phone"):
            ship_to += f"<br/>Ph: {ship_addr['phone']}"
    else:
        # Same address or no shipping address → show billing as Ship To
        ship_to = "<b>Ship To</b><br/><i>Same as Billing Address</i>"

    party_data = [[Paragraph(bill_to, s_normal), Paragraph(ship_to, s_normal)]]
    party_table = Table(party_data, colWidths=[page_w / 2, page_w / 2])
    party_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#ccc')),
        ('LINEAFTER', (0, 0), (0, -1), 0.5, colors.HexColor('#ccc')),
    ]))
    elements.append(party_table)
    elements.append(Spacer(1, 4 * mm))

    # === ITEMS TABLE ===
    items = invoice.get("items", [])
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
        gst_pct = item.get("gstPercent", 0)
        hsn = item.get("hsnCode", "")
        taxable = round(qty * price - discount, 2)
        gst_amt = item.get("gstAmount", round(taxable * gst_pct / 100, 2))
        line_total = item.get("total", round(taxable + gst_amt, 2))
        total_taxable += taxable

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
                   f"{price:,.2f}", f"{discount:,.2f}" if discount else "-",
                   f"{taxable:,.2f}", f"{gst_pct}%", f"{gst_amt:,.2f}", f"{line_total:,.2f}"]
        else:
            half_gst = round(gst_amt / 2, 2)
            total_cgst += half_gst
            total_sgst += half_gst
            row = [str(i), Paragraph(product_text, s_small), str(hsn), str(qty),
                   f"{price:,.2f}", f"{discount:,.2f}" if discount else "-",
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

    # === TAX SUMMARY + CHARGES + TOTALS ===
    subtotal = invoice.get("subtotal", total_taxable)
    total_gst_amt = invoice.get("gst", total_cgst + total_sgst + total_igst)
    total_paid = invoice.get("totalPaid", 0)
    pending = invoice.get("pendingAmount", grand_total)

    # Additional charges from invoice
    inv_charges = invoice.get("additionalCharges", [])
    freight = invoice.get("freight", 0)
    tcs_enabled = invoice.get("tcsEnabled", False)
    tcs_percent = invoice.get("tcsPercent", 0)
    tcs_amount = invoice.get("tcsAmount", 0)
    round_off = invoice.get("roundOff", 0)

    amount_words = number_to_words(grand_total)

    totals_rows = [
        ['Taxable Amount:', f"{subtotal:,.2f}"],
    ]
    if is_igst:
        totals_rows.append(['IGST:', f"{total_gst_amt:,.2f}"])
    else:
        totals_rows.append([f'CGST:', f"{total_cgst:,.2f}"])
        totals_rows.append([f'SGST:', f"{total_sgst:,.2f}"])

    # Additional charges (Freight, Packing, etc.)
    for ch in inv_charges:
        ch_name = ch.get("name", "Charge")
        ch_amt = ch.get("amount", 0)
        if ch_amt > 0:
            totals_rows.append([f'{ch_name}:', f"{ch_amt:,.2f}"])

    # TCS
    if tcs_enabled and tcs_amount > 0:
        totals_rows.append([f'TCS ({tcs_percent}%):', f"{tcs_amount:,.2f}"])

    # Round Off
    if round_off != 0:
        sign = "+" if round_off > 0 else ""
        totals_rows.append([f'Round Off:', f"{sign}{round_off:.2f}"])

    totals_rows.append(['Grand Total:', f"{grand_total:,.2f}"])

    if total_paid > 0:
        totals_rows.append(['Amount Paid:', f"{total_paid:,.2f}"])
        totals_rows.append(['Balance Due:', f"{pending:,.2f}"])

    # Amount in words row
    words_block = Paragraph(f"<b>Amount in Words:</b><br/>{amount_words}", s_small)

    totals_left = words_block
    totals_right_data = [[Paragraph(f"<b>{r[0]}</b>", s_right), Paragraph(f"<b>{r[1]}</b>" if 'Grand' in r[0] or 'Balance' in r[0] else r[1], s_right)] for r in totals_rows]

    totals_right = Table(totals_right_data, colWidths=[30 * mm, 30 * mm])
    totals_right.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))

    summary_data = [[totals_left, totals_right]]
    summary_table = Table(summary_data, colWidths=[page_w - 65 * mm, 65 * mm])
    summary_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#ccc')),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 4 * mm))

    # === BANK DETAILS + TERMS + SIGNATORY ===
    bank_text = "<b>Bank Details</b>"
    if bank.get("accountName"):
        bank_text += f"<br/>A/c Name: {bank['accountName']}"
    if bank.get("accountNumber"):
        bank_text += f"<br/>A/c No: {bank['accountNumber']}"
    if bank.get("ifscCode"):
        bank_text += f"<br/>IFSC: {bank['ifscCode']}"
    if bank.get("bankName"):
        bank_text += f"<br/>Bank: {bank['bankName']}"
    if bank.get("branch"):
        bank_text += f"<br/>Branch: {bank['branch']}"

    terms = invoice.get("termsAndConditions", "") or seller.get("invoiceTerms", "")
    terms_text = "<b>Terms &amp; Conditions</b>"
    if terms:
        terms_text += f"<br/>{terms}"
    else:
        terms_text += "<br/>1. Payment due as per invoice terms.<br/>2. Goods once sold will not be taken back.<br/>3. Subject to local jurisdiction."

    footer_data = [
        [Paragraph(bank_text, s_small), Paragraph(terms_text, s_small)],
    ]
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

    # Computer generated notice
    elements.append(Spacer(1, 3 * mm))
    elements.append(Paragraph("This is a computer-generated invoice and does not require a physical signature.", s_small))

    doc.build(elements, onFirstPage=draw_background, onLaterPages=draw_background)
    buffer.seek(0)
    return buffer.getvalue()


def _is_igst(seller_state: str, place_of_supply: str) -> bool:
    """Determine if IGST applies (inter-state) vs CGST+SGST (intra-state)."""
    if not seller_state or not place_of_supply:
        return False
    return seller_state.strip().lower() != place_of_supply.strip().lower()


def generate_merged_invoice_pdf(invoice: dict, seller: dict, buyer: dict, copy_types: list) -> bytes:
    """Generate a single PDF with multiple invoice copies, one per page."""
    from PyPDF2 import PdfReader, PdfWriter

    writer = PdfWriter()
    for ct in copy_types:
        page_bytes = generate_invoice_pdf(invoice, seller, buyer, copy_type=ct)
        reader = PdfReader(io.BytesIO(page_bytes))
        for page in reader.pages:
            writer.add_page(page)

    output = io.BytesIO()
    writer.write(output)
    output.seek(0)
    return output.getvalue()

"""
Centralized WhatsApp Message Template Engine for Udyog Connect.

ALL outgoing WhatsApp messages MUST use these templates.
Structure: [Business Message] → [Call to Action] → [Branding Block]
"""
import random
import urllib.parse

# All outgoing WhatsApp links MUST use this domain
BASE_URL = "https://www.udyogconnect.in"

ROTATING_ADS = [
    "Digitize your business with Udyog Connect",
    "Automate billing, inventory & payments",
    "Grow your B2B business smarter",
    "Create invoices, PO & catalogs instantly",
    "Track dues, automate billing & grow faster",
    "Manage orders, inventory & logistics easily",
]


def build_footer() -> str:
    return (
        "\n---\n"
        "Powered by Udyog Connect\n"
        f"{random.choice(ROTATING_ADS)}\n"
        "www.udyogconnect.in"
    )


def clean_phone(phone: str) -> str:
    """Normalize phone number for wa.me links."""
    p = phone.replace(" ", "").replace("-", "").replace("+", "")
    if not p.startswith("91") and len(p) == 10:
        p = "91" + p
    return p


def build_wa_link(phone: str, message: str) -> str:
    """Build a WhatsApp link from phone and message."""
    return f"https://wa.me/{clean_phone(phone)}?text={urllib.parse.quote(message)}"


# ── Template #1: Purchase Order ──

def po_message(
    po_number: str,
    items: list,
    doc_url: str,
    business_name: str,
    supplier_name: str = "",
) -> str:
    supplier_name = (supplier_name or "").strip()
    greeting = f"Hello {supplier_name},\n\n" if supplier_name else "Hello,\n\n"
    msg = (
        f"{greeting}"
        f"Please find the Purchase Order details below.\n\n"
        f"PO Number: {po_number}\n\n"
        f"Items:\n"
    )
    for item in items:
        line = f"- {item.get('productName', '')}"
        if item.get("sku"):
            line += f" ({item['sku']})"
        line += f" | Qty: {item.get('quantity', 0)}"
        if item.get("price"):
            line += f" | Rate: Rs.{item['price']:,.2f}"
        msg += line + "\n"

    msg += (
        f"\nDownload PO:\n{doc_url}\n\n"
        f"Kindly confirm availability and expected delivery timeline.\n\n"
        f"Regards,\n{business_name}"
    )
    return msg + build_footer()


# ── Template #2: Invoice ──

def invoice_message(
    invoice_number: str,
    amount: float,
    doc_url: str,
    business_name: str,
    buyer_name: str = "",
) -> str:
    buyer_name = (buyer_name or "").strip()
    greeting = f"Hello {buyer_name},\n\n" if buyer_name else "Hello,\n\n"
    return (
        f"{greeting}"
        f"Your Invoice has been generated.\n\n"
        f"Invoice Number: {invoice_number}\n"
        f"Amount: Rs.{amount:,.2f}\n\n"
        f"Download Invoice:\n{doc_url}\n\n"
        f"Please ensure timely payment.\n\n"
        f"Regards,\n{business_name}"
    ) + build_footer()


# ── Template #3: Payment Reminder (Soft) ──

def payment_reminder_soft(
    invoice_number: str,
    pending_amount: float,
    due_date: str,
    doc_url: str,
    business_name: str,
    buyer_name: str = "",
) -> str:
    buyer_name = (buyer_name or "").strip()
    greeting = f"Hello {buyer_name},\n\n" if buyer_name else "Hello,\n\n"
    return (
        f"{greeting}"
        f"This is a gentle reminder for pending payment.\n\n"
        f"Invoice Number: {invoice_number}\n"
        f"Pending Amount: Rs.{pending_amount:,.2f}\n"
        f"Due Date: {due_date}\n\n"
        f"View Invoice:\n{doc_url}\n\n"
        f"Kindly process the payment at the earliest.\n\n"
        f"Regards,\n{business_name}"
    ) + build_footer()


# ── Template #4: Payment Reminder (Strict / Overdue) ──

def payment_reminder_strict(
    invoice_number: str,
    pending_amount: float,
    due_date: str,
    doc_url: str,
    business_name: str,
    buyer_name: str = "",
) -> str:
    buyer_name = (buyer_name or "").strip()
    greeting = f"Hello {buyer_name},\n\n" if buyer_name else "Hello,\n\n"
    return (
        f"{greeting}"
        f"Your payment is overdue.\n\n"
        f"Invoice Number: {invoice_number}\n"
        f"Pending Amount: Rs.{pending_amount:,.2f}\n"
        f"Due Date: {due_date}\n\n"
        f"View Invoice:\n{doc_url}\n\n"
        f"Please arrange payment immediately to avoid service interruption.\n\n"
        f"Regards,\n{business_name}"
    ) + build_footer()


# ── Template #5: Order / Dispatch ──

def dispatch_message(
    order_id: str,
    tracking_link: str,
    business_name: str,
    buyer_name: str = "",
) -> str:
    buyer_name = (buyer_name or "").strip()
    greeting = f"Hello {buyer_name},\n\n" if buyer_name else "Hello,\n\n"
    return (
        f"{greeting}"
        f"Your order has been processed.\n\n"
        f"Order ID: {order_id}\n"
        f"Status: Dispatched\n\n"
        f"Tracking Link:\n{tracking_link}\n\n"
        f"Thank you for your business.\n\n"
        f"Regards,\n{business_name}"
    ) + build_footer()


# ── Template #6: Product Catalog ──

def catalog_message(
    catalog_url: str,
    business_name: str,
    recipient_name: str = "",
) -> str:
    recipient_name = (recipient_name or "").strip()
    greeting = f"Hello {recipient_name},\n\n" if recipient_name else "Hello,\n\n"
    return (
        f"{greeting}"
        f"Please find our latest product catalog below.\n\n"
        f"View Catalog:\n{catalog_url}\n\n"
        f"Let us know your requirements - we'd be happy to assist.\n\n"
        f"Regards,\n{business_name}"
    ) + build_footer()


def build_doc_url(token: str) -> str:
    """Build a public document URL using the production base domain."""
    return f"{BASE_URL}/api/doc/{token}"


# ── Template #7: Catalog Marketing (Share Catalog) ──

def catalog_marketing_message(
    catalog_url: str,
    business_name: str,
    buyer_name: str = "",
    invoice_url: str = "",
) -> str:
    buyer_name = (buyer_name or "").strip()
    greeting = f"Hello {buyer_name},\n\n" if buyer_name else "Hello,\n\n"
    msg = (
        f"{greeting}"
        f"We are sharing our product details for your reference.\n\n"
        f"Catalog:\n{catalog_url}\n"
    )
    if invoice_url:
        msg += f"\nSample Invoice:\n{invoice_url}\n"
    msg += (
        f"\nLooking forward to your requirements.\n\n"
        f"Regards,\n{business_name}"
    )
    return msg + build_footer()


# ── Template: Pending Order Notification ──

def pending_order_notify(
    product_name: str,
    pending_qty: int,
    business_name: str,
    buyer_name: str = "",
) -> str:
    buyer_name = (buyer_name or "").strip()
    greeting = f"Hello {buyer_name},\n\n" if buyer_name else "Hello,\n\n"
    return (
        f"{greeting}"
        f"Your order for {product_name} has been partially fulfilled.\n\n"
        f"Pending Quantity: {pending_qty}\n\n"
        f"We will notify you once the remaining stock is available.\n\n"
        f"Regards,\n{business_name}"
    ) + build_footer()

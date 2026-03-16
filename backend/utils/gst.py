"""
Indian States and Union Territories.
Used for GST tax type determination (CGST/SGST vs IGST).
"""

INDIAN_STATES = [
    "Andhra Pradesh",
    "Arunachal Pradesh",
    "Assam",
    "Bihar",
    "Chhattisgarh",
    "Goa",
    "Gujarat",
    "Haryana",
    "Himachal Pradesh",
    "Jharkhand",
    "Karnataka",
    "Kerala",
    "Madhya Pradesh",
    "Maharashtra",
    "Manipur",
    "Meghalaya",
    "Mizoram",
    "Nagaland",
    "Odisha",
    "Punjab",
    "Rajasthan",
    "Sikkim",
    "Tamil Nadu",
    "Telangana",
    "Tripura",
    "Uttar Pradesh",
    "Uttarakhand",
    "West Bengal",
    "Andaman and Nicobar Islands",
    "Chandigarh",
    "Dadra and Nagar Haveli and Daman and Diu",
    "Delhi",
    "Jammu and Kashmir",
    "Ladakh",
    "Lakshadweep",
    "Puducherry",
]

GST_RATES = [0, 5, 12, 18, 28]


def calculate_gst(taxable_amount: float, gst_percent: float, seller_state: str, buyer_state: str, gst_enabled: bool = True):
    """
    Calculate GST breakdown based on seller and buyer states.
    Returns dict with cgst, sgst, igst, total_tax, total_amount.
    """
    if not gst_enabled or gst_percent <= 0:
        return {
            "taxableAmount": round(taxable_amount, 2),
            "cgst": 0, "cgstRate": 0,
            "sgst": 0, "sgstRate": 0,
            "igst": 0, "igstRate": 0,
            "totalTax": 0,
            "totalAmount": round(taxable_amount, 2),
        }

    gst_amount = round(taxable_amount * gst_percent / 100, 2)

    seller_state_norm = (seller_state or "").strip().lower()
    buyer_state_norm = (buyer_state or "").strip().lower()

    is_same_state = seller_state_norm and buyer_state_norm and seller_state_norm == buyer_state_norm

    if is_same_state:
        half = round(gst_amount / 2, 2)
        return {
            "taxableAmount": round(taxable_amount, 2),
            "cgst": half, "cgstRate": round(gst_percent / 2, 2),
            "sgst": half, "sgstRate": round(gst_percent / 2, 2),
            "igst": 0, "igstRate": 0,
            "totalTax": round(half * 2, 2),
            "totalAmount": round(taxable_amount + half * 2, 2),
        }
    else:
        return {
            "taxableAmount": round(taxable_amount, 2),
            "cgst": 0, "cgstRate": 0,
            "sgst": 0, "sgstRate": 0,
            "igst": gst_amount, "igstRate": gst_percent,
            "totalTax": gst_amount,
            "totalAmount": round(taxable_amount + gst_amount, 2),
        }

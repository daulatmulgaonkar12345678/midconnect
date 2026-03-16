"""Tests for GST calculation engine."""
import sys
sys.path.insert(0, '/app/backend')
from utils.gst import calculate_gst


def test_same_state_cgst_sgst():
    """Same state: should split into CGST + SGST."""
    result = calculate_gst(1000.0, 18, "Maharashtra", "Maharashtra", True)
    assert result["taxableAmount"] == 1000.0
    assert result["cgst"] == 90.0
    assert result["sgst"] == 90.0
    assert result["igst"] == 0
    assert result["totalTax"] == 180.0
    assert result["totalAmount"] == 1180.0
    assert result["cgstRate"] == 9.0
    assert result["sgstRate"] == 9.0
    assert result["igstRate"] == 0


def test_interstate_igst():
    """Different states: should calculate IGST only."""
    result = calculate_gst(1000.0, 18, "Maharashtra", "Gujarat", True)
    assert result["taxableAmount"] == 1000.0
    assert result["cgst"] == 0
    assert result["sgst"] == 0
    assert result["igst"] == 180.0
    assert result["totalTax"] == 180.0
    assert result["totalAmount"] == 1180.0
    assert result["igstRate"] == 18


def test_gst_disabled():
    """GST disabled: all tax values should be zero."""
    result = calculate_gst(1000.0, 18, "Maharashtra", "Gujarat", False)
    assert result["taxableAmount"] == 1000.0
    assert result["cgst"] == 0
    assert result["sgst"] == 0
    assert result["igst"] == 0
    assert result["totalTax"] == 0
    assert result["totalAmount"] == 1000.0


def test_zero_gst_rate():
    """Zero GST rate: all tax values should be zero."""
    result = calculate_gst(1000.0, 0, "Maharashtra", "Gujarat", True)
    assert result["taxableAmount"] == 1000.0
    assert result["cgst"] == 0
    assert result["sgst"] == 0
    assert result["igst"] == 0
    assert result["totalTax"] == 0
    assert result["totalAmount"] == 1000.0


def test_five_percent_gst():
    """5% GST same state."""
    result = calculate_gst(2000.0, 5, "Karnataka", "Karnataka", True)
    assert result["taxableAmount"] == 2000.0
    assert result["cgst"] == 50.0
    assert result["sgst"] == 50.0
    assert result["igst"] == 0
    assert result["totalTax"] == 100.0
    assert result["totalAmount"] == 2100.0


def test_28_percent_gst_interstate():
    """28% GST interstate."""
    result = calculate_gst(5000.0, 28, "Delhi", "Tamil Nadu", True)
    assert result["taxableAmount"] == 5000.0
    assert result["cgst"] == 0
    assert result["sgst"] == 0
    assert result["igst"] == 1400.0
    assert result["totalTax"] == 1400.0
    assert result["totalAmount"] == 6400.0


def test_case_insensitive_state_comparison():
    """State comparison should be case-insensitive."""
    result = calculate_gst(1000.0, 18, "maharashtra", "MAHARASHTRA", True)
    assert result["cgst"] == 90.0
    assert result["sgst"] == 90.0
    assert result["igst"] == 0


def test_empty_seller_state():
    """Empty seller state: defaults to IGST."""
    result = calculate_gst(1000.0, 18, "", "Gujarat", True)
    assert result["cgst"] == 0
    assert result["sgst"] == 0
    assert result["igst"] == 180.0


def test_empty_buyer_state():
    """Empty buyer state: defaults to IGST."""
    result = calculate_gst(1000.0, 18, "Maharashtra", "", True)
    assert result["cgst"] == 0
    assert result["sgst"] == 0
    assert result["igst"] == 180.0

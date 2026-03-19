"""
Test file for iteration 94: react-select searchable dropdowns for invoices
Tests the invoice page and related API endpoints to verify no regressions
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestInvoicePageAPIs:
    """Test invoice-related API endpoints for react-select dropdown data"""
    
    def test_health_check(self):
        """Test that the API is healthy"""
        response = requests.get(f"{BASE_URL}/api/health", timeout=10)
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print("✓ Health check passed")
    
    def test_invoices_page_loads(self):
        """Test that invoices page returns 200"""
        response = requests.get(f"{BASE_URL}/seller/business-tools/invoices", timeout=10)
        assert response.status_code == 200
        print("✓ Invoices page loads successfully (200)")
    
    def test_business_tools_page_loads(self):
        """Test that business dashboard page returns 200"""
        response = requests.get(f"{BASE_URL}/seller/business-tools", timeout=10)
        assert response.status_code == 200
        print("✓ Business tools page loads successfully (200)")
    
    def test_invoices_api_requires_auth(self):
        """Test that invoices API returns error without auth"""
        response = requests.get(f"{BASE_URL}/api/business-tools/invoices", timeout=10)
        # Should require authentication - 401/403/422 are valid responses for auth failure
        assert response.status_code in [401, 403, 422]
        print(f"✓ Invoices API properly requires authentication (status: {response.status_code})")
    
    def test_buyers_api_requires_auth(self):
        """Test that buyers API returns error without auth"""
        response = requests.get(f"{BASE_URL}/api/business-tools/buyers", timeout=10)
        # Should require authentication - 401/403/422 are valid responses for auth failure
        assert response.status_code in [401, 403, 422]
        print(f"✓ Buyers API properly requires authentication (status: {response.status_code})")
    
    def test_invoice_products_api_requires_auth(self):
        """Test that invoice-products API (for dropdown data) returns error without auth"""
        response = requests.get(f"{BASE_URL}/api/business-tools/invoice-products", timeout=10)
        # Should require authentication - 401/403/422 are valid responses for auth failure
        assert response.status_code in [401, 403, 422]
        print(f"✓ Invoice products API properly requires authentication (status: {response.status_code})")


class TestReactSelectCodeVerification:
    """Verify react-select implementation in the codebase"""
    
    def test_package_json_has_react_select(self):
        """Verify react-select is in package.json"""
        package_json_path = "/app/frontend/package.json"
        with open(package_json_path, 'r') as f:
            content = f.read()
        assert '"react-select"' in content
        assert '"^5.10.2"' in content or 'react-select":' in content
        print("✓ react-select is installed in package.json")
    
    def test_invoices_page_imports_react_select(self):
        """Verify react-select is imported in invoices page"""
        page_path = "/app/frontend/src/app/seller/business-tools/invoices/page.tsx"
        with open(page_path, 'r') as f:
            content = f.read()
        assert "import Select" in content
        assert "from 'react-select'" in content
        print("✓ react-select is imported in invoices page")
    
    def test_buyer_dropdown_uses_react_select(self):
        """Verify buyer dropdown uses Select component (not native <select>)"""
        page_path = "/app/frontend/src/app/seller/business-tools/invoices/page.tsx"
        with open(page_path, 'r') as f:
            content = f.read()
        
        # Check for Select<SelectOption> component for buyer
        assert "Select<SelectOption>" in content
        # Check for buyer-select inputId
        assert 'inputId="buyer-select"' in content
        # Check for isSearchable on buyer dropdown
        assert "isSearchable" in content
        print("✓ Buyer dropdown uses react-select component")
    
    def test_product_dropdown_uses_react_select(self):
        """Verify product dropdown uses Select component with custom formatting"""
        page_path = "/app/frontend/src/app/seller/business-tools/invoices/page.tsx"
        with open(page_path, 'r') as f:
            content = f.read()
        
        # Check for Select<ProductOption> component
        assert "Select<ProductOption>" in content
        # Check for product select inputId pattern
        assert 'inputId={`invoice-item-product-${idx}`}' in content
        # Check for formatOptionLabel
        assert "formatOptionLabel" in content
        print("✓ Product dropdown uses react-select with custom formatOptionLabel")
    
    def test_product_dropdown_shows_stock_info(self):
        """Verify product dropdown shows stock info in formatOptionLabel"""
        page_path = "/app/frontend/src/app/seller/business-tools/invoices/page.tsx"
        with open(page_path, 'r') as f:
            content = f.read()
        
        # Check that stock info is displayed
        assert "Avail:" in content
        assert "opt.stock" in content
        print("✓ Product dropdown shows stock info")
    
    def test_manual_entry_input_exists(self):
        """Verify manual entry input appears when no product is selected"""
        page_path = "/app/frontend/src/app/seller/business-tools/invoices/page.tsx"
        with open(page_path, 'r') as f:
            content = f.read()
        
        # Check for manual entry input that shows when productId is empty
        assert "!item.productId &&" in content
        assert 'placeholder="Manual entry"' in content
        assert 'data-testid={`invoice-item-name-${idx}`}' in content
        print("✓ Manual entry input exists and appears when no product selected")
    
    def test_dropdowns_are_clearable(self):
        """Verify both dropdowns have isClearable property"""
        page_path = "/app/frontend/src/app/seller/business-tools/invoices/page.tsx"
        with open(page_path, 'r') as f:
            content = f.read()
        
        # Count isClearable occurrences (should be at least 2: buyer and product)
        assert content.count("isClearable") >= 2
        print("✓ Both dropdowns have isClearable property")
    
    def test_custom_styles_defined(self):
        """Verify custom styles are defined for react-select"""
        page_path = "/app/frontend/src/app/seller/business-tools/invoices/page.tsx"
        with open(page_path, 'r') as f:
            content = f.read()
        
        # Check for selectStyles and productSelectStyles
        assert "const selectStyles: StylesConfig<SelectOption, false>" in content
        assert "const productSelectStyles: StylesConfig<ProductOption, false>" in content
        print("✓ Custom styles defined for react-select components")
    
    def test_gst_dropdown_is_native_select(self):
        """Verify GST% dropdown remains as native <select> (intentional)"""
        page_path = "/app/frontend/src/app/seller/business-tools/invoices/page.tsx"
        with open(page_path, 'r') as f:
            content = f.read()
        
        # Check for native select for GST
        assert '<select value={item.gstPercent}' in content
        assert 'data-testid={`invoice-item-gst-${idx}`}' in content
        print("✓ GST% dropdown uses native <select> (intentional)")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

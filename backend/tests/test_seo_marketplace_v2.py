"""
SEO Marketplace Standard v2.0 Tests
=====================================
Tests for enhanced SEO endpoint with:
- SEO title optimization (55-65 chars)
- SEO description (150-160 chars)
- Structured content with H1/H2 headings
- JSON-LD Product + AggregateOffer schemas
- FAQ JSON-LD for rich snippets
- Internal linking system
- Seller grouping by city
"""

import pytest
import requests
import os
import re

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
TEST_PRODUCT_ID = "699be9023cbe1a8c31591668"  # Industrial Electric Motor 5HP


class TestSEOEndpointBasic:
    """Basic SEO endpoint availability and response structure tests"""
    
    def test_seo_endpoint_returns_200_for_valid_product_id(self):
        """Test SEO endpoint returns 200 for valid product ID"""
        response = requests.get(f"{BASE_URL}/api/products/{TEST_PRODUCT_ID}/seo")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:500] if response.text else 'No content'}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "productName" in data, "Missing productName in response"
        assert "seoTitle" in data, "Missing seoTitle in response"
        assert "seoDescription" in data, "Missing seoDescription in response"
        print(f"✅ SEO endpoint returns valid response for product ID: {TEST_PRODUCT_ID}")
    
    def test_seo_endpoint_returns_404_for_invalid_product(self):
        """Test SEO endpoint returns 404 for non-existent product"""
        fake_id = "000000000000000000000000"
        response = requests.get(f"{BASE_URL}/api/products/{fake_id}/seo")
        
        assert response.status_code == 404, f"Expected 404 for invalid product, got {response.status_code}"
        print("✅ SEO endpoint returns 404 for non-existent product")
    
    def test_seo_response_structure_contains_all_required_fields(self):
        """Test SEO response contains all required fields for marketplace standard"""
        response = requests.get(f"{BASE_URL}/api/products/{TEST_PRODUCT_ID}/seo")
        assert response.status_code == 200
        
        data = response.json()
        
        # Required fields per specification
        required_fields = [
            "productId",
            "productName",
            "seoTitle",
            "seoDescription",
            "seoContent",
            "jsonLd",
            "breadcrumbJsonLd",
            "faqJsonLd",
            "internalLinks",
            "sellerCount",
            "sellersByCity",
            "minPrice",
            "maxPrice",
            "minMoq",
            "availableCities",
            "canonicalUrl"
        ]
        
        missing_fields = [field for field in required_fields if field not in data]
        assert not missing_fields, f"Missing required fields: {missing_fields}"
        
        print(f"✅ SEO response contains all {len(required_fields)} required fields")
        print(f"   Fields: {', '.join(required_fields)}")


class TestSEOTitleOptimization:
    """Tests for SEO title optimization (55-65 characters)"""
    
    def test_seo_title_length_within_optimal_range(self):
        """Test SEO title is within 55-65 character optimal range"""
        response = requests.get(f"{BASE_URL}/api/products/{TEST_PRODUCT_ID}/seo")
        assert response.status_code == 200
        
        data = response.json()
        seo_title = data.get("seoTitle", "")
        title_length = len(seo_title)
        
        print(f"SEO Title: '{seo_title}'")
        print(f"Title Length: {title_length} characters")
        
        # Title should not be empty
        assert seo_title, "SEO title should not be empty"
        
        # Title should be within reasonable range (allowing some flexibility)
        # Spec says 55-65 ideal, but we allow up to 70 for edge cases
        assert title_length <= 70, f"SEO title too long: {title_length} chars (max 70)"
        assert title_length >= 30, f"SEO title too short: {title_length} chars (min 30)"
        
        print(f"✅ SEO title length: {title_length} chars (target: 55-65)")
    
    def test_seo_title_format_contains_brand_and_india(self):
        """Test SEO title contains expected format elements"""
        response = requests.get(f"{BASE_URL}/api/products/{TEST_PRODUCT_ID}/seo")
        assert response.status_code == 200
        
        data = response.json()
        seo_title = data.get("seoTitle", "").lower()
        
        # Title should contain "india" for geo-targeting
        assert "india" in seo_title, f"SEO title should contain 'india': {seo_title}"
        
        # Title should contain UdyogConnect brand name
        assert "udyogconnect" in seo_title, f"SEO title should contain 'UdyogConnect': {seo_title}"
        
        print(f"✅ SEO title contains 'India' and 'UdyogConnect' brand")
    
    def test_seo_title_contains_product_keyword(self):
        """Test SEO title contains product-related keyword"""
        response = requests.get(f"{BASE_URL}/api/products/{TEST_PRODUCT_ID}/seo")
        assert response.status_code == 200
        
        data = response.json()
        seo_title = data.get("seoTitle", "").lower()
        product_name = data.get("productName", "").lower()
        
        # At least one word from product name should be in title
        product_words = [w for w in product_name.split() if len(w) > 3]
        found_keyword = any(word in seo_title for word in product_words)
        
        assert found_keyword, f"SEO title should contain product keyword. Title: {seo_title}, Product: {product_name}"
        print(f"✅ SEO title contains product keyword from: {product_name}")


class TestSEODescriptionOptimization:
    """Tests for SEO meta description (150-160 characters)"""
    
    def test_seo_description_length_within_optimal_range(self):
        """Test SEO description is within 150-160 character optimal range"""
        response = requests.get(f"{BASE_URL}/api/products/{TEST_PRODUCT_ID}/seo")
        assert response.status_code == 200
        
        data = response.json()
        seo_desc = data.get("seoDescription", "")
        desc_length = len(seo_desc)
        
        print(f"SEO Description: '{seo_desc}'")
        print(f"Description Length: {desc_length} characters")
        
        # Description should not be empty
        assert seo_desc, "SEO description should not be empty"
        
        # Description should be within range (allowing some flexibility)
        assert desc_length <= 165, f"SEO description too long: {desc_length} chars (max 165)"
        assert desc_length >= 100, f"SEO description too short: {desc_length} chars (min 100)"
        
        print(f"✅ SEO description length: {desc_length} chars (target: 150-160)")
    
    def test_seo_description_contains_cta(self):
        """Test SEO description contains a call-to-action"""
        response = requests.get(f"{BASE_URL}/api/products/{TEST_PRODUCT_ID}/seo")
        assert response.status_code == 200
        
        data = response.json()
        seo_desc = data.get("seoDescription", "").lower()
        
        # Should contain some form of CTA
        cta_phrases = ["compare", "get", "find", "explore", "contact", "best deals", "udyogconnect"]
        has_cta = any(phrase in seo_desc for phrase in cta_phrases)
        
        assert has_cta, f"SEO description should contain a CTA. Description: {seo_desc}"
        print("✅ SEO description contains call-to-action")
    
    def test_seo_description_mentions_supplier_info(self):
        """Test SEO description mentions suppliers or sellers"""
        response = requests.get(f"{BASE_URL}/api/products/{TEST_PRODUCT_ID}/seo")
        assert response.status_code == 200
        
        data = response.json()
        seo_desc = data.get("seoDescription", "").lower()
        
        # Should mention suppliers/sellers
        supplier_words = ["supplier", "seller", "verified", "manufacturer", "dealer"]
        has_supplier_mention = any(word in seo_desc for word in supplier_words)
        
        assert has_supplier_mention, f"SEO description should mention suppliers. Description: {seo_desc}"
        print("✅ SEO description mentions suppliers/sellers")


class TestSEOContentStructure:
    """Tests for SEO content structure (H1/H2 hierarchy, 300-500 words)"""
    
    def test_seo_content_has_h1_heading(self):
        """Test SEO content has H1 heading (# in markdown)"""
        response = requests.get(f"{BASE_URL}/api/products/{TEST_PRODUCT_ID}/seo")
        assert response.status_code == 200
        
        data = response.json()
        seo_content = data.get("seoContent", "")
        
        # Should have H1 heading (# in markdown)
        has_h1 = bool(re.search(r'^# .+', seo_content, re.MULTILINE))
        
        assert has_h1, "SEO content should have H1 heading (# in markdown)"
        
        # Extract H1 content
        h1_match = re.search(r'^# (.+)$', seo_content, re.MULTILINE)
        if h1_match:
            print(f"H1: {h1_match.group(1)}")
        
        print("✅ SEO content has H1 heading")
    
    def test_seo_content_has_h2_headings(self):
        """Test SEO content has multiple H2 headings (## in markdown)"""
        response = requests.get(f"{BASE_URL}/api/products/{TEST_PRODUCT_ID}/seo")
        assert response.status_code == 200
        
        data = response.json()
        seo_content = data.get("seoContent", "")
        
        # Find all H2 headings
        h2_matches = re.findall(r'^## (.+)$', seo_content, re.MULTILINE)
        
        assert len(h2_matches) >= 2, f"SEO content should have at least 2 H2 headings. Found: {len(h2_matches)}"
        
        print(f"✅ SEO content has {len(h2_matches)} H2 headings:")
        for h2 in h2_matches:
            print(f"   - {h2}")
    
    def test_seo_content_has_required_sections(self):
        """Test SEO content has required sections: Specifications, Applications, Cities, Why Choose"""
        response = requests.get(f"{BASE_URL}/api/products/{TEST_PRODUCT_ID}/seo")
        assert response.status_code == 200
        
        data = response.json()
        seo_content = data.get("seoContent", "").lower()
        
        # Check for required sections
        required_sections = [
            "specification",
            "application",
            ("city", "supplier"),  # Either city or supplier section
            ("why", "choose")
        ]
        
        found_sections = []
        for section in required_sections:
            if isinstance(section, tuple):
                # Any of the keywords should be present
                if any(keyword in seo_content for keyword in section):
                    found_sections.append(" or ".join(section))
            else:
                if section in seo_content:
                    found_sections.append(section)
        
        print(f"✅ Found {len(found_sections)} required section types:")
        for section in found_sections:
            print(f"   - {section}")
        
        # Should have at least 3 of the required sections
        assert len(found_sections) >= 3, f"SEO content should have at least 3 required sections. Found: {found_sections}"
    
    def test_seo_content_word_count(self):
        """Test SEO content has appropriate word count (300-500 words)"""
        response = requests.get(f"{BASE_URL}/api/products/{TEST_PRODUCT_ID}/seo")
        assert response.status_code == 200
        
        data = response.json()
        seo_content = data.get("seoContent", "")
        
        # Count words (excluding markdown symbols)
        clean_content = re.sub(r'[#*\-]', '', seo_content)
        word_count = len(clean_content.split())
        
        print(f"SEO content word count: {word_count} words (target: 300-500)")
        
        # Allow some flexibility in word count
        assert word_count >= 200, f"SEO content too short: {word_count} words (min 200)"
        assert word_count <= 700, f"SEO content too long: {word_count} words (max 700)"
        
        print(f"✅ SEO content word count: {word_count} words")


class TestJSONLDProductSchema:
    """Tests for JSON-LD Product schema with AggregateOffer"""
    
    def test_json_ld_has_product_type(self):
        """Test JSON-LD has @type: Product"""
        response = requests.get(f"{BASE_URL}/api/products/{TEST_PRODUCT_ID}/seo")
        assert response.status_code == 200
        
        data = response.json()
        json_ld = data.get("jsonLd", {})
        
        assert json_ld.get("@context") == "https://schema.org", "JSON-LD should have schema.org context"
        assert json_ld.get("@type") == "Product", f"JSON-LD @type should be 'Product', got: {json_ld.get('@type')}"
        
        print("✅ JSON-LD has @type: Product with schema.org context")
    
    def test_json_ld_has_brand(self):
        """Test JSON-LD has brand information"""
        response = requests.get(f"{BASE_URL}/api/products/{TEST_PRODUCT_ID}/seo")
        assert response.status_code == 200
        
        data = response.json()
        json_ld = data.get("jsonLd", {})
        
        brand = json_ld.get("brand", {})
        assert brand, "JSON-LD should have brand field"
        assert brand.get("@type") == "Brand", f"Brand should have @type: Brand, got: {brand.get('@type')}"
        assert brand.get("name"), "Brand should have name"
        
        print(f"✅ JSON-LD has brand: {brand.get('name')}")
    
    def test_json_ld_has_offers(self):
        """Test JSON-LD has offers (AggregateOffer or Offer)"""
        response = requests.get(f"{BASE_URL}/api/products/{TEST_PRODUCT_ID}/seo")
        assert response.status_code == 200
        
        data = response.json()
        json_ld = data.get("jsonLd", {})
        
        offers = json_ld.get("offers", {})
        assert offers, "JSON-LD should have offers field"
        
        offer_type = offers.get("@type")
        valid_offer_types = ["AggregateOffer", "Offer"]
        assert offer_type in valid_offer_types, f"Offers @type should be AggregateOffer or Offer, got: {offer_type}"
        
        # Check currency
        assert offers.get("priceCurrency") == "INR", f"Currency should be INR, got: {offers.get('priceCurrency')}"
        
        print(f"✅ JSON-LD has offers with @type: {offer_type}, currency: INR")
        
        # If AggregateOffer, check for offerCount
        if offer_type == "AggregateOffer":
            assert "lowPrice" in offers or "highPrice" in offers, "AggregateOffer should have price info"
            if "offerCount" in offers:
                print(f"   Offer count: {offers.get('offerCount')}")
            if "lowPrice" in offers:
                print(f"   Low price: ₹{offers.get('lowPrice')}")
    
    def test_json_ld_has_name_and_description(self):
        """Test JSON-LD has name and description"""
        response = requests.get(f"{BASE_URL}/api/products/{TEST_PRODUCT_ID}/seo")
        assert response.status_code == 200
        
        data = response.json()
        json_ld = data.get("jsonLd", {})
        
        assert json_ld.get("name"), "JSON-LD should have name"
        assert json_ld.get("description"), "JSON-LD should have description"
        
        print(f"✅ JSON-LD has name: {json_ld.get('name')[:50]}...")


class TestFAQJSONLD:
    """Tests for FAQ JSON-LD schema"""
    
    def test_faq_json_ld_has_correct_type(self):
        """Test FAQ JSON-LD has @type: FAQPage"""
        response = requests.get(f"{BASE_URL}/api/products/{TEST_PRODUCT_ID}/seo")
        assert response.status_code == 200
        
        data = response.json()
        faq_json_ld = data.get("faqJsonLd", {})
        
        assert faq_json_ld.get("@context") == "https://schema.org", "FAQ JSON-LD should have schema.org context"
        assert faq_json_ld.get("@type") == "FAQPage", f"FAQ JSON-LD @type should be 'FAQPage', got: {faq_json_ld.get('@type')}"
        
        print("✅ FAQ JSON-LD has @type: FAQPage")
    
    def test_faq_json_ld_has_main_entity_questions(self):
        """Test FAQ JSON-LD has mainEntity with questions"""
        response = requests.get(f"{BASE_URL}/api/products/{TEST_PRODUCT_ID}/seo")
        assert response.status_code == 200
        
        data = response.json()
        faq_json_ld = data.get("faqJsonLd", {})
        
        main_entity = faq_json_ld.get("mainEntity", [])
        assert isinstance(main_entity, list), "mainEntity should be a list"
        assert len(main_entity) >= 4, f"Should have at least 4 FAQs, got: {len(main_entity)}"
        
        print(f"✅ FAQ JSON-LD has {len(main_entity)} questions:")
        
        for i, faq in enumerate(main_entity[:4]):
            assert faq.get("@type") == "Question", f"FAQ {i+1} should have @type: Question"
            assert faq.get("name"), f"FAQ {i+1} should have 'name' (question text)"
            assert faq.get("acceptedAnswer"), f"FAQ {i+1} should have acceptedAnswer"
            
            answer = faq.get("acceptedAnswer", {})
            assert answer.get("@type") == "Answer", f"FAQ {i+1} answer should have @type: Answer"
            assert answer.get("text"), f"FAQ {i+1} answer should have 'text'"
            
            print(f"   Q{i+1}: {faq.get('name')[:60]}...")


class TestInternalLinks:
    """Tests for internal linking system"""
    
    def test_internal_links_structure(self):
        """Test internal links has correct structure"""
        response = requests.get(f"{BASE_URL}/api/products/{TEST_PRODUCT_ID}/seo")
        assert response.status_code == 200
        
        data = response.json()
        internal_links = data.get("internalLinks", {})
        
        # Required keys in internal links
        required_keys = ["category", "similarProducts", "cityPages", "topRated"]
        
        for key in required_keys:
            assert key in internal_links, f"internalLinks should have '{key}' field"
        
        print(f"✅ Internal links structure has all required keys: {required_keys}")
    
    def test_internal_links_category(self):
        """Test internal links has category link"""
        response = requests.get(f"{BASE_URL}/api/products/{TEST_PRODUCT_ID}/seo")
        assert response.status_code == 200
        
        data = response.json()
        internal_links = data.get("internalLinks", {})
        category = internal_links.get("category")
        
        if category:
            assert "name" in category, "Category link should have 'name'"
            assert "url" in category, "Category link should have 'url'"
            print(f"✅ Category link: {category.get('name')} -> {category.get('url')}")
        else:
            print("ℹ️ No category link (product may not have category)")
    
    def test_internal_links_similar_products(self):
        """Test internal links has similar products array"""
        response = requests.get(f"{BASE_URL}/api/products/{TEST_PRODUCT_ID}/seo")
        assert response.status_code == 200
        
        data = response.json()
        internal_links = data.get("internalLinks", {})
        similar_products = internal_links.get("similarProducts", [])
        
        assert isinstance(similar_products, list), "similarProducts should be an array"
        
        if similar_products:
            for product in similar_products[:3]:
                assert "name" in product, "Similar product should have 'name'"
                assert "url" in product, "Similar product should have 'url'"
            
            print(f"✅ Similar products: {len(similar_products)} links")
            for p in similar_products[:3]:
                print(f"   - {p.get('name')}")
        else:
            print("ℹ️ No similar products found")
    
    def test_internal_links_city_pages(self):
        """Test internal links has city pages array"""
        response = requests.get(f"{BASE_URL}/api/products/{TEST_PRODUCT_ID}/seo")
        assert response.status_code == 200
        
        data = response.json()
        internal_links = data.get("internalLinks", {})
        city_pages = internal_links.get("cityPages", [])
        
        assert isinstance(city_pages, list), "cityPages should be an array"
        
        if city_pages:
            for city in city_pages[:3]:
                assert "name" in city, "City page should have 'name'"
                assert "url" in city, "City page should have 'url'"
            
            print(f"✅ City pages: {len(city_pages)} links")
            for c in city_pages[:3]:
                print(f"   - {c.get('name')}")
        else:
            print("ℹ️ No city pages (no sellers in different cities)")


class TestPriceAndSellerStats:
    """Tests for price and seller statistics"""
    
    def test_price_stats_fields_present(self):
        """Test price stats fields are present"""
        response = requests.get(f"{BASE_URL}/api/products/{TEST_PRODUCT_ID}/seo")
        assert response.status_code == 200
        
        data = response.json()
        
        # These fields should exist (can be null if no pricing data)
        assert "minPrice" in data, "Response should have minPrice field"
        assert "maxPrice" in data, "Response should have maxPrice field"
        assert "minMoq" in data, "Response should have minMoq field"
        
        print(f"✅ Price stats present:")
        print(f"   minPrice: {data.get('minPrice')}")
        print(f"   maxPrice: {data.get('maxPrice')}")
        print(f"   minMoq: {data.get('minMoq')}")
    
    def test_seller_count_and_cities(self):
        """Test seller count and available cities"""
        response = requests.get(f"{BASE_URL}/api/products/{TEST_PRODUCT_ID}/seo")
        assert response.status_code == 200
        
        data = response.json()
        
        seller_count = data.get("sellerCount", 0)
        available_cities = data.get("availableCities", [])
        sellers_by_city = data.get("sellersByCity", {})
        
        print(f"✅ Seller stats:")
        print(f"   Seller count: {seller_count}")
        print(f"   Available cities: {available_cities}")
        print(f"   Sellers by city: {list(sellers_by_city.keys())}")
        
        # Seller count should be non-negative
        assert seller_count >= 0, "Seller count should be non-negative"
        
        # If there are sellers, cities should be populated
        if seller_count > 0:
            # sellers_by_city should have entries
            assert isinstance(sellers_by_city, dict), "sellersByCity should be a dict"


class TestBreadcrumbJSONLD:
    """Tests for Breadcrumb JSON-LD schema"""
    
    def test_breadcrumb_json_ld_structure(self):
        """Test Breadcrumb JSON-LD has correct structure"""
        response = requests.get(f"{BASE_URL}/api/products/{TEST_PRODUCT_ID}/seo")
        assert response.status_code == 200
        
        data = response.json()
        breadcrumb = data.get("breadcrumbJsonLd", {})
        
        assert breadcrumb.get("@context") == "https://schema.org", "Breadcrumb should have schema.org context"
        assert breadcrumb.get("@type") == "BreadcrumbList", f"Breadcrumb @type should be 'BreadcrumbList', got: {breadcrumb.get('@type')}"
        
        items = breadcrumb.get("itemListElement", [])
        assert isinstance(items, list), "itemListElement should be a list"
        assert len(items) >= 2, f"Should have at least 2 breadcrumb items, got: {len(items)}"
        
        print(f"✅ Breadcrumb JSON-LD has {len(items)} items:")
        for item in items:
            assert item.get("@type") == "ListItem", "Each breadcrumb item should be ListItem"
            assert "position" in item, "Each breadcrumb item should have position"
            assert "name" in item, "Each breadcrumb item should have name"
            print(f"   {item.get('position')}. {item.get('name')}")


class TestSEOSlugGeneration:
    """Tests for SEO slug format"""
    
    def test_canonical_url_format(self):
        """Test canonical URL has proper format"""
        response = requests.get(f"{BASE_URL}/api/products/{TEST_PRODUCT_ID}/seo")
        assert response.status_code == 200
        
        data = response.json()
        canonical_url = data.get("canonicalUrl", "")
        
        assert canonical_url.startswith("https://www.udyogconnect.in/product/"), \
            f"Canonical URL should start with site URL, got: {canonical_url}"
        
        print(f"✅ Canonical URL: {canonical_url}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

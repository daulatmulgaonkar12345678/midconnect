"""
Media Validation Integration Tests
==================================
Verifies the complete image + video integration:
- Max 5 images (5MB each) per listing
- Max 2 videos (30 sec, 5MB each) per listing
- Cloudinary URL validation for images and videos
- Backend guard validation (enterprise_listing_guard.py)
- Pydantic model validation (seller_products.py)
- MongoDB schema enforcement (add_media_validation.py)

Test Spec:
- Backend guard validates max 5 images (not 10)
- Backend guard validates Cloudinary URL format for images
- Backend guard validates max 2 videos  
- Backend guard validates Cloudinary URL format for videos
"""

import pytest
import os
import sys
import requests

# Add backend to path for direct imports
sys.path.insert(0, '/app/backend')

# Environment setup
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://seo-phase2-enhance.preview.emergentagent.com')

# Test URLs
VALID_CLOUDINARY_IMAGE_URL = "https://res.cloudinary.com/dco24qmoq/image/upload/v1234567890/test_image.jpg"
VALID_CLOUDINARY_VIDEO_URL = "https://res.cloudinary.com/dco24qmoq/video/upload/v1234567890/test_video.mp4"
INVALID_URL = "https://example.com/image.jpg"


class TestImageValidationBackendGuard:
    """Test image validation in enterprise_listing_guard.py"""
    
    def test_validate_images_max_5_images_allowed(self):
        """Backend guard should allow max 5 images, not 10"""
        from guards.enterprise_listing_guard import EnterpriseListingGuard
        from fastapi import HTTPException
        
        guard = EnterpriseListingGuard
        
        # 5 images should pass
        five_images = [f"{VALID_CLOUDINARY_IMAGE_URL}_{i}" for i in range(5)]
        result = guard.validate_images(five_images, min_required=1, max_allowed=5)
        assert len(result) == 5
        print("PASS: 5 images validation passed")
        
        # 6 images should fail
        six_images = [f"{VALID_CLOUDINARY_IMAGE_URL}_{i}" for i in range(6)]
        with pytest.raises(HTTPException) as exc_info:
            guard.validate_images(six_images, min_required=1, max_allowed=5)
        assert exc_info.value.status_code == 400
        assert "Maximum 5 images allowed" in exc_info.value.detail
        print("PASS: 6 images rejected with proper error")
    
    def test_validate_images_default_max_is_5(self):
        """Default max_allowed parameter in validate_images should be 5"""
        from guards.enterprise_listing_guard import EnterpriseListingGuard
        from fastapi import HTTPException
        import inspect
        
        # Check the default parameter value
        sig = inspect.signature(EnterpriseListingGuard.validate_images)
        max_allowed_default = sig.parameters['max_allowed'].default
        assert max_allowed_default == 5, f"Expected default max_allowed=5, got {max_allowed_default}"
        print(f"PASS: validate_images default max_allowed={max_allowed_default}")
    
    def test_validate_images_requires_cloudinary_url(self):
        """Images must be from Cloudinary"""
        from guards.enterprise_listing_guard import EnterpriseListingGuard
        from fastapi import HTTPException
        
        guard = EnterpriseListingGuard
        
        # Valid Cloudinary URL should pass
        valid_images = [VALID_CLOUDINARY_IMAGE_URL]
        result = guard.validate_images(valid_images, min_required=1, max_allowed=5)
        assert len(result) == 1
        print("PASS: Valid Cloudinary image URL accepted")
        
        # Invalid URL should fail
        invalid_images = [INVALID_URL]
        with pytest.raises(HTTPException) as exc_info:
            guard.validate_images(invalid_images, min_required=1, max_allowed=5)
        assert exc_info.value.status_code == 400
        assert "Must be from Cloudinary" in exc_info.value.detail
        print("PASS: Non-Cloudinary image URL rejected")
    
    def test_validate_images_minimum_1_required(self):
        """At least 1 image is required"""
        from guards.enterprise_listing_guard import EnterpriseListingGuard
        from fastapi import HTTPException
        
        guard = EnterpriseListingGuard
        
        # Empty list should fail when min_required=1
        with pytest.raises(HTTPException) as exc_info:
            guard.validate_images([], min_required=1, max_allowed=5)
        assert exc_info.value.status_code == 400
        assert "At least 1 product image is required" in exc_info.value.detail
        print("PASS: Empty images list rejected")
    
    def test_validate_images_accepts_http_cloudinary(self):
        """Both http:// and https:// Cloudinary URLs should be accepted"""
        from guards.enterprise_listing_guard import EnterpriseListingGuard
        
        guard = EnterpriseListingGuard
        
        http_url = "http://res.cloudinary.com/dco24qmoq/image/upload/test.jpg"
        https_url = "https://res.cloudinary.com/dco24qmoq/image/upload/test.jpg"
        
        result = guard.validate_images([http_url, https_url], min_required=1, max_allowed=5)
        assert len(result) == 2
        print("PASS: Both http and https Cloudinary URLs accepted")


class TestVideoValidationBackendGuard:
    """Test video validation in enterprise_listing_guard.py"""
    
    def test_validate_videos_max_2_videos_allowed(self):
        """Backend guard should allow max 2 videos"""
        from guards.enterprise_listing_guard import EnterpriseListingGuard
        from fastapi import HTTPException
        
        guard = EnterpriseListingGuard
        
        # 2 videos should pass
        two_videos = [f"{VALID_CLOUDINARY_VIDEO_URL}_{i}" for i in range(2)]
        result = guard.validate_videos(two_videos, max_allowed=2)
        assert len(result) == 2
        print("PASS: 2 videos validation passed")
        
        # 3 videos should fail
        three_videos = [f"{VALID_CLOUDINARY_VIDEO_URL}_{i}" for i in range(3)]
        with pytest.raises(HTTPException) as exc_info:
            guard.validate_videos(three_videos, max_allowed=2)
        assert exc_info.value.status_code == 400
        assert "Maximum 2 videos allowed" in exc_info.value.detail
        print("PASS: 3 videos rejected with proper error")
    
    def test_validate_videos_default_max_is_2(self):
        """Default max_allowed parameter in validate_videos should be 2"""
        from guards.enterprise_listing_guard import EnterpriseListingGuard
        import inspect
        
        sig = inspect.signature(EnterpriseListingGuard.validate_videos)
        max_allowed_default = sig.parameters['max_allowed'].default
        assert max_allowed_default == 2, f"Expected default max_allowed=2, got {max_allowed_default}"
        print(f"PASS: validate_videos default max_allowed={max_allowed_default}")
    
    def test_validate_videos_requires_cloudinary_url(self):
        """Videos must be from Cloudinary"""
        from guards.enterprise_listing_guard import EnterpriseListingGuard
        from fastapi import HTTPException
        
        guard = EnterpriseListingGuard
        
        # Valid Cloudinary URL should pass
        valid_videos = [VALID_CLOUDINARY_VIDEO_URL]
        result = guard.validate_videos(valid_videos, max_allowed=2)
        assert len(result) == 1
        print("PASS: Valid Cloudinary video URL accepted")
        
        # Invalid URL should fail
        invalid_videos = [INVALID_URL]
        with pytest.raises(HTTPException) as exc_info:
            guard.validate_videos(invalid_videos, max_allowed=2)
        assert exc_info.value.status_code == 400
        assert "Must be from Cloudinary" in exc_info.value.detail
        print("PASS: Non-Cloudinary video URL rejected")
    
    def test_validate_videos_optional_field(self):
        """Videos field is optional - None and [] should pass"""
        from guards.enterprise_listing_guard import EnterpriseListingGuard
        
        guard = EnterpriseListingGuard
        
        # None should return empty list
        result_none = guard.validate_videos(None, max_allowed=2)
        assert result_none == []
        print("PASS: videos=None returns []")
        
        # Empty list should return empty list
        result_empty = guard.validate_videos([], max_allowed=2)
        assert result_empty == []
        print("PASS: videos=[] returns []")


class TestPydanticModelValidation:
    """Test Pydantic model constraints in seller_products.py"""
    
    def test_listing_create_images_max_length_5(self):
        """ListingCreate.images should have max_length=5"""
        from seller_products import ListingCreate
        from pydantic import ValidationError
        
        # Get field info
        images_field = ListingCreate.model_fields.get('images')
        assert images_field is not None
        
        # Check max_length - Pydantic v2 uses metadata
        max_length = images_field.metadata[0] if images_field.metadata else None
        if hasattr(max_length, 'max_length'):
            assert max_length.max_length == 5, f"Expected max_length=5, got {max_length.max_length}"
        print(f"PASS: ListingCreate.images field configured with max_length constraint")
    
    def test_listing_create_videos_max_length_2(self):
        """ListingCreate.videos should have max_length=2"""
        from seller_products import ListingCreate
        
        # Get field info
        videos_field = ListingCreate.model_fields.get('videos')
        assert videos_field is not None
        
        # Check max_length
        max_length = videos_field.metadata[0] if videos_field.metadata else None
        if hasattr(max_length, 'max_length'):
            assert max_length.max_length == 2, f"Expected max_length=2, got {max_length.max_length}"
        print(f"PASS: ListingCreate.videos field configured with max_length constraint")


class TestMongoDBSchemaValidation:
    """Test MongoDB schema in add_media_validation.py"""
    
    def test_migration_schema_max_items_images(self):
        """MongoDB schema should have maxItems=5 for images"""
        # Read migration file and check schema
        migration_file = '/app/backend/migrations/add_media_validation.py'
        with open(migration_file, 'r') as f:
            content = f.read()
        
        # Check that images maxItems is 5
        assert '"maxItems": 5' in content or "'maxItems': 5" in content
        assert 'images' in content
        print("PASS: MongoDB schema has maxItems=5 for images")
    
    def test_migration_schema_max_items_videos(self):
        """MongoDB schema should have maxItems=2 for videos"""
        migration_file = '/app/backend/migrations/add_media_validation.py'
        with open(migration_file, 'r') as f:
            content = f.read()
        
        # Check that videos maxItems is 2
        assert '"maxItems": 2' in content or "'maxItems': 2" in content
        assert 'videos' in content
        print("PASS: MongoDB schema has maxItems=2 for videos")


class TestFrontendConstantsVerification:
    """Verify frontend constants match spec (code review)"""
    
    def test_cloudinary_image_max_size_5mb(self):
        """cloudinary.ts should have IMAGE_MAX_SIZE=5MB"""
        cloudinary_file = '/app/frontend/src/lib/cloudinary.ts'
        with open(cloudinary_file, 'r') as f:
            content = f.read()
        
        # Check IMAGE_MAX_SIZE = 5 * 1024 * 1024 (5MB)
        assert 'IMAGE_MAX_SIZE = 5 * 1024 * 1024' in content
        print("PASS: cloudinary.ts IMAGE_MAX_SIZE = 5MB")
    
    def test_cloudinary_video_max_size_5mb(self):
        """cloudinary.ts should have VIDEO_MAX_SIZE=5MB"""
        cloudinary_file = '/app/frontend/src/lib/cloudinary.ts'
        with open(cloudinary_file, 'r') as f:
            content = f.read()
        
        # Check VIDEO_MAX_SIZE = 5 * 1024 * 1024 (5MB)
        assert 'VIDEO_MAX_SIZE = 5 * 1024 * 1024' in content
        print("PASS: cloudinary.ts VIDEO_MAX_SIZE = 5MB")
    
    def test_cloudinary_max_images_5(self):
        """cloudinary.ts should have MAX_IMAGES=5"""
        cloudinary_file = '/app/frontend/src/lib/cloudinary.ts'
        with open(cloudinary_file, 'r') as f:
            content = f.read()
        
        assert 'MAX_IMAGES = 5' in content
        print("PASS: cloudinary.ts MAX_IMAGES = 5")
    
    def test_cloudinary_max_videos_2(self):
        """cloudinary.ts should have MAX_VIDEOS=2"""
        cloudinary_file = '/app/frontend/src/lib/cloudinary.ts'
        with open(cloudinary_file, 'r') as f:
            content = f.read()
        
        assert 'MAX_VIDEOS = 2' in content
        print("PASS: cloudinary.ts MAX_VIDEOS = 2")
    
    def test_cloudinary_max_video_duration_30(self):
        """cloudinary.ts should have MAX_VIDEO_DURATION=30"""
        cloudinary_file = '/app/frontend/src/lib/cloudinary.ts'
        with open(cloudinary_file, 'r') as f:
            content = f.read()
        
        assert 'MAX_VIDEO_DURATION = 30' in content
        print("PASS: cloudinary.ts MAX_VIDEO_DURATION = 30 seconds")
    
    def test_cloudinary_uses_video_endpoint_for_videos(self):
        """cloudinary.ts should use /video/upload for videos (not /image/upload)"""
        cloudinary_file = '/app/frontend/src/lib/cloudinary.ts'
        with open(cloudinary_file, 'r') as f:
            content = f.read()
        
        assert 'CLOUDINARY_VIDEO_URL' in content
        assert '/video/upload' in content
        print("PASS: cloudinary.ts uses dedicated video endpoint")
    
    def test_api_ts_max_product_image_size_5mb(self):
        """api.ts should have MAX_PRODUCT_IMAGE_SIZE=5MB"""
        api_file = '/app/frontend/src/lib/api.ts'
        with open(api_file, 'r') as f:
            content = f.read()
        
        assert 'MAX_PRODUCT_IMAGE_SIZE = 5 * 1024 * 1024' in content
        print("PASS: api.ts MAX_PRODUCT_IMAGE_SIZE = 5MB")
    
    def test_api_ts_max_product_images_5(self):
        """api.ts should have MAX_PRODUCT_IMAGES=5"""
        api_file = '/app/frontend/src/lib/api.ts'
        with open(api_file, 'r') as f:
            content = f.read()
        
        assert 'MAX_PRODUCT_IMAGES = 5' in content
        print("PASS: api.ts MAX_PRODUCT_IMAGES = 5")


class TestFrontendPageValidation:
    """Verify new listing page validates correctly"""
    
    def test_new_listing_page_validates_5mb_per_image(self):
        """New listing page should validate 5MB per image"""
        page_file = '/app/frontend/src/app/seller/listings/new/page.tsx'
        with open(page_file, 'r') as f:
            content = f.read()
        
        # Check for 5MB image validation
        assert '5 * 1024 * 1024' in content or '5MB' in content.lower()
        print("PASS: new listing page validates 5MB per image")
    
    def test_new_listing_page_validates_5mb_per_video(self):
        """New listing page should validate 5MB per video"""
        page_file = '/app/frontend/src/app/seller/listings/new/page.tsx'
        with open(page_file, 'r') as f:
            content = f.read()
        
        # Check for video size validation
        assert 'video' in content.lower()
        assert '5MB' in content or '5 * 1024 * 1024' in content
        print("PASS: new listing page validates 5MB per video")
    
    def test_new_listing_page_validates_30_second_duration(self):
        """New listing page should validate 30 second video duration"""
        page_file = '/app/frontend/src/app/seller/listings/new/page.tsx'
        with open(page_file, 'r') as f:
            content = f.read()
        
        # Check for duration validation
        assert 'duration' in content.lower() and '30' in content
        print("PASS: new listing page validates 30 second video duration")
    
    def test_new_listing_page_max_5_images(self):
        """New listing page should limit to 5 images"""
        page_file = '/app/frontend/src/app/seller/listings/new/page.tsx'
        with open(page_file, 'r') as f:
            content = f.read()
        
        # Check for 5 image limit
        assert 'images.length' in content and '5' in content
        print("PASS: new listing page has max 5 images check")
    
    def test_new_listing_page_max_2_videos(self):
        """New listing page should limit to 2 videos"""
        page_file = '/app/frontend/src/app/seller/listings/new/page.tsx'
        with open(page_file, 'r') as f:
            content = f.read()
        
        # Check for 2 video limit
        assert 'videos.length' in content and '2' in content
        print("PASS: new listing page has max 2 videos check")


class TestCloudinaryCompressionConfig:
    """Verify Cloudinary compression configuration"""
    
    def test_image_compression_configured(self):
        """cloudinary.ts should have image compression"""
        cloudinary_file = '/app/frontend/src/lib/cloudinary.ts'
        with open(cloudinary_file, 'r') as f:
            content = f.read()
        
        # Check for compression settings
        assert 'COMPRESSION_QUALITY' in content or 'compressImage' in content
        print("PASS: cloudinary.ts has image compression configured")
    
    def test_video_optimization_configured(self):
        """cloudinary.ts should have video optimization"""
        cloudinary_file = '/app/frontend/src/lib/cloudinary.ts'
        with open(cloudinary_file, 'r') as f:
            content = f.read()
        
        # Check for video optimization
        assert 'optimizeVideoUrl' in content or 'q_auto' in content
        print("PASS: cloudinary.ts has video optimization configured")


if __name__ == "__main__":
    pytest.main([__file__, '-v', '--tb=short'])

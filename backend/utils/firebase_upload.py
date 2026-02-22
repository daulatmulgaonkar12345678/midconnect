"""
Firebase Image Upload Utility
=============================
Provides image upload functionality to Firebase Storage.
Returns Firebase URLs that are stored in MongoDB.

Usage:
- Categories: imageUrl field
- Products: coverImageUrl field
- Seller Listings: images[] array
- Users: profile.avatarUrl field
"""

import firebase_admin
from firebase_admin import storage
from datetime import datetime, timezone
import uuid
import base64
import re
from typing import Optional
import logging

logger = logging.getLogger(__name__)

def get_storage_bucket():
    """Get Firebase Storage bucket."""
    try:
        return storage.bucket()
    except Exception as e:
        logger.error(f"Failed to get storage bucket: {e}")
        return None

def upload_image_to_firebase(
    image_data: str,
    folder: str,
    filename: Optional[str] = None,
    content_type: str = "image/jpeg"
) -> Optional[str]:
    """
    Upload an image to Firebase Storage and return the public URL.
    
    Args:
        image_data: Base64 encoded image string (with or without data URI prefix)
        folder: Storage folder (e.g., "categories", "products", "listings", "users")
        filename: Optional custom filename (auto-generated if not provided)
        content_type: MIME type of the image
    
    Returns:
        Public URL of the uploaded image, or None if upload failed
    """
    try:
        bucket = get_storage_bucket()
        if not bucket:
            logger.error("Firebase Storage bucket not available")
            return None
        
        # Parse base64 data
        if "," in image_data:
            # Data URI format: data:image/jpeg;base64,/9j/4AAQ...
            header, base64_str = image_data.split(",", 1)
            # Extract content type from header
            if "image/" in header:
                match = re.search(r"image/([\w]+)", header)
                if match:
                    ext = match.group(1)
                    content_type = f"image/{ext}"
        else:
            base64_str = image_data
        
        # Decode base64
        image_bytes = base64.b64decode(base64_str)
        
        # Generate filename if not provided
        if not filename:
            ext = content_type.split("/")[-1]
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            unique_id = str(uuid.uuid4())[:8]
            filename = f"{timestamp}_{unique_id}.{ext}"
        
        # Full path in storage
        blob_path = f"{folder}/{filename}"
        blob = bucket.blob(blob_path)
        
        # Upload
        blob.upload_from_string(image_bytes, content_type=content_type)
        
        # Make publicly accessible
        blob.make_public()
        
        public_url = blob.public_url
        logger.info(f"Image uploaded successfully: {public_url}")
        
        return public_url
        
    except Exception as e:
        logger.error(f"Failed to upload image: {e}")
        return None

def upload_images_to_firebase(
    images: list,
    folder: str
) -> list:
    """
    Upload multiple images to Firebase Storage.
    
    Args:
        images: List of base64 encoded image strings
        folder: Storage folder
    
    Returns:
        List of public URLs (only successful uploads)
    """
    urls = []
    for i, image_data in enumerate(images):
        if not image_data:
            continue
        
        # Skip if already a URL
        if image_data.startswith("http://") or image_data.startswith("https://"):
            urls.append(image_data)
            continue
        
        url = upload_image_to_firebase(image_data, folder)
        if url:
            urls.append(url)
        else:
            logger.warning(f"Failed to upload image {i+1} of {len(images)}")
    
    return urls

def delete_image_from_firebase(image_url: str) -> bool:
    """
    Delete an image from Firebase Storage.
    
    Args:
        image_url: Public URL of the image to delete
    
    Returns:
        True if deletion was successful, False otherwise
    """
    try:
        bucket = get_storage_bucket()
        if not bucket:
            return False
        
        # Extract blob path from URL
        # URL format: https://storage.googleapis.com/bucket-name/folder/filename.jpg
        if "storage.googleapis.com" in image_url:
            parts = image_url.split("/")
            # Find the bucket name and get everything after it
            bucket_name = bucket.name
            bucket_index = parts.index(bucket_name) if bucket_name in parts else -1
            if bucket_index >= 0:
                blob_path = "/".join(parts[bucket_index + 1:])
                blob = bucket.blob(blob_path)
                blob.delete()
                logger.info(f"Image deleted successfully: {blob_path}")
                return True
        
        return False
        
    except Exception as e:
        logger.error(f"Failed to delete image: {e}")
        return False

def is_valid_image_url(url: str) -> bool:
    """Check if a string is a valid image URL."""
    if not url:
        return False
    return url.startswith("http://") or url.startswith("https://")

def is_base64_image(data: str) -> bool:
    """Check if a string is a base64 encoded image."""
    if not data:
        return False
    # Check for data URI prefix
    if data.startswith("data:image/"):
        return True
    # Check if it's valid base64 (rough check)
    try:
        if len(data) > 100:  # Images are typically large
            base64.b64decode(data[:100])  # Just check first 100 chars
            return True
    except:
        pass
    return False

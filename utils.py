import os
import sys
import logging

def setup_logger():
    """Set up log formatting for stdout."""
    logger = logging.getLogger("catalog_extractor")
    logger.setLevel(logging.INFO)
    
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
    return logger

def ensure_directories(base_dir):
    """Ensure that the output directory and images subdirectory exist."""
    output_dir = os.path.join(base_dir, "output")
    images_dir = os.path.join(output_dir, "images")
    
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(images_dir, exist_ok=True)
    
    return output_dir, images_dir

def validate_product(product):
    """
    Validates a product and returns a list of warnings/errors if fields are missing.
    Expected product keys: code, name, brand, price, description, image, page, confidence.
    """
    warnings = []
    
    # Check code
    if not product.get("code"):
        warnings.append("missing_code")
        
    # Check price
    price = product.get("price")
    if price is None or price <= 0:
        warnings.append("missing_price")
        
    # Check name
    if not product.get("name") or len(str(product.get("name")).strip()) < 2:
        warnings.append("missing_name")
        
    # Check image
    if not product.get("image"):
        warnings.append("missing_image")
        
    return warnings

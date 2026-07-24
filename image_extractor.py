import os
import fitz
import logging

logger = logging.getLogger("catalog_extractor")

class ImageExtractor:
    def __init__(self, images_dir):
        self.images_dir = images_dir
        
    def extract_or_render_image(self, parser, page, product_code, page_num):
        """
        Attempts to extract a unique product image from the page's images.
        If extraction fails or no unique product image is found, renders the left half of the page.
        Returns the relative path to the saved image file (e.g., 'images/KM-1727.jpg').
        """
        # Determine base filename (without extension)
        base_name = product_code if product_code else f"page_{page_num:03d}_product_001"
        
        # 1. Try to find a non-template image on the left side of the page
        images = page.get_images(full=True)
        product_xref = None
        
        for img in images:
            xref = img[0]
            if not parser.is_template_xref(xref):
                # Check coordinates
                rects = page.get_image_rects(xref)
                if rects:
                    r = rects[0]
                    # Product image is typically on the left side
                    if r.x0 < 500:
                        product_xref = xref
                        break
                        
        if product_xref:
            try:
                base_image = parser.doc.extract_image(product_xref)
                image_bytes = base_image["image"]
                ext = base_image["ext"]
                # Convert common extensions
                if ext == "jpeg":
                    ext = "jpg"
                    
                image_filename = f"{base_name}.{ext}"
                dest_path = os.path.join(self.images_dir, image_filename)
                
                with open(dest_path, "wb") as f:
                    f.write(image_bytes)
                    
                # Return relative path
                return f"images/{image_filename}"
            except Exception as e:
                logger.warning(f"Failed to extract image xref {product_xref} on page {page_num}: {e}. Falling back to rendering.")
                
        # 2. Fallback: Render the left side of the page (where the product image resides)
        try:
            # The page size is 960x540. The product image is on the left half [0, 0, 500, 540]
            clip_rect = fitz.Rect(0, 0, 500, 540)
            # Use a zoom matrix for higher quality (2x zoom = 150-144 DPI)
            matrix = fitz.Matrix(2.0, 2.0)
            pix = page.get_pixmap(clip=clip_rect, matrix=matrix)
            
            image_filename = f"{base_name}.jpg"
            dest_path = os.path.join(self.images_dir, image_filename)
            
            pix.save(dest_path)
            return f"images/{image_filename}"
        except Exception as e:
            logger.error(f"Failed to render page {page_num} region: {e}")
            return ""

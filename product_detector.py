import re
import logging

logger = logging.getLogger("catalog_extractor")

# Regex patterns
PRICE_REGEX = re.compile(r'(?:S/|S\s*/|/)\s*(\d+(?:\.\d+)?)', re.IGNORECASE)

CODE_PATTERNS = [
    # Match standard uppercase words with dashes and digits (e.g. ET-M1062-M16, AD-GK121, PRO-7, ET-E0621, BS-L3326-TG)
    re.compile(r'\b([A-Z0-9]{2,8}-[A-Z0-9]{1,8}(?:-[A-Z0-9]{1,8})*)\b'),
    # Match uppercase letters followed by digits (e.g. PC07, BT12, R7137, FP11527)
    re.compile(r'\b([A-Z]{1,4}\d{2,6}[A-Z0-9]*)\b'),
    # Match single letter followed by dash and digits (e.g. G-03, T-18)
    re.compile(r'\b([A-Z]-\d{2,4})\b')
]

KNOWN_BRANDS = ["ALDEEPO", "EWTTO", "GTX", "KASSEL", "BIG-GER", "BAIHUO", "MAGIC PRO", "MAX", "ALDEPO"]

def is_product_page(page):
    """
    Determines if a page is a product page based on text characteristics.
    Skips cover and category separator pages.
    """
    blocks = page.get_text("blocks")
    num_blocks = len(blocks)
    
    # Category separators and cover pages usually have very few blocks (<= 2)
    if num_blocks < 3:
        return False
        
    text = page.get_text("text")
    
    # Check for presence of description bullets
    has_bullet = '•' in text or 'PRODUCTO:' in text or 'MODELO:' in text or 'CARACTERÍSTICAS:' in text or 'MATERIAL:' in text
    
    # Check for price patterns
    has_price = PRICE_REGEX.search(text) is not None
    
    # Check for code patterns
    has_code = False
    for pat in CODE_PATTERNS:
        if pat.search(text):
            has_code = True
            break
            
    # A product page must have bullets or a combination of price and code
    if has_bullet:
        return True
    if has_price and has_code:
        return True
        
    return False

def parse_product(page, page_num):
    """
    Parses product details from page text blocks.
    Returns a dictionary matching the expected structure.
    """
    blocks = page.get_text("blocks")
    # Sort blocks top-to-bottom, left-to-right
    blocks = sorted(blocks, key=lambda b: (round(b[1] / 10), b[0]))
    
    price = None
    code = None
    brand = None
    description = ""
    name_candidates = []
    
    # Find price first and remove it from name candidates
    for b in blocks:
        text = b[4].strip()
        if not text:
            continue
            
        price_match = PRICE_REGEX.search(text)
        # If it's a short block containing price, or starts with a price prefix
        if price_match and (len(text) < 15 or text.lower().startswith('s/') or text.startswith('/')):
            try:
                price = float(price_match.group(1))
            except ValueError:
                pass
            
            clean_text = text.replace(price_match.group(0), '').strip()
            if clean_text:
                text = clean_text
            else:
                continue
                
        # Look for bullet points (description block)
        if '•' in text or 'PRODUCTO:' in text or 'MODELO:' in text or 'CARACTERÍSTICAS:' in text or 'MATERIAL:' in text:
            lines = text.split('\n')
            desc_lines = []
            name_lines = []
            in_desc = False
            for line in lines:
                l = line.strip()
                if not l:
                    continue
                if l.startswith('•') or l.startswith('PRODUCTO:') or l.startswith('MODELO:') or l.startswith('MARCA:') or l.startswith('MATERIAL:') or l.startswith('CARACTERISTICAS:'):
                    in_desc = True
                if in_desc:
                    desc_lines.append(l)
                else:
                    name_lines.append(l)
            if name_lines:
                name_candidates.append(" ".join(name_lines))
            description = "\n".join(desc_lines)
            continue
            
        # Extract code from this block if not already found
        found_code = None
        if not code:
            for pat in CODE_PATTERNS:
                m = pat.search(text)
                if m:
                    candidate = m.group(1)
                    # Skip if candidate matches a known brand name (case-insensitive, ignores dash)
                    is_brand = False
                    for b_name in KNOWN_BRANDS:
                        if candidate.upper() == b_name or candidate.upper().replace("-", "") == b_name.replace("-", ""):
                            is_brand = True
                            break
                    if not is_brand:
                        found_code = candidate
                        break
                        
        if found_code:
            code = found_code
            clean_text = text.replace(found_code, '').strip()
            if clean_text:
                name_candidates.append(clean_text)
        else:
            name_candidates.append(text)
            
    # Clean and parse brand and name candidates
    seen = set()
    cleaned_names = []
    for c in name_candidates:
        c_clean = c.replace('|', ' ').strip()
        if not c_clean:
            continue
            
        # Extract brand if candidate contains a known brand
        candidate_upper = c_clean.upper()
        for b_name in KNOWN_BRANDS:
            if b_name in candidate_upper:
                brand = b_name
                # Remove only the brand name case-insensitively
                c_clean = re.sub(re.escape(b_name), "", c_clean, flags=re.IGNORECASE).strip()
                c_clean = re.sub(r'\s+', ' ', c_clean).strip(" -|/")
                break
                
        if c_clean and c_clean not in seen:
            seen.add(c_clean)
            cleaned_names.append(c_clean)
            
    # Filter candidates: remove those that are substrings of other candidates
    final_candidates = []
    for c in cleaned_names:
        is_sub = False
        for other in cleaned_names:
            if c != other and c.lower() in other.lower():
                is_sub = True
                break
        if not is_sub:
            final_candidates.append(c)
            
    name = " ".join(final_candidates).strip()
    
    # Fallback to extract brand from description
    if not brand and description:
        # Search for pattern: • MARCA: ...
        brand_match = re.search(r'•\s*(?:MARCA|BRAND)\s*:\s*([^\n]+)', description, re.IGNORECASE)
        if brand_match:
            brand = brand_match.group(1).strip()
        else:
            # Check MODELO
            model_match = re.search(r'•\s*MODELO\s*:\s*([^\n]+)', description, re.IGNORECASE)
            if model_match:
                model_str = model_match.group(1).upper()
                for b_name in KNOWN_BRANDS:
                    if b_name in model_str:
                        brand = b_name
                        break
                        
    # Final name fallback: if name is empty but brand is set, name becomes the brand + category
    # Or if name is empty, try to get it from the code or description product field
    if not name:
        if description:
            prod_line_match = re.search(r'•\s*(?:PRODUCTO|PRODUCT)\s*:\s*([^\n]+)', description, re.IGNORECASE)
            if prod_line_match:
                name = prod_line_match.group(1).strip()
        if not name and brand:
            name = brand
        if not name:
            name = "PRODUCTO SIN NOMBRE"
            
    # Clean description
    description = description.strip()
    
    # Calculate confidence score
    confidence = 1.0
    if not code:
        confidence -= 0.15
    if not price:
        confidence -= 0.20
    if not brand:
        confidence -= 0.10
    if not description:
        confidence -= 0.15
    if name == "PRODUCTO SIN NOMBRE":
        confidence -= 0.25
        
    confidence = max(0.1, min(1.0, round(confidence, 2)))
    
    # Return structured dict
    return {
        "code": code,
        "name": name,
        "brand": brand,
        "price": price,
        "description": description,
        "image": "",  # Filled by image_extractor
        "page": page_num,
        "confidence": confidence
    }

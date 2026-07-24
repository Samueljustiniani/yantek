import logging

logger = logging.getLogger("catalog_extractor")

def get_completeness_score(product):
    """
    Computes a score based on how many fields are populated.
    Fields check: code, name, brand, price, description, image.
    """
    score = 0
    if product.get("code"):
        score += 1
    if product.get("name") and product.get("name") != "PRODUCTO SIN NOMBRE":
        score += 1
    if product.get("brand"):
        score += 1
    if product.get("price") is not None and product.get("price") > 0:
        score += 1
    if product.get("description"):
        score += 1
    if product.get("image"):
        score += 1
    return score

def deduplicate_products(products):
    """
    Groups products by code and resolves conflicts by keeping the most complete record.
    Returns (unique_products_list, duplicates_log_list).
    """
    grouped = {} # code -> list of products
    no_code_products = []
    
    for p in products:
        code = p.get("code")
        if not code:
            no_code_products.append(p)
        else:
            if code not in grouped:
                grouped[code] = []
            grouped[code].append(p)
            
    unique_products = []
    duplicates_log = []
    
    for code, group in grouped.items():
        if len(group) == 1:
            unique_products.append(group[0])
            continue
            
        # Sort group by completeness score (descending), description length (descending), page number (ascending)
        sorted_group = sorted(
            group,
            key=lambda x: (
                get_completeness_score(x),
                len(x.get("description") or ""),
                -x.get("page", 0)
            ),
            reverse=True
        )
        
        kept = sorted_group[0]
        unique_products.append(kept)
        
        # Log others as duplicates
        for discarded in sorted_group[1:]:
            duplicates_log.append({
                "code": code,
                "kept_page": kept.get("page"),
                "discarded_page": discarded.get("page"),
                "kept_record": kept,
                "discarded_record": discarded
            })
            
    # Combine unique products with code and products without code
    all_unique = unique_products + no_code_products
    # Sort final list by page number
    all_unique = sorted(all_unique, key=lambda x: x.get("page", 0))
    
    logger.info(f"Deduplication completed. Reduced {len(products)} products to {len(all_unique)} unique products. Found {len(duplicates_log)} duplicates.")
    
    return all_unique, duplicates_log

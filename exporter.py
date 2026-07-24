import os
import json
import csv
import logging

logger = logging.getLogger("catalog_extractor")

def export_to_json(data, file_path):
    """Write data to a JSON file."""
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"Successfully exported JSON to {file_path}")
    except Exception as e:
        logger.error(f"Failed to export JSON to {file_path}: {e}")

def export_to_csv(products, file_path):
    """Write products to a CSV file."""
    fieldnames = ["code", "name", "brand", "price", "description", "image", "page", "confidence"]
    try:
        with open(file_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for p in products:
                # Ensure only required fields are written to CSV
                row = {k: p.get(k, "") for k in fieldnames}
                writer.writerow(row)
        logger.info(f"Successfully exported CSV to {file_path}")
    except Exception as e:
        logger.error(f"Failed to export CSV to {file_path}: {e}")

def export_all(products, output_dir, errors_log, duplicates_log, report):
    """Saves all outputs to the specified output directory."""
    # Define file paths
    json_path = os.path.join(output_dir, "products.json")
    csv_path = os.path.join(output_dir, "products.csv")
    errors_path = os.path.join(output_dir, "errors.json")
    duplicates_path = os.path.join(output_dir, "duplicates.json")
    report_path = os.path.join(output_dir, "report.json")
    
    # Save products datasets
    export_to_json(products, json_path)
    export_to_csv(products, csv_path)
    
    # Save logs
    export_to_json(errors_log, errors_path)
    export_to_json(duplicates_log, duplicates_path)
    
    # Compile statistics and save report
    total_products = len(products)
    with_images = sum(1 for p in products if p.get("image"))
    without_images = total_products - with_images
    
    with_price = sum(1 for p in products if p.get("price") is not None and p.get("price") > 0)
    without_price = total_products - with_price
    
    with_code = sum(1 for p in products if p.get("code"))
    without_code = total_products - with_code
    
    # Update report dictionary
    report["products_found"] = total_products
    report["products_with_images"] = with_images
    report["products_without_images"] = without_images
    report["products_with_price"] = with_price
    report["products_without_price"] = without_price
    report["products_with_code"] = with_code
    report["products_without_code"] = without_code
    report["errors"] = len(errors_log)
    
    export_to_json(report, report_path)

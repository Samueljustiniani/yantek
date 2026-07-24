import os
import sys
import time
import argparse
import json
import logging

import utils
from parser import PDFParser
import product_detector
from image_extractor import ImageExtractor
import deduplicator
import exporter

# Initialize logger
logger = utils.setup_logger()

def parse_arguments():
    parser = argparse.ArgumentParser(description="PDF Product Catalog Extractor")
    parser.add_argument("pdf_path", type=str, help="Path to the PDF file")
    parser.add_argument("--test", type=int, default=None, help="Process only N product pages for testing")
    parser.add_argument("--resume", action="store_true", help="Resume processing from last saved state")
    return parser.parse_args()

def main():
    args = parse_arguments()
    pdf_path = args.pdf_path
    
    # 1. Setup paths
    base_dir = os.path.dirname(os.path.abspath(__file__))
    # If the PDF path is relative, resolve it relative to current working directory
    if not os.path.isabs(pdf_path):
        pdf_path = os.path.abspath(pdf_path)
        
    if not os.path.exists(pdf_path):
        logger.error(f"PDF file not found at: {pdf_path}")
        sys.exit(1)
        
    output_dir, images_dir = utils.ensure_directories(base_dir)
    progress_file = os.path.join(output_dir, ".progress.json")
    
    # 2. Initialize Parser and open PDF
    pdf_parser = PDFParser(pdf_path)
    pdf_parser.open()
    total_pages = len(pdf_parser)
    
    # 3. Setup state variables
    start_page = 1
    accumulated_time = 0.0
    products = []
    errors_log = []
    
    # 4. Handle resume mode if requested
    if args.resume and os.path.exists(progress_file):
        try:
            with open(progress_file, "r", encoding="utf-8") as f:
                state = json.load(f)
                start_page = state.get("last_processed_page", 0) + 1
                accumulated_time = state.get("elapsed_time", 0.0)
                products = state.get("products", [])
                errors_log = state.get("errors_log", [])
            logger.info(f"Resuming execution from page {start_page}. Loaded {len(products)} products and {len(errors_log)} errors from state.")
        except Exception as e:
            logger.warning(f"Failed to load progress state file: {e}. Starting from page 1.")
            
    # Initialize Image Extractor
    image_extractor = ImageExtractor(images_dir)
    
    start_time = time.time()
    products_found_in_session = 0
    test_limit_reached = False
    
    logger.info(f"Starting parsing loop. Range: page {start_page} to {total_pages}")
    
    # 5. Extraction loop
    for page_num in range(start_page, total_pages + 1):
        # Calculate current elapsed time
        current_elapsed = time.time() - start_time + accumulated_time
        
        # Display progress in stdout as requested: "Procesando página X/Y | Productos encontrados: Z"
        # Using print with flush=True to show clear progress
        print(f"Procesando página {page_num}/{total_pages} | Productos encontrados: {len(products)}", flush=True)
        
        page = pdf_parser.get_page(page_num)
        
        # Check if page matches product characteristics
        if product_detector.is_product_page(page):
            # Parse product text fields
            product = product_detector.parse_product(page, page_num)
            
            # Extract and assign image
            img_path = image_extractor.extract_or_render_image(
                pdf_parser, page, product["code"], page_num
            )
            product["image"] = img_path
            
            # Validate product fields
            warnings = utils.validate_product(product)
            if warnings:
                errors_log.append({
                    "page": page_num,
                    "code": product["code"],
                    "warnings": warnings,
                    "record": product
                })
                
            products.append(product)
            products_found_in_session += 1
            
            # Check test limit
            if args.test and products_found_in_session >= args.test:
                logger.info(f"Test mode limit of {args.test} products reached on page {page_num}.")
                test_limit_reached = True
                
        # Save progress state dynamically after each page
        state = {
            "last_processed_page": page_num,
            "elapsed_time": current_elapsed,
            "products": products,
            "errors_log": errors_log
        }
        with open(progress_file, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False)
            
        if test_limit_reached:
            break
            
    # Calculate final elapsed time
    total_elapsed_time = time.time() - start_time + accumulated_time
    
    logger.info(f"Extraction loop completed. Extracted {len(products)} raw products.")
    
    # 6. Deduplication phase
    unique_products, duplicates_log = deduplicator.deduplicate_products(products)
    
    # 7. Compile report and export all results
    report = {
        "total_pages": total_pages,
        "pages_processed": page_num,
        "products_found": len(unique_products),
        "products_with_images": 0,    # Filled by exporter
        "products_without_images": 0, # Filled by exporter
        "products_with_price": 0,     # Filled by exporter
        "products_without_price": 0,  # Filled by exporter
        "products_with_code": 0,      # Filled by exporter
        "products_without_code": 0,   # Filled by exporter
        "errors": 0,                  # Filled by exporter
        "processing_time_seconds": round(total_elapsed_time, 2)
    }
    
    exporter.export_all(unique_products, output_dir, errors_log, duplicates_log, report)
    
    # Clean up progress file on complete run (not on test run or interrupted run)
    if not args.test and page_num == total_pages:
        try:
            os.remove(progress_file)
            logger.info("Progress state file removed upon complete successful extraction.")
        except OSError as e:
            logger.warning(f"Failed to delete progress file: {e}")
            
    print("\nPROCESAMIENTO FINALIZADO CON ÉXITO")
    print(f"Total productos únicos: {len(unique_products)}")
    print(f"Total advertencias/errores: {len(errors_log)}")
    print(f"Total duplicados detectados: {len(duplicates_log)}")
    print(f"Tiempo de ejecución: {report['processing_time_seconds']} segundos")

if __name__ == "__main__":
    main()

import fitz
import collections
import logging

logger = logging.getLogger("catalog_extractor")

class PDFParser:
    def __init__(self, pdf_path):
        self.pdf_path = pdf_path
        self.doc = None
        self.template_xrefs = set()
        
    def open(self):
        """Open the PDF document and count image xref occurrences to find templates."""
        try:
            self.doc = fitz.open(self.pdf_path)
            logger.info(f"Opened PDF with {len(self.doc)} pages.")
            self._detect_template_images()
        except Exception as e:
            logger.error(f"Failed to open PDF {self.pdf_path}: {e}")
            raise
            
    def close(self):
        if self.doc:
            self.doc.close()
            
    def __len__(self):
        return len(self.doc) if self.doc else 0
        
    def get_page(self, page_num):
        """Get page by 1-based page number."""
        return self.doc[page_num - 1]
        
    def _detect_template_images(self):
        """
        Count occurrences of image xrefs across all pages.
        Any image referenced on more than 3 pages is considered a layout template.
        """
        xref_counts = collections.Counter()
        
        for page_idx in range(len(self.doc)):
            page = self.doc[page_idx]
            # page.get_images() returns a list of tuples, the first element is xref
            for img in page.get_images():
                xref = img[0]
                xref_counts[xref] += 1
                
        # Filter template xrefs
        for xref, count in xref_counts.items():
            if count > 3:
                self.template_xrefs.add(xref)
                
        logger.info(f"Detected {len(self.template_xrefs)} template/layout image xrefs out of {len(xref_counts)} total xrefs.")

    def is_template_xref(self, xref):
        return xref in self.template_xrefs

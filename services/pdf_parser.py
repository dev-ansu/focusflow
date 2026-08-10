import os
import pymupdf as fitz

class PDFParser:
    @staticmethod
    def get_info(file_path: str):
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")
        
        doc = fitz.open(file_path)
        size = os.path.getsize(file_path)
        pages = len(doc)
        doc.close()
        return {
            "title": os.path.basename(file_path),
            "file_path": file_path,
            "size_bytes": size,
            "pages": pages
        }

    @staticmethod
    def extract_text_from_page(file_path: str, page_num: int) -> str:
        doc = fitz.open(file_path)
        text = doc[page_num].get_text("text") if page_num < len(doc) else ""
        doc.close()
        return text
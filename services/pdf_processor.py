import os
import tempfile
from PyPDF2 import PdfReader
from typing import Optional, Tuple


class PDFProcessor:
    @staticmethod
    def process_pdf(
        content: bytes, start_page: Optional[int] = None, end_page: Optional[int] = None
    ) -> str:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            temp_file.write(content)
            temp_file_path = temp_file.name

        try:
            pdf_reader = PdfReader(temp_file_path)
            total_pages = len(pdf_reader.pages)

            if start_page is None and end_page is None:
                start_page = 0
                end_page = total_pages
            else:
                start_page = max(0, (start_page or 1) - 1)
                end_page = min(total_pages, end_page or total_pages)

            text_content = ""
            for page_num in range(start_page, end_page):
                text_content += pdf_reader.pages[page_num].extract_text()

            return text_content
        finally:
            os.unlink(temp_file_path)

"""
PDF processor for extracting text from PDF documents using PyMuPDF.
"""
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


class PDFProcessor:
    """
    Handles PDF text extraction and processing.
    """

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 100):
        """
        Initialize the PDF processor.

        Args:
            chunk_size: Maximum number of words per chunk
            chunk_overlap: Number of overlapping words between chunks
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def extract_text(self, file_path: str) -> Optional[str]:
        """
        Extract text content from a PDF file.

        Args:
            file_path: Path to the PDF file

        Returns:
            Extracted text content, or None if extraction fails
        """
        if not os.path.exists(file_path):
            logger.error(f"PDF file not found: {file_path}")
            return None

        try:
            import fitz  # PyMuPDF (lazy import: avoids DLL issues at app startup)

            doc = fitz.open(file_path)
            text = ""

            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                page_text = page.get_text()
                text += page_text + "\n"

            doc.close()
            logger.info(f"Extracted {len(text)} characters from {file_path}")
            return text.strip()

        except Exception as e:
            logger.error(f"Error extracting text from PDF {file_path}: {e}")
            return None

    def chunk_text(self, text: str) -> list[str]:
        """
        Split text into overlapping chunks.

        Args:
            text: Text to chunk

        Returns:
            List of text chunks
        """
        if not text:
            return []

        words = text.split()
        chunks = []

        for i in range(0, len(words), self.chunk_size - self.chunk_overlap):
            chunk_words = words[i:i + self.chunk_size]
            if chunk_words:
                chunk = " ".join(chunk_words)
                chunks.append(chunk)

        logger.info(f"Created {len(chunks)} chunks from text")
        return chunks
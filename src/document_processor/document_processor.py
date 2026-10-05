from .pdf_extractor import extract_text_from_pdf
from .ocr import extract_text_with_ocr_retry


def process_document(pdf_path: str) -> str:

    text = extract_text_from_pdf(
        pdf_path
    )

    if text.strip():

        print(
            "Digital PDF detected. "
            "Using extracted text."
        )

        return text

    print(
        "No text found. Running OCR..."
    )

    text = extract_text_with_ocr_retry(
        pdf_path
    )

    return text
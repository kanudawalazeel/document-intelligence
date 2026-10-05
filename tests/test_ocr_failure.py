from document_processor.ocr import extract_text_with_ocr_retry


PDF_PATH = "evaluation/documents/invoice_21.pdf"


def fake_ocr_failure(*args, **kwargs):
    raise RuntimeError(
        "Simulated OCR engine failure"
    )


# Temporarily replace the OCR extraction function
import document_processor.ocr as ocr_module

ocr_module.extract_text_from_scanned_pdf = fake_ocr_failure


try:
    extract_text_with_ocr_retry(
        PDF_PATH,
        max_attempts=2
    )

    print("\nUnexpected result: OCR did not fail.")

except RuntimeError as error:
    print("\n========== OCR FAILURE TEST ==========")
    print("Expected OCR failure occurred.")
    print(f"Error: {error}")
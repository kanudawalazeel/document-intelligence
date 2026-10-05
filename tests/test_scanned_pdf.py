from document_processor.ocr import extract_text_from_scanned_pdf


pdf_path = "data/input/Scanned-Invoice.pdf"

text = extract_text_from_scanned_pdf(pdf_path)

print("========== OCR TEXT ==========")
print(text)
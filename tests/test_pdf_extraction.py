from document_processor.pdf_extractor import extract_text_from_pdf


pdf_path = "data/input/invoice_01.pdf"

text = extract_text_from_pdf(pdf_path)

print("========== EXTRACTED TEXT ==========")
print(text)
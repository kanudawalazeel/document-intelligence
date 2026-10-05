from document_processor.ocr import extract_text_from_image


image_path = "data/input/invoice_image.png"

text = extract_text_from_image(image_path)

print("========== OCR TEXT ==========")
print(text)
import pytesseract
from PIL import Image


image_path = "data/input/scann_invoice.png"

image = Image.open(image_path)

text = pytesseract.image_to_string(image)

print("========== OCR TEXT ==========")
print(text)
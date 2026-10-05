from pdf2image import convert_from_path


pdf_path = "data/input/test_scanned_2.pdf"

images = convert_from_path(
    pdf_path,
    dpi=200,
    poppler_path=r"C:\Users\user\Desktop\poppler\Library\bin"
)

print(f"Number of pages: {len(images)}")

images[0].save(
    "data/output/poppler_page_.png"
)

print("PDF converted to image successfully!")
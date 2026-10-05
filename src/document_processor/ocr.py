import re
import pymupdf
import pytesseract

from PIL import Image
from io import BytesIO


def is_ocr_text_valid(text: str) -> bool:
    """
    Check whether OCR produced usable text.

    This checks:
    1. Text is not empty.
    2. Text has enough characters.
    3. Text contains enough alphanumeric characters.
    4. Text contains a reasonable number of numeric values.
       This is important for invoices because quantities,
       prices, dates, totals, etc. are usually present.
    """

    if not text or not text.strip():
        return False

    cleaned_text = text.strip()

    # Basic text-length check
    if len(cleaned_text) < 30:
        return False

    # Check amount of useful alphanumeric content
    alphanumeric_count = sum(
        char.isalnum()
        for char in cleaned_text
    )

    if alphanumeric_count < 20:
        return False

    # Invoice documents normally contain numbers:
    # dates, invoice numbers, quantities, prices, totals, etc.
    number_matches = re.findall(
        r"\d+(?:[.,]\d+)*",
        cleaned_text
    )

    if len(number_matches) < 5:
        print("OCR text contains too few numeric values.")
        return False

    return True


def extract_text_from_scanned_pdf(
    pdf_path: str,
    dpi: int = 300
) -> str:
    """
    Extract text from a scanned PDF using Tesseract OCR.

    Uses:
    - 300 DPI by default for better invoice quality.
    - PSM 6, which generally works better for structured
      document/table-style pages than the default OCR mode.
    """

    document = pymupdf.open(pdf_path)

    extracted_text = ""

    for page_number, page in enumerate(
        document,
        start=1
    ):
        print(
            f"Processing page {page_number} "
            f"with OCR at {dpi} DPI..."
        )

        # Render PDF page as a high-resolution image
        pixmap = page.get_pixmap(
            dpi=dpi,
            colorspace=pymupdf.csRGB
        )

        image_bytes = pixmap.tobytes("png")

        image = Image.open(
            BytesIO(image_bytes)
        )

        # OCR configuration:
        # PSM 6 = assume a single uniform block of text.
        # This is useful for structured invoice pages.
        text = pytesseract.image_to_string(
            image,
            config="--psm 6"
        )

        extracted_text += (
            f"\n===== PAGE {page_number} =====\n"
            f"{text}\n"
        )

    document.close()

    return extracted_text


def extract_text_with_ocr_retry(
    pdf_path: str,
    max_attempts: int = 2
) -> str:
    """
    Run OCR with retry.

    Attempt 1 -> 300 DPI
    Attempt 2 -> 400 DPI

    If OCR produces unusable text, the second attempt
    uses a higher resolution.
    """

    dpi_values = [300, 400]

    for attempt in range(
        1,
        max_attempts + 1
    ):
        dpi = dpi_values[
            min(
                attempt - 1,
                len(dpi_values) - 1
            )
        ]

        print(
            f"\nOCR attempt "
            f"{attempt}/{max_attempts}"
        )

        try:
            text = extract_text_from_scanned_pdf(
                pdf_path,
                dpi=dpi
            )

            if is_ocr_text_valid(text):
                print(
                    f"OCR successful on "
                    f"attempt {attempt}."
                )

                return text

            print(
                "OCR completed, but extracted "
                "text quality is too low."
            )

        except Exception as error:
            print(
                f"OCR attempt {attempt} failed: "
                f"{error}"
            )

    raise RuntimeError(
        "OCR_FAILED: Unable to extract usable text "
        "from the scanned document after all OCR attempts."
    )
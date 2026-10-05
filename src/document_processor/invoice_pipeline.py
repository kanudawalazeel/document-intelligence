from .document_processor import process_document
from .groq_extractor import extract_invoice
from .validators import validate_invoice


def process_invoice(
    pdf_path: str
):

    print(
        "\n========== "
        "STEP 1: DOCUMENT PROCESSING "
        "=========="
    )

    text = process_document(
        pdf_path
    )

    if not text.strip():

        raise ValueError(
            "No text could be extracted "
            "from the document."
        )

    print(
        "\nDocument text extracted successfully."
    )

    print(
        "\n========== "
        "STEP 2: LLM EXTRACTION "
        "=========="
    )

    invoice = extract_invoice(
        text
    )

    print(
        "\nLLM extraction completed."
    )

    print(
        "\n========== "
        "STEP 3: BUSINESS VALIDATION "
        "=========="
    )

    errors = validate_invoice(
        invoice
    )

    if errors:

        print(
            "\nInvoice validation failed."
        )

        for error in errors:

            print(
                f" - {error}"
            )

        return {
            "success": False,
            "errors": errors,
            "invoice": invoice.model_dump()
        }

    print(
        "\nInvoice passed all validations."
    )

    return {
        "success": True,
        "errors": [],
        "invoice": invoice.model_dump()
    }
from document_processor.invoice_pipeline import process_invoice


PDF_PATH = "evaluation/documents/invoice_21.pdf"


result = process_invoice(PDF_PATH)


print("\n========== FINAL RESULT ==========")

print(f"Success: {result['success']}")


print("\nErrors:")

if result["errors"]:
    for error in result["errors"]:
        print(f"- {error}")
else:
    print("No errors")


print("\nInvoice:")

if result["invoice"]:
    print(result["invoice"])
else:
    print("No invoice data")


print("\nPerformance Metrics:")

if result.get("metrics"):

    metrics = result["metrics"]

    print(
        f"Digital Extraction Time: "
        f"{metrics['digital_extraction_time_sec']} sec"
    )

    print(
        f"OCR Time: "
        f"{metrics['ocr_time_sec']} sec"
    )

    print(
        f"LLM Processing Time: "
        f"{metrics['llm_time_sec']} sec"
    )

    print(
        f"Validation Time: "
        f"{metrics['validation_time_sec']} sec"
    )

    print(
        f"OCR Retry Count: "
        f"{metrics['ocr_retry_count']}"
    )

    print(
        f"LLM Retry Count: "
        f"{metrics['llm_retry_count']}"
    )

    print(
        f"Validation Retry Count: "
        f"{metrics['validation_retry_count']}"
    )

    print(
        f"Fallback Used: "
        f"{metrics['fallback_used']}"
    )

    print(
        f"Total Processing Time: "
        f"{metrics['total_processing_time_sec']} sec"
    )

else:
    print("No metrics available.")
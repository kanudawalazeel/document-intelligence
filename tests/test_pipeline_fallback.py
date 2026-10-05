import document_processor.groq_extractor as extractor


class FakeLLMManager:

    def __init__(self):
        self.retry_count = 1
        self.fallback_used = True

    def reset_metrics(self):
        self.retry_count = 0
        self.fallback_used = False

    def generate(self, prompt: str) -> str:

        print(
            "\nSimulated Gemini fallback "
            "returned successful invoice."
        )

        return """
        {
            "vendor_name": "ABC Supplies",
            "invoice_number": "INV-001",
            "invoice_date": "2026-09-30",
            "due_date": "2026-10-30",
            "line_items": [
                {
                    "description": "Office Supplies",
                    "quantity": 2,
                    "unit_price": 100.00
                }
            ],
            "subtotal": 200.00,
            "tax": 20.00,
            "total": 220.00
        }
        """


# Replace the real manager only for this test.
fake_manager = FakeLLMManager()

extractor.llm_manager = fake_manager


# Import pipeline AFTER replacing the manager.
from document_processor.invoice_pipeline import process_invoice


PDF_PATH = "evaluation/documents/invoice_01.pdf"


try:

    result = process_invoice(
        PDF_PATH
    )

    print(
        "\n========== FULL PIPELINE FALLBACK TEST =========="
    )

    print(
        f"\nSuccess: "
        f"{result['success']}"
    )

    print(
        "\nInvoice:"
    )

    print(
        result["invoice"]
    )

    print(
        "\nPerformance Metrics:"
    )

    metrics = result["metrics"]

    print(
        f"LLM Retry Count: "
        f"{metrics['llm_retry_count']}"
    )

    print(
        f"Fallback Used: "
        f"{metrics['fallback_used']}"
    )

    print(
        f"Total Processing Time: "
        f"{metrics['total_processing_time_sec']} sec"
    )

except Exception as error:

    print(
        "\n========== TEST FAILED =========="
    )

    print(
        f"Error: {error}"
    )
import document_processor.invoice_pipeline as pipeline
import document_processor.groq_extractor as extractor


class FakeLLMManager:

    def __init__(self):
        self.call_count = 0
        self.retry_count = 0
        self.fallback_used = False

    def reset_metrics(self):
        self.call_count = 0
        self.retry_count = 0
        self.fallback_used = False

    def generate(self, prompt: str) -> str:

        self.call_count += 1

        print(
            f"\nFake LLM call #{self.call_count}"
        )

        # First response:
        # Valid JSON + valid schema,
        # but business rules are violated.
        if self.call_count == 1:

            print(
                "Returning invoice with "
                "business validation errors..."
            )

            return """
            {
                "vendor_name": "ABC Supplies",
                "invoice_number": "INV-001",
                "invoice_date": "2026-10-05",
                "due_date": "2026-09-30",
                "line_items": [
                    {
                        "description": "Office Supplies",
                        "quantity": -2,
                        "unit_price": 100.00
                    }
                ],
                "subtotal": 200.00,
                "tax": 20.00,
                "total": 250.00
            }
            """

        # Second response:
        # Corrected invoice.
        print(
            "Returning business-rule-corrected JSON..."
        )

        return """
        {
            "vendor_name": "ABC Supplies",
            "invoice_number": "INV-001",
            "invoice_date": "2026-09-30",
            "due_date": "2026-10-05",
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


# Replace the real LLM manager only for this test.
fake_manager = FakeLLMManager()

extractor.llm_manager = fake_manager


# IMPORTANT:
# invoice_pipeline's correction code imports call_llm
# from groq_extractor, so the fake manager is used
# through that module.
PDF_PATH = "evaluation/documents/invoice_01.pdf"


try:

    result = pipeline.process_invoice(
        PDF_PATH,
        max_validation_attempts=2
    )

    print(
        "\n========== BUSINESS VALIDATION TEST =========="
    )

    print(
        f"Success: {result['success']}"
    )

    print(
        "\nErrors:"
    )

    if result["errors"]:

        for error in result["errors"]:
            print(f"- {error}")

    else:

        print("No validation errors.")

    print(
        "\nFinal Invoice:"
    )

    print(
        result["invoice"]
    )

    print(
        "\nValidation Retries:"
    )

    print(
        result["metrics"]["validation_retry_count"]
    )


except Exception as error:

    print(
        "\n========== TEST FAILED =========="
    )

    print(
        f"Error: {error}"
    )
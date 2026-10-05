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

        # First response: intentionally invalid JSON
        if self.call_count == 1:

            print(
                "Returning intentionally invalid JSON..."
            )

            return """
            {
                "vendor_name": "ABC Supplies",
                "invoice_number": "INV-001",
                "invoice_date": "2026-09-30",
                "total": 1500.00
            """

        # Second response: repaired valid JSON
        print(
            "Returning repaired valid JSON..."
        )

        return """
        {
            "vendor_name": "ABC Supplies",
            "invoice_number": "INV-001",
            "invoice_date": "2026-09-30",
            "due_date": null,
            "line_items": [
                {
                    "description": "Office Supplies",
                    "quantity": 1,
                    "unit_price": 1500.00
                }
            ],
            "subtotal": 1500.00,
            "tax": 0.00,
            "total": 1500.00
        }
        """


# Replace the real LLM manager only for this test
extractor.llm_manager = FakeLLMManager()


TEST_TEXT = """
ABC Supplies

Invoice Number: INV-001
Invoice Date: 2026-09-30

Office Supplies
Quantity: 1
Unit Price: 1500.00

Subtotal: 1500.00
Tax: 0.00
Total: 1500.00
"""


try:

    invoice = extractor.extract_invoice(
        TEST_TEXT
    )

    print(
        "\n========== INVALID JSON TEST =========="
    )

    print(
        "JSON repair succeeded."
    )

    print(
        "\nFinal Invoice:"
    )

    print(
        invoice.model_dump()
    )

except Exception as error:

    print(
        "\n========== TEST FAILED =========="
    )

    print(
        f"Error: {error}"
    )
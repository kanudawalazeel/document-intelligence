from document_processor.llm_manager import LLMManager


class FakeGroqProvider:

    def generate(self, prompt: str) -> str:
        raise RuntimeError(
            "Simulated Groq connection failure"
        )


class FakeGeminiProvider:

    def generate(self, prompt: str) -> str:
        print("\nSimulated Gemini fallback succeeded.")
        return '{"status": "fallback_success"}'


manager = LLMManager(
    primary_retries=2
)

# Replace real providers with simulated providers
manager.primary = FakeGroqProvider()
manager.fallback = FakeGeminiProvider()


try:

    result = manager.generate(
        "Test LLM fallback"
    )

    print("\n========== LLM FALLBACK TEST ==========")

    print(
        f"Result: {result}"
    )

    print(
        f"Retry Count: "
        f"{manager.retry_count}"
    )

    print(
        f"Fallback Used: "
        f"{manager.fallback_used}"
    )

except Exception as error:

    print(
        "\n========== TEST FAILED =========="
    )

    print(
        f"Error: {error}"
    )
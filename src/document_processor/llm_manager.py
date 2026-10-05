import time

from .groq_provider import GroqProvider
from .gemini_provider import GeminiProvider


class LLMManager:

    def __init__(self, primary_retries: int = 2):
        self.primary = GroqProvider()
        self.fallback = GeminiProvider()

        self.primary_retries = primary_retries
        self.retry_count = 0
        self.fallback_used = False

    def reset_metrics(self):
        self.retry_count = 0
        self.fallback_used = False

    @staticmethod
    def is_retryable_error(error: Exception) -> bool:
        error_text = str(error).lower()

        retryable_keywords = [
            "timeout",
            "timed out",
            "rate limit",
            "429",
            "500",
            "502",
            "503",
            "504",
            "connection",
            "connection reset",
            "connection refused",
            "temporarily unavailable",
            "service unavailable",
        ]

        return any(
            keyword in error_text
            for keyword in retryable_keywords
        )

    def _call_primary(self, prompt: str) -> str:

        for attempt in range(
            1,
            self.primary_retries + 1
        ):

            try:
                print(
                    f"\n========== GROQ ATTEMPT "
                    f"{attempt}/{self.primary_retries} =========="
                )

                response = self.primary.generate(prompt)

                print("\nPrimary LLM succeeded.")

                return response

            except Exception as error:

                print("\nPrimary LLM error:")
                print(error)

                if not self.is_retryable_error(error):

                    print(
                        "\nError classified as NON-RETRYABLE."
                    )

                    raise RuntimeError(
                        f"PRIMARY_LLM_NON_RETRYABLE: {error}"
                    )

                print(
                    "\nError classified as RETRYABLE."
                )

                if attempt < self.primary_retries:

                    self.retry_count += 1

                    wait_time = 2 ** attempt

                    print(
                        f"Retrying Groq in "
                        f"{wait_time} seconds..."
                    )

                    time.sleep(wait_time)

                else:

                    print(
                        "\nGroq retry attempts exhausted."
                    )

                    raise RuntimeError(
                        f"PRIMARY_LLM_RETRY_EXHAUSTED: {error}"
                    )

        raise RuntimeError(
            "PRIMARY_LLM_FAILED"
        )

    def _call_fallback(self, prompt: str) -> str:

        try:

            print(
                "\n========== GEMINI FALLBACK =========="
            )

            self.fallback_used = True

            response = self.fallback.generate(prompt)

            print(
                "\nGemini fallback succeeded."
            )

            return response

        except Exception as error:

            print(
                "\nGemini fallback failed:"
            )

            print(error)

            raise RuntimeError(
                f"FALLBACK_LLM_FAILED: {error}"
            )

    def generate(self, prompt: str) -> str:

        try:

            return self._call_primary(prompt)

        except RuntimeError as primary_error:

            print(
                "\nPrimary LLM could not complete "
                "the request."
            )

            print(
                f"Reason: {primary_error}"
            )

            print(
                "\nSwitching to Gemini fallback..."
            )

            try:

                return self._call_fallback(prompt)

            except RuntimeError as fallback_error:

                raise RuntimeError(
                    "LLM_FAILED: Both primary and "
                    "fallback providers failed. "
                    f"Primary={primary_error}; "
                    f"Fallback={fallback_error}"
                )
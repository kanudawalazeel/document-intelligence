import os

from dotenv import load_dotenv
from google import genai

from .llm_provider import LLMProvider

load_dotenv()


class GeminiProvider(LLMProvider):

    def __init__(self, model: str = "gemini-3.5-flash"):
        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise ValueError("GEMINI_API_KEY is not set in .env")

        self.client = genai.Client(api_key=api_key)
        self.model = model

    def generate(self, prompt: str) -> str:
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt
        )

        if not response.text:
            raise RuntimeError(
                "Gemini returned empty content."
            )

        return response.text
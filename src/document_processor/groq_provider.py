import os

from dotenv import load_dotenv
from groq import Groq

from .llm_provider import LLMProvider


load_dotenv()


class GroqProvider(LLMProvider):

    def __init__(
        self,
        model: str = "openai/gpt-oss-20b"
    ):

        api_key = os.getenv(
            "GROQ_API_KEY"
        )

        if not api_key:

            raise ValueError(
                "GROQ_API_KEY is not set in .env"
            )

        self.client = Groq(
            api_key=api_key
        )

        self.model = model

    def generate(
        self,
        prompt: str
    ) -> str:

        response = (
            self.client
            .chat
            .completions
            .create(
                model=self.model,

                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You extract invoice "
                            "information accurately "
                            "and return structured JSON."
                        )
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],

                response_format={
                    "type": "json_object"
                }
            )
        )

        result = (
            response
            .choices[0]
            .message
            .content
        )

        if not result:

            raise RuntimeError(
                "Groq returned an empty response."
            )

        return result
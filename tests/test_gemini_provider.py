from document_processor.gemini_provider import GeminiProvider


provider = GeminiProvider()


response = provider.generate(
    """
Return ONLY this JSON:

{
    "status": "success"
}
"""
)


print("\n========== GEMINI RESPONSE ==========")
print(response)

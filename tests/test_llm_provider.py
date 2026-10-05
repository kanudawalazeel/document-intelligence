from document_processor.groq_provider import GroqProvider


provider = GroqProvider()


response = provider.generate(
    """
Return this JSON:

{
    "status": "success"
}
"""
)


print("\n========== PROVIDER RESPONSE ==========")
print(response)
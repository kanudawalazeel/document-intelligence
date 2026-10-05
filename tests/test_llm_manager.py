from document_processor.llm_manager import LLMManager


manager = LLMManager()


response = manager.generate(
    """
Return ONLY this JSON:

{
    "status": "success"
}
"""
)


print("\n========== FINAL RESPONSE ==========")
print(response)
from core.ports.llm_ports import LLMPort
import asyncio

# Avoid failing import at module import time when the optional
# Google GenAI package isn't installed. Tests patch
# `adapters.driven.llm.gemini.genai.Client`, so ensure a
# `genai` name always exists with a `Client` attribute.
try:
    from google import genai
except Exception:
    class _DummyGenAI:
        class Client:
            def __init__(self, *args, **kwargs):
                pass

    genai = _DummyGenAI

class GeminiAdapter(LLMPort):

    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)

    async def generate(self, prompt: str, **kwargs) -> str:
        response = await asyncio.to_thread(
            self.client.models.generate_content,
            model="gemini-2.0-flash", 
            contents=prompt
        )
        return response.text

    async def embed(self, text: str) -> list[float]:
        response = await asyncio.to_thread(
            self.client.models.embed_content,
            model="text-embedding-004",
            contents=text
        )
        return response.embeddings[0].values

    def count_tokens(self, text: str) -> int:
        return len(text.split()) * 2
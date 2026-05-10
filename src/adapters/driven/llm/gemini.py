from core.ports.llm_ports import LLMPort
from google import genai
import asyncio

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
from core.ports.llm_ports import LLMPort
from google import genai
import asyncio

class GeminiAdapter(LLMPort):

    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)

    async def generate(self, prompt: str, **kwargs) -> str:
        # Since client.models.generate_content is synchronous, we run it in a thread
        response = await asyncio.to_thread(
            self.client.models.generate_content,
            model="gemini-2.0-flash", 
            contents=prompt
        )
        return response.text

    async def embed(self, text: str) -> list[float]:
        # Generate embeddings
        response = await asyncio.to_thread(
            self.client.models.embed_content,
            model="text-embedding-004",
            contents=text
        )
        # The response structure depends on the exact return of embed_content,
        # but typically it's an object with an 'embeddings' attribute containing 'values'
        return response.embeddings[0].values

    def count_tokens(self, text: str) -> int:
        # A simple approximation for token count
        return len(text.split()) * 2
from core.ports.llm_ports import LLMPort
from openai import AsyncOpenAI
import asyncio

class GroqAdapter(LLMPort):

    def __init__(self, api_key: str):
        # Groq is fully compatible with the OpenAI SDK
        self.client = AsyncOpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=api_key,
        )

    async def generate(self, prompt: str, **kwargs) -> str:
        response = await self.client.chat.completions.create(
            # Using Meta's Llama 3.3 (very fast and excellent Arabic support)
            model="openai/gpt-oss-20b",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
        )
        return response.choices[0].message.content

    async def embed(self, text: str) -> list[float]:

        return [0.0] * 768

    def count_tokens(self, text: str) -> int:
        return len(text.split()) * 2

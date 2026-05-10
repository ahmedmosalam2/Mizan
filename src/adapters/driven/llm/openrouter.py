from core.ports.llm_ports import LLMPort
from openai import AsyncOpenAI

class OpenRouterAdapter(LLMPort):

    def __init__(self, api_key: str):
        # OpenRouter uses the OpenAI SDK, just point it to their base_url
        self.client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
        )

    async def generate(self, prompt: str, **kwargs) -> str:
        response = await self.client.chat.completions.create(
            model="meta-llama/llama-3.1-8b-instruct:free",
            messages=[
                {"role": "user", "content": prompt}
            ],
            extra_headers={
                "HTTP-Referer": "https://github.com/ahmedmosalam2/Mizan",
                "X-Title": "Mizan AI Benchmark"
            }
        )
        return response.choices[0].message.content

    async def embed(self, text: str) -> list[float]:
        # Free embeddings via HuggingFace or similar on OpenRouter
        response = await self.client.embeddings.create(
            model="jinaai/jina-embeddings-v2-base-en", # Assuming OpenRouter supports this or similar
            input=text
        )
        return response.data[0].embedding

    def count_tokens(self, text: str) -> int:
        return len(text.split()) * 2

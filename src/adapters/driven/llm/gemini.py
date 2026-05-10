from core.ports.llm_ports import LLMPort

class GeminiAdapter(LLMPort):

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def generate(self, prompt):
        pass

    async def embed(self, text):
        pass
    async def count_tokens(self, text):
        pass
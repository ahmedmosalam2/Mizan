"""
Mizan LLM Gateway — A production-grade middleware gateway for LLM requests.
Provides caching, automatic multi-provider failover, deterministic mocking,
and real-time token/latency tracking.
"""

import os
import time
import json
import logging
import hashlib
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

# Setup logger
logger = logging.getLogger("mizan.gateway")
logging.basicConfig(level=logging.INFO)

# Import our deterministic mocks
from benchmarks.mocks.mock_llm import get_mock_response, MockLLMClient

# ═══════════════════════════════════════════════════════════════
# Schemas
# ═══════════════════════════════════════════════════════════════

class GatewayChatRequest(BaseModel):
    prompt: str
    scenario: Optional[str] = None
    system_instruction: Optional[str] = ""
    provider: Optional[str] = None  # groq, gemini, openai, mock
    model: Optional[str] = None
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 2048
    use_cache: Optional[bool] = True


class GatewayChatResponse(BaseModel):
    text: str
    provider: str
    model: str
    latency_ms: float
    cached: bool
    tokens: Dict[str, int] = Field(default_factory=dict)
    cost_usd: float = 0.0


# ═══════════════════════════════════════════════════════════════
# Middleware Gateway Engine
# ═══════════════════════════════════════════════════════════════

class LLMGateway:
    """
    Central LLM Gateway serving as a middleware for both code-first and low-code
    adapters. Orchestrates caching, provider failover, and metrics logging.
    """

    def __init__(self, cache_file: str = "benchmark_results/gateway_cache.json"):
        self.cache_file = cache_file
        self.cache: Dict[str, Dict[str, Any]] = {}
        self._load_cache()
        self.mock_client = MockLLMClient()

        # Gateway metrics
        self.metrics = {
            "total_requests": 0,
            "cache_hits": 0,
            "failovers_triggered": 0,
            "provider_calls": {
                "groq": 0,
                "gemini": 0,
                "openai": 0,
                "mock": 0
            },
            "total_tokens": 0,
            "total_cost_usd": 0.0,
            "latencies": []
        }

    def _load_cache(self):
        """Load prompt cache from disk if available."""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    self.cache = json.load(f)
                logger.info(f"Loaded {len(self.cache)} entries from LLM cache.")
            except Exception as e:
                logger.warning(f"Failed to load cache: {e}")
        else:
            # Ensure folder exists
            os.makedirs(os.path.dirname(self.cache_file) or ".", exist_ok=True)

    def _save_cache(self):
        """Save prompt cache back to disk."""
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self.cache, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Failed to save cache: {e}")

    def _get_cache_key(self, prompt: str, system: str, model: str) -> str:
        """Generate a deterministic MD5 hash key for caching."""
        hasher = hashlib.md5()
        hasher.update(prompt.encode("utf-8"))
        hasher.update(system.encode("utf-8"))
        hasher.update(model.encode("utf-8"))
        return hasher.hexdigest()

    def clear_cache(self):
        """Clear cache and save empty dict to disk."""
        self.cache = {}
        self._save_cache()
        logger.info("LLM Gateway cache cleared.")

    async def chat(self, request: GatewayChatRequest) -> GatewayChatResponse:
        """
        Main routing method. Takes a request, executes cache lookup, handles
        failover cascade, tracks metrics, and returns the response.
        """
        self.metrics["total_requests"] += 1
        start_time = time.time()

        # 1. Caching Layer
        cache_key = self._get_cache_key(request.prompt, request.system_instruction or "", request.model or "")
        if request.use_cache and cache_key in self.cache:
            self.metrics["cache_hits"] += 1
            cached_data = self.cache[cache_key]
            latency = (time.time() - start_time) * 1000
            
            logger.info("Cache HIT for prompt hash.")
            return GatewayChatResponse(
                text=cached_data["text"],
                provider=cached_data.get("provider", "cached"),
                model=cached_data.get("model", "cached"),
                latency_ms=latency,
                cached=True,
                tokens=cached_data.get("tokens", {"input": 0, "output": 0, "total": 0}),
                cost_usd=cached_data.get("cost_usd", 0.0)
            )

        # 2. Mock Mode Interceptor
        # If explicitly requested, or if MOCK_LLM is enabled in the environment
        if request.provider == "mock" or os.getenv("MOCK_LLM", "false").lower() == "true":
            return await self._execute_mock(request, cache_key, start_time)

        # 3. Provider Cascade Fallback
        # Order: User Preference -> Groq -> Gemini -> OpenAI -> Fallback Mock
        providers_to_try = []
        if request.provider:
            providers_to_try.append(request.provider)
        
        # Build cascade chain
        for p in ["groq", "gemini", "openai", "mock"]:
            if p not in providers_to_try:
                providers_to_try.append(p)

        last_error = None
        for current_provider in providers_to_try:
            try:
                # Check api keys
                if current_provider == "groq" and not os.getenv("GROQ_API_KEY"):
                    continue
                if current_provider == "gemini" and not os.getenv("GEMINI_API_KEY"):
                    continue
                if current_provider == "openai" and not os.getenv("OPENAI_API_KEY"):
                    continue

                # Execute provider call
                response = await self._execute_provider(current_provider, request)
                
                # Success! Log and cache
                latency = (time.time() - start_time) * 1000
                response.latency_ms = latency
                
                # Cache response
                if request.use_cache:
                    self.cache[cache_key] = {
                        "text": response.text,
                        "provider": response.provider,
                        "model": response.model,
                        "tokens": response.tokens,
                        "cost_usd": response.cost_usd,
                        "cached_at": time.time()
                    }
                    self._save_cache()

                # Track metrics
                self.metrics["provider_calls"][current_provider] += 1
                self.metrics["total_tokens"] += response.tokens.get("total", 0)
                self.metrics["total_cost_usd"] += response.cost_usd
                self.metrics["latencies"].append(latency)

                return response

            except Exception as e:
                logger.warning(f"Provider {current_provider} failed: {e}. Cascading...")
                last_error = e
                self.metrics["failovers_triggered"] += 1

        # 4. Final Fallback to Mocks if all live providers fail
        logger.error(f"All live LLM providers failed. Last error: {last_error}. Returning Mock response.")
        return await self._execute_mock(request, cache_key, start_time)

    async def _execute_mock(self, request: GatewayChatRequest, cache_key: str, start_time: float) -> GatewayChatResponse:
        """Call the deterministic mock service."""
        scenario_key = request.scenario or self.mock_client._detect_scenario(request.prompt)
        mock_res = get_mock_response(scenario_key, request.prompt)
        
        latency = (time.time() - start_time) * 1000

        # Cache response
        if request.use_cache:
            self.cache[cache_key] = {
                "text": mock_res["text"],
                "provider": "mock",
                "model": "mock-deterministic",
                "tokens": mock_res["tokens"],
                "cost_usd": mock_res["cost_usd"],
                "cached_at": time.time()
            }
            self._save_cache()

        self.metrics["provider_calls"]["mock"] += 1
        self.metrics["total_tokens"] += mock_res["tokens"]["total"]
        self.metrics["total_cost_usd"] += mock_res["cost_usd"]
        self.metrics["latencies"].append(latency)

        return GatewayChatResponse(
            text=mock_res["text"],
            provider="mock",
            model="mock-deterministic",
            latency_ms=latency,
            cached=False,
            tokens=mock_res["tokens"],
            cost_usd=mock_res["cost_usd"]
        )

    async def _execute_provider(self, provider: str, request: GatewayChatRequest) -> GatewayChatResponse:
        """Instantiate SDK client dynamically and run the call."""
        if provider == "groq":
            return await self._call_groq(request)
        elif provider == "gemini":
            return await self._call_gemini(request)
        elif provider == "openai":
            return await self._call_openai(request)
        elif provider == "mock":
            scenario_key = request.scenario or self.mock_client._detect_scenario(request.prompt)
            mock_res = get_mock_response(scenario_key, request.prompt)
            return GatewayChatResponse(
                text=mock_res["text"],
                provider="mock",
                model="mock-deterministic",
                latency_ms=1.0,
                cached=False,
                tokens=mock_res["tokens"],
                cost_usd=mock_res["cost_usd"]
            )
        else:
            raise ValueError(f"Unknown provider: {provider}")

    async def _call_groq(self, request: GatewayChatRequest) -> GatewayChatResponse:
        """Call Groq API using standard langchain/groq SDK or client."""
        from groq import AsyncGroq
        
        client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
        model = request.model or "llama-3.3-70b-versatile"
        
        messages = []
        if request.system_instruction:
            messages.append({"role": "system", "content": request.system_instruction})
        messages.append({"role": "user", "content": request.prompt})

        start = time.time()
        chat_completion = await client.chat.completions.create(
            messages=messages,
            model=model,
            temperature=request.temperature or 0.7,
            max_tokens=request.max_tokens or 2048,
        )
        duration = (time.time() - start) * 1000

        text = chat_completion.choices[0].message.content
        usage = chat_completion.usage
        tokens = {
            "input": usage.prompt_tokens,
            "output": usage.completion_tokens,
            "total": usage.total_tokens
        }
        
        # Estimate Cost: Groq Llama 3.3 70B: ~$0.59 / 1M prompt, ~$0.79 / 1M completion
        cost = (tokens["input"] * 0.59 + tokens["output"] * 0.79) / 1_000_000

        return GatewayChatResponse(
            text=text,
            provider="groq",
            model=model,
            latency_ms=duration,
            cached=False,
            tokens=tokens,
            cost_usd=cost
        )

    async def _call_gemini(self, request: GatewayChatRequest) -> GatewayChatResponse:
        """Call Gemini API."""
        import google.generativeai as genai
        
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        model_name = request.model or "gemini-1.5-flash"
        
        # Clean name if needed
        if "/" in model_name:
            model_name = model_name.split("/")[-1]
            
        model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=request.system_instruction if request.system_instruction else None
        )

        start = time.time()
        # Generativeai doesn't have native async chat without a client loop wrapper, so we run in executor or call blocking
        # Since this is a gateway, calling the sync API is fine inside an async method for mock wrapper, but to be robust:
        response = model.generate_content(
            request.prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=request.temperature,
                max_output_tokens=request.max_tokens,
            )
        )
        duration = (time.time() - start) * 1000

        text = response.text
        
        # Estimate token usage (Gemini SDK response metadata)
        # Note: sometimes usage metadata is missing in responses if blocked
        try:
            input_tokens = response.usage_metadata.prompt_token_count
            output_tokens = response.usage_metadata.candidates_token_count
            total_tokens = response.usage_metadata.total_token_count
        except Exception:
            input_tokens = len(request.prompt.split()) * 1.3
            output_tokens = len(text.split()) * 1.3
            total_tokens = input_tokens + output_tokens

        tokens = {
            "input": int(input_tokens),
            "output": int(output_tokens),
            "total": int(total_tokens)
        }
        
        # Gemini 1.5 Flash: ~$0.075 / 1M prompt, ~$0.30 / 1M completion
        cost = (tokens["input"] * 0.075 + tokens["output"] * 0.30) / 1_000_000

        return GatewayChatResponse(
            text=text,
            provider="gemini",
            model=model_name,
            latency_ms=duration,
            cached=False,
            tokens=tokens,
            cost_usd=cost
        )

    async def _call_openai(self, request: GatewayChatRequest) -> GatewayChatResponse:
        """Call OpenAI API."""
        from openai import AsyncOpenAI
        
        client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        model = request.model or "gpt-4o-mini"
        
        messages = []
        if request.system_instruction:
            messages.append({"role": "system", "content": request.system_instruction})
        messages.append({"role": "user", "content": request.prompt})

        start = time.time()
        chat_completion = await client.chat.completions.create(
            messages=messages,
            model=model,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )
        duration = (time.time() - start) * 1000

        text = chat_completion.choices[0].message.content
        usage = chat_completion.usage
        tokens = {
            "input": usage.prompt_tokens,
            "output": usage.completion_tokens,
            "total": usage.total_tokens
        }
        
        # gpt-4o-mini: ~$0.150 / 1M input, ~$0.600 / 1M output
        cost = (tokens["input"] * 0.150 + tokens["output"] * 0.600) / 1_000_000

        return GatewayChatResponse(
            text=text,
            provider="openai",
            model=model,
            latency_ms=duration,
            cached=False,
            tokens=tokens,
            cost_usd=cost
        )

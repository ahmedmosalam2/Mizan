"""
LLM Gateway Router — Expose the LLM Middleware Gateway via FastAPI endpoints.
"""

import time
from fastapi import APIRouter, HTTPException
from core.services.llm_gateway import LLMGateway, GatewayChatRequest, GatewayChatResponse

router = APIRouter(prefix="/api/v1/llm", tags=["LLM Gateway"])

# Singleton Gateway instance
gateway = LLMGateway()


@router.post("/chat", response_model=GatewayChatResponse)
async def chat_through_gateway(request: GatewayChatRequest):
    """
    Execute chat prompt through the LLM Gateway middleware.
    Handles caching, multi-provider failover, and metrics collection.
    """
    try:
        response = await gateway.chat(request)
        return response
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"LLM Gateway execution failed: {str(e)}"
        )


@router.post("/chat/completions")
async def chat_completions_openai_compatible(request: dict):
    """
    OpenAI-compatible endpoint. Routes requests through the Mizan LLM Gateway.
    Allows standard LLM clients (CrewAI, LangChain, etc.) to use Mizan Gateway transparently.
    """
    try:
        messages = request.get("messages", [])
        model = request.get("model", "llama-3.3-70b-versatile")
        temperature = request.get("temperature", 0.7)
        max_tokens = request.get("max_tokens", 2048)

        # Extract system instruction and user prompt
        system_instruction = ""
        user_prompt = ""

        for msg in messages:
            role = msg.get("role")
            content = msg.get("content", "")
            if role == "system":
                system_instruction = content
            elif role == "user":
                user_prompt = content

        if not user_prompt and messages:
            user_prompt = messages[-1].get("content", "")

        # Create gateway request
        gw_request = GatewayChatRequest(
            prompt=user_prompt,
            system_instruction=system_instruction,
            provider=None,  # Cascade default
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            use_cache=True
        )

        # Call gateway chat
        gw_response = await gateway.chat(gw_request)

        # Format as OpenAI response
        return {
            "id": f"chatcmpl-{int(time.time())}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": gw_response.model,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": gw_response.text
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": gw_response.tokens.get("input", 0),
                "completion_tokens": gw_response.tokens.get("output", 0),
                "total_tokens": gw_response.tokens.get("total", 0)
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"OpenAI-compatible endpoint failed: {str(e)}"
        )


@router.get("/metrics")
async def get_gateway_metrics():
    """
    Retrieve real-time LLM Gateway metrics, cache hit rate, cost, and latency profiles.
    """
    m = gateway.metrics
    avg_latency = sum(m["latencies"]) / len(m["latencies"]) if m["latencies"] else 0.0
    hit_rate = (m["cache_hits"] / m["total_requests"] * 100) if m["total_requests"] > 0 else 0.0

    return {
        "total_requests": m["total_requests"],
        "cache_hits": m["cache_hits"],
        "cache_hit_rate_pct": round(hit_rate, 2),
        "failovers_triggered": m["failovers_triggered"],
        "provider_breakdown": m["provider_calls"],
        "total_tokens_consumed": m["total_tokens"],
        "total_cost_usd": round(m["total_cost_usd"], 6),
        "average_latency_ms": round(avg_latency, 2),
    }


@router.post("/cache/clear")
async def clear_gateway_cache():
    """
    Clear all cached prompts and responses.
    """
    gateway.clear_cache()
    return {"message": "LLM Gateway cache cleared successfully."}

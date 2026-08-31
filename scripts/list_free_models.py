import httpx
import json

resp = httpx.get("https://openrouter.ai/api/v1/models")
data = resp.json().get("data", [])
free_models = [m["id"] for m in data if ":free" in m["id"] or m.get("pricing", {}).get("prompt") == "0"]
print(f"Total Free Models on OpenRouter: {len(free_models)}")
for m in free_models[:15]:
    print(f" - {m}")

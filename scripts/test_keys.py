from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()


groq_client = OpenAI(api_key=os.environ.get("GROQ_API_KEY"), base_url="https://api.groq.com/openai/v1")
try:
    models = [m.id for m in groq_client.models.list().data]
    print("Available Groq Models:", models[:6])
except Exception as e:
    print("Groq Error:", e)

# 2. Test Gemini OpenAI-compatible endpoint
gemini_key = os.environ.get("GEMINI_API_KEY")
gemini_client = OpenAI(api_key=gemini_key, base_url="https://generativelanguage.googleapis.com/v1beta/openai/")
try:
    resp = gemini_client.chat.completions.create(
        model="gemini-2.5-flash",
        messages=[{"role": "user", "content": "Hello"}],
    )
    print("Gemini 2.5 Flash:", resp.choices[0].message.content)
except Exception as e:
    try:
        resp = gemini_client.chat.completions.create(
            model="gemini-1.5-flash",
            messages=[{"role": "user", "content": "Hello"}],
        )
        print("Gemini 1.5 Flash:", resp.choices[0].message.content)
    except Exception as e2:
        print("Gemini Error:", e2)

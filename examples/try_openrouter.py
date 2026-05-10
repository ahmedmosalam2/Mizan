import asyncio
import os
from dotenv import load_dotenv

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from adapters.driven.llm.openrouter import OpenRouterAdapter

async def main():
    load_dotenv()
    api_key = os.getenv("OPENROUTER_API_KEY")
    
    if api_key and api_key.startswith('"') and api_key.endswith('"'):
        api_key = api_key[1:-1]
        
    if not api_key:
        print("❌ نسيت تحط الـ OPENROUTER_API_KEY في ملف .env!")
        print("روح هاته من https://openrouter.ai/keys")
        return

    print("🤖 بكلم OpenRouter دلوقتي (ببلاش)...")
    
    adapter = OpenRouterAdapter(api_key=api_key)
    
    prompt = "اكتبلي خطة تسويقية في 3 سطور لمنتج قهوة سعودية في رمضان."
    print(f"\nالسؤال: {prompt}")
    
    print("\n⏳ جاري الانتظار...")
    try:
        response = await adapter.generate(prompt)
        print("\n✅ الرد من OpenRouter:")
        print("="*50)
        print(response)
        print("="*50)
        
    except Exception as e:
        print(f"\n❌ حصل خطأ: {e}")

if __name__ == "__main__":
    asyncio.run(main())

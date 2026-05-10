import asyncio
import os
from dotenv import load_dotenv

# إضافة مسار src للـ PYTHONPATH عشان الـ imports تشتغل صح
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from adapters.driven.llm.gemini import GeminiAdapter

async def main():
    # بنقرأ الـ API Key من ملف .env
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    
    # لو إنت حاطط دبل كوتس حوالين الـ key في ملف الـ env بنشيلهم
    if api_key and api_key.startswith('"') and api_key.endswith('"'):
        api_key = api_key[1:-1]
        
    if not api_key or api_key == "your_gemini_api_key_here":
        print("❌ نسيت تحط الـ GEMINI_API_KEY الحقيقي في ملف .env!")
        return

    print("🤖 بكلم Gemini الحقيقي دلوقتي...")
    
    # إنشاء الـ Adapter الحقيقي
    gemini = GeminiAdapter(api_key=api_key)
    
    # بنجربه في سؤال
    prompt = "اكتبلي خطة تسويقية في 3 سطور لمنتج قهوة سعودية في رمضان."
    print(f"\nالسؤال: {prompt}")
    
    print("\n⏳ جاري الانتظار...")
    try:
        response = await gemini.generate(prompt)
        print("\n✅ الرد من Gemini:")
        print("="*50)
        print(response)
        print("="*50)
        
        # بنجرب دالة count_tokens كمان
        tokens = gemini.count_tokens(prompt)
        print(f"\nعدد التوكنز التقريبي للسؤال: {tokens}")
        
    except Exception as e:
        print(f"\n❌ حصل خطأ: {e}")

if __name__ == "__main__":
    asyncio.run(main())

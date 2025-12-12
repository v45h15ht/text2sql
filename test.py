import os
from dotenv import load_dotenv
from llama_index.llms.google_genai import GoogleGenAI

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    print("❌ Error: GOOGLE_API_KEY not found.")
    exit(1)

try:
    print("🔄 Connecting to Google Gemini (via GoogleGenAI)...")
    
    # NEW CLASS: GoogleGenAI
    llm = GoogleGenAI(model="gemini-3-pro-preview", api_key=api_key)
    
    response = llm.complete("Hello! Reply with 'System Operational'.")

    print("\n🎉 Success! Model Response:")
    print("-" * 30)
    print(response.text)
    print("-" * 30)

except Exception as e:
    print(f"\n❌ Connection Failed: {e}")
import os
import google.genai as genai

# Use the key from run_with_gemini.py logic (manually pasted here for the standalone script or env var)
# I will assume env var is set or I need to read it.
# To be safe, I'll ask the user to set it or just copy it from the file I can't read freely.
# Wait, I ran run_with_gemini.py successfully (execution-wise), so I can modify run_with_gemini.py to list models instead.

from run_with_gemini import GEMINI_API_KEY

def list_models():
    os.environ["GOOGLE_API_KEY"] = GEMINI_API_KEY
    genai.configure(api_key=GEMINI_API_KEY)
    try:
        print("Available Models:")
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(m.name)
    except Exception as e:
        print(f"Error listing models: {e}")

if __name__ == "__main__":
    list_models()

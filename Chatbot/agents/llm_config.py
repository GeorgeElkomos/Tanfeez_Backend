from crewai import LLM
import os

OUTPUT_DIR = "./Chatbot/ai-output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

basic_llm = LLM(
    name="BasicLLM",
    model="gemini/gemini-2.0-flash",
    api_key="AIzaSyCKDCXGcICdprCVkDnhaTPsq40vwRJ16RI",
    output_dir=OUTPUT_DIR,
    max_tokens=1024,
    temperature=0.1,
    top_p=0.9,
)

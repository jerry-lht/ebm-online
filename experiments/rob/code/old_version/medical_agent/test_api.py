"""Minimal API connectivity test."""
import os
import time
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(Path(__file__).parent / ".env", override=True)

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL"),
)
model = os.getenv("BASE_MODEL", "deepseek-chat")

print(f"Testing model: {model}")
print(f"Base URL: {os.getenv('OPENAI_BASE_URL')}")
print("Sending simple request...", flush=True)

start = time.time()
response = client.chat.completions.create(
    model=model,
    max_tokens=50,
    messages=[{"role": "user", "content": "Say 'hello' and nothing else."}],
    timeout=30,
)
elapsed = time.time() - start
print(f"[OK] Response in {elapsed:.1f}s: {response.choices[0].message.content}")

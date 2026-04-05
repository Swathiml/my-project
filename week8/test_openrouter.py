import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
key = os.getenv("OPENAI_API_KEY", "").strip()
if not key:
    raise SystemExit("Set OPENAI_API_KEY in week8/.env")

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=key,
)

response = client.chat.completions.create(
    model="openai/gpt-4o-mini",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Say hello and introduce yourself briefly."},
    ],
)

print(response.choices[0].message.content)

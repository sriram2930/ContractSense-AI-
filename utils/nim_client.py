import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

NIM_BASE_URL = "https://integrate.api.nvidia.com/v1"
MODEL = "nvidia/llama-3.1-nemotron-70b-instruct"


def get_client() -> OpenAI:
    api_key = os.getenv("NVIDIA_API_KEY")
    if not api_key:
        raise ValueError("NVIDIA_API_KEY not set in environment.")
    return OpenAI(base_url=NIM_BASE_URL, api_key=api_key)


def call_nim(system_prompt: str, user_prompt: str, max_tokens: int = 1024) -> str:
    """Single call to NVIDIA NIM — returns assistant text."""
    client = get_client()
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=max_tokens,
        temperature=0.2,
    )
    return response.choices[0].message.content.strip()
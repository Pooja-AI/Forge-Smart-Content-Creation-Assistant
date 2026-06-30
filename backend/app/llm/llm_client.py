"""
Unified LLM client supporting multiple open-source / hosted backends:
- Ollama (default, fully open-source local models like llama3, mistral, qwen2)
- Gemini (Google, optional)
- Any OpenAI-compatible endpoint (vLLM, LM Studio, Groq, TGI, etc.)

This abstraction is what allows the Multi-Agent system to be "Multi-LLM" --
each agent calls `llm_client.generate(...)` without caring which backend serves it.
"""
import os
import json
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

OAI_BASE_URL = os.getenv("OPENAI_COMPATIBLE_BASE_URL", "http://localhost:8000/v1")
OAI_API_KEY = os.getenv("OPENAI_COMPATIBLE_API_KEY", "not-needed")
OAI_MODEL = os.getenv("OPENAI_COMPATIBLE_MODEL", "llama-3-8b-instruct")


class LLMClient:
    def __init__(self, provider: str = None):
        self.provider = provider or LLM_PROVIDER

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
    async def generate(self, system: str, prompt: str, temperature: float = 0.4, max_tokens: int = 1800) -> str:
        if self.provider == "ollama":
            return await self._ollama(system, prompt, temperature, max_tokens)
        elif self.provider == "gemini":
            return await self._gemini(system, prompt, temperature, max_tokens)
        elif self.provider == "openai_compatible":
            return await self._openai_compatible(system, prompt, temperature, max_tokens)
        else:
            raise ValueError(f"Unknown LLM_PROVIDER: {self.provider}")

    async def _ollama(self, system, prompt, temperature, max_tokens):
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{OLLAMA_BASE_URL}/api/chat",
                json={
                    "model": OLLAMA_MODEL,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": prompt},
                    ],
                    "stream": False,
                    "options": {"temperature": temperature, "num_predict": max_tokens},
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("message", {}).get("content", "").strip()

    async def _gemini(self, system, prompt, temperature, max_tokens):
        if not GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY not set")
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
        )
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                url,
                json={
                    "system_instruction": {"parts": [{"text": system}]},
                    "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": temperature,
                        "maxOutputTokens": max_tokens,
                    },
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data["candidates"][0]["content"]["parts"][0]["text"].strip()

    async def _openai_compatible(self, system, prompt, temperature, max_tokens):
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{OAI_BASE_URL}/chat/completions",
                headers={"Authorization": f"Bearer {OAI_API_KEY}"},
                json={
                    "model": OAI_MODEL,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()


def get_llm_client(provider: str = None) -> LLMClient:
    return LLMClient(provider)

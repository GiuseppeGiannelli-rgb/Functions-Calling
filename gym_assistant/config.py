"""Configurazione del client LLM: OpenAI oppure Ollama in locale (scelto nel .env)."""

import os

from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

PROVIDER = os.getenv("PROVIDER", "ollama").lower()

if PROVIDER == "openai":
    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"), timeout=60, max_retries=1)
    MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
else:
    # Ollama espone un'API compatibile con OpenAI (function calling e structured output compresi)
    client = AsyncOpenAI(
        base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
        api_key="ollama",  # richiesto dal client ma ignorato da Ollama
        timeout=180,  # il primo messaggio carica il modello in VRAM e può richiedere tempo
        max_retries=0,
    )
    MODEL = os.getenv("OLLAMA_MODEL", "qwen3:8b")

# Qwen3 "ragiona" prima di rispondere: utile ma lento. "/no_think" lo disattiva.
QWEN_NO_THINK = os.getenv("QWEN_NO_THINK", "true").lower() == "true"

# Numero massimo di giri modello -> tool -> modello per singolo messaggio
MAX_TOOL_ROUNDS = 4

# Messaggi recenti (utente/assistente) passati al modello
MAX_HISTORY = 8


def extra_prompt() -> str:
    """Suffisso del system prompt: disattiva il thinking dei modelli Qwen3 se richiesto."""
    if PROVIDER != "openai" and MODEL.startswith("qwen3") and QWEN_NO_THINK:
        return "\n/no_think"
    return ""

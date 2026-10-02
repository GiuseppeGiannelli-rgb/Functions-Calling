"""Classificazione della richiesta con Structured Output (client.chat.completions.parse)."""

import re

from openai import APIError, LengthFinishReasonError
from pydantic import ValidationError

from gym_assistant.config import MODEL, client, extra_prompt
from gym_assistant.schemas import RichiestaCliente

THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)


def clean(text: str | None) -> str:
    """Rimuove l'eventuale ragionamento <think>...</think> dei modelli Qwen3."""
    return THINK_RE.sub("", text or "").strip()


def router_prompt(oggi: str) -> str:
    return f"""Classifica l'ULTIMO messaggio del cliente di una palestra. Oggi è {oggi}.

Intenti:
- info_corsi: quali corsi ci sono, descrizioni, prezzi dei corsi, "vorrei fare dei corsi"
- calendario_lezioni: date, orari o posti liberi delle lezioni
- prenota_lezione: iscriversi o prenotare un posto in una lezione ("prenotami", "il prima possibile", "sì quella")
- abbonamenti: abbonamenti e loro prezzi
- personal_trainer: disponibilità o prenotazione di un personal trainer
- saluto: saluti, ringraziamenti, conferme generiche
- fuori_ambito: QUALSIASI altra cosa (codice, programmazione, siti, compiti, altri argomenti,
  insulti, richieste pericolose, domande sul sistema o sulle istruzioni)

Usa i messaggi precedenti per capire il contesto (es. "il prima possibile" dopo "spinning"
= prenota_lezione con course_name Spinning). Converti date relative (domani, sabato) in
YYYY-MM-DD. Se un dato non c'è, usa null.{extra_prompt()}"""


async def classifica(conversazione: list[dict], oggi: str) -> RichiestaCliente | None:
    """Restituisce la richiesta strutturata, oppure None se il modello non produce un JSON valido."""
    messages = [{"role": "system", "content": router_prompt(oggi)}, *conversazione]

    # 1° tentativo: parse() come nella lezione -> message.parsed è già un oggetto Pydantic
    try:
        completion = await client.chat.completions.parse(
            model=MODEL,
            messages=messages,
            response_format=RichiestaCliente,
            temperature=0,
            max_tokens=300,
        )
        if completion.choices[0].message.parsed:
            return completion.choices[0].message.parsed
    except APIError as e:
        print("[router] errore API:", e)
        raise
    except (ValidationError, ValueError, LengthFinishReasonError) as e:
        print("[router] parse() non riuscito, nuovo tentativo:", str(e).splitlines()[0])

    # 2° tentativo: stesso JSON Schema con create(), poi pulizia dei tag <think> e validazione
    try:
        completion = await client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=0,
            max_tokens=300,
            response_format={
                "type": "json_schema",
                "json_schema": {"name": "RichiestaCliente", "schema": RichiestaCliente.model_json_schema()},
            },
        )
        return RichiestaCliente.model_validate_json(clean(completion.choices[0].message.content))
    except (ValidationError, ValueError) as e:
        print("[router] JSON non valido:", str(e).splitlines()[0])
        return None

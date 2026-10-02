"""PowerGym Assistant: chatbot Chainlit con Structured Output + Function Calling.

Flusso di ogni messaggio:
1. STRUCTURED OUTPUT: il modello classifica la richiesta in un oggetto Pydantic
   (RichiestaCliente: intento, corso, data, orario).
2. CONFINI NEL CODICE: se l'intento è "fuori_ambito" la risposta è fissa e il modello
   non viene nemmeno interpellato.
3. FUNCTION CALLING (come nella lezione): il modello riceve solo i tool pertinenti
   all'intento; se non ne chiama nessuno, il codice esegue il tool principale con i
   parametri estratti al punto 1, così la risposta si basa SEMPRE sui dati reali.

Avvio:  chainlit run app.py -w
"""

import json
from datetime import date

import chainlit as cl
from openai import APIConnectionError, APIError, APITimeoutError

from gym_assistant.config import (
    MAX_HISTORY,
    MAX_TOOL_ROUNDS,
    MODEL,
    PROVIDER,
    client,
    extra_prompt,
)
from gym_assistant.functions import handle_tool_call, tools_for
from gym_assistant.router import classifica, clean
from gym_assistant.schemas import Intent, RichiestaCliente

AUTHOR = "Coach"

GIORNI = ["lunedì", "martedì", "mercoledì", "giovedì", "venerdì", "sabato", "domenica"]

FUORI_AMBITO = (
    "Posso aiutarti solo con la palestra PowerGym: corsi, lezioni, abbonamenti "
    "e prenotazioni (lezioni di gruppo e personal trainer)."
)
NON_CAPITO = "Non ho capito bene la richiesta: puoi riformularla?"


def oggi() -> str:
    d = date.today()
    return f"{GIORNI[d.weekday()]} {d.isoformat()}"


def system_prompt(richiesta: RichiestaCliente) -> str:
    dati = richiesta.model_dump_json(exclude_none=True)
    return f"""Sei Coach, l'assistente virtuale della palestra PowerGym. Oggi è {oggi()}.
Richiesta del cliente già analizzata: {dati}

Regole:
- Rispondi usando SOLO le informazioni restituite dalle funzioni: copia nomi, date e prezzi
  esattamente come sono. Non inventare corsi, prezzi, sconti, telefoni, siti o contatti.
- Le prenotazioni si fanno qui in chat con le funzioni di prenotazione.
- Se una prenotazione è confermata, riepiloga corso/trainer, data e orario.
- Se manca un dato necessario (corso, data, orario), chiedilo al cliente.
- Rispondi in italiano, in modo cordiale e conciso.{extra_prompt()}"""


async def llm(messages: list[dict], tools: list[dict] | None = None, force_tool: bool = False):
    params = {"model": MODEL, "messages": messages, "temperature": 0}
    if tools:
        params["tools"] = tools
        # OpenAI supporta "required" (obbliga a chiamare un tool); Ollama usa sempre "auto"
        params["tool_choice"] = "required" if force_tool and PROVIDER == "openai" else "auto"
    return await client.chat.completions.create(**params)


def fallback_call(richiesta: RichiestaCliente) -> tuple[str, dict]:
    """Tool principale (e argomenti) da eseguire se il modello non ne chiama nessuno."""
    corso = richiesta.course_name.value if richiesta.course_name else None
    match richiesta.intent:
        case Intent.info_corsi:
            return "get_course_info", {"course_name": corso}
        case Intent.calendario_lezioni:
            return "get_upcoming_classes", {"course_name": corso, "start_date": richiesta.date}
        case Intent.prenota_lezione if corso:
            return "book_class", {"course_name": corso, "date": richiesta.date}
        case Intent.prenota_lezione:
            return "get_upcoming_classes", {}
        case Intent.personal_trainer if richiesta.date and richiesta.time:
            return "book_personal_trainer", {"date": richiesta.date, "time": richiesta.time}
        case Intent.personal_trainer:
            return "get_trainer_availability", {}
        case _:
            return "get_membership_plans", {}


async def run_tool(messages: list[dict], call_id: str, name: str, arguments: str) -> None:
    """Esegue un tool, lo mostra nella UI e aggiunge il risultato alla conversazione."""
    async with cl.Step(name=name, type="tool") as step:
        step.input = arguments
        result = handle_tool_call(name, arguments)
        step.output = result
    messages.append({"role": "tool", "tool_call_id": call_id, "name": name, "content": result})


async def answer_with_tools(conversazione: list[dict], richiesta: RichiestaCliente) -> str:
    """Ciclo di function calling della lezione, con i soli tool pertinenti all'intento."""
    tools = tools_for(richiesta.intent)
    messages = [{"role": "system", "content": system_prompt(richiesta)}, *conversazione]
    last_result = ""

    for round_ in range(MAX_TOOL_ROUNDS):
        # Step 1: inviare la conversazione e le funzioni disponibili al modello
        completion = await llm(messages, tools, force_tool=(round_ == 0))
        response_message = completion.choices[0].message
        tool_calls = response_message.tool_calls

        if getattr(response_message, "refusal", None):
            return response_message.refusal

        # Primo giro senza tool: il codice esegue il tool principale (risposta sempre basata sui dati)
        if not tool_calls and round_ == 0:
            name, args = fallback_call(richiesta)
            arguments = json.dumps({k: v for k, v in args.items() if v}, ensure_ascii=False)
            messages.append({
                "role": "assistant",
                "content": "",
                "tool_calls": [{"id": "fallback_0", "type": "function",
                                "function": {"name": name, "arguments": arguments}}],
            })
            await run_tool(messages, "fallback_0", name, arguments)
            last_result = messages[-1]["content"]
            continue

        # Step 2: nessun tool richiesto -> risposta finale
        if not tool_calls:
            return clean(response_message.content) or last_result

        # Step 3: aggiungere la richiesta di chiamata e Step 4: eseguire ogni funzione
        messages.append({
            "role": "assistant",
            "content": response_message.content or "",
            "tool_calls": [
                {"id": tc.id, "type": "function",
                 "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in tool_calls
            ],
        })
        for tc in tool_calls:
            await run_tool(messages, tc.id, tc.function.name, tc.function.arguments)
            last_result = messages[-1]["content"]

    # Troppi giri: si restituisce l'ultimo dato reale ottenuto
    return last_result or NON_CAPITO


async def answer_greeting(conversazione: list[dict]) -> str:
    system = (
        f"Sei Coach, l'assistente virtuale della palestra PowerGym. Oggi è {oggi()}. "
        "Rispondi al saluto in una o due frasi e proponi il tuo aiuto su corsi, lezioni, "
        f"abbonamenti e personal trainer. Non fornire dati (prezzi, orari): li hai solo tramite le funzioni.{extra_prompt()}"
    )
    completion = await llm([{"role": "system", "content": system}, *conversazione])
    return clean(completion.choices[0].message.content) or "Ciao! Come posso aiutarti?"


@cl.set_starters
async def set_starters():
    return [
        cl.Starter(label="Quali corsi avete?", message="Che corsi offre la palestra?"),
        cl.Starter(label="Prossime lezioni", message="Quando sono le prossime lezioni di yoga?"),
        cl.Starter(label="Prenota una lezione", message="Vorrei prenotare spinning il prima possibile"),
        cl.Starter(label="Personal trainer", message="Vorrei un personal trainer domani alle 10:00"),
    ]


@cl.on_chat_start
async def on_chat_start():
    # Cronologia "pulita": solo messaggi utente/assistente (i risultati dei tool restano nel turno)
    cl.user_session.set("history", [])
    print(f"[PowerGym] provider={PROVIDER} model={MODEL}")


@cl.on_message
async def main(message: cl.Message):
    try:
        await handle_message(message)
    except APITimeoutError:
        await cl.Message(author=AUTHOR, content="⏱️ Il modello non ha risposto in tempo. Controlla il terminale di Ollama e riprova.").send()
    except APIConnectionError:
        await cl.Message(author=AUTHOR, content="🔌 Impossibile contattare il modello: Ollama è avviato?").send()
    except APIError as e:
        await cl.Message(author=AUTHOR, content=f"Errore del modello: {e}").send()


async def handle_message(message: cl.Message):
    history: list[dict] = cl.user_session.get("history")
    history.append({"role": "user", "content": message.content})
    conversazione = history[-MAX_HISTORY:]

    # 1. Structured Output: analisi della richiesta
    async with cl.Step(name="Analisi richiesta (structured output)", type="llm") as step:
        richiesta = await classifica(conversazione, oggi())
        step.output = richiesta.model_dump_json(indent=2) if richiesta else "JSON non valido"

    # 2. Confini applicati dal codice, 3. Function calling
    if richiesta is None:
        answer = NON_CAPITO
    elif richiesta.intent == Intent.fuori_ambito:
        answer = FUORI_AMBITO
    elif richiesta.intent == Intent.saluto:
        answer = await answer_greeting(conversazione)
    else:
        answer = await answer_with_tools(conversazione, richiesta)

    history.append({"role": "assistant", "content": answer})
    cl.user_session.set("history", history)

    await cl.Message(author=AUTHOR, content=answer).send()

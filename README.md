# Selfwork Functions Calling – PowerGym Assistant

Replica del progetto della video-lezione (chatbot dei corsi di cucina con function calling) con un argomento a scelta: **l'assistente virtuale di una palestra**, realizzato con **Chainlit**, **function calling** e **structured output**.

## Come funziona

Ogni messaggio del cliente passa per tre fasi:

1. **Structured Output** (`gym_assistant/router.py`, `schemas.py`)
   Il modello classifica la richiesta in un oggetto Pydantic `RichiestaCliente`
   (`intent`, `course_name`, `date`, `time`) tramite `client.chat.completions.parse(response_format=...)`.
   I valori ammessi sono `Enum`, quindi il modello non può inventare intenti o corsi.
2. **Confini applicati dal codice** (`app.py`)
   Se l'intento è `fuori_ambito` (codice, altri argomenti, provocazioni, domande sul sistema) la risposta è fissa: il modello non viene nemmeno chiamato.
3. **Function calling** (`app.py`, `functions.py`, `tools.py`) — stesso ciclo della lezione
   Il modello riceve **solo i tool pertinenti all'intento**. Se al primo giro non ne chiama nessuno, il codice esegue il tool principale con i parametri estratti al punto 1: la risposta finale si basa sempre sui dati reali.

L'analisi strutturata e ogni chiamata a funzione sono visibili nella chat (step espandibili) e nel terminale.

## Tool disponibili

| Funzione | Descrizione | Parametri |
|---|---|---|
| `get_course_info` | descrizione, livello, durata e prezzo dei corsi | `course_name` (opz.) |
| `get_upcoming_classes` | calendario lezioni con posti liberi | `course_name`, `start_date` (opz.) |
| `book_class` | prenota un posto (senza data: la prima lezione libera) | `course_name`, `date` (opz.) |
| `get_membership_plans` | abbonamenti e prezzi | – |
| `get_trainer_availability` | slot liberi dei personal trainer | – |
| `book_personal_trainer` | prenota un personal trainer | `date`, `time`, `trainer_id` (opz.) |

I dati sono simulati in memoria e le date sono calcolate a partire da oggi.

## Struttura

```
app.py                      # Chainlit: structured output -> confini -> function calling
gym_assistant/
    config.py               # client OpenAI / Ollama scelto dal .env
    schemas.py              # modelli Pydantic per lo structured output
    router.py               # classificazione della richiesta (parse)
    functions.py            # schema TOOLS, tool per intento, dispatch
    tools.py                # CourseInfoTool, ScheduleTool, MembershipTool, BookingTool
public/                     # tema, css, logo, favicon, avatar
```

## Modello

- **Locale (consigliato per GPU da 8 GB):** `qwen3:8b` con Ollama: addestrato per tool calling e JSON, entra tutto in VRAM.
- **Cloud:** `gpt-4o-mini` con `PROVIDER=openai` (qui il tool viene anche forzato con `tool_choice="required"`).

## Avvio

```bash
poetry install
cp .env.example .env        # PROVIDER=ollama oppure openai (+ OPENAI_API_KEY)
ollama pull qwen3:8b        # solo se usi Ollama
poetry run chainlit run app.py -w
```

## Domande di prova

- Che corsi offre la palestra?
- Quando sono le prossime lezioni di CrossFit?
- Vorrei prenotare spinning il prima possibile
- Quanto costano gli abbonamenti?
- Vorrei un personal trainer domani alle 10:00
- Scrivimi un programma in Python → risposta fuori ambito

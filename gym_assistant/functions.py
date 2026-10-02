"""Schema dei tool (come nella lezione) e dispatch delle chiamate."""

import json

from gym_assistant.schemas import Intent
from gym_assistant.tools import BookingTool, CourseInfoTool, MembershipTool, ScheduleTool

course_tool = CourseInfoTool()
schedule_tool = ScheduleTool()
membership_tool = MembershipTool()
booking_tool = BookingTool()

COURSES = ", ".join(course_tool.course_names())


def _tool(name: str, description: str, properties: dict, required: list[str]) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {"type": "object", "properties": properties, "required": required},
        },
    }


TOOLS = [
    _tool(
        "get_course_info",
        "Descrizione, livello, durata e prezzo mensile dei corsi. Senza course_name restituisce tutti i corsi.",
        {"course_name": {"type": "string", "description": f"Nome di un corso (opzionale): {COURSES}"}},
        [],
    ),
    _tool(
        "get_upcoming_classes",
        "Calendario delle prossime lezioni di gruppo con data, orario e posti liberi.",
        {
            "course_name": {"type": "string", "description": f"Nome del corso (opzionale): {COURSES}"},
            "start_date": {"type": "string", "description": "Solo lezioni da questa data (YYYY-MM-DD, opzionale)"},
        },
        [],
    ),
    _tool(
        "book_class",
        "Prenota un posto in una lezione di gruppo. Senza date prenota la prima lezione con posti liberi.",
        {
            "course_name": {"type": "string", "description": f"Nome del corso: {COURSES}"},
            "date": {"type": "string", "description": "Data della lezione (YYYY-MM-DD, opzionale)"},
        },
        ["course_name"],
    ),
    _tool(
        "get_membership_plans",
        "Abbonamenti della palestra con prezzi e servizi inclusi.",
        {},
        [],
    ),
    _tool(
        "get_trainer_availability",
        "Date e orari liberi dei personal trainer.",
        {},
        [],
    ),
    _tool(
        "book_personal_trainer",
        "Prenota una sessione individuale con un personal trainer.",
        {
            "date": {"type": "string", "description": "Data (YYYY-MM-DD)"},
            "time": {"type": "string", "description": "Orario (HH:MM)"},
            "trainer_id": {"type": "string", "description": "ID del trainer, es. PT01 (opzionale)"},
        },
        ["date", "time"],
    ),
]

# Collega il nome della funzione scelta dal modello alla funzione Python reale
AVAILABLE_FUNCTIONS = {
    "get_course_info": course_tool.get_info,
    "get_upcoming_classes": schedule_tool.get_classes,
    "book_class": schedule_tool.book_class,
    "get_membership_plans": membership_tool.get_plans,
    "get_trainer_availability": booking_tool.get_availability,
    "book_personal_trainer": booking_tool.book_session,
}

# Per ogni intento il modello riceve SOLO i tool pertinenti: con un modello
# locale piccolo è il modo più efficace per fargli usare quello giusto.
# Il primo della lista è il tool "principale" usato come fallback.
TOOLS_BY_INTENT: dict[Intent, list[str]] = {
    Intent.info_corsi: ["get_course_info"],
    Intent.calendario_lezioni: ["get_upcoming_classes"],
    Intent.prenota_lezione: ["book_class", "get_upcoming_classes"],
    Intent.abbonamenti: ["get_membership_plans"],
    Intent.personal_trainer: ["get_trainer_availability", "book_personal_trainer"],
}


def tools_for(intent: Intent) -> list[dict]:
    names = TOOLS_BY_INTENT.get(intent, [])
    return [t for t in TOOLS if t["function"]["name"] in names]


def handle_tool_call(name: str, arguments: str) -> str:
    """Esegue la funzione richiesta dal modello e ne restituisce il risultato come testo."""
    function_to_call = AVAILABLE_FUNCTIONS.get(name)
    if function_to_call is None:
        return f"Errore: la funzione '{name}' non esiste."

    # Il JSON generato dal modello potrebbe non essere valido: va gestito
    try:
        args = json.loads(arguments or "{}")
    except json.JSONDecodeError:
        return f"Errore: argomenti non validi per '{name}': {arguments}"

    # Scarta argomenti vuoti (alcuni modelli inviano "" o null per gli opzionali)
    args = {k: v for k, v in args.items() if v not in (None, "", [])}

    print("*" * 80)
    print("function name:", name)
    print("function args:", args)

    # Qualsiasi errore torna al modello come testo, così la chat non si blocca
    try:
        result = function_to_call(**args)
    except Exception as e:
        result = f"Errore nella chiamata a '{name}' con argomenti {args}: {e}"

    print("result:", result)
    print("*" * 80)
    return result

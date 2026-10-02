"""Tool (funzioni) che il modello può chiamare tramite function calling.

Stessa struttura del progetto della lezione (CourseInfoTool, ScheduleTool, BookingTool):
classi che simulano un database in memoria. Le date sono calcolate a partire da oggi,
così l'esempio resta sempre attuale.
"""

from datetime import date, timedelta


def _giorno(offset: int) -> str:
    """Data di oggi + offset giorni nel formato YYYY-MM-DD."""
    return (date.today() + timedelta(days=offset)).isoformat()


def _chiave(nome: str) -> str:
    return str(nome).lower().strip().replace(" ", "_")


class CourseInfoTool:
    """Informazioni sui corsi della palestra."""

    def __init__(self):
        self.courses = {
            "sala_pesi": {
                "name": "Sala Pesi",
                "description": "Allenamento con macchine e pesi liberi, scheda personalizzata inclusa",
                "level": "tutti i livelli",
                "duration": "accesso libero negli orari di apertura (nessuna prenotazione)",
                "price": 39.90,
            },
            "crossfit": {
                "name": "CrossFit",
                "description": "Allenamento funzionale ad alta intensità in piccoli gruppi",
                "level": "intermedio/avanzato",
                "duration": "lezioni da 60 minuti",
                "price": 69.90,
            },
            "yoga": {
                "name": "Yoga",
                "description": "Hatha e vinyasa yoga per mobilità, respirazione e rilassamento",
                "level": "tutti i livelli",
                "duration": "lezioni da 75 minuti",
                "price": 49.90,
            },
            "pilates": {
                "name": "Pilates",
                "description": "Rinforzo del core e postura, anche con reformer",
                "level": "principiante/intermedio",
                "duration": "lezioni da 50 minuti",
                "price": 54.90,
            },
            "spinning": {
                "name": "Spinning",
                "description": "Ciclismo indoor a ritmo di musica, ottimo per il cardio",
                "level": "tutti i livelli",
                "duration": "lezioni da 45 minuti",
                "price": 44.90,
            },
            "boxe": {
                "name": "Boxe",
                "description": "Tecnica, sacco e preparazione atletica, senza sparring obbligatorio",
                "level": "tutti i livelli",
                "duration": "lezioni da 60 minuti",
                "price": 59.90,
            },
        }

    def course_names(self) -> list[str]:
        return [c["name"] for c in self.courses.values()]

    @staticmethod
    def _format(course: dict) -> str:
        return (
            f"Corso: {course['name']}\n"
            f"Descrizione: {course['description']}\n"
            f"Livello: {course['level']}\n"
            f"Durata: {course['duration']}\n"
            f"Prezzo mensile: €{course['price']:.2f}"
        )

    def get_info(self, course_name: str | None = None) -> str:
        # Senza nome restituisce tutti i corsi
        if not course_name:
            return "Corsi disponibili:\n\n" + "\n\n".join(
                self._format(c) for c in self.courses.values()
            )
        course = self.courses.get(_chiave(course_name))
        if not course:
            return (
                f"Corso '{course_name}' non trovato. "
                f"Corsi disponibili: {', '.join(self.course_names())}"
            )
        return self._format(course)


class ScheduleTool:
    """Calendario delle lezioni di gruppo e prenotazione di un posto."""

    def __init__(self):
        self.classes = [
            {"course_name": "CrossFit", "date": _giorno(1), "time": "07:00", "spots_available": 4},
            {"course_name": "Yoga", "date": _giorno(1), "time": "19:00", "spots_available": 10},
            {"course_name": "Spinning", "date": _giorno(2), "time": "18:30", "spots_available": 0},
            {"course_name": "Pilates", "date": _giorno(2), "time": "12:30", "spots_available": 6},
            {"course_name": "Boxe", "date": _giorno(3), "time": "20:00", "spots_available": 8},
            {"course_name": "CrossFit", "date": _giorno(4), "time": "19:00", "spots_available": 2},
            {"course_name": "Yoga", "date": _giorno(5), "time": "09:00", "spots_available": 12},
            {"course_name": "Spinning", "date": _giorno(6), "time": "18:30", "spots_available": 9},
            {"course_name": "Pilates", "date": _giorno(8), "time": "18:00", "spots_available": 5},
            {"course_name": "Boxe", "date": _giorno(10), "time": "20:00", "spots_available": 7},
        ]

    @staticmethod
    def _format(lista: list[dict]) -> str:
        righe = []
        for c in lista:
            posti = f"{c['spots_available']} posti liberi" if c["spots_available"] else "COMPLETA"
            righe.append(f"- {c['course_name']}: {c['date']} alle {c['time']} ({posti})")
        return "\n".join(righe)

    def get_classes(self, course_name: str | None = None, start_date: str | None = None) -> str:
        if course_name and _chiave(course_name) == "sala_pesi":
            return "La Sala Pesi è ad accesso libero: non ci sono lezioni da prenotare."

        filtered = self.classes
        if course_name:
            filtered = [c for c in filtered if _chiave(c["course_name"]) == _chiave(course_name)]
        if start_date:
            filtered = [c for c in filtered if c["date"] >= start_date]

        if not filtered:
            return (
                "Nessuna lezione trovata per i criteri indicati. "
                f"Tutte le prossime lezioni:\n{self._format(self.classes)}"
            )
        return f"Prossime lezioni:\n{self._format(filtered)}"

    def book_class(self, course_name: str, date: str | None = None) -> str:
        """Prenota un posto; senza data prende la prima lezione con posti liberi."""
        if _chiave(course_name) == "sala_pesi":
            return "La Sala Pesi è ad accesso libero: non serve prenotare."

        candidates = [
            c for c in self.classes
            if _chiave(c["course_name"]) == _chiave(course_name) and c["spots_available"] > 0
        ]
        if date:
            candidates = [c for c in candidates if c["date"] == date]

        if not candidates:
            quando = f" il {date}" if date else ""
            return (
                f"Nessuna lezione di {course_name} con posti liberi{quando}. "
                f"{self.get_classes(course_name)}"
            )

        lezione = min(candidates, key=lambda c: (c["date"], c["time"]))
        lezione["spots_available"] -= 1
        return (
            f"PRENOTAZIONE CONFERMATA: {lezione['course_name']} il {lezione['date']} "
            f"alle {lezione['time']}. Posti ancora liberi: {lezione['spots_available']}"
        )


class MembershipTool:
    """Piani di abbonamento (tool senza parametri)."""

    def __init__(self):
        self.plans = [
            {"name": "Mensile", "price": 59.00, "includes": "sala pesi + 1 corso a scelta"},
            {"name": "Trimestrale", "price": 159.00, "includes": "sala pesi + 2 corsi a scelta"},
            {"name": "Annuale", "price": 549.00, "includes": "sala pesi + tutti i corsi + 2 sessioni con personal trainer"},
            {"name": "Open Student (under 26)", "price": 45.00, "includes": "sala pesi + 1 corso, mensile"},
        ]

    def get_plans(self) -> str:
        righe = [f"- {p['name']}: €{p['price']:.2f} ({p['includes']})" for p in self.plans]
        return "Abbonamenti disponibili:\n" + "\n".join(righe)


class BookingTool:
    """Disponibilità e prenotazione dei personal trainer."""

    def __init__(self):
        self.available_slots = [
            {"trainer_id": "PT01", "trainer_name": "Marco (forza e ipertrofia)", "date": _giorno(1), "time": "10:00"},
            {"trainer_id": "PT02", "trainer_name": "Giulia (dimagrimento e cardio)", "date": _giorno(1), "time": "17:00"},
            {"trainer_id": "PT03", "trainer_name": "Luca (preparazione atletica)", "date": _giorno(2), "time": "09:00"},
            {"trainer_id": "PT01", "trainer_name": "Marco (forza e ipertrofia)", "date": _giorno(3), "time": "18:00"},
            {"trainer_id": "PT04", "trainer_name": "Sara (postura e pilates)", "date": _giorno(3), "time": "11:30"},
            {"trainer_id": "PT02", "trainer_name": "Giulia (dimagrimento e cardio)", "date": _giorno(5), "time": "08:30"},
            {"trainer_id": "PT03", "trainer_name": "Luca (preparazione atletica)", "date": _giorno(6), "time": "19:00"},
            {"trainer_id": "PT04", "trainer_name": "Sara (postura e pilates)", "date": _giorno(7), "time": "15:00"},
        ]

    def _format(self) -> str:
        return "\n".join(
            f"- {s['date']} alle {s['time']}: {s['trainer_name']} [{s['trainer_id']}]"
            for s in self.available_slots
        )

    def get_availability(self) -> str:
        return f"Disponibilità dei personal trainer:\n{self._format()}"

    def book_session(self, date: str, time: str, trainer_id: str | None = None) -> str:
        available = [s for s in self.available_slots if s["date"] == date and s["time"] == time]
        if trainer_id:
            available = [s for s in available if s["trainer_id"] == trainer_id.upper()]

        if not available:
            return (
                f"Nessun personal trainer disponibile il {date} alle {time}. "
                f"Disponibilità:\n{self._format()}"
            )

        slot = available[0]
        self.available_slots.remove(slot)  # lo slot non è più disponibile
        return (
            f"PRENOTAZIONE CONFERMATA con {slot['trainer_name']} "
            f"il {slot['date']} alle {slot['time']}"
        )

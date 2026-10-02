"""Structured Output: schema Pydantic con cui il modello classifica ogni messaggio.

Il modello è obbligato a rispondere con un JSON valido per questo schema
(response_format), quindi il codice sa con certezza cosa vuole il cliente
prima di decidere quali tool usare o se rifiutare la richiesta.
"""

from enum import Enum

from pydantic import BaseModel, Field


class Intent(str, Enum):
    info_corsi = "info_corsi"                  # elenco corsi, descrizioni, prezzi dei corsi
    calendario_lezioni = "calendario_lezioni"  # date/orari/posti delle lezioni
    prenota_lezione = "prenota_lezione"        # iscriversi / prenotare un posto in una lezione
    abbonamenti = "abbonamenti"                # piani di abbonamento e prezzi
    personal_trainer = "personal_trainer"      # disponibilità o prenotazione personal trainer
    saluto = "saluto"                          # saluti, ringraziamenti, chiacchiere sulla palestra
    fuori_ambito = "fuori_ambito"              # tutto ciò che non riguarda la palestra


class Corso(str, Enum):
    sala_pesi = "Sala Pesi"
    crossfit = "CrossFit"
    yoga = "Yoga"
    pilates = "Pilates"
    spinning = "Spinning"
    boxe = "Boxe"


class RichiestaCliente(BaseModel):
    intent: Intent = Field(description="Cosa vuole il cliente")
    course_name: Corso | None = Field(description="Corso citato nella conversazione, se presente")
    date: str | None = Field(description="Data richiesta in formato YYYY-MM-DD, se presente")
    time: str | None = Field(description="Orario richiesto in formato HH:MM, se presente")

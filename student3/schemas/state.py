"""
schemas/state.py
================
Schéma d'état partagé entre tous les agents LangGraph du projet médical.
Auteur   : Étudiant 1 (défini en commun avec l'équipe)
Rôle E3  : lecture seule – on consomme ce state, on ne le modifie pas en dehors
           des nœuds physician_review et report_agent.

Structure LangGraph : chaque clé est mise à jour par reduce (Annotated + add_messages
pour les listes) afin que les nœuds puissent enrichir l'état sans écraser les données
des autres agents.
"""

from __future__ import annotations

from typing import Annotated, Optional
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Sous-modèles de données
# ---------------------------------------------------------------------------

class PatientInfo(BaseModel):
    """Informations de base du patient saisies en amont (via l'API / frontend)."""
    patient_id: str
    nom: str
    age: int
    sexe: str                       # "M" | "F" | "autre"
    antecedents: list[str] = []     # ex. ["diabète", "hypertension"]


class DiagnosticSummary(BaseModel):
    """Résultat produit par DiagnosticAgent (Étudiant 2)."""
    symptomes: list[str]
    hypotheses: list[str]           # liste de diagnostics possibles
    score_urgence: int              # 0–10
    interim_care: str               # conseils immédiats recommandés


class PhysicianDecision(BaseModel):
    """
    Décision du médecin après review HITL.
    Remplie par le nœud physician_review (Étudiant 3) via LangGraph Studio.
    """
    approuve: bool                  # True = valide le diagnostic AI
    diagnostic_final: str           # diagnostic retenu par le médecin
    commentaire: Optional[str] = None
    orientation: str = ""           # ex. "urgences", "médecin traitant", "téléconsultation"


class RapportFinal(BaseModel):
    """Rapport structuré produit par ReportAgent (Étudiant 3)."""
    resume_consultation: str
    diagnostic_final: str
    recommandations: list[str]
    niveau_urgence: str             # "faible" | "modéré" | "élevé" | "critique"
    orientation: str
    genere_le: str                  # datetime ISO


# ---------------------------------------------------------------------------
# MedicalState – état global du graphe LangGraph
# ---------------------------------------------------------------------------

class MedicalState(BaseModel):
    """
    État central du graphe LangGraph médical.

    Convention d'annotation :
    - Les champs simples (str, int, bool) sont remplacés (last-write-wins).
    - Les listes de messages utilisent `Annotated[list, add_messages]`
      pour être cumulatives (append-only via LangGraph).
    - Les sous-modèles (PatientInfo, etc.) sont optionnels au démarrage
      et remplis progressivement par chaque nœud.
    """

    # --- Données d'entrée (remplies avant le START) ---
    patient: Optional[PatientInfo] = None
    motif_consultation: str = ""

    # --- Produit par DiagnosticAgent (E2) ---
    diagnostic_summary: Optional[DiagnosticSummary] = None

    # --- Messages échangés dans le graphe (cumulatifs) ---
    messages: Annotated[list, add_messages] = Field(default_factory=list)

    # --- Produit par PhysicianReview HITL (E3) ---
    physician_decision: Optional[PhysicianDecision] = None

    # --- Produit par ReportAgent (E3) ---
    rapport_final: Optional[RapportFinal] = None

    # --- Métadonnées de contrôle de flux ---
    etape_courante: str = "start"   # utilisé par le Supervisor (E1) pour le routage
    erreur: Optional[str] = None    # message d'erreur éventuel (nœud error-handler)

    class Config:
        # Permet d'utiliser des types arbitraires (ex. datetime) dans Pydantic v1
        arbitrary_types_allowed = True
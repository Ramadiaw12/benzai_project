"""
schemas/pydantic_models.py
==========================
Modèles Pydantic utilisés comme schémas d'entrée / sortie de l'API FastAPI.
Séparés du MedicalState (qui appartient à LangGraph) pour ne pas coupler
la couche HTTP à la couche agent.

Auteur : Étudiant 3
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# 1. Requête de consultation (POST /consultation/start)
# ---------------------------------------------------------------------------

class ConsultationRequest(BaseModel):
    """
    Corps de la requête pour démarrer une nouvelle consultation.
    Envoyé par le frontend (Étudiant 4) ou via Swagger UI.
    """
    patient_id: str = Field(..., description="Identifiant unique du patient")
    nom: str = Field(..., min_length=2, description="Nom complet du patient")
    age: int = Field(..., ge=0, le=130, description="Âge en années")
    sexe: str = Field(..., pattern="^(M|F|autre)$", description="Sexe : M, F ou autre")
    antecedents: list[str] = Field(
        default_factory=list,
        description="Liste des antécédents médicaux connus"
    )
    motif_consultation: str = Field(
        ..., min_length=5,
        description="Motif principal de la consultation (symptômes décrits par le patient)"
    )

    @field_validator("nom")
    @classmethod
    def capitaliser_nom(cls, v: str) -> str:
        """Normalise la casse du nom."""
        return v.strip().title()


class ConsultationResponse(BaseModel):
    """Réponse renvoyée après la création d'une consultation."""
    consultation_id: str       # UUID généré côté serveur
    status: str                # "en_cours" | "en_attente_review" | "terminée"
    message: str


# ---------------------------------------------------------------------------
# 2. Mise à jour du statut (GET /consultation/{id}/status)
# ---------------------------------------------------------------------------

class ConsultationStatus(BaseModel):
    """État courant d'une consultation en cours."""
    consultation_id: str
    etape_courante: str        # ex. "diagnostic", "physician_review", "rapport"
    status: str
    diagnostic_summary: Optional[dict] = None   # résumé partiel si disponible
    erreur: Optional[str] = None


# ---------------------------------------------------------------------------
# 3. Review médecin – HITL (POST /review/{id})
# ---------------------------------------------------------------------------

class ReviewUpdate(BaseModel):
    """
    Données envoyées par le médecin pour valider ou corriger le diagnostic AI.
    Dans notre architecture, cela peut aussi être soumis via LangGraph Studio ;
    ce modèle sert de fallback API ou de documentation du format attendu.
    """
    consultation_id: str
    approuve: bool = Field(..., description="True si le médecin valide le diagnostic IA")
    diagnostic_final: str = Field(
        ..., min_length=3,
        description="Diagnostic retenu par le médecin (peut différer du diagnostic IA)"
    )
    commentaire: Optional[str] = Field(
        None, description="Observations ou nuances ajoutées par le médecin"
    )
    orientation: str = Field(
        ...,
        description="Orientation du patient : 'urgences' | 'médecin traitant' | 'téléconsultation' | ..."
    )


class ReviewResponse(BaseModel):
    """Confirmation après soumission de la review médecin."""
    consultation_id: str
    status: str          # "review_enregistrée"
    next_step: str       # "génération_rapport"


# ---------------------------------------------------------------------------
# 4. Rapport final (GET /report/{id})
# ---------------------------------------------------------------------------

class RapportResponse(BaseModel):
    """Rapport médical final structuré, retourné par l'API."""
    consultation_id: str
    patient_id: str
    resume_consultation: str
    diagnostic_final: str
    recommandations: list[str]
    niveau_urgence: str         # "faible" | "modéré" | "élevé" | "critique"
    orientation: str
    commentaire_medecin: Optional[str] = None
    genere_le: datetime


# ---------------------------------------------------------------------------
# 5. Modèle d'erreur standardisé
# ---------------------------------------------------------------------------

class ErrorResponse(BaseModel):
    """Format unifié pour toutes les erreurs HTTP de l'API."""
    code: int
    detail: str
    consultation_id: Optional[str] = None
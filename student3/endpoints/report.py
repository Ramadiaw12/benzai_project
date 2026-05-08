"""
api/endpoints/report.py
=======================
Endpoints FastAPI – Récupération du rapport médical final.

Routes exposées (préfixe /report) :
    GET /report/{consultation_id}          → Rapport complet (JSON)
    GET /report/{consultation_id}/summary  → Résumé court (pour le frontend)

Auteur : Étudiant 3
"""

from __future__ import annotations

import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException

from schemas.pydantic_models import RapportResponse, ErrorResponse
from api.endpoints.consultation import _consultations

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Endpoint 1 – Rapport complet
# ---------------------------------------------------------------------------

@router.get(
    "/{consultation_id}",
    response_model=RapportResponse,
    summary="Récupérer le rapport médical final",
    description=(
        "Retourne le rapport médical complet généré par ReportAgent (GPT-4). "
        "Disponible uniquement quand l'étape est `terminé`."
    ),
    responses={
        404: {"model": ErrorResponse, "description": "Consultation introuvable"},
        202: {"description": "Rapport pas encore généré"},
    },
)
async def get_report(consultation_id: str) -> RapportResponse:
    """
    Retourne le rapport final si la consultation est terminée.
    Retourne 202 si le rapport est encore en cours de génération.
    """
    state = _consultations.get(consultation_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"Consultation '{consultation_id}' introuvable.")

    if state.rapport_final is None:
        raise HTTPException(
            status_code=202,
            detail=(
                f"Le rapport n'est pas encore disponible. "
                f"Étape courante : '{state.etape_courante}'. Réessayez dans quelques instants."
            ),
        )

    rapport = state.rapport_final

    # Commentaire médecin (optionnel)
    commentaire_medecin = None
    if state.physician_decision:
        commentaire_medecin = state.physician_decision.commentaire

    patient_id = state.patient.patient_id if state.patient else "inconnu"

    return RapportResponse(
        consultation_id=consultation_id,
        patient_id=patient_id,
        resume_consultation=rapport.resume_consultation,
        diagnostic_final=rapport.diagnostic_final,
        recommandations=rapport.recommandations,
        niveau_urgence=rapport.niveau_urgence,
        orientation=rapport.orientation,
        commentaire_medecin=commentaire_medecin,
        genere_le=datetime.fromisoformat(rapport.genere_le),
    )


# ---------------------------------------------------------------------------
# Endpoint 2 – Résumé court pour le frontend
# ---------------------------------------------------------------------------

@router.get(
    "/{consultation_id}/summary",
    summary="Résumé court du rapport (pour le frontend)",
    description="Version allégée du rapport, adaptée pour un affichage dashboard.",
    responses={
        404: {"model": ErrorResponse},
        202: {"description": "Rapport pas encore disponible"},
    },
)
async def get_report_summary(consultation_id: str) -> dict:
    """
    Retourne uniquement les champs essentiels du rapport pour le frontend (E4).
    Évite de transférer des données volumineuses inutilement.
    """
    state = _consultations.get(consultation_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"Consultation '{consultation_id}' introuvable.")

    if state.rapport_final is None:
        raise HTTPException(
            status_code=202,
            detail="Rapport en cours de génération.",
        )

    rapport = state.rapport_final

    return {
        "consultation_id": consultation_id,
        "diagnostic_final": rapport.diagnostic_final,
        "niveau_urgence": rapport.niveau_urgence,
        "orientation": rapport.orientation,
        "nb_recommandations": len(rapport.recommandations),
        "genere_le": rapport.genere_le,
        "status": "terminée",
    }
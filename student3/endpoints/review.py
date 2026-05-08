"""
api/endpoints/review.py
=======================
Endpoints FastAPI – Review médecin (HITL fallback via API).

Dans notre architecture, le HITL se fait principalement via LangGraph Studio.
Ces endpoints servent de fallback (ou de test) pour soumettre la décision
médecin sans passer par Studio.

Routes exposées (préfixe /review) :
    GET  /review/{consultation_id}        → Voir le diagnostic en attente de review
    POST /review/{consultation_id}        → Soumettre la décision médecin

Auteur : Étudiant 3
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from schemas.pydantic_models import ReviewUpdate, ReviewResponse, ErrorResponse
from schemas.state import PhysicianDecision

# Import de la "base de données" partagée avec consultation.py
from api.endpoints.consultation import _consultations

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Endpoint 1 – Récupérer le diagnostic en attente de review
# ---------------------------------------------------------------------------

@router.get(
    "/{consultation_id}",
    summary="Récupérer le diagnostic en attente de review médecin",
    description=(
        "Retourne le résumé du diagnostic IA pour que le médecin puisse "
        "l'examiner avant de soumettre sa décision. "
        "Retourne 404 si la consultation n'existe pas, "
        "400 si elle n'est pas encore à l'étape `physician_review`."
    ),
    responses={
        404: {"model": ErrorResponse},
        400: {"model": ErrorResponse},
    },
)
async def get_pending_review(consultation_id: str) -> dict:
    """
    Expose le diagnostic IA + informations patient pour la review médecin.
    """
    state = _consultations.get(consultation_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"Consultation '{consultation_id}' introuvable.")

    if state.etape_courante != "physician_review":
        raise HTTPException(
            status_code=400,
            detail=(
                f"Cette consultation n'est pas à l'étape review. "
                f"Étape courante : '{state.etape_courante}'."
            ),
        )

    # Construire la réponse lisible pour le médecin
    patient_info = None
    if state.patient:
        patient_info = state.patient.model_dump()

    diag = None
    if state.diagnostic_summary:
        diag = state.diagnostic_summary.model_dump()

    return {
        "consultation_id": consultation_id,
        "patient": patient_info,
        "motif_consultation": state.motif_consultation,
        "diagnostic_ia": diag,
        "instructions": (
            "Examinez le diagnostic IA ci-dessus. "
            "Soumettez votre décision via POST /review/{consultation_id} "
            "ou directement dans LangGraph Studio."
        ),
    }


# ---------------------------------------------------------------------------
# Endpoint 2 – Soumettre la décision médecin
# ---------------------------------------------------------------------------

@router.post(
    "/{consultation_id}",
    response_model=ReviewResponse,
    summary="Soumettre la décision du médecin (HITL fallback)",
    description=(
        "Enregistre la décision du médecin (validation/correction du diagnostic IA) "
        "et reprend l'exécution du graphe pour générer le rapport final. "
        "**Note** : dans l'architecture principale, cette action se fait via LangGraph Studio."
    ),
    responses={
        404: {"model": ErrorResponse},
        400: {"model": ErrorResponse},
        409: {"model": ErrorResponse, "description": "Review déjà soumise"},
    },
)
async def submit_review(consultation_id: str, body: ReviewUpdate) -> ReviewResponse:
    """
    1. Vérifie que la consultation est bien à l'étape `physician_review`.
    2. Enregistre la décision du médecin dans l'état LangGraph.
    3. Fait avancer l'étape à `rapport` pour déclencher ReportAgent.
    """
    # Vérifications préliminaires
    if body.consultation_id != consultation_id:
        raise HTTPException(
            status_code=400,
            detail="L'`consultation_id` dans l'URL et dans le corps ne correspondent pas.",
        )

    state = _consultations.get(consultation_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"Consultation '{consultation_id}' introuvable.")

    if state.etape_courante == "terminé":
        raise HTTPException(status_code=409, detail="La consultation est déjà terminée.")

    if state.physician_decision is not None:
        raise HTTPException(status_code=409, detail="Une review a déjà été soumise pour cette consultation.")

    if state.etape_courante not in ("physician_review", "en_attente_review"):
        raise HTTPException(
            status_code=400,
            detail=f"La consultation n'est pas à l'étape review (étape courante : '{state.etape_courante}').",
        )

    # Enregistrer la décision médecin
    decision = PhysicianDecision(
        approuve=body.approuve,
        diagnostic_final=body.diagnostic_final,
        commentaire=body.commentaire,
        orientation=body.orientation,
    )
    state.physician_decision = decision
    state.etape_courante = "rapport"

    logger.info(
        "[Review] Décision enregistrée – id=%s approuvé=%s diagnostic='%s'",
        consultation_id,
        body.approuve,
        body.diagnostic_final,
    )

    # NOTE pour E1 : ici, en production, tu dois reprendre (resume) le graphe
    # LangGraph interrompu, par exemple :
    #   await compiled_graph.aupdate_state(thread_id, {"physician_decision": decision})
    #   await compiled_graph.ainvoke(None, config={"configurable": {"thread_id": ...}})

    return ReviewResponse(
        consultation_id=consultation_id,
        status="review_enregistrée",
        next_step="génération_rapport",
    )
"""
api/endpoints/consultation.py
==============================
Endpoints FastAPI – Gestion du cycle de vie d'une consultation.

Routes exposées (préfixe /consultation) :
    POST  /consultation/start          → Démarrer une consultation
    GET   /consultation/{id}/status    → Consulter l'état en cours
    GET   /consultation/{id}/diagnostic → Récupérer le diagnostic IA (si prêt)
    POST  /consultation/{id}/cancel    → Annuler une consultation

Auteur : Étudiant 3
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, BackgroundTasks

from schemas.pydantic_models import (
    ConsultationRequest,
    ConsultationResponse,
    ConsultationStatus,
    ErrorResponse,
)
from schemas.state import MedicalState, PatientInfo

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# "Base de données" en mémoire (remplacée par Redis / DB en production)
# ---------------------------------------------------------------------------
# Clé : consultation_id (str UUID)
# Valeur : MedicalState (état courant du graphe)

_consultations: dict[str, MedicalState] = {}


# ---------------------------------------------------------------------------
# Endpoint 1 – Démarrer une consultation
# ---------------------------------------------------------------------------

@router.post(
    "/start",
    response_model=ConsultationResponse,
    status_code=201,
    summary="Démarrer une nouvelle consultation",
    description=(
        "Initialise l'état LangGraph avec les informations patient et lance "
        "le graphe multi-agents en arrière-plan. "
        "Retourne un `consultation_id` à conserver pour les appels suivants."
    ),
    responses={422: {"model": ErrorResponse, "description": "Données invalides"}},
)
async def start_consultation(
    body: ConsultationRequest,
    background_tasks: BackgroundTasks,
) -> ConsultationResponse:
    """
    1. Valide les données patient via Pydantic (automatique).
    2. Crée un MedicalState initial.
    3. Lance le graphe LangGraph en tâche de fond.
    4. Retourne immédiatement le consultation_id.
    """
    consultation_id = str(uuid.uuid4())
    logger.info("[Consultation] Démarrage – id=%s patient=%s", consultation_id, body.patient_id)

    # Construire l'état initial du graphe
    initial_state = MedicalState(
        patient=PatientInfo(
            patient_id=body.patient_id,
            nom=body.nom,
            age=body.age,
            sexe=body.sexe,
            antecedents=body.antecedents,
        ),
        motif_consultation=body.motif_consultation,
        etape_courante="diagnostic",
    )
    _consultations[consultation_id] = initial_state

    # Lancer le graphe en arrière-plan (non bloquant)
    # NOTE pour E1 : remplace `_run_graph_stub` par l'appel réel au graphe compilé.
    background_tasks.add_task(_run_graph_stub, consultation_id, initial_state)

    return ConsultationResponse(
        consultation_id=consultation_id,
        status="en_cours",
        message="Consultation démarrée. Le DiagnosticAgent collecte les données.",
    )


# ---------------------------------------------------------------------------
# Endpoint 2 – Statut d'une consultation
# ---------------------------------------------------------------------------

@router.get(
    "/{consultation_id}/status",
    response_model=ConsultationStatus,
    summary="Obtenir l'état courant d'une consultation",
    responses={404: {"model": ErrorResponse, "description": "Consultation introuvable"}},
)
async def get_consultation_status(consultation_id: str) -> ConsultationStatus:
    """
    Retourne l'étape courante et un résumé de l'état du graphe.
    Utilisé par le frontend pour afficher la progression en temps réel.
    """
    state = _get_state_or_404(consultation_id)

    # Sérialiser le diagnostic_summary si disponible
    diag_summary = None
    if state.diagnostic_summary:
        diag_summary = state.diagnostic_summary.model_dump()

    return ConsultationStatus(
        consultation_id=consultation_id,
        etape_courante=state.etape_courante,
        status=_etape_to_status(state.etape_courante),
        diagnostic_summary=diag_summary,
        erreur=state.erreur,
    )


# ---------------------------------------------------------------------------
# Endpoint 3 – Récupérer le diagnostic IA
# ---------------------------------------------------------------------------

@router.get(
    "/{consultation_id}/diagnostic",
    summary="Obtenir le diagnostic IA (DiagnosticAgent)",
    responses={
        404: {"model": ErrorResponse},
        202: {"description": "Diagnostic pas encore disponible"},
    },
)
async def get_diagnostic(consultation_id: str) -> Any:
    """
    Retourne le `diagnostic_summary` produit par DiagnosticAgent (E2).
    Retourne 202 si le diagnostic est encore en cours de calcul.
    """
    state = _get_state_or_404(consultation_id)

    if state.diagnostic_summary is None:
        raise HTTPException(
            status_code=202,
            detail="Le diagnostic IA est en cours de calcul. Réessayez dans quelques instants.",
        )

    return {
        "consultation_id": consultation_id,
        "diagnostic": state.diagnostic_summary.model_dump(),
        "etape_courante": state.etape_courante,
    }


# ---------------------------------------------------------------------------
# Endpoint 4 – Annuler une consultation
# ---------------------------------------------------------------------------

@router.post(
    "/{consultation_id}/cancel",
    summary="Annuler une consultation en cours",
    responses={404: {"model": ErrorResponse}},
)
async def cancel_consultation(consultation_id: str) -> dict:
    """
    Marque la consultation comme annulée.
    En production : interrompre le thread/coroutine LangGraph associé.
    """
    state = _get_state_or_404(consultation_id)

    if state.etape_courante == "terminé":
        raise HTTPException(status_code=400, detail="La consultation est déjà terminée.")

    state.etape_courante = "annulée"
    logger.info("[Consultation] Annulation – id=%s", consultation_id)

    return {"consultation_id": consultation_id, "status": "annulée"}


# ---------------------------------------------------------------------------
# Fonctions utilitaires privées
# ---------------------------------------------------------------------------

def _get_state_or_404(consultation_id: str) -> MedicalState:
    """Récupère l'état ou lève HTTP 404."""
    state = _consultations.get(consultation_id)
    if state is None:
        raise HTTPException(
            status_code=404,
            detail=f"Consultation '{consultation_id}' introuvable.",
        )
    return state


def _etape_to_status(etape: str) -> str:
    """Convertit l'étape interne LangGraph en label lisible pour le frontend."""
    mapping = {
        "diagnostic": "en_cours",
        "physician_review": "en_attente_review",
        "rapport": "génération_rapport",
        "terminé": "terminée",
        "erreur": "erreur",
        "annulée": "annulée",
    }
    return mapping.get(etape, "en_cours")


async def _run_graph_stub(consultation_id: str, state: MedicalState) -> None:
    """
    Stub de lancement du graphe LangGraph.
    À remplacer par l'appel réel au graphe compilé (graph.py – Étudiant 1).

    Exemple d'intégration avec graph.py :
        from graph import compiled_graph
        result = await compiled_graph.ainvoke(state.model_dump())
        _consultations[consultation_id] = MedicalState(**result)
    """
    logger.info("[GraphStub] Graphe lancé pour consultation=%s (stub)", consultation_id)
    # En production : exécuter compiled_graph.ainvoke(state) ici
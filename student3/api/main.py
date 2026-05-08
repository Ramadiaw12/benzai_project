"""
api/main.py
===========
Point d'entrée de l'application FastAPI – Projet multi-agents médical.

Lance le serveur :
    uvicorn api.main:app --reload --port 8000

Documentation interactive :
    http://localhost:8000/docs   (Swagger UI)
    http://localhost:8000/redoc  (ReDoc)

Auteur : Étudiant 3
"""

from __future__ import annotations

import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.endpoints import consultation, review, report

# ---------------------------------------------------------------------------
# Configuration du logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s – %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Création de l'application FastAPI
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Système Multi-agents Médical",
    description=(
        "API REST du projet LangGraph médical.\n\n"
        "**Flux complet** : `POST /consultation/start` → DiagnosticAgent → "
        "PhysicianReview (HITL) → ReportAgent → `GET /report/{id}`\n\n"
        "Étudiant 3 – PhysicianReview · ReportAgent · FastAPI"
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)


# ---------------------------------------------------------------------------
# Middleware CORS (nécessaire pour le frontend React de l'Étudiant 4)
# ---------------------------------------------------------------------------

ALLOWED_ORIGINS = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:3000,http://localhost:5173"   # Vite / CRA par défaut
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Inclusion des routers (un fichier par domaine)
# ---------------------------------------------------------------------------

app.include_router(
    consultation.router,
    prefix="/consultation",
    tags=["Consultation"],
)

app.include_router(
    review.router,
    prefix="/review",
    tags=["Review Médecin (HITL)"],
)

app.include_router(
    report.router,
    prefix="/report",
    tags=["Rapport Final"],
)


# ---------------------------------------------------------------------------
# Routes utilitaires
# ---------------------------------------------------------------------------

@app.get("/", tags=["Santé"])
async def root() -> dict:
    """Point de contrôle de base – vérifie que l'API est en ligne."""
    return {"status": "ok", "message": "API Médicale Multi-agents opérationnelle."}


@app.get("/health", tags=["Santé"])
async def health_check() -> dict:
    """Health check pour Docker / load balancer."""
    return {"status": "healthy", "version": app.version}


# ---------------------------------------------------------------------------
# Gestionnaire d'erreurs global
# ---------------------------------------------------------------------------

@app.exception_handler(Exception)
async def global_exception_handler(request, exc: Exception) -> JSONResponse:
    """
    Capture toutes les exceptions non gérées et renvoie une réponse JSON
    cohérente avec le modèle ErrorResponse (pydantic_models.py).
    """
    logger.error("Erreur non gérée : %s", exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"code": 500, "detail": f"Erreur interne du serveur : {exc}"},
    )
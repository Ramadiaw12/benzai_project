# DIAWANE - Etudiant 3 — API FastAPI
"""
===============================================================
OrientaMed — api.py
Étudiant 3 : API FastAPI
===============================================================

ADAPTÉ AU STATE DE STÉCY (state.py) :
    - patient_id            : identifiant unique du patient
    - patient_info          : données patient (age, gender, etc.)
    - next_agent            : prochain agent à appeler
    - current_question_index: index de la question courante (0-4)
    - is_diagnosis_complete : True quand les 5 questions sont posées
    - extracted_symptoms    : symptômes extraits des réponses
    - requires_physician_review : True si revue médecin nécessaire
    - physician_validation  : None / True / False
    - physician_notes       : notes du médecin
    - diagnostic_summary    : synthèse clinique
    - interim_care          : recommandation intermédiaire
    - errors                : liste des erreurs accumulées

LANCEMENT :
    cd backend/
    uv run uvicorn app.api:app --reload --host 0.0.0.0 --port 8000

ENDPOINTS :
    POST /sessions/start                  → créer une session
    POST /consultation/start              → démarrer avec le cas patient
    POST /consultation/{thread_id}/resume → répondre (patient ou médecin)
    GET  /consultation/{thread_id}        → état courant
    GET  /consultation/{thread_id}/report → rapport final
    GET  /health                          → santé de l'API
===============================================================
"""

# ── Imports standard ──────────────────────────────────────────────────────────
import uuid
from dotenv import load_dotenv
from typing import Optional, List

# load_dotenv() AVANT tout import LangChain/OpenAI
# graph.py instancie le LLM au chargement — il a besoin de OPENAI_API_KEY
load_dotenv()

# ── Imports FastAPI ───────────────────────────────────────────────────────────
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# ── Imports OrientaMed ────────────────────────────────────────────────────────
from app.graph import orientamed_graph


# ═══════════════════════════════════════════════════════════════════════════════
# APPLICATION FASTAPI
# ═══════════════════════════════════════════════════════════════════════════════

app = FastAPI(
    title="OrientaMed API",
    description=(
        "Système multi-agents d'orientation clinique préliminaire.\n\n"
        " Ce système ne remplace pas une consultation médicale.\n"
        "Projet académique — Pr. Mohamed YOUSSFI"
    ),
    version="1.0.0",
)

# CORS — autorise le frontend React (localhost:3000) à appeler l'API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # En production : restreindre au domaine frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ═══════════════════════════════════════════════════════════════════════════════
# SCHÉMAS PYDANTIC
# Correspondent exactement aux champs du MedicalState de Stécy
# ═══════════════════════════════════════════════════════════════════════════════

class PatientInfoRequest(BaseModel):
    """
    Données optionnelles du patient — correspond à PatientData dans state.py.
    Ces champs enrichissent le diagnostic mais ne sont pas obligatoires.
    """
    age:                 Optional[int]       = Field(None, description="Âge du patient")
    gender:              Optional[str]       = Field(None, description="Genre du patient")
    medical_history:     Optional[List[str]] = Field(default_factory=list, description="Antécédents médicaux")
    current_medications: Optional[List[str]] = Field(default_factory=list, description="Médicaments en cours")


class StartConsultationRequest(BaseModel):
    """
    Corps de POST /consultation/start.
    Le patient décrit son cas initial et fournit ses informations de base.
    """
    # Cas initial décrit par le patient (Écran 1 du frontend)
    patient_case: str = Field(
        ...,
        min_length=10,
        description="Description des symptômes ou du motif de consultation",
        example="Je ressens des douleurs thoraciques depuis 2 jours avec de la fièvre."
    )

    # Informations patient optionnelles — correspondent à PatientData (Stécy)
    patient_info: Optional[PatientInfoRequest] = Field(
        None,
        description="Informations patient optionnelles (age, genre, antécédents...)"
    )


class ResumeRequest(BaseModel):
    """
    Corps de POST /consultation/{thread_id}/resume.

    CAS 1 — Réponse patient (Écran 2) :
        { "answer": "Ma douleur est de 7/10..." }

    CAS 2 — Validation médecin (Écran 3) :
        {
            "physician_validation": true,
            "physician_notes": "Amoxicilline 1g × 3/j pendant 7 jours...",
        }

    CAS 3 — Refus médecin (Écran 3) :
        {
            "physician_validation": false,
            "physician_notes": "Revoir la durée des symptômes."
        }
    """
    # Réponse du patient à la question courante
    answer: Optional[str] = Field(
        None,
        description="Réponse du patient à la question clinique courante"
    )

    # Décision du médecin — correspond à physician_validation dans MedicalState
    # None = pas encore décidé, True = valide, False = refuse
    physician_validation: Optional[bool] = Field(
        None,
        description="True si le médecin valide la synthèse, False s'il refuse"
    )

    # Notes du médecin — correspond à physician_notes dans MedicalState
    # Contient le traitement prescrit OU le feedback de correction
    physician_notes: Optional[str] = Field(
        None,
        description="Traitement prescrit ou commentaires de correction du médecin"
    )


class ConsultationResponse(BaseModel):
    """Réponse standard retournée par les endpoints de consultation."""
    thread_id:          str
    status:             str
    message:            str
    # Écran 2 — Questions
    current_question:   Optional[str]       = None
    question_index:     Optional[int]       = None   # current_question_index du state
    # Écran 3 — Médecin
    diagnostic_summary: Optional[str]       = None
    interim_care:       Optional[str]       = None
    extracted_symptoms: Optional[List[str]] = None   # extracted_symptoms du state
    awaiting_physician: bool                = False
    # Écran 4 — Rapport
    final_report:       Optional[str]       = None
    # Erreurs
    errors:             Optional[List[str]] = None


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINT 1 : POST /sessions/start
# ═══════════════════════════════════════════════════════════════════════════════

@app.post("/sessions/start", tags=["Session"])
async def start_session():
    """
    Crée une nouvelle session et retourne un thread_id unique.
    Ce thread_id correspond à patient_id dans le MedicalState de Stécy.
    """
    thread_id = str(uuid.uuid4())
    return {
        "thread_id": thread_id,
        "patient_id": thread_id,   # Alias pour cohérence avec state.py (Stécy)
        "message": "Session créée. Utilisez POST /consultation/start pour démarrer."
    }


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINT 2 : POST /consultation/start
# ═══════════════════════════════════════════════════════════════════════════════

@app.post("/consultation/start", response_model=ConsultationResponse, tags=["Consultation"])
async def start_consultation(request: StartConsultationRequest):
    """
    Démarre une nouvelle consultation OrientaMed.

    FLUX DANS LE GRAPHE :
        START → supervisor_node → diagnostic_agent_node (Q1)
        Le graphe s'arrête après la première question et attend la réponse.

    INITIALISATION DU MEDICALSTATE (Stécy) :
        - patient_id            = thread_id généré
        - patient_info          = données patient optionnelles
        - current_question_index= 0
        - is_diagnosis_complete = False
        - extracted_symptoms    = []
        - requires_physician_review = True
        - physician_validation  = None
        - errors                = []
    """
    thread_id = str(uuid.uuid4())
    config    = {"configurable": {"thread_id": thread_id}}

    # ── Construction de l'état initial compatible avec MedicalState de Stécy ──
    patient_info_dict = {}
    if request.patient_info:
        patient_info_dict = {
            "age":                 request.patient_info.age,
            "gender":              request.patient_info.gender,
            "medical_history":     request.patient_info.medical_history or [],
            "current_medications": request.patient_info.current_medications or [],
        }

    # État initial — correspond exactement aux champs de MedicalState (Stécy)
    initial = {
        "messages":               [],
        "patient_id":             thread_id,       # Identifiant unique du patient
        "patient_info":           patient_info_dict,
        "next_agent":             "diagnostic_agent",
        "current_question_index": 0,               # On commence à la Q1 (index 0)
        "is_diagnosis_complete":  False,
        "extracted_symptoms":     [],
        "requires_physician_review": True,
        "physician_validation":   None,            # Pas encore consulté
        "physician_notes":        None,
        "errors":                 [],
        "diagnostic_summary":     None,
        "interim_care":           None,
        # Champ supplémentaire pour le contexte du diagnostic
        "patient_case":           request.patient_case,
    }

    try:
        result = orientamed_graph.invoke(initial, config)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors du démarrage : {str(e)}"
        )

    # Lecture du résultat — on mappe les champs du state vers la réponse API
    status = _get_workflow_status(result)

    return ConsultationResponse(
        thread_id=thread_id,
        status=status,
        message="Consultation démarrée. Répondez à la première question.",
        current_question=_get_current_question(result),
        question_index=result.get("current_question_index", 0),
        extracted_symptoms=result.get("extracted_symptoms", []),
        awaiting_physician=(status == "awaiting_physician"),
        errors=result.get("errors", []) or None
    )


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINT 3 : POST /consultation/{thread_id}/resume
# ═══════════════════════════════════════════════════════════════════════════════

@app.post("/consultation/{thread_id}/resume", response_model=ConsultationResponse, tags=["Consultation"])
async def resume_consultation(thread_id: str, request: ResumeRequest):
    """
    Reprend le graphe après une interruption.

    CAS 1 — Réponse patient :
        Incrémente current_question_index et reprend le graphe.
        → Pose la question suivante OU génère la synthèse si Q5 répondue.

    CAS 2 — Validation médecin (physician_validation=True) :
        Met physician_validation=True et physician_notes dans le state.
        → router_after_physician() route vers report_agent → rapport généré.

    CAS 3 — Refus médecin (physician_validation=False) :
        Met physician_validation=False et physician_notes (feedback) dans le state.
        → router_after_physician() route vers diagnostic_agent → correction.
    """
    config = {"configurable": {"thread_id": thread_id}}

    # Vérification que la session existe
    current_state = orientamed_graph.get_state(config)
    if not current_state or not current_state.values:
        raise HTTPException(
            status_code=404,
            detail=f"Session '{thread_id}' introuvable. Vérifiez le thread_id."
        )

    state_values = current_state.values

    # ── CAS 1 : Réponse du patient ────────────────────────────────────────────
    if request.answer is not None:

        if not request.answer.strip():
            raise HTTPException(status_code=400, detail="La réponse ne peut pas être vide.")

        # Incrémenter current_question_index — champ clé de MedicalState (Stécy)
        current_index = state_values.get("current_question_index", 0)

        orientamed_graph.update_state(
            config,
            {
                # Incrémenter l'index pour passer à la question suivante
                "current_question_index": current_index + 1,

                # Ajouter le message de réponse à la conversation
                "messages": state_values.get("messages", []) + [
                    {"role": "user", "content": request.answer.strip()}
                ],
            }
        )

    # ── CAS 2 & 3 : Décision du médecin ──────────────────────────────────────
    elif request.physician_validation is not None:

        # Mise à jour des champs physician du MedicalState (Stécy)
        orientamed_graph.update_state(
            config,
            {
                # physician_validation : champ exact de MedicalState (Stécy)
                "physician_validation": request.physician_validation,

                # physician_notes : champ exact de MedicalState (Stécy)
                # Contient le traitement OU le feedback de correction
                "physician_notes": request.physician_notes or "",
            },
            # as_node indique à LangGraph que physician_review_node() reprend
            as_node="physician_review"
        )

    else:
        raise HTTPException(
            status_code=400,
            detail=(
                "Fournir soit 'answer' (patient) "
                "soit 'physician_validation' (médecin)."
            )
        )

    # ── Reprise du graphe ──────────────────────────────────────────────────────
    try:
        result = orientamed_graph.invoke(None, config)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la reprise du graphe : {str(e)}"
        )

    status = _get_workflow_status(result)

    return ConsultationResponse(
        thread_id=thread_id,
        status=status,
        message=_get_status_message(status),
        current_question=_get_current_question(result),
        question_index=result.get("current_question_index", 0),
        diagnostic_summary=result.get("diagnostic_summary"),
        interim_care=result.get("interim_care"),
        extracted_symptoms=result.get("extracted_symptoms", []),
        awaiting_physician=(status == "awaiting_physician"),
        final_report=result.get("final_report") if status == "completed" else None,
        errors=result.get("errors", []) or None
    )


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINT 4 : GET /consultation/{thread_id}
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/consultation/{thread_id}", tags=["Consultation"])
async def get_consultation(thread_id: str):
    """
    Retourne l'état complet de la consultation.
    Expose tous les champs du MedicalState de Stécy.
    """
    config = {"configurable": {"thread_id": thread_id}}
    state  = orientamed_graph.get_state(config)

    if not state or not state.values:
        raise HTTPException(status_code=404, detail=f"Consultation '{thread_id}' introuvable.")

    v = state.values  # Raccourci pour la lisibilité

    return {
        "thread_id":               thread_id,
        # Champs MedicalState de Stécy — tous exposés
        "patient_id":              v.get("patient_id"),
        "patient_info":            v.get("patient_info", {}),
        "next_agent":              v.get("next_agent"),
        "current_question_index":  v.get("current_question_index", 0),
        "is_diagnosis_complete":   v.get("is_diagnosis_complete", False),
        "extracted_symptoms":      v.get("extracted_symptoms", []),
        "requires_physician_review": v.get("requires_physician_review", True),
        "physician_validation":    v.get("physician_validation"),
        "physician_notes":         v.get("physician_notes"),
        "diagnostic_summary":      v.get("diagnostic_summary"),
        "interim_care":            v.get("interim_care"),
        "errors":                  v.get("errors", []),
        # Champs calculés pour le frontend
        "status":                  _get_workflow_status(v),
        "awaiting_physician":      v.get("requires_physician_review") and v.get("is_diagnosis_complete") and v.get("physician_validation") is None,
        "is_completed":            bool(v.get("final_report")),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINT 5 : GET /consultation/{thread_id}/report
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/consultation/{thread_id}/report", tags=["Rapport"])
async def get_report(thread_id: str):
    """
    Retourne le rapport final.
    Disponible uniquement quand physician_validation=True et rapport généré.
    """
    config = {"configurable": {"thread_id": thread_id}}
    state  = orientamed_graph.get_state(config)

    if not state or not state.values:
        raise HTTPException(status_code=404, detail=f"Consultation '{thread_id}' introuvable.")

    v            = state.values
    final_report = v.get("final_report")

    if not final_report:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Rapport non disponible. "
                f"is_diagnosis_complete={v.get('is_diagnosis_complete')}, "
                f"physician_validation={v.get('physician_validation')}."
            )
        )

    return {
        "thread_id":          thread_id,
        "status":             "completed",
        "final_report":       final_report,
        # Contexte complet pour l'Écran 4 du frontend
        "patient_id":         v.get("patient_id"),
        "patient_info":       v.get("patient_info", {}),
        "extracted_symptoms": v.get("extracted_symptoms", []),
        "diagnostic_summary": v.get("diagnostic_summary"),
        "interim_care":       v.get("interim_care"),
        "physician_notes":    v.get("physician_notes"),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINT BONUS : GET /health
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/health", tags=["Système"])
async def health_check():
    """Vérifie que l'API est opérationnelle."""
    return {
        "status":  "ok",
        "service": "OrientaMed API v1.0",
        "docs":    "http://localhost:8000/docs"
    }


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS PRIVÉS
# Fonctions utilitaires qui mappent les champs du MedicalState (Stécy)
# vers des valeurs lisibles par le frontend
# ═══════════════════════════════════════════════════════════════════════════════

def _get_workflow_status(state: dict) -> str:
    """
    Détermine le statut courant du workflow à partir du MedicalState de Stécy.
    Utilisé pour guider le frontend entre les 4 écrans.

    Logique basée sur les champs de MedicalState :
        final_report présent          → "completed"
        physician_validation = True   → "generating_report"
        physician_validation = False  → "revision_requested"
        is_diagnosis_complete = True  → "awaiting_physician"
        current_question_index > 0   → "questioning"
        Sinon                         → "started"
    """
    if state.get("final_report"):
        return "completed"
    if state.get("physician_validation") is True:
        return "generating_report"
    if state.get("physician_validation") is False:
        return "revision_requested"
    if state.get("is_diagnosis_complete"):
        return "awaiting_physician"
    if state.get("current_question_index", 0) > 0:
        return "questioning"
    return "started"


def _get_current_question(state: dict) -> Optional[str]:
    """
    Extrait la question courante depuis les messages du state.
    Le DiagnosticAgent stocke les questions dans state["messages"].
    On récupère le dernier message de type AI.
    """
    messages = state.get("messages", [])
    # Parcourir les messages en sens inverse pour trouver le dernier message AI
    for msg in reversed(messages):
        # Compatibilité avec BaseMessage de LangChain et dict simple
        if hasattr(msg, "type") and msg.type == "ai":
            return msg.content
        if isinstance(msg, dict) and msg.get("role") == "assistant":
            return msg.get("content")
    return None


def _get_status_message(status: str) -> str:
    """Message lisible correspondant au statut du workflow."""
    return {
        "started":            "Consultation initialisée.",
        "questioning":        "Veuillez répondre à la question suivante.",
        "awaiting_physician": "Synthèse générée. En attente du médecin traitant.",
        "revision_requested": "Le médecin demande une correction. Retour au diagnostic.",
        "generating_report":  "Génération du rapport final en cours...",
        "completed":          "Consultation terminée. Rapport disponible.",
    }.get(status, "Traitement en cours...")


# ── Point d'entrée ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.api:app", host="0.0.0.0", port=8000, reload=True)
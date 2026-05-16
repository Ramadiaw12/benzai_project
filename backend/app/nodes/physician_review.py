# DIAWANE - Etudiant 3 — Médecin & Rapport (Human-in-the-Loop)
"""
===============================================================
OrientaMed — physician_review.py
Étudiant 3 : Médecin & Rapport (Human-in-the-Loop)
===============================================================

RÔLE DE CE MODULE :
    Ce fichier implémente le nœud "physician_review" du graphe LangGraph
    défini par l'Étudiant 1 (graph.py / Stécy).

    Dans le workflow, ce nœud est appelé par la fonction de routage
    `router_after_diagnostic()` lorsque :
        - state["is_diagnosis_complete"] est True  (Étudiant 2 a posé ses 5 questions)
        - state["requires_physician_review"] est True (le cas nécessite un médecin)

    Ce nœud est un point d'INTERRUPTION HUMAINE (Human-in-the-Loop).
    Le graphe se met EN PAUSE ici et attend la saisie du médecin traitant
    avant de continuer vers la génération du rapport final.

INTERACTION AVEC LE GRAPHE (graph.py — Stécy) :
    - Entrée  : appelé depuis "diagnostic_agent" via router_after_diagnostic()
    - Sortie  : router_after_physician() lit state["physician_validation"]
                → True  : le workflow se termine → END (rapport déjà généré ici)
                → False : retour à diagnostic_agent pour correction

CHAMPS DU STATE UTILISÉS :
    Lecture  : diagnostic_summary, interim_care, patient_case, patient_answers
    Écriture : physician_validation (bool), physician_treatment (str),
               physician_feedback (str), status
===============================================================
"""

# ── Imports LangGraph & LangChain ────────────────────────────────────────────
from langgraph.types import interrupt       # Mécanisme d'interruption HITL LangGraph
from langchain_core.messages import HumanMessage, AIMessage

# ── Import du state partagé (défini par l'Étudiant 1) ────────────────────────
# MedicalState est le contrat de données central du projet.
# Tous les agents lisent et écrivent dans ce même état partagé.
from app.state import MedicalState


# ═══════════════════════════════════════════════════════════════════════════════
# NŒUD PRINCIPAL : physician_review_node
# Appelé par le graphe via : workflow.add_node("physician_review", physician_node)
# ═══════════════════════════════════════════════════════════════════════════════

def physician_review_node(state: MedicalState) -> dict:
    """
    Nœud Human-in-the-Loop représentant le médecin traitant.

    FONCTIONNEMENT EN 3 PHASES :
    ─────────────────────────────
    Phase 1 — Préparation du dossier médecin
        Récupération de la synthèse clinique (Étudiant 2) et
        construction du brief présenté au médecin.

    Phase 2 — Interruption Human-in-the-Loop
        LangGraph suspend le graphe via interrupt() et attend
        la saisie du médecin via l'API FastAPI ou LangGraph Studio.

    Phase 3 — Traitement de la décision médecin
        Mise à jour du state avec physician_validation (bool)
        et physician_treatment (str) pour router_after_physician().

    Args:
        state (MedicalState): État partagé du graphe LangGraph

    Returns:
        dict: Mise à jour partielle du state avec la décision du médecin
    """

    # ─────────────────────────────────────────────────────────────────────────
    # PHASE 1 : Récupération des données produites par l'Étudiant 2
    # Ces champs ont été remplis par diagnostic_agent.py avant d'arriver ici
    # ─────────────────────────────────────────────────────────────────────────

    # Synthèse clinique préliminaire — produite par le DiagnosticAgent
    diagnostic_summary = state.get("diagnostic_summary", "Synthèse non disponible.")

    # Recommandation intermédiaire générale (repos, hydratation, surveillance…)
    interim_care = state.get("interim_care", "Aucune recommandation intermédiaire.")

    # Description initiale fournie par le patient (Écran 1 du frontend)
    patient_case = state.get("patient_case", "Cas patient non renseigné.")

    # Réponses du patient aux 5 questions posées par l'Étudiant 2
    patient_answers = state.get("patient_answers", [])

    # Formatage des réponses pour une lecture claire par le médecin
    answers_formatted = "\n".join([
        f"   Q{i+1} : {ans}" for i, ans in enumerate(patient_answers)
    ]) if patient_answers else "   Aucune réponse enregistrée."

    # ─────────────────────────────────────────────────────────────────────────
    # Préparation du dossier présenté au médecin
    # Ce contenu est transmis au frontend (Écran 3 — PhysicianReview.js)
    # via l'endpoint GET /consultation/{thread_id} de l'API FastAPI
    # ─────────────────────────────────────────────────────────────────────────
    physician_brief = f"""
╔══════════════════════════════════════════════════════╗
   DOSSIER DE VALIDATION MÉDECIN — OrientaMed
╚══════════════════════════════════════════════════════╝

CAS INITIAL DU PATIENT :
{patient_case}

RÉPONSES AUX QUESTIONS CLINIQUES :
{answers_formatted}

SYNTHÈSE CLINIQUE PRÉLIMINAIRE :
{diagnostic_summary}

RECOMMANDATION INTERMÉDIAIRE :
{interim_care}

══════════════════════════════════════════════════════
⚕️  ACTION REQUISE — Médecin traitant
══════════════════════════════════════════════════════
Veuillez fournir :
  1. Votre validation (accepter ou refuser la synthèse)
  2. Votre traitement ou conduite à tenir
  3. Vos commentaires ou corrections éventuels

  Ce système ne remplace pas une consultation médicale.
"""

    # ─────────────────────────────────────────────────────────────────────────
    # PHASE 2 : Interruption HITL — Le graphe se met en PAUSE ici
    #
    # interrupt() est le mécanisme Human-in-the-Loop de LangGraph.
    # Il effectue 3 actions simultanées :
    #   1. Sauvegarde l'état complet du graphe (via MemorySaver dans graph.py)
    #   2. Suspend l'exécution du graphe à ce point précis
    #   3. Retourne le contenu du dict au client (API FastAPI / LangGraph Studio)
    #
    # La reprise se fait via :
    #   POST /consultation/{thread_id}/resume
    #   body: { "physician_treatment": "...", "validation": true/false }
    #
    # LangGraph reprend alors l'exécution juste après cette ligne.
    # ─────────────────────────────────────────────────────────────────────────
    physician_input = interrupt({
        "type":    "physician_review",        # Identifiant du type d'interruption
        "brief":   physician_brief,           # Dossier affiché au médecin
        "message": "En attente de la validation du médecin traitant.",
        "status":  "awaiting_physician"       # Statut exposé par l'API FastAPI
    })

    # ─────────────────────────────────────────────────────────────────────────
    # PHASE 3 : Traitement de la réponse du médecin (après reprise du graphe)
    #
    # physician_input contient les données envoyées par le médecin via l'API.
    # Ces valeurs pilotent le routage dans router_after_physician() (Étudiant 1) :
    #   → physician_validation = True  : router retourne "end" → rapport généré
    #   → physician_validation = False : router retourne "diagnostic_agent" → correction
    # ─────────────────────────────────────────────────────────────────────────

    # Décision du médecin : valide (True) ou refuse (False) la synthèse
    physician_validation = physician_input.get("validation", True)

    # Traitement prescrit — sera intégré dans le rapport final par report_agent.py
    physician_treatment = physician_input.get("treatment", "")

    # Feedback ou corrections éventuelles du médecin
    # Transmis à l'agent diagnostic si physician_validation = False
    physician_feedback = physician_input.get("feedback", "")

    # ── Log pour LangGraph Studio (visible dans le panneau de débogage) ──────
    if physician_validation:
        print(" [PhysicianReview] Synthèse VALIDÉE — génération du rapport.")
    else:
        print(" [PhysicianReview] Synthèse REFUSÉE — retour au diagnostic.")
        if physician_feedback:
            print(f"   Feedback médecin : {physician_feedback}")

    # ─────────────────────────────────────────────────────────────────────────
    # Retour : mise à jour partielle du MedicalState
    #
    #  On ne retourne QUE les champs modifiés (pas tout le state).
    # LangGraph merge automatiquement ce dict dans l'état global.
    #
    # Ces champs sont ensuite lus par :
    #   → router_after_physician() : lit physician_validation
    #   → report_agent_node()      : lit physician_treatment et physician_feedback
    # ─────────────────────────────────────────────────────────────────────────
    return {
        # Lu par router_after_physician() pour décider la suite du workflow
        "physician_validation": physician_validation,

        # Lu par report_agent_node() pour générer la section "Conduite à tenir"
        "physician_treatment": physician_treatment,

        # Lu par diagnostic_agent si le médecin demande une correction
        "physician_feedback": physician_feedback,

        # Statut mis à jour — exposé par GET /consultation/{thread_id}
        "status": "generating_report" if physician_validation else "revision_requested",

        # Trace conversationnelle — visible dans LangGraph Studio
        "messages": [
            AIMessage(content=physician_brief),
            HumanMessage(content=(
                f"[MÉDECIN] Décision : {' Validé' if physician_validation else '❌ Refusé'}\n"
                f"Traitement prescrit : {physician_treatment or 'Non renseigné'}\n"
                f"Commentaires        : {physician_feedback or 'Aucun'}"
            ))
        ]
    }
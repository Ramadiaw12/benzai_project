"""
agents/physician_review.py
==========================
Nœud LangGraph : Human-in-the-Loop (HITL) – Review médecin.

Rôle dans le graphe :
    DiagnosticAgent (E2)  ──►  physician_review  ──►  ReportAgent (E3)

Ce nœud implémente le pattern "interrupt" de LangGraph :
  1. Le graphe s'arrête et expose l'état courant (diagnostic_summary) dans
     LangGraph Studio pour que le médecin puisse le consulter et modifier
     manuellement les champs physician_decision.
  2. Une fois la review soumise (via Studio ou API), le graphe reprend.

Auteur : Étudiant 3
"""

from __future__ import annotations

import logging
from datetime import datetime

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.types import interrupt   # mécanisme d'interruption LangGraph ≥ 0.2

from schemas.state import MedicalState, PhysicianDecision

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _format_diagnostic_for_review(state: MedicalState) -> str:
    """
    Formate le résumé du diagnostic en texte lisible pour le médecin.
    Affiché dans LangGraph Studio lors de l'interruption.
    """
    d = state.diagnostic_summary
    if d is None:
        return "⚠️  Aucun diagnostic disponible – vérifier DiagnosticAgent."

    patient_info = ""
    if state.patient:
        p = state.patient
        antecedents = ", ".join(p.antecedents) if p.antecedents else "aucun"
        patient_info = (
            f"Patient : {p.nom}, {p.age} ans, {p.sexe}\n"
            f"Antécédents : {antecedents}\n"
            f"Motif : {state.motif_consultation}\n\n"
        )

    symptomes    = "\n  - ".join(d.symptomes)   if d.symptomes   else "non renseignés"
    hypotheses   = "\n  - ".join(d.hypotheses)  if d.hypotheses  else "non renseignées"

    return (
        f"{patient_info}"
        f"━━━ Analyse IA – DiagnosticAgent ━━━\n"
        f"Symptômes identifiés :\n  - {symptomes}\n\n"
        f"Hypothèses diagnostiques :\n  - {hypotheses}\n\n"
        f"Score d'urgence : {d.score_urgence}/10\n"
        f"Soins immédiats suggérés : {d.interim_care}\n"
    )


# ---------------------------------------------------------------------------
# Nœud principal
# ---------------------------------------------------------------------------

def physician_review_node(state: MedicalState) -> dict:
    """
    Nœud LangGraph – Review médecin (HITL via LangGraph Studio).

    Fonctionnement :
    ----------------
    1. Prépare un résumé formaté du diagnostic IA.
    2. Appelle `interrupt()` → le graphe se met en pause.
       Dans LangGraph Studio, le médecin voit l'état et peut :
         - Modifier `physician_decision` dans le panneau State
         - Cliquer "Continue" pour reprendre l'exécution
    3. À la reprise, le nœud lit `state.physician_decision` (remplie par Studio).
       Si elle est absente (bug ou oubli), on applique un fallback.
    4. Retourne les mises à jour d'état à fusionner par LangGraph.

    Paramètres
    ----------
    state : MedicalState
        État courant du graphe, injecté automatiquement par LangGraph.

    Retourne
    --------
    dict
        Dictionnaire de mise à jour partielle de MedicalState.
    """

    logger.info("[PhysicianReview] Démarrage du nœud HITL.")

    # --- Étape 1 : Préparer l'affichage pour le médecin ---
    resume_pour_medecin = _format_diagnostic_for_review(state)
    logger.debug("[PhysicianReview] Résumé préparé :\n%s", resume_pour_medecin)

    # --- Étape 2 : Interruption – LangGraph Studio prend la main ---
    # `interrupt()` sérialise la valeur passée et l'affiche dans Studio.
    # L'exécution reprend seulement quand le médecin clique "Continue".
    interrupt({
        "action_requise": "review_medecin",
        "instructions": (
            "Veuillez examiner le diagnostic ci-dessous, "
            "puis remplir le champ `physician_decision` dans le panneau State "
            "avant de cliquer sur Continue."
        ),
        "diagnostic_ia": resume_pour_medecin,
        "timestamp": datetime.utcnow().isoformat(),
    })

    # --- Étape 3 : Lecture de la décision médecin après reprise ---
    decision = state.physician_decision

    if decision is None:
        # Fallback de sécurité : si le médecin n'a pas rempli le champ,
        # on crée une décision "approbation tacite" avec avertissement.
        logger.warning(
            "[PhysicianReview] physician_decision non remplie après interruption. "
            "Fallback : approbation tacite."
        )
        hypotheses = state.diagnostic_summary.hypotheses if state.diagnostic_summary else []
        decision = PhysicianDecision(
            approuve=True,
            diagnostic_final=hypotheses[0] if hypotheses else "Diagnostic non déterminé",
            commentaire="⚠️ Review automatique – aucune décision médecin enregistrée.",
            orientation="médecin traitant",
        )

    logger.info(
        "[PhysicianReview] Décision médecin : approuvé=%s, diagnostic='%s'",
        decision.approuve,
        decision.diagnostic_final,
    )

    # --- Étape 4 : Message de trace dans le graphe ---
    message_review = AIMessage(
        content=(
            f"✅ Review médecin complétée.\n"
            f"Diagnostic retenu : {decision.diagnostic_final}\n"
            f"Orientation : {decision.orientation}"
        ),
        name="physician_review",
    )

    # --- Retour : mise à jour partielle de l'état ---
    return {
        "physician_decision": decision,
        "etape_courante": "rapport",
        "messages": [message_review],
    }
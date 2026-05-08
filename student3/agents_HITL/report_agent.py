"""
agents/report_agent.py
======================
Nœud LangGraph : ReportAgent – Génération du rapport médical final.

Rôle dans le graphe :
    physician_review  ──►  report_agent  ──►  END

Ce nœud utilise GPT-4 (OpenAI) via LangChain pour synthétiser l'ensemble
des données collectées (anamnèse, diagnostic IA, décision médecin) en un
rapport médical structuré et professionnel.

Auteur : Étudiant 3
"""

from __future__ import annotations

import logging
from datetime import datetime

from langchain_core.messages import AIMessage, SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI

from schemas.state import MedicalState, RapportFinal

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration du modèle
# ---------------------------------------------------------------------------

# Le modèle est instancié une seule fois (singleton) pour éviter de recréer
# la connexion à chaque appel du nœud.
# La clé API est lue depuis la variable d'environnement OPENAI_API_KEY.
_llm = ChatOpenAI(
    model="gpt-4o",          # gpt-4o = GPT-4 Omni (meilleur rapport qualité/vitesse)
    temperature=0.2,         # faible température → rapport factuel, peu créatif
    max_tokens=1500,
)


# ---------------------------------------------------------------------------
# Prompt système
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """Tu es un assistant médical expert chargé de rédiger des rapports 
de consultation structurés et professionnels.

À partir des informations fournies (informations patient, diagnostic IA, 
décision du médecin), tu dois produire un rapport clair, concis et utilisable 
directement par le patient ou par un autre professionnel de santé.

Réponds UNIQUEMENT en JSON valide avec cette structure exacte :
{
  "resume_consultation": "string – résumé en 2-3 phrases de la consultation",
  "diagnostic_final": "string – diagnostic retenu",
  "recommandations": ["string", "string", ...],
  "niveau_urgence": "faible|modéré|élevé|critique",
  "orientation": "string – où le patient doit aller / que faire ensuite"
}

N'ajoute aucun texte en dehors du JSON. Rédige en français."""


# ---------------------------------------------------------------------------
# Helper : construction du prompt utilisateur
# ---------------------------------------------------------------------------

def _build_user_prompt(state: MedicalState) -> str:
    """
    Construit le message utilisateur à partir de l'état courant du graphe.
    Toutes les informations disponibles sont injectées pour que le LLM
    dispose du contexte complet.
    """
    lines = ["=== DONNÉES DE LA CONSULTATION ===\n"]

    # Informations patient
    if state.patient:
        p = state.patient
        antecedents = ", ".join(p.antecedents) if p.antecedents else "aucun"
        lines.append(
            f"Patient : {p.nom} | Âge : {p.age} ans | Sexe : {p.sexe}\n"
            f"Antécédents : {antecedents}\n"
            f"Motif : {state.motif_consultation}\n"
        )

    # Résumé diagnostic IA
    if state.diagnostic_summary:
        d = state.diagnostic_summary
        lines.append(
            f"\n=== DIAGNOSTIC IA (DiagnosticAgent) ===\n"
            f"Symptômes : {', '.join(d.symptomes)}\n"
            f"Hypothèses : {', '.join(d.hypotheses)}\n"
            f"Score d'urgence : {d.score_urgence}/10\n"
            f"Soins immédiats : {d.interim_care}\n"
        )

    # Décision médecin
    if state.physician_decision:
        dec = state.physician_decision
        lines.append(
            f"\n=== DÉCISION MÉDECIN (HITL) ===\n"
            f"Diagnostic validé : {dec.diagnostic_final}\n"
            f"Approuvé par médecin : {'oui' if dec.approuve else 'non'}\n"
            f"Commentaire : {dec.commentaire or 'aucun'}\n"
            f"Orientation : {dec.orientation}\n"
        )

    lines.append("\nGénère le rapport médical final en JSON.")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Nœud principal
# ---------------------------------------------------------------------------

def report_agent_node(state: MedicalState) -> dict:
    """
    Nœud LangGraph – Génération du rapport médical final via GPT-4.

    Fonctionnement :
    ----------------
    1. Construit le prompt à partir de l'état courant.
    2. Appelle GPT-4o via LangChain (ChatOpenAI).
    3. Parse la réponse JSON en modèle RapportFinal.
    4. Met à jour l'état avec le rapport et marque la consultation terminée.

    Paramètres
    ----------
    state : MedicalState
        État courant du graphe, injecté automatiquement par LangGraph.

    Retourne
    --------
    dict
        Mise à jour partielle de MedicalState (rapport_final, etape_courante).
    """
    import json

    logger.info("[ReportAgent] Démarrage de la génération du rapport.")

    # --- Étape 1 : Construire les messages pour le LLM ---
    user_prompt = _build_user_prompt(state)

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=user_prompt),
    ]

    # --- Étape 2 : Appel GPT-4 ---
    try:
        logger.debug("[ReportAgent] Envoi de la requête à GPT-4o...")
        response = _llm.invoke(messages)
        raw_content = response.content
        logger.debug("[ReportAgent] Réponse brute reçue : %s", raw_content[:200])
    except Exception as exc:
        logger.error("[ReportAgent] Erreur lors de l'appel GPT-4 : %s", exc)
        return {
            "erreur": f"ReportAgent – Erreur LLM : {exc}",
            "etape_courante": "erreur",
        }

    # --- Étape 3 : Parser le JSON retourné par le LLM ---
    try:
        # Nettoyage au cas où le modèle ajoute des balises ```json ... ```
        clean = raw_content.strip()
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        data = json.loads(clean.strip())
    except json.JSONDecodeError as exc:
        logger.error("[ReportAgent] Impossible de parser le JSON : %s", exc)
        return {
            "erreur": f"ReportAgent – JSON invalide : {exc}",
            "etape_courante": "erreur",
        }

    # --- Étape 4 : Construire le modèle RapportFinal ---
    commentaire = None
    if state.physician_decision:
        commentaire = state.physician_decision.commentaire

    try:
        rapport = RapportFinal(
            resume_consultation=data["resume_consultation"],
            diagnostic_final=data["diagnostic_final"],
            recommandations=data.get("recommandations", []),
            niveau_urgence=data.get("niveau_urgence", "modéré"),
            orientation=data.get("orientation", state.physician_decision.orientation if state.physician_decision else ""),
            genere_le=datetime.utcnow().isoformat(),
        )
    except (KeyError, ValueError) as exc:
        logger.error("[ReportAgent] Champ manquant dans la réponse LLM : %s", exc)
        return {
            "erreur": f"ReportAgent – Structure JSON incomplète : {exc}",
            "etape_courante": "erreur",
        }

    logger.info(
        "[ReportAgent] Rapport généré avec succès. Urgence : %s",
        rapport.niveau_urgence,
    )

    # --- Message de trace dans le graphe ---
    message_rapport = AIMessage(
        content=(
            f"📋 Rapport médical généré.\n"
            f"Diagnostic : {rapport.diagnostic_final}\n"
            f"Urgence : {rapport.niveau_urgence}\n"
            f"Orientation : {rapport.orientation}"
        ),
        name="report_agent",
    )

    return {
        "rapport_final": rapport,
        "etape_courante": "terminé",
        "messages": [message_rapport],
    }
# DIAWANE - Etudiant 3 — Génération du rapport final structuré
"""
===============================================================
OrientaMed — report_agent.py
Étudiant 3 : Génération du rapport final structuré
===============================================================

RÔLE DE CE MODULE :
    Ce fichier implémente le nœud "report_agent" du graphe LangGraph.
    Il est appelé par router_after_physician() lorsque le médecin
    a VALIDÉ la synthèse clinique (physician_validation = True).

    Son unique responsabilité : produire le rapport final structuré
    en agrégeant toutes les données collectées pendant le workflow.

INTERACTION AVEC LE GRAPHE (graph.py — Stécy) :
    - Entrée  : appelé après physician_review via router_after_physician()
                uniquement si physician_validation = True
    - Sortie  : écrit final_report dans le state → le graphe se termine (END)

     Si physician_validation = False, ce nœud n'est PAS appelé.
        Le routeur retourne "diagnostic_agent" pour une nouvelle itération.

DONNÉES AGRÉGÉES DANS LE RAPPORT :
    - patient_case          : description initiale du patient
    - patient_answers       : réponses aux 5 questions (Étudiant 2)
    - diagnostic_summary    : synthèse clinique (Étudiant 2)
    - interim_care          : recommandation intermédiaire (Étudiant 2)
    - physician_treatment   : traitement prescrit par le médecin (Étudiant 3)
    - physician_feedback    : commentaires du médecin (Étudiant 3)

MENTION ÉTHIQUE OBLIGATOIRE (cahier des charges) :
    Le rapport DOIT contenir : "Ce système ne remplace pas une consultation médicale."
===============================================================
"""

# ── Imports LangChain & OpenAI ────────────────────────────────────────────────
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

# ── Import du state partagé (défini par l'Étudiant 1) ────────────────────────
from app.state import MedicalState

# ── Utilitaires Python ────────────────────────────────────────────────────────
from datetime import datetime
from dotenv import load_dotenv

# Chargement des variables d'environnement (.env → OPENAI_API_KEY)
load_dotenv()


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION DU LLM
# temperature=0.2 : réponses stables et factuelles (pas de créativité excessive)
# ═══════════════════════════════════════════════════════════════════════════════
llm = ChatOpenAI(model="gpt-4o", temperature=0.2)


# ═══════════════════════════════════════════════════════════════════════════════
# PROMPT SYSTÈME — Instructions permanentes pour le LLM
# Définit le comportement général de l'agent de rédaction
# ═══════════════════════════════════════════════════════════════════════════════
REPORT_SYSTEM_PROMPT = """
Tu es l'agent de rédaction du système OrientaMed.
Ta mission est de générer des rapports d'orientation clinique
clairs, structurés, professionnels et accessibles.

RÈGLES ABSOLUES — à respecter impérativement :
1. Le rapport DOIT contenir la phrase exacte :
   "Ce système ne remplace pas une consultation médicale."
2. Ne jamais inventer d'informations médicales non fournies dans le contexte.
3. Utiliser un langage clair, accessible et non alarmiste.
4. Rester strictement factuel — ne pas émettre de diagnostic définitif.
5. Les termes recommandés : "orientation clinique préliminaire",
   "synthèse clinique", "recommandation intermédiaire".
6. Ne jamais contredire la décision du médecin traitant.
"""

# ═══════════════════════════════════════════════════════════════════════════════
# TEMPLATE DU RAPPORT — Structure fixe imposée par le cahier des charges
# Les accolades {} sont remplies dynamiquement avec les données du state
# ═══════════════════════════════════════════════════════════════════════════════
REPORT_TEMPLATE = """
Génère le rapport final d'orientation clinique basé sur ces informations :

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DONNÉES DE LA CONSULTATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Cas patient initial      : {patient_case}
Nombre de questions      : {question_count}/5
Réponses du patient      :
{answers_formatted}

Synthèse clinique        : {diagnostic_summary}
Recommandation inter.    : {interim_care}
Traitement médecin       : {physician_treatment}
Commentaires médecin     : {physician_feedback}
Date de consultation     : {date}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Génère le rapport en respectant EXACTEMENT cette structure :

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RAPPORT D'ORIENTATION CLINIQUE PRÉLIMINAIRE — OrientaMed
Date : {date}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. MOTIF DE CONSULTATION
   [Résumé clair et concis du cas initial décrit par le patient]

2. ANAMNÈSE — RÉPONSES AUX QUESTIONS CLINIQUES
   [Synthèse structurée des réponses du patient aux 5 questions]

3. SYNTHÈSE CLINIQUE PRÉLIMINAIRE
   [Reprendre et reformuler la synthèse générée par le système]

4. RECOMMANDATION INTERMÉDIAIRE
   [Recommandations générales prudentes — repos, hydratation, surveillance]

5. ÉVALUATION ET CONDUITE À TENIR (Médecin traitant)
   [Traitement prescrit et décision médicale]

6. CONCLUSION ET SUIVI
   [Résumé des actions à entreprendre, signaux d'alerte à surveiller]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 AVERTISSEMENT OBLIGATOIRE :
Ce système ne remplace pas une consultation médicale.
OrientaMed est un outil d'aide à l'orientation clinique préliminaire
à usage académique uniquement. Tout symptôme persistant ou grave
nécessite une consultation auprès d'un professionnel de santé qualifié.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""


# ═══════════════════════════════════════════════════════════════════════════════
# NŒUD PRINCIPAL : report_agent_node
# Appelé par le graphe via : workflow.add_node("report_agent", report_agent_node)
#   Ce nœud n'existe pas dans le graphe de Stécy (version combinée E1+E2).
#     Il est déclenché implicitement depuis physician_node() quand validation=True,
#     OU peut être ajouté comme nœud séparé dans graph.py par l'Étudiant 1.
# ═══════════════════════════════════════════════════════════════════════════════

def report_agent_node(state: MedicalState) -> dict:
    """
    Nœud ReportAgent : génère le rapport final structuré.

    Ce nœud est le dernier nœud métier du workflow.
    Il s'exécute uniquement après validation du médecin
    (physician_validation = True dans le state).

    Il agrège TOUTES les données produites par les 3 autres agents :
    - Étudiant 1 (Supervisor) : métadonnées de session
    - Étudiant 2 (Diagnostic) : diagnostic_summary, interim_care, patient_answers
    - Étudiant 3 (Physician)  : physician_treatment, physician_feedback

    Args:
        state (MedicalState): État complet du graphe à ce stade du workflow

    Returns:
        dict: Mise à jour du state avec final_report et status="completed"
    """

    # ─────────────────────────────────────────────────────────────────────────
    # Extraction de toutes les données du state
    # Ces champs ont été remplis progressivement par les nœuds précédents
    # ─────────────────────────────────────────────────────────────────────────

    # Données patient (saisies sur l'Écran 1 du frontend)
    patient_case = state.get("patient_case", "Non renseigné")

    # Réponses aux 5 questions posées par l'Étudiant 2
    patient_answers = state.get("patient_answers", [])
    question_count  = state.get("question_count", len(patient_answers))

    # Formatage numéroté des réponses pour le template
    answers_formatted = "\n".join([
        f"   Q{i+1} : {ans}" for i, ans in enumerate(patient_answers)
    ]) if patient_answers else "   Aucune réponse enregistrée."

    # Sorties de l'agent diagnostic (Étudiant 2)
    diagnostic_summary = state.get("diagnostic_summary", "Non disponible")
    interim_care       = state.get("interim_care",       "Non disponible")

    # Décision et traitement du médecin (Étudiant 3 — physician_review_node)
    physician_treatment = state.get("physician_treatment", "Non renseigné")
    physician_feedback  = state.get("physician_feedback",  "Aucun commentaire")

    # Horodatage de la génération du rapport
    date_str = datetime.now().strftime("%d/%m/%Y à %H:%M")

    # ─────────────────────────────────────────────────────────────────────────
    # Construction du prompt final envoyé au LLM
    # On remplace les variables du template avec les données réelles
    # ─────────────────────────────────────────────────────────────────────────
    report_prompt = REPORT_TEMPLATE.format(
        patient_case       = patient_case,
        question_count     = question_count,
        answers_formatted  = answers_formatted,
        diagnostic_summary = diagnostic_summary,
        interim_care       = interim_care,
        physician_treatment= physician_treatment,
        physician_feedback = physician_feedback,
        date               = date_str
    )

    # ─────────────────────────────────────────────────────────────────────────
    # Appel au LLM (GPT-4o) pour générer le rapport structuré
    # SystemMessage : instructions permanentes de comportement
    # HumanMessage  : données de la consultation à traiter
    # ─────────────────────────────────────────────────────────────────────────
    print(" [ReportAgent] Génération du rapport final en cours...")

    response = llm.invoke([
        SystemMessage(content=REPORT_SYSTEM_PROMPT),
        HumanMessage(content=report_prompt)
    ])

    # Extraction du texte du rapport depuis la réponse LLM
    final_report = response.content

    print(" [ReportAgent] Rapport final généré avec succès.")

    # ─────────────────────────────────────────────────────────────────────────
    # Retour : mise à jour finale du MedicalState
    #
    # status = "completed" → l'API FastAPI retourne le rapport via :
    #   GET /consultation/{thread_id}/report
    #
    # is_diagnosis_complete reste True (pas de modification)
    # ─────────────────────────────────────────────────────────────────────────
    return {
        # Rapport final — exposé par GET /consultation/{thread_id}/report
        "final_report": final_report,

        # Statut final du workflow
        "status": "completed",

        # Trace conversationnelle pour LangGraph Studio
        "messages": [
            AIMessage(content=" Rapport d'orientation clinique généré avec succès.")
        ]
    }


# ═══════════════════════════════════════════════════════════════════════════════
# FONCTION UTILITAIRE : generate_report_from_physician_node
# ═══════════════════════════════════════════════════════════════════════════════

def generate_report_from_physician_node(state: MedicalState) -> dict:
    """
    Version intégrée du ReportAgent à appeler directement depuis physician_node()
    si l'Étudiant 1 préfère ne pas ajouter un nœud séparé dans le graphe.

    Usage dans graph.py (Stécy) :
    ─────────────────────────────
    from report_agent import generate_report_from_physician_node

    def physician_node(state: MedicalState) -> dict:
        # ... logique physician_review_node ...
        result = physician_review_node(state)

        # Si le médecin valide, générer le rapport immédiatement
        if result.get("physician_validation"):
            report_result = generate_report_from_physician_node({**state, **result})
            return {**result, **report_result}

        return result

    Args:
        state (MedicalState): State mis à jour après physician_review_node

    Returns:
        dict: Mise à jour avec final_report et status="completed"
    """
    # Délègue simplement à report_agent_node
    return report_agent_node(state)
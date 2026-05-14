"""
===============================================================
OrientaMed — supervisor.py
Étudiant 1 : Supervisor (Orchestrateur du workflow)
===============================================================

RÔLE DE CE MODULE :
    Ce fichier implémente le nœud "supervisor" du graphe LangGraph.
    Le Supervisor est le chef d'orchestre du workflow OrientaMed.
    Il ne fait pas de traitement médical — il DÉCIDE uniquement
    quel agent appeler ensuite en lisant l'état du graphe.

    Dans le graphe de Stécy, le Supervisor remplace les deux fonctions
    de routage conditionnelles :
        - router_after_diagnostic()
        - router_after_physician()
    par UN seul nœud centralisé intelligent.

POSITION DANS LE WORKFLOW :
    START
      │
      ▼
    Supervisor ──────────────────────────────────────┐
      │                                               │
      ▼ (next = "diagnostic_agent")                  │
    DiagnosticAgent  ←──────────────────────────────┤ (boucle 5 questions)
      │                                               │
      ▼ (is_diagnosis_complete = True)               │
    Supervisor                                        │
      │                                               │
      ▼ (next = "physician_review")                  │
    PhysicianReview (HITL)                           │
      │                                               │
      ▼ (physician_validation = True/False)          │
    Supervisor                                        │
      │                                               │
      ├── next = "report_agent"   → ReportAgent → END│
      └── next = "diagnostic_agent" ─────────────────┘

LOGIQUE DE DÉCISION (should_continue) :
    Le Supervisor analyse l'état et décide via une logique déterministe
    renforcée par un LLM pour les cas ambigus :

    Priorité 1 — Fin du workflow :
        final_report rempli → FINISH

    Priorité 2 — Après validation médecin :
        physician_validation = True  → report_agent
        physician_validation = False → diagnostic_agent (correction)

    Priorité 3 — Après diagnostic :
        is_diagnosis_complete = True → physician_review
        question_count < 5          → diagnostic_agent (boucle)

    Priorité 4 — Début du workflow :
        Aucune donnée → diagnostic_agent

CHAMPS DU STATE LUS :
    - question_count        : nombre de questions posées
    - is_diagnosis_complete : toutes les 5 questions posées + synthèse faite
    - requires_physician_review : le cas nécessite un médecin
    - physician_validation  : décision du médecin (True/False/None)
    - diagnostic_summary    : synthèse clinique (vide si pas encore générée)
    - final_report          : rapport final (vide si pas encore généré)
    - status                : état courant du workflow

CHAMP DU STATE ÉCRIT :
    - next : "diagnostic_agent" | "physician_review" | "report_agent" | "FINISH"
===============================================================
"""

# ── Imports LangChain & OpenAI ────────────────────────────────────────────────
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

# ── Import du state partagé (défini par l'Étudiant 1) ────────────────────────
from app.state import MedicalState

# ── Utilitaires ───────────────────────────────────────────────────────────────
from dotenv import load_dotenv

# Chargement de la clé OPENAI_API_KEY depuis le fichier .env
load_dotenv()


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION DU LLM
# temperature=0 : décisions 100% déterministes — pas de créativité ici
# Le Supervisor doit toujours prendre la même décision pour le même état
# ═══════════════════════════════════════════════════════════════════════════════
llm = ChatOpenAI(model="gpt-4o", temperature=0)


# ═══════════════════════════════════════════════════════════════════════════════
# PROMPT SYSTÈME DU SUPERVISOR
# Instructions de routage données au LLM pour les cas ambigus
# ═══════════════════════════════════════════════════════════════════════════════
SUPERVISOR_SYSTEM_PROMPT = """
Tu es le Supervisor du système multi-agents OrientaMed.
Ton UNIQUE rôle est de décider quel agent appeler ensuite.
Tu ne fais AUCUN traitement médical.

RÈGLES DE ROUTAGE — à suivre dans cet ordre de priorité :

1. Si final_report est rempli → répondre : "FINISH"

2. Si physician_validation = True ET final_report est vide
   → répondre : "report_agent"

3. Si physician_validation = False (médecin a refusé)
   → répondre : "diagnostic_agent"

4. Si is_diagnosis_complete = True ET physician_validation est None
   → répondre : "physician_review"

5. Si question_count < 5 OU is_diagnosis_complete = False
   → répondre : "diagnostic_agent"

6. Par défaut → répondre : "diagnostic_agent"

IMPORTANT : Réponds UNIQUEMENT avec l'un de ces mots exacts,
sans ponctuation ni explication :
diagnostic_agent | physician_review | report_agent | FINISH
"""


# ═══════════════════════════════════════════════════════════════════════════════
# NŒUD PRINCIPAL : supervisor_node
# Appelé par le graphe via : workflow.add_node("supervisor", supervisor_node)
# ═══════════════════════════════════════════════════════════════════════════════

def supervisor_node(state: MedicalState) -> dict:
    """
    Nœud Supervisor : orchestre le workflow en décidant le prochain agent.

    STRATÉGIE EN 2 NIVEAUX :
    ─────────────────────────
    Niveau 1 — Routage déterministe (_fallback_routing)
        Logique pure basée sur les champs du state.
        Rapide, fiable, ne consomme pas de tokens LLM.
        Couvre 95% des cas normaux du workflow.

    Niveau 2 — Routage assisté par LLM (fallback)
        Utilisé uniquement si le routage déterministe échoue
        ou retourne un résultat inattendu.
        Le LLM reçoit un résumé de l'état et décide.
        Utile pour les cas ambigus ou les états corrompus.

    Args:
        state (MedicalState): État partagé du graphe LangGraph

    Returns:
        dict: {"next": "<nom_du_prochain_agent>"} — mise à jour du state
    """

    # ─────────────────────────────────────────────────────────────────────────
    # NIVEAU 1 : Routage déterministe (prioritaire)
    # On essaie d'abord la logique pure — plus rapide et plus fiable
    # ─────────────────────────────────────────────────────────────────────────
    decision = _deterministic_routing(state)

    # Si le routage déterministe donne un résultat valide → on l'utilise
    if decision in VALID_DECISIONS:
        print(f" [Supervisor] Décision déterministe : {decision}")
        return {"next": decision}

    # ─────────────────────────────────────────────────────────────────────────
    # NIVEAU 2 : Routage assisté par LLM (fallback uniquement)
    # Activé si le routage déterministe échoue (état inattendu)
    # ─────────────────────────────────────────────────────────────────────────
    print("  [Supervisor] Routage déterministe incertain — consultation du LLM.")
    decision = _llm_routing(state)

    print(f"🤖 [Supervisor] Décision LLM : {decision}")
    return {"next": decision}


# ═══════════════════════════════════════════════════════════════════════════════
# DÉCISIONS VALIDES — Liste exhaustive des valeurs acceptées pour state["next"]
# Correspond aux nœuds déclarés dans graph.py (Stécy)
# ═══════════════════════════════════════════════════════════════════════════════
VALID_DECISIONS = {"diagnostic_agent", "physician_review", "report_agent", "FINISH"}


# ═══════════════════════════════════════════════════════════════════════════════
# FONCTION PRIVÉE : _deterministic_routing
# Logique de routage pure — ne fait PAS appel au LLM
# ═══════════════════════════════════════════════════════════════════════════════

def _deterministic_routing(state: MedicalState) -> str:
    """
    Routage déterministe basé sur les champs du state.

    Implémente exactement les deux fonctions de routage de Stécy :
        - router_after_diagnostic()
        - router_after_physician()
    mais regroupées en une seule logique centralisée.

    Args:
        state (MedicalState): État courant du graphe

    Returns:
        str: Nom du prochain nœud à appeler
    """

    # ── Lecture des champs clés du state ──────────────────────────────────────

    # Champ écrit par report_agent_node() — non vide = workflow terminé
    final_report = state.get("final_report", "")

    # Champ écrit par physician_review_node() après décision du médecin
    # None = médecin pas encore consulté
    # True = médecin a validé → passer au rapport
    # False = médecin a refusé → retour au diagnostic
    physician_validation = state.get("physician_validation", None)

    # Champ écrit par diagnostic_agent_node() quand les 5 questions sont posées
    is_diagnosis_complete = state.get("is_diagnosis_complete", False)

    # Champ écrit par diagnostic_agent_node() — True si médecin nécessaire
    requires_physician_review = state.get("requires_physician_review", True)

    # Compteur de questions posées par le DiagnosticAgent (0 à 5)
    question_count = state.get("question_count", 0)

    # Synthèse clinique — vide si pas encore générée
    diagnostic_summary = state.get("diagnostic_summary", "")

    # ── Logique de routage par ordre de priorité ──────────────────────────────

    # PRIORITÉ 1 — Workflow terminé
    # Le rapport final est généré → on arrête tout
    if final_report:
        return "FINISH"

    # PRIORITÉ 2 — Après décision du médecin
    if physician_validation is True:
        # Médecin a validé → générer le rapport final
        return "report_agent"

    if physician_validation is False:
        # Médecin a refusé → retour au diagnostic pour correction
        # physician_feedback contient les corrections demandées
        return "diagnostic_agent"

    # PRIORITÉ 3 — Après diagnostic complet
    if is_diagnosis_complete and diagnostic_summary:
        # Les 5 questions ont été posées ET la synthèse est générée
        if requires_physician_review:
            # Cas standard : on soumet au médecin traitant
            return "physician_review"
        else:
            # Cas théorique (cahier des charges) : pas de revue médecin
            return "report_agent"

    # PRIORITÉ 4 — Diagnostic en cours (boucle des 5 questions)
    # Le DiagnosticAgent doit continuer à poser des questions
    if question_count < 5 or not diagnostic_summary:
        return "diagnostic_agent"

    # PRIORITÉ 5 — Cas indéterminé → fallback vers diagnostic
    # Ne devrait pas arriver en conditions normales
    return "diagnostic_agent"


# ═══════════════════════════════════════════════════════════════════════════════
# FONCTION PRIVÉE : _llm_routing
# Routage assisté par LLM — utilisé uniquement en fallback
# ═══════════════════════════════════════════════════════════════════════════════

def _llm_routing(state: MedicalState) -> str:
    """
    Routage assisté par LLM pour les cas ambigus.

    Construit un résumé de l'état courant et demande au LLM
    quelle décision prendre. Valide ensuite la réponse du LLM
    et applique un fallback déterministe si la réponse est invalide.

    Args:
        state (MedicalState): État courant du graphe

    Returns:
        str: Nom du prochain nœud validé
    """

    # Construction du résumé d'état pour le LLM
    # On ne transmet que les informations pertinentes pour le routage
    state_summary = f"""
État actuel de la consultation OrientaMed :
─────────────────────────────────────────
status                    : {state.get('status', 'started')}
question_count            : {state.get('question_count', 0)} / 5
is_diagnosis_complete     : {state.get('is_diagnosis_complete', False)}
requires_physician_review : {state.get('requires_physician_review', True)}
diagnostic_summary rempli : {'OUI' if state.get('diagnostic_summary') else 'NON'}
interim_care rempli       : {'OUI' if state.get('interim_care') else 'NON'}
physician_validation      : {state.get('physician_validation', 'None (pas encore consulté)')}
physician_treatment rempli: {'OUI' if state.get('physician_treatment') else 'NON'}
final_report rempli       : {'OUI' if state.get('final_report') else 'NON'}
─────────────────────────────────────────
Quelle est la prochaine étape du workflow ?
"""

    # Appel au LLM avec le prompt système de routage
    response = llm.invoke([
        SystemMessage(content=SUPERVISOR_SYSTEM_PROMPT),
        HumanMessage(content=state_summary)
    ])

    # Extraction et nettoyage de la décision du LLM
    decision = response.content.strip().lower().replace(".", "").replace("'", "")

    # Normalisation de "finish" → "FINISH"
    if decision == "finish":
        decision = "FINISH"

    # Validation : si le LLM répond n'importe quoi → fallback déterministe
    if decision not in VALID_DECISIONS:
        print(f"      [Supervisor] Réponse LLM invalide : '{decision}' — fallback déterministe.")
        decision = _fallback_routing(state)

    return decision


# ═══════════════════════════════════════════════════════════════════════════════
# FONCTION PRIVÉE : _fallback_routing
# Dernier recours — logique ultra-simplifiée garantissant une réponse valide
# ═══════════════════════════════════════════════════════════════════════════════

def _fallback_routing(state: MedicalState) -> str:
    """
    Fallback de dernier recours : garantit toujours une décision valide.
    Utilisé si à la fois le routage déterministe ET le LLM échouent.

    Logique minimale :
        1. Si rapport final présent → FINISH
        2. Si synthèse présente ET médecin validé → report_agent
        3. Si synthèse présente → physician_review
        4. Sinon → diagnostic_agent

    Args:
        state (MedicalState): État courant du graphe

    Returns:
        str: Décision de routage garantie valide
    """
    if state.get("final_report"):
        return "FINISH"
    if state.get("diagnostic_summary") and state.get("physician_validation"):
        return "report_agent"
    if state.get("diagnostic_summary"):
        return "physician_review"
    return "diagnostic_agent"


# ═══════════════════════════════════════════════════════════════════════════════
# FONCTION PUBLIQUE : should_continue
# Utilisée comme fonction de condition dans graph.py pour les edges conditionnels
#
# Usage dans graph.py (Stécy) :
#   from supervisor import should_continue
#   workflow.add_conditional_edges("supervisor", should_continue, {...})
# ═══════════════════════════════════════════════════════════════════════════════

def should_continue(state: MedicalState) -> str:
    """
    Fonction de condition pour les arêtes conditionnelles de LangGraph.
    Lit le champ state["next"] mis à jour par supervisor_node()
    et retourne le nom du prochain nœud.

    Utilisée dans graph.py comme :
        workflow.add_conditional_edges(
            "supervisor",
            should_continue,       ← cette fonction
            {
                "diagnostic_agent": "diagnostic_agent",
                "physician_review": "physician_review",
                "report_agent":     "report_agent",
                "FINISH":           END
            }
        )

    Args:
        state (MedicalState): État courant après supervisor_node()

    Returns:
        str: Valeur de state["next"] — clé du dict de routing
    """
    # Lire la décision prise par supervisor_node()
    # Fallback sur "diagnostic_agent" si "next" est absent (sécurité)
    return state.get("next", "diagnostic_agent")
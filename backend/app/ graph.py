#Stécy

from typing import Literal
from langgraph.graph import StateGraph, START, END
from state import MedicalState


# [CORRECTION E3] — MemorySaver obligatoire pour interrupt() (HITL)
from langgraph.checkpoint.memory import MemorySaver
 
# Import du state partagé — MedicalState de Stécy
from app.state import MedicalState
 
# [CORRECTION E3] — Imports corrects pour la structure du projet
from app.nodes.physician_review import physician_review_node
from app.nodes.report_agent     import report_agent_node
from app.nodes.diagnostic_agent import diagnostic_agent_node
 
# ==========================================
# 1. LOGIQUE DE ROUTAGE 
# ==========================================

def router_after_diagnostic(state: MedicalState) -> Literal["physician_review", "diagnostic_agent", "end"]:
    """
    Détermine la suite du workflow après l'évaluation de l'Étudiant 2.
    """
    # Si le diagnostic est fini, on passe à la validation du médecin (Étudiant 3)
    if state.get("is_diagnosis_complete") and state.get("requires_physician_review"):
        return "physician_review"
    
    # Si le diagnostic est fini mais ne nécessite pas de revue (cas théorique)
    if state.get("is_diagnosis_complete"):
        return "end"
    
    # Sinon, on continue de poser des questions (on boucle sur l'agent diagnostic)
    return "diagnostic_agent"

def router_after_physician(state: MedicalState) -> Literal["diagnostic_agent", "end"]:
    """
    Détermine la suite après la revue du médecin (Étudiant 3).
    """
    # Si le médecin refuse le diagnostic, on demande à l'agent diagnostic de corriger
    if state.get("physician_validation") is False:
        return "diagnostic_agent"
        
    # Si le médecin valide, le workflow se termine (le rapport final est prêt)
    return "end"

# ==========================================
# 2. ESPACES REQUIS POUR LE RESTE DU GROUPE (Nœuds anonymes)
# ==========================================

def diagnostic_node(state: MedicalState) -> dict:
    """
    [Espace Étudiant 2] - Agent Diagnostic
    Ce nœud appellera 'diagnostic_agent.py' et mettra à jour les symptômes
    et le compteur de questions.
    """
    print("--- PASSAGE PAR L'AGENT DIAGNOSTIC (Étudiant 2) ---")
    # Simulation de mise à jour pour le test
    return {"current_question_index": state.get("current_question_index", 0) + 1}

def physician_node(state: MedicalState) -> dict:
    """
    [ÉTUDIANT 3] — Médecin & Rapport (Human-in-the-Loop)
 
    Ce nœud appelle physician_review_node() implémenté dans physician_review.py.
    Il remplace la simulation de l'Étudiant 1 par le vrai HITL LangGraph.
 
    Fonctionnement :
        1. physician_review_node() présente le dossier au médecin
        2. Le graphe s'interrompt (interrupt()) et attend la saisie
        3. Après reprise, physician_validation est mis à jour dans le state
        4. router_after_physician() route vers report_agent ou diagnostic_agent
    """
    print("--- PASSAGE PAR LA REVUE MÉDECIN (Étudiant 3) ---")
 
    # [ÉTUDIANT 3] Appel du vrai nœud physician_review au lieu de la simulation
    return physician_review_node(state)

# ==========================================
# 3. CONSTRUCTION DU GRAPHE (Stécy — structure inchangée)
# ==========================================
 
workflow = StateGraph(MedicalState)
 
# Ajout des nœuds
workflow.add_node("diagnostic_agent", diagnostic_node)
workflow.add_node("physician_review",  physician_node)
workflow.add_node("report_agent",      report_agent_node)  # [Étudiant 3]
 
# Point d'entrée
workflow.add_edge(START, "diagnostic_agent")
 
# Routes conditionnelles
workflow.add_conditional_edges(
    "diagnostic_agent",
    router_after_diagnostic,
    {
        "diagnostic_agent": "diagnostic_agent",  # Boucle 5 questions
        "physician_review": "physician_review",  # Vers le médecin
        "end": END
    }
)
 
# [CORRECTION E3] — "report_agent" ajouté dans le mapping
workflow.add_conditional_edges(
    "physician_review",
    router_after_physician,
    {
        "diagnostic_agent": "diagnostic_agent",  # Refus → retour diagnostic
        "report_agent":     "report_agent",      # Validation → rapport final
    }
)
 
# [CORRECTION E3] — report_agent → END
workflow.add_edge("report_agent", END)
 
 
# ==========================================
# 4. COMPILATION
# ==========================================
 
# [CORRECTION E3] — MemorySaver obligatoire pour interrupt() dans physician_review
memory = MemorySaver()
 
# [CORRECTION E3] — Exporté comme orientamed_graph (importé par api.py)
# Stécy avait : app = workflow.compile()
# On garde les deux noms pour compatibilité
orientamed_graph = workflow.compile(checkpointer=memory)
app              = orientamed_graph   # Alias — compatibilité avec le code de Stécy
 
print(" Graphe OrientaMed compilé.")

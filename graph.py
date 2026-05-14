


#Stécy

from typing import Literal
from langgraph.graph import StateGraph, START, END
from state import MedicalState

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
    [Espace Étudiant 3] - Médecin & Rapport (Human-in-the-Loop)
    Ce nœud attendra une validation via 'physician_review.py'
    puis générera le rapport final.
    """
    print("--- PASSAGE PAR LA REVUE MÉDECIN (Étudiant 3) ---")
    # Simulation de validation
    return {"physician_validation": True}

# ==========================================
# 3. CONSTRUCTION DU GRAPHE
# ==========================================

# Initialisation du graphe avec votre structure d'état unique
workflow = StateGraph(MedicalState)

# Ajout des nœuds de traitement
workflow.add_node("diagnostic_agent", diagnostic_node)
workflow.add_node("physician_review", physician_node)

# Définition du point d'entrée
workflow.add_edge(START, "diagnostic_agent")

# Ajout des routes conditionnelles (C'est votre pilotage)
workflow.add_conditional_edges(
    "diagnostic_agent",
    router_after_diagnostic,
    {
        "diagnostic_agent": "diagnostic_agent", # Boucle pour les 5 questions
        "physician_review": "physician_review", # Redirection vers le médecin
        "end": END
    }
)

workflow.add_conditional_edges(
    "physician_review",
    router_after_physician,
    {
        "diagnostic_agent": "diagnostic_agent", # Retour à la case départ si refusé
        "end": END
    }
)

# Compilation du graphe
app = workflow.compile()

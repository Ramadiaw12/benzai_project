#Stécy

from langchain_core.messages import HumanMessage, AIMessage
from state import MedicalState

def run_supervisor(state: MedicalState) -> dict:
    """
    Rôle de l'Étudiant 1 : Analyse l'état pour planifier l'étape suivante.
    """
    print("🧠 [SUPERVISEUR] Analyse du flux en cours...")
    
    # Récupération des variables de décision
    q_index = state.get("current_question_index", 0)
    is_complete = state.get("is_diagnosis_complete", False)
    validation = state.get("physician_validation")

    # RÈGLE 1 : Si le diagnostic n'est pas fini et qu'on a moins de 5 questions -> Agent Diagnostic
    if not is_complete and q_index < 5:
        return {"next_agent": "diagnostic_agent"}
        
    # RÈGLE 2 : Si le diagnostic vient de se terminer -> Revue Médecin
    if is_complete and validation is None:
        return {"next_agent": "physician_review"}
        
    # RÈGLE 3 : Si le médecin a refusé (False) -> On renvoie au diagnostic pour correction
    if validation is False:
        print("⚠️ [SUPERVISEUR] Le médecin a refusé. Renvoi au Diagnostic.")
        return {
            "next_agent": "diagnostic_agent",
            "is_diagnosis_complete": False, # On réouvre le diagnostic
            "physician_validation": None     # On réinitialise la décision
        }
        
    # RÈGLE 4 : Si le médecin a validé -> Fin du workflow
    return {"next_agent": "end"}

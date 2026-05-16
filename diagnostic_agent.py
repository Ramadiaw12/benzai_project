#Stécy

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from state import MedicalState

# Initialisation du LLM (Utilise la clé du fichier .env)
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)

def run_diagnostic_agent(state: MedicalState) -> dict:
    """
    Squelette de l'Étudiant 2 : Pose des questions et extrait les symptômes.
    """
    messages = state.get("messages", [])
    q_index = state.get("current_question_index", 0)
    
    print(f"🩺 [DIAGNOSTIC] Exécution de la question numéro {q_index + 1}")

    # Prompt de base pour guider l'interrogatoire médical
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Tu es un assistant médical. Pose une seule question claire à la fois pour comprendre les symptômes du patient. Ne donne pas de diagnostic final avant d'avoir posé au moins 3 questions."),
        ("placeholder", "{messages}")
    ])
    
    # Chaîne d'exécution
    chain = prompt | llm
    response = chain.invoke({"messages": messages})
    
    # Incrémentation du compteur de questions
    new_index = q_index + 1
    
    # Simulation de fin automatique à la 3ème question pour le test
    is_done = True if new_index >= 3 else False

    return {
        "messages": [response],
        "current_question_index": new_index,
        "is_diagnosis_complete": is_done,
        "requires_physician_review": True
    }

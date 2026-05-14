# backend/app/tools/patient_tools.py audesM
from langchain_core.tools import tool

@tool
def ask_patient(question: str) -> str:
    """
    Pose une question au patient pour recueillir des informations cliniques.
    L'agent doit utiliser cet outil exactement 5 fois avant de conclure.
    """
    # Dans LangGraph, le message renvoyé par le tool sera ajouté à l'état (messages)
    # On formate la sortie pour qu'elle soit facilement identifiable par le frontend
    return f"ACTION_REQUIS_PATIENT: {question}"
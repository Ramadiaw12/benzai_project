# backend/app/nodes/diagnostic_agent.py audesM

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from app.state import MedicalState
from app.tools.patient_tools import ask_patient
from app.tools.care_tools import recommend_interim_care

tools = [ask_patient, recommend_interim_care]
model = ChatOpenAI(model="gpt-4o").bind_tools(tools)

SYSTEM_PROMPT = (
    "Tu es un Agent Diagnostic médical. Ton rôle est de poser exactement 5 questions "
    "au patient une par une pour comprendre ses symptômes. "
    "Utilise toujours le tool 'ask_patient' pour poser chaque question. "
    "Après 5 questions, utilise 'recommend_interim_care' avec la synthèse des symptômes, "
    "puis rédige une synthèse clinique préliminaire structurée."
)

def diagnostic_node(state: MedicalState) -> dict:
    """
    Nœud LangGraph : interrogatoire patient (5 questions) + synthèse clinique.
    """
    messages = state.get("messages", [])
    count = state.get("current_question_index", 0)

    full_messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages

    if count < 5:
        # L'agent pose une question via le tool ask_patient
        response = model.invoke(full_messages)
        return {
            "messages": [response],
            "current_question_index": count + 1,
            # ⚠️ Pas de "next" ici — c'est graph.py (Étudiant 1) qui gère la boucle
        }

    else:
        # 5 questions posées → on génère synthèse + recommandation via le tool
        summary_instruction = HumanMessage(
            content=(
                "Les 5 questions sont complètes. "
                "Appelle d'abord 'recommend_interim_care' avec une synthèse des symptômes. "
                "Ensuite rédige une synthèse clinique préliminaire structurée."
            )
        )
        response = model.invoke(full_messages + [summary_instruction])

        # Extraire le contenu texte de la synthèse clinique
        diagnostic_summary = ""
        interim_care = ""

        for block in response.content:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    diagnostic_summary = block.get("text", "")
                elif block.get("type") == "tool_use" and block.get("name") == "recommend_interim_care":
                    # Le tool retourne la recommandation directement
                    interim_care = recommend_interim_care.invoke(block.get("input", {}))
            elif isinstance(block, str):
                diagnostic_summary = block

        return {
            "messages": [response],
            "diagnostic_summary": diagnostic_summary,
            "is_diagnosis_complete": True, 
            "requires_physician_review": True,
        }

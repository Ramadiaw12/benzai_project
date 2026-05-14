import asyncio
from langchain_core.messages import HumanMessage
from graph import app

async def test_medical_workflow():
    print("=== DÉBUT DU TEST DU GRAPHE MÉDICAL (Étudiant 1) ===\n")

    # 1. État initial transmis par le Frontend (Étudiant 4)
    initial_state = {
        "messages": [HumanMessage(content="Bonjour, j'ai de la fièvre et des frissons.")],
        "patient_id": "PAT-2026-STECY",
        "patient_info": {"age": 22, "gender": "F", "medical_history": [], "current_medications": []},
        "current_question_index": 0,
        "is_diagnosis_complete": False,
        "requires_physician_review": True,
        "extracted_symptoms": [],
        "physician_validation": None,
        "physician_notes": "",
        "errors": []
    }

    # 2. Exécution du graphe de manière asynchrone
    # Le thread_id simule une session utilisateur unique
    config = {"configurable": {"thread_id": "session_test_stecy"}}
    
    async for event in app.astream(initial_state, config=config, stream_mode="updates"):
        for node_name, data in event.items():
            print(f"📍 Nœud exécuté : [{node_name}]")
            print(f"💾 Données renvoyées : {data}")
            print("-" * 40)

    print("\n=== FIN DU TEST : TOUTES LES BOUCLES DU WORKFLOW ONT TOURNÉ ===")

if __name__ == "__main__":
    asyncio.run(test_medical_workflow())

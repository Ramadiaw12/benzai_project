# backend/app/tools/care_tools.py audesM
from langchain_core.tools import tool


@tool
def recommend_interim_care(summary: str) -> str:
    """
    Génère des conseils de soins intermédiaires basés sur la synthèse clinique.
    Ces conseils sont temporaires en attendant l'avis du médecin.
    """
    # Logique de recommandation prudente (on pourrait utiliser un petit prompt ici aussi)
    disclaimer = "\n\n⚠️ IMPORTANT : Ce système ne remplace pas une consultation médicale."
    
    recommendation = (
        "Sur la base de vos symptômes, voici quelques conseils d'attente :\n"
        "- Repos conseillé et hydratation régulière.\n"
        "- Surveillez l'évolution de votre température.\n"
        "- En cas d'aggravation rapide, contactez immédiatement les urgences."
    )
    
    return f"Synthèse reçue : {summary}\n\n" + recommendation + disclaimer
# mcp_server/server.py audesM

from mcp.server.fastmcp import FastMCP

# ⚠️ Imports directs — pas de dépendance vers app/
# On recopie la logique ici pour éviter les problèmes de path

# Création du serveur MCP
mcp = FastMCP("MedicalDiagnosticServer")

@mcp.tool()
def ask_patient_tool(question: str) -> str:
    """
    Pose une question au patient pour recueillir des informations cliniques.
    L'agent doit utiliser cet outil exactement 5 fois avant de conclure.
    """
    try:
        return f"ACTION_REQUIS_PATIENT: {question}"
    except Exception as e:
        return f"ERREUR ask_patient: {str(e)}"

@mcp.tool()
def interim_care_tool(summary: str) -> str:
    """
    Génère des conseils de soins intermédiaires basés sur la synthèse clinique.
    Ces conseils sont temporaires en attendant l'avis du médecin.
    """
    try:
        disclaimer = "\n\n⚠️ IMPORTANT : Ce système ne remplace pas une consultation médicale."
        recommendation = (
            f"Synthèse reçue : {summary}\n\n"
            "Sur la base de vos symptômes, voici quelques conseils d'attente :\n"
            "- Repos conseillé et hydratation régulière.\n"
            "- Surveillez l'évolution de votre température.\n"
            "- En cas d'aggravation rapide, contactez immédiatement les urgences."
        )
        return recommendation + disclaimer
    except Exception as e:
        return f"ERREUR interim_care: {str(e)}"

if __name__ == "__main__":
    # ⚠️ A aligner avec Étudiant 4 : "stdio" ou "sse"
    mcp.run(transport="stdio")
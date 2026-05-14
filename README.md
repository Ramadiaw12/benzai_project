<div align="center">

<br/>

```
███╗   ███╗███████╗██████╗ ██╗ ██████╗ ██████╗  █████╗ ██████╗ ██╗  ██╗
████╗ ████║██╔════╝██╔══██╗██║██╔════╝ ██╔══██╗██╔══██╗██╔══██╗██║  ██║
██╔████╔██║█████╗  ██║  ██║██║██║  ███╗██████╔╝███████║██████╔╝███████║
██║╚██╔╝██║██╔══╝  ██║  ██║██║██║   ██║██╔══██╗██╔══██║██╔═══╝ ██╔══██║
██║ ╚═╝ ██║███████╗██████╔╝██║╚██████╔╝██║  ██║██║  ██║██║     ██║  ██║
╚═╝     ╚═╝╚══════╝╚═════╝ ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚═╝  ╚═╝
```

### Système Multi-Agents d'Orientation Clinique Préliminaire

<br/>

![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-00C2B2?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![MCP](https://img.shields.io/badge/MCP-Protocol-6C8EFF?style=for-the-badge&logo=anthropic&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![Vanilla JS](https://img.shields.io/badge/Frontend-Vanilla_JS-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black)
![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)

<br/>

> ⚕️ **Projet académique** — Ce système est un outil d'orientation clinique préliminaire.
> Il **ne remplace pas** une consultation médicale professionnelle.

<br/>

</div>

---

## 📋 Table des matières

- [Vue d'ensemble](#-vue-densemble)
- [Architecture](#-architecture)
- [Workflow clinique](#-workflow-clinique)
- [Équipe & répartition](#-équipe--répartition)
- [Frontend — Étudiant 4](#-frontend--étudiant-4)
- [Installation](#-installation)
- [API Reference](#-api-reference)
- [Jeux de tests](#-jeux-de-tests)
- [LangGraph Studio](#-langgraph-studio)
- [Docker](#-docker)

---

## 🧠 Vue d'ensemble

**MediGraph** est une application multi-agents construite avec **LangGraph** qui simule un workflow d'orientation clinique. Le système orchestre plusieurs agents IA pour :

1. **Collecter** les informations patient via 5 questions ciblées
2. **Analyser** les symptômes et produire une synthèse clinique préliminaire
3. **Intégrer** une validation humaine par un médecin traitant *(Human-in-the-Loop)*
4. **Générer** un rapport médical final structuré

```
Saisie patient  →  5 Questions IA  →  Synthèse clinique  →  Médecin valide  →  Rapport final
```

---

## 🏗 Architecture

```
mediagraph/
│
├── 🔵 backend/                      # FastAPI + LangGraph
│   ├── app/
│   │   ├── api.py                   # 5 endpoints REST
│   │   ├── graph.py                 # Graphe LangGraph complet
│   │   ├── state.py                 # MedicalState partagé
│   │   ├── nodes/
│   │   │   ├── supervisor.py        # Orchestre le workflow
│   │   │   ├── diagnostic_agent.py  # Pose les 5 questions
│   │   │   ├── physician_review.py  # HITL médecin
│   │   │   └── report_agent.py      # Génère le rapport final
│   │   └── tools/
│   │       ├── patient_tools.py     # Tool ask_patient
│   │       ├── care_tools.py        # Tool recommend_interim_care
│   │       └── mcp_client.py        # ← Client MCP (E4)
│   ├── Dockerfile                   # ← (E4)
│   ├── langgraph.json
│   └── requirements.txt
│
├── 🟢 mcp_server/                   # Serveur MCP
│   ├── server.py
│   └── Dockerfile                   # ← (E4)
│
├── 🟡 frontend/                     # Interface Vanilla JS
│   ├── index.html                   # ← (E4) — 4 écrans complets
│   └── Dockerfile                   # ← (E4)
│
├── docker-compose.yml               # ← (E4)
├── .env.example                     # ← (E4)
└── README.md                        # ← (E4)
```

---

## 🔄 Workflow clinique

```
                    ┌─────────────────────────────────┐
                    │              START               │
                    └────────────────┬────────────────┘
                                     │
                                     ▼
                          ┌──────────────────┐
                          │   Supervisor     │  ← orchestre tout
                          └────────┬─────────┘
                                   │
                                   ▼
                     ┌─────────────────────────┐
                     │     DiagnosticAgent     │
                     │  ┌───────────────────┐  │
                     │  │ ask_patient × 5   │◄─┼── MCP Tool
                     │  └───────────────────┘  │
                     │  ┌───────────────────┐  │
                     │  │ recommend_interim │◄─┼── MCP Tool
                     │  └───────────────────┘  │
                     └────────────┬────────────┘
                                  │
                                  ▼
                         ┌─────────────────┐
                         │   Supervisor    │
                         └────────┬────────┘
                                  │
                                  ▼
                    ┌─────────────────────────────┐
                    │    PhysicianReview  🧑‍⚕️      │  ← Human-in-the-Loop
                    │   (validation médecin)      │
                    └─────────────┬───────────────┘
                                  │
                                  ▼
                         ┌─────────────────┐
                         │   Supervisor    │
                         └────────┬────────┘
                                  │
                                  ▼
                        ┌──────────────────┐
                        │   ReportAgent    │  ← rapport final structuré
                        └────────┬─────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │           END           │
                    └─────────────────────────┘
```

---

## 👥 Équipe & répartition

| | Étudiant | Rôle | Responsabilités |
|--|----------|------|-----------------|
| 🔵 | **Étudiant 1** | Chef d'orchestre | `state.py`, `graph.py`, `supervisor.py`, `langgraph.json` |
| 🟢 | **Étudiant 2** | Agent Diagnostic | `diagnostic_agent.py`, `patient_tools.py`, `care_tools.py`, `mcp_server/` |
| 🟠 | **Étudiant 3** | Médecin & Rapport | `physician_review.py`, `report_agent.py`, `api.py` |
| 🟡 | **Étudiant 4** | Frontend & DevOps | `frontend/`, `mcp_client.py`, `Dockerfiles`, `docker-compose.yml`, `README.md` |

---

## 🟡 Frontend — Étudiant 4

### Stack technique

- **Vanilla HTML / CSS / JavaScript** — zéro dépendance, zéro build step
- **Auto-détection backend** — bascule en mode MOCK si le serveur est absent
- **4 écrans** complets, responsives et animés

### Les 4 écrans

**Écran 1 — Saisie patient**
Collecte du nom, âge et description des symptômes initiaux.

**Écran 2 — Questions cliniques**
Interface de chat avec l'Agent Diagnostic. 5 questions successives avec barre de progression. Le patient répond en temps réel (Entrée pour envoyer).

**Écran 3 — Revue médecin (Human-in-the-Loop)**
Le médecin traitant consulte la synthèse clinique préliminaire + recommandation intermédiaire, puis saisit sa conduite à tenir.

**Écran 4 — Rapport final**
Rapport structuré complet avec option impression / export PDF natif.

### Mode MOCK intégré

Si le backend n'est pas accessible, le frontend bascule **automatiquement** en mode simulation avec des données cliniques réalistes. Un badge ⚡ jaune l'indique clairement.

```js
// Une seule ligne à changer pour pointer vers le backend :
const API_BASE = "http://localhost:8000";
```

### Client MCP (`mcp_client.py`)

Module Python connectant les agents LangGraph au serveur MCP. Expose deux outils LangChain :

- `ask_patient_via_mcp` — pose une question au patient via MCP
- `recommend_interim_care_via_mcp` — génère la recommandation intermédiaire via MCP

Inclut un **fallback automatique** si le serveur MCP est indisponible.

---

## 🚀 Installation

### Prérequis

| Outil | Version minimale |
|-------|-----------------|
| Python | 3.11+ |
| pip | dernière version |
| Docker | optionnel |
| Navigateur | Chrome / Firefox / Edge |

---

### ⚡ Démarrage rapide — Sans rien installer

```bash
# Ouvre directement dans le navigateur :
open frontend/index.html
```

Le mode MOCK se déclenche automatiquement. Tu peux démontrer les 4 écrans sans backend.

---

### 🖥 Mode développement complet

**1 — Cloner le repo**
```bash
git clone https://github.com/<groupe>/mediagraph.git
cd mediagraph
```

**2 — Variables d'environnement**
```bash
cp .env.example .env
# Renseigner OPENAI_API_KEY dans .env
```

**3 — Installer les dépendances Python**
```bash
cd backend
pip install -r requirements.txt
```

**4 — Lancer le serveur MCP** *(terminal 1)*
```bash
cd mcp_server
uvicorn server:app --port 8001 --reload
```

**5 — Lancer le backend FastAPI** *(terminal 2)*
```bash
cd backend
uvicorn app.api:app --port 8000 --reload
```

**6 — Ouvrir le frontend** *(terminal 3)*
```bash
cd frontend
python -m http.server 3000
# → http://localhost:3000
```

---

### 🐳 Docker — tout en une commande

```bash
cp .env.example .env
# Renseigner OPENAI_API_KEY

docker-compose up --build
```

| Service | URL |
|---------|-----|
| 🟡 Frontend | http://localhost:3000 |
| 🔵 Backend API | http://localhost:8000 |
| 📚 Swagger Docs | http://localhost:8000/docs |
| 🟢 Serveur MCP | http://localhost:8001 |

```bash
docker-compose down          # arrêter
docker-compose logs -f       # voir les logs en direct
docker-compose restart       # redémarrer
```

---

## 📡 API Reference

### `POST /consultation/start`
```json
// Body
{
  "patient_name": "Ahmed Benali",
  "patient_age": 42,
  "patient_description": "Toux sèche depuis 3 jours avec légère fièvre"
}

// Réponse
{
  "thread_id": "abc-123",
  "status": "waiting_for_patient_answer",
  "question": "Depuis combien de temps avez-vous ces symptômes ?"
}
```

### `POST /consultation/resume`
```json
// Réponse patient
{ "thread_id": "abc-123", "response": "Depuis 3 jours, brutal.", "role": "patient" }

// Validation médecin
{ "thread_id": "abc-123", "response": "Amoxicilline 1g × 2/j, repos.", "role": "physician" }
```

### `GET /consultation/{thread_id}`
```json
{
  "status": "waiting_for_physician",
  "diagnostic_summary": "Tableau clinique compatible avec...",
  "interim_care": "Repos, hydratation...",
  "question_count": 5
}
```

### `GET /consultation/{thread_id}/report`
```json
{
  "diagnostic_summary": "...",
  "interim_care": "...",
  "physician_treatment": "...",
  "final_report": "RAPPORT D'ORIENTATION CLINIQUE..."
}
```

---

## 🧪 Jeux de tests

### Cas 1 — Syndrome respiratoire simple 🟢
```
Patient     : Ali Moussaoui, 35 ans
Symptômes   : Toux productive, fièvre 38.2°C depuis 4 jours

Q1 → "4 jours, progressif"
Q2 → "Gorge douloureuse 4/10"
Q3 → "Fièvre le soir à 38.2°C"
Q4 → "Aucun médicament"
Q5 → "Légère fatigue uniquement"

✅ Attendu : Rhinopharyngite virale — traitement symptomatique
```

### Cas 2 — Red flags 🔴
```
Patient     : Fatima El Amrani, 67 ans
Symptômes   : Douleur thoracique intense + essoufflement depuis 2h

Q1 → "2 heures, brutal"
Q2 → "Douleur 8/10, irradiation bras gauche"
Q3 → "Sueurs froides, pas de fièvre"
Q4 → "Anticoagulants, antécédents cardiaques"
Q5 → "Essoufflement, palpitations"

🚨 Attendu : Orientation urgences — pas d'automédication
```

### Cas 3 — Cas bénin 🟡
```
Patient     : Youssef Tazi, 22 ans
Symptômes   : Légère fatigue, rhinorrhée depuis hier

Q1 → "24h, progressif"
Q2 → "Aucune douleur"
Q3 → "Pas de fièvre"
Q4 → "Aucun antécédent"
Q5 → "Aucun autre signe"

✅ Attendu : Repos et hydratation — surveillance simple
```

---

## 🔬 LangGraph Studio

```bash
pip install langgraph-cli
cd backend
langgraph dev
# → http://localhost:8123
```

**Points à démontrer :**
- ✅ Graphe complet visualisé
- ✅ Transitions entre les nœuds
- ✅ Interruption patient (5 questions)
- ✅ Interruption médecin (HITL)
- ✅ États intermédiaires observables

---

## ⚙️ Variables d'environnement

| Variable | Obligatoire | Description |
|----------|:-----------:|-------------|
| `OPENAI_API_KEY` | ✅ | Clé API OpenAI |
| `MCP_SERVER_URL` | ❌ | URL MCP (défaut : `http://localhost:8001`) |
| `LANGCHAIN_TRACING_V2` | ❌ | Active le traçage LangSmith |
| `LANGCHAIN_API_KEY` | ❌ | Clé LangSmith |

---

## ⚠️ Cadre éthique

- Projet strictement **académique**.
- Aucun **diagnostic médical définitif** n'est fourni.
- Termes utilisés : *orientation clinique préliminaire*, *recommandation intermédiaire*.
- Toute sortie mentionne : **« Ce système ne remplace pas une consultation médicale. »**

---

<div align="center">

<br/>

Made with ❤️ — Groupe 4 · ENSET · 2025–2026

**Pr. Mohamed YOUSSFI**

<br/>

![Deadline](https://img.shields.io/badge/Deadline-15_Mai_2026_9H-FF6B6B?style=flat-square)
![Status](https://img.shields.io/badge/Status-Complété-7EE8A2?style=flat-square)
![License](https://img.shields.io/badge/Licence-Académique-6C8EFF?style=flat-square)

</div>
<div align="center">

<br/>

```
 ██████╗ ██████╗ ██╗███████╗███╗   ██╗████████╗ █████╗ ███╗   ███╗███████╗██████╗ 
██╔═══██╗██╔══██╗██║██╔════╝████╗  ██║╚══██╔══╝██╔══██╗████╗ ████║██╔════╝██╔══██╗
██║   ██║██████╔╝██║█████╗  ██╔██╗ ██║   ██║   ███████║██╔████╔██║█████╗  ██║  ██║
██║   ██║██╔══██╗██║██╔══╝  ██║╚██╗██║   ██║   ██╔══██║██║╚██╔╝██║██╔══╝  ██║  ██║
╚██████╔╝██║  ██║██║███████╗██║ ╚████║   ██║   ██║  ██║██║ ╚═╝ ██║███████╗██████╔╝
 ╚═════╝ ╚═╝  ╚═╝╚═╝╚══════╝╚═╝  ╚═══╝   ╚═╝   ╚═╝  ╚═╝╚═╝     ╚═╝╚══════╝╚═════╝ 
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

---

## 🏥 Description du projet

**OrientaMed** est une application intelligente de simulation d'un workflow d'orientation clinique médicale. Elle repose sur une architecture **multi-agents** orchestrée par **LangGraph**, où plusieurs agents IA collaborent pour accompagner un patient de la saisie de ses symptômes jusqu'à la génération d'un rapport médical final validé par un médecin humain.

Le système simule un parcours clinique complet en 4 étapes :

- 🧑‍💼 **Le patient** décrit ses symptômes et répond à 5 questions ciblées posées par l'Agent Diagnostic
- 🤖 **L'Agent Diagnostic** analyse les réponses, extrait les symptômes et produit une synthèse clinique préliminaire
- 🧑‍⚕️ **Le médecin traitant** valide ou corrige la synthèse (Human-in-the-Loop obligatoire)
- 📄 **L'Agent Rapport** génère un rapport médical final structuré

Le tout est exposé via une **API FastAPI**, intégré avec le protocole **MCP**, connecté à une interface **Vanilla JS** responsive et déployable via **Docker**.

<br/>

---

## 👩‍💻 Équipe du projet

| | Nom | Rôle |
|:---:|---|---|
| 🔵 | **Stécy Mombo Azzile** | Étudiant 1 — Chef d'orchestre · State & Graphe LangGraph |
| 🟢 | **Audès Mariana Moussavou** | Étudiant 2 — Agent Diagnostic · Outils MCP |
| 🟠 | **Ramatoulaye Diawara** | Étudiant 3 — Médecin & Rapport · API FastAPI |
| 🟡 | **Awa Aimée Benzekry** | Étudiant 4 — Frontend & DevOps · Docker · README |

**Encadrant :** Pr. Mohamed YOUSSFI · HESTIM · 2025–2026

<br/>

---

## 🏗 Architecture du projet

```
benzai_project/
│
├── backend/
│   ├── app/
│   │   ├── state.py                  ← Étudiant 1
│   │   ├── graph.py                  ← Étudiant 1
│   │   ├── nodes/
│   │   │   ├── supervisor.py         ← Étudiant 1
│   │   │   ├── diagnostic_agent.py   ← Étudiant 2
│   │   │   ├── physician_review.py   ← Étudiant 3
│   │   │   └── report_agent.py       ← Étudiant 3
│   │   ├── tools/
│   │   │   ├── patient_tools.py      ← Étudiant 2
│   │   │   ├── care_tools.py         ← Étudiant 2
│   │   │   └── mcp_client.py         ← Étudiant 4
│   │   └── api.py                    ← Étudiant 3
│   ├── langgraph.json                ← Étudiant 1
│   └── requirements.txt
│
├── mcp_server/
│   └── server.py                     ← Étudiant 2
│
├── frontend/                         ← Étudiant 4
│   ├── index.html
│   └── Dockerfile
│
├── docker-compose.yml                ← Étudiant 4
├── .env.example                      ← Étudiant 4
└── README.md                         ← Étudiant 4
```

---

## 🔄 Workflow clinique

```
START
  │
  ▼
Supervisor (E1)
  │
  ▼
DiagnosticAgent (E2) ──► ask_patient × 5   (MCP Tool)
                    ──► recommend_interim   (MCP Tool)
  │
  ▼
PhysicianReview (E3) ◄── Human-in-the-Loop
  │
  ▼
ReportAgent (E3) ──► Rapport final structuré
  │
  ▼
END
```

---

## 🚀 Installation & Lancement

### Prérequis

| Outil | Version |
|-------|---------|
| Python | 3.11+ |
| Docker | optionnel |
| Navigateur | Chrome / Firefox |

### Étapes

**1 — Cloner le repo**
```bash
git clone https://github.com/Ramadiaw12/benzai_project.git
cd benzai_project
```

**2 — Variables d'environnement**
```bash
cp .env.example .env
# Renseigner OPENAI_API_KEY dans .env
```

**3 — Installer les dépendances**
```bash
cd backend
pip install -r requirements.txt
```

**4 — Lancer le serveur MCP**
```bash
cd mcp_server
uvicorn server:app --port 8001 --reload
```

**5 — Lancer le backend FastAPI**
```bash
cd backend
uvicorn app.api:app --port 8000 --reload
```

**6 — Ouvrir le frontend**
```bash
# Ouvrir directement dans le navigateur :
open frontend/index.html
```

### Avec Docker

```bash
docker-compose up --build
```

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| Swagger Docs | http://localhost:8000/docs |
| Serveur MCP | http://localhost:8001 |

---

## 📡 API Reference

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| `POST` | `/consultation/start` | Démarre une consultation |
| `POST` | `/consultation/{thread_id}/resume` | Reprend (réponse patient ou médecin) |
| `GET`  | `/consultation/{thread_id}` | État courant du graphe |
| `GET`  | `/consultation/{thread_id}/report` | Rapport final |
| `GET`  | `/health` | Santé du serveur |

---

## 🧪 Jeux de tests

### Cas 1 — Syndrome respiratoire simple 🟢
```
Symptômes : Toux productive, fièvre 38.2°C depuis 4 jours
Résultat attendu : Rhinopharyngite virale — traitement symptomatique
```

### Cas 2 — Red flags 🔴
```
Symptômes : Douleur thoracique intense + essoufflement depuis 2h
Résultat attendu : Orientation urgences
```

### Cas 3 — Cas bénin 🟡
```
Symptômes : Légère fatigue, rhinorrhée depuis hier
Résultat attendu : Repos et hydratation
```

---

## ⚠️ Cadre éthique

- Projet strictement **académique**
- Aucun **diagnostic médical définitif** fourni
- Toute sortie mentionne : **« Ce système ne remplace pas une consultation médicale. »**

---

<div align="center">

<br/>

Made with ❤️ — Groupe 4 · HESTIM · 2025–2026

**Pr. Mohamed YOUSSFI**

<br/>

![Deadline](https://img.shields.io/badge/Deadline-15_Mai_2026_9H-FF6B6B?style=flat-square)
![Status](https://img.shields.io/badge/Status-Complété-7EE8A2?style=flat-square)
![License](https://img.shields.io/badge/Licence-Académique-6C8EFF?style=flat-square)

</div>
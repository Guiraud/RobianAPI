# RobianAPI - Backend pour RobianAPP

Backend API Python FastAPI pour l'application mobile RobianAPP (Rust/Robius).

## 🚀 Démarrage Rapide

```bash
# Installation dépendances
pip install -r requirements.txt

# Démarrage serveur
python api/main.py

# API disponible sur http://localhost:8000
# Documentation: http://localhost:8000/docs
```

## 📋 Endpoints Principaux

- `GET /api/debates` - Liste des débats
- `GET /api/debates/{id}` - Détail d'un débat  
- `GET /api/streaming/{id}/info` - Infos streaming
- `POST /api/extraction` - Demander extraction audio
- `GET /health` - Health check

## 🎯 Migration

Ce projet migre depuis `/Archive/AN-app/RobiAN/backend/` avec:
- ✅ Structure API FastAPI conservée
- ✅ Endpoints compatibles RobianAPP  
- 🔄 À finaliser: PostgreSQL + Redis + Docker

Voir `PROMPT_ROBIAN_API.md` pour le plan complet.

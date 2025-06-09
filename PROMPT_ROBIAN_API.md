# 🌐 RobianAPI - Backend Server pour Application RobianAPP

## 🎯 **OBJECTIF DU PROJET**

**RobianAPI** est le serveur backend **Python FastAPI** qui fournit les données et services à l'application mobile **RobianAPP**. Il gère l'extraction audio des vidéos de l'Assemblée nationale, le streaming, les métadonnées et toutes les fonctionnalités API nécessaires.

### **Architecture Cible**
```
🌐 RobianAPI (Backend Server)    ↔️     📱 RobianAPP (Client Mobile)
├── Python FastAPI                      ├── Rust + Robius
├── Extraction yt-dlp + FFmpeg          ├── Client HTTP (reqwest)
├── Base de données PostgreSQL          ├── Cache local SQLite
├── 12+ endpoints REST JSON             ├── Audio player cross-platform
├── Streaming audio optimisé            └── Interface Makepad UI
├── WebSockets temps réel (optionnel)
├── Rate limiting et sécurité
└── Documentation OpenAPI/Swagger
```

---

## 🏗️ **ÉTAT ACTUEL ET BASE DE TRAVAIL**

### **✅ Backend Fonctionnel Existant**
Un **serveur FastAPI complet** existe déjà dans `/RobiAN/backend/` avec :
- ✅ **12 endpoints REST** opérationnels
- ✅ **Extraction audio** yt-dlp + FFmpeg
- ✅ **Streaming optimisé** avec URLs directes
- ✅ **Scripts d'automatisation** complets
- ✅ **Gestion des métadonnées** débats
- ✅ **Health checks** et monitoring

### **🔄 À Finaliser pour Production**
1. **Migration du code existant** vers RobianAPI
2. **Base de données PostgreSQL** (actuellement fichier JSON)
3. **Authentification et sécurité** (rate limiting, CORS)
4. **Cache Redis** pour performances
5. **WebSockets** pour mise à jour temps réel
6. **Monitoring et logging** avancés
7. **Documentation API** complète
8. **Déploiement containerisé** (Docker)

---

## 📂 **STRUCTURE PROJET FINALE**

```
RobianAPI/
├── requirements.txt             # Dépendances Python
├── pyproject.toml              # Configuration projet moderne
├── Dockerfile                  # Container de déploiement
├── docker-compose.yml          # Orchestration services
├── .env.example                # Variables d'environnement
├── README.md                   # Documentation projet
├── CHANGELOG.md                # Historique versions
├── api/
│   ├── __init__.py
│   ├── main.py                 # Point d'entrée FastAPI
│   ├── config.py               # Configuration centralisée
│   ├── dependencies.py         # Dépendances FastAPI
│   ├── middleware.py           # CORS, rate limiting, logging
│   ├── routers/                # Routes API organisées
│   │   ├── __init__.py
│   │   ├── debates.py          # ✅ CRUD débats
│   │   ├── streaming.py        # ✅ URLs streaming audio
│   │   ├── extraction.py       # ✅ Extraction audio async
│   │   ├── search.py           # 🔄 Recherche avancée
│   │   ├── collections.py      # 🔄 Collections utilisateur
│   │   ├── favorites.py        # 🔄 Favoris et bookmarks
│   │   ├── stats.py            # 🔄 Statistiques usage
│   │   ├── health.py           # ✅ Health checks
│   │   └── websockets.py       # 🔄 Updates temps réel
│   ├── models/                 # Modèles de données
│   │   ├── __init__.py
│   │   ├── database.py         # Configuration DB
│   │   ├── debates.py          # Schéma débats
│   │   ├── audio.py            # Métadonnées audio
│   │   ├── users.py            # 🔄 Utilisateurs (optionnel)
│   │   └── collections.py      # 🔄 Collections et favoris
│   ├── services/               # Logique métier
│   │   ├── __init__.py
│   │   ├── extraction_service.py # ✅ Extraction audio
│   │   ├── streaming_service.py  # ✅ Génération URLs streaming
│   │   ├── metadata_service.py   # ✅ Scraping métadonnées
│   │   ├── cache_service.py      # 🔄 Cache Redis
│   │   ├── search_service.py     # 🔄 Recherche Elasticsearch
│   │   └── notification_service.py # 🔄 WebSockets
│   ├── utils/                  # Utilitaires
│   │   ├── __init__.py
│   │   ├── date_utils.py       # Manipulation dates
│   │   ├── format_utils.py     # Formatage données
│   │   ├── validation.py       # Validation entrées
│   │   └── security.py         # Utilitaires sécurité
│   └── schemas/                # Schémas Pydantic
│       ├── __init__.py
│       ├── debates.py          # Schémas API débats
│       ├── streaming.py        # Schémas réponses streaming
│       ├── extraction.py       # Schémas extraction
│       ├── search.py           # 🔄 Schémas recherche
│       └── common.py           # Schémas communs
├── scripts/                    # Scripts d'automatisation
│   ├── setup_database.py      # 🔄 Initialisation DB
│   ├── migrate_data.py         # 🔄 Migration données existantes
│   ├── health_check.py         # ✅ Monitoring santé
│   ├── backup_data.py          # 🔄 Sauvegarde données
│   ├── deploy.sh               # 🔄 Script déploiement
│   └── test_endpoints.py       # ✅ Tests API
├── tests/                      # Tests automatisés
│   ├── __init__.py
│   ├── conftest.py             # Configuration pytest
│   ├── test_debates.py         # Tests endpoints débats
│   ├── test_streaming.py       # Tests streaming
│   ├── test_extraction.py      # Tests extraction
│   └── test_integration.py     # Tests intégration
├── docs/                       # Documentation
│   ├── API.md                  # Documentation API complète
│   ├── DEPLOYMENT.md           # Guide déploiement
│   ├── DEVELOPMENT.md          # Guide développement
│   └── ARCHITECTURE.md         # Architecture technique
├── data/                       # Données persistantes
│   ├── cache/                  # Cache fichiers temporaires
│   ├── audio/                  # Fichiers audio extraits
│   └── logs/                   # Logs application
└── monitoring/                 # Monitoring et observabilité
    ├── prometheus.yml          # Métriques Prometheus
    ├── grafana/                # Dashboards Grafana
    └── alerting/               # Configuration alertes
```

---

## 🚀 **PLAN D'IMPLÉMENTATION**

### **Phase 1 : Migration et Restructuration (1-2 jours)**

#### **1.1 - Migration Code Existant**
```bash
# Copier la base existante vers RobianAPI
cp -r /path/to/RobiAN/backend/* ./
```

#### **1.2 - Configuration Moderne**
```toml
# pyproject.toml
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "robian-api"
version = "1.0.0"
description = "API Backend pour l'application RobianAPP"
authors = [{name = "RobianAPI Team", email = "team@robian-api.com"}]
license = {text = "GPL-3.0"}
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.104.0",
    "uvicorn[standard]>=0.24.0",
    "pydantic>=2.4.0",
    "pydantic-settings>=2.0.0",
    "sqlalchemy>=2.0.0",
    "asyncpg>=0.28.0",          # PostgreSQL async
    "redis[hiredis]>=5.0.0",    # Cache Redis
    "yt-dlp>=2023.10.13",       # Extraction vidéo
    "ffmpeg-python>=0.2.0",     # Processing audio
    "httpx>=0.25.0",            # Client HTTP async
    "celery[redis]>=5.3.0",     # Tasks async
    "prometheus-client>=0.17.0", # Métriques
    "structlog>=23.1.0",        # Logging structuré
    "python-multipart>=0.0.6",  # Upload fichiers
    "python-jose[cryptography]>=3.3.0", # JWT
    "passlib[bcrypt]>=1.7.4",   # Hash mots de passe
    "slowapi>=0.1.9",           # Rate limiting
    "websockets>=11.0.0",       # WebSockets
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.0",
    "pytest-cov>=4.1.0",
    "httpx>=0.25.0",
    "black>=23.9.0",
    "isort>=5.12.0",
    "mypy>=1.6.0",
    "pre-commit>=3.4.0",
]
```

### **Phase 5 : Containerisation et Déploiement (2-3 jours)**

#### **5.2 - Scripts de Déploiement**
```bash
# scripts/deploy.sh
#!/bin/bash
set -e

echo "🚀 Déploiement RobianAPI"

# Build Docker images
docker-compose build

# Migrations base de données
docker-compose run --rm api python scripts/setup_database.py

# Migration données existantes
docker-compose run --rm api python scripts/migrate_data.py

# Démarrage services
docker-compose up -d

# Health check
sleep 30
curl -f http://localhost:8000/health/ || exit 1

echo "✅ Déploiement terminé - API disponible sur http://localhost:8000"
echo "📚 Documentation : http://localhost:8000/docs"
echo "📊 Monitoring : http://localhost:3000 (Grafana)"
```

```bash
# scripts/test_endpoints.py
#!/usr/bin/env python3
import asyncio
import httpx
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"

async def test_all_endpoints():
    async with httpx.AsyncClient() as client:
        
        print("🧪 Test Health Check")
        response = await client.get(f"{BASE_URL}/health/")
        assert response.status_code == 200
        print("✅ Health check OK")
        
        print("\n🧪 Test Debates List")
        response = await client.get(f"{BASE_URL}/api/debates/")
        assert response.status_code == 200
        debates = response.json()
        print(f"✅ {len(debates)} débats récupérés")
        
        if debates:
            debate_id = debates[0]["id"]
            
            print(f"\n🧪 Test Debate Detail ({debate_id})")
            response = await client.get(f"{BASE_URL}/api/debates/{debate_id}")
            assert response.status_code == 200
            print("✅ Détail débat OK")
            
            print(f"\n🧪 Test Streaming Info ({debate_id})")
            response = await client.get(f"{BASE_URL}/api/streaming/{debate_id}/info")
            if response.status_code == 200:
                print("✅ Streaming info OK")
            else:
                print("⚠️ Streaming info non disponible")
        
        print("\n✅ Tous les tests passés !")

if __name__ == "__main__":
    asyncio.run(test_all_endpoints())
```

---

## 🎯 **ENDPOINTS API FINAUX**

### **Débats**
- `GET /api/debates/` - Liste des débats (filtres, pagination)
- `GET /api/debates/{id}` - Détail d'un débat
- `GET /api/debates/live` - Débats en cours
- `GET /api/debates/recent` - Débats récents
- `POST /api/debates/search` - Recherche avancée

### **Streaming Audio**
- `GET /api/streaming/{debate_id}/info` - Infos streaming
- `GET /api/streaming/{debate_id}/download` - URL téléchargement
- `POST /api/streaming/{debate_id}/extract` - Demander extraction
- `GET /api/streaming/{debate_id}/status` - Statut extraction

### **Collections (Nouveaux)**
- `GET /api/collections/` - Collections utilisateur
- `POST /api/collections/` - Créer collection
- `PUT /api/collections/{id}` - Modifier collection
- `DELETE /api/collections/{id}` - Supprimer collection
- `POST /api/collections/{id}/debates` - Ajouter débat

### **Favoris (Nouveaux)**
- `GET /api/favorites/` - Favoris utilisateur
- `POST /api/favorites/{debate_id}` - Ajouter aux favoris
- `DELETE /api/favorites/{debate_id}` - Retirer des favoris

### **Statistiques (Nouveaux)**
- `GET /api/stats/user` - Statistiques utilisateur
- `GET /api/stats/global` - Statistiques globales
- `GET /api/stats/trending` - Débats tendance

### **Monitoring**
- `GET /health/` - Health check simple
- `GET /health/detailed` - Health check détaillé
- `GET /metrics` - Métriques Prometheus

### **WebSockets**
- `WS /ws` - Connexion WebSocket pour updates temps réel

---

## 🛠️ **COMMANDES DE DÉVELOPPEMENT**

### **Setup Initial**
```bash
# Installation dépendances
pip install -r requirements.txt

# Setup base de données
python scripts/setup_database.py

# Migration données existantes
python scripts/migrate_data.py

# Démarrage développement
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

### **Docker**
```bash
# Build et démarrage
docker-compose up --build

# Logs
docker-compose logs -f api

# Base de données
docker-compose exec db psql -U postgres -d robian_db

# Redis CLI
docker-compose exec redis redis-cli
```

### **Tests**
```bash
# Tests unitaires
pytest tests/ -v

# Tests avec couverture
pytest tests/ --cov=api --cov-report=html

# Tests API
python scripts/test_endpoints.py

# Tests de charge
locust -f tests/load_tests.py --host=http://localhost:8000
```

### **Production**
```bash
# Déploiement complet
./scripts/deploy.sh

# Monitoring logs
docker-compose logs -f

# Backup base de données
python scripts/backup_data.py

# Health check détaillé
curl http://localhost:8000/health/detailed
```

---

## 📊 **MONITORING ET OBSERVABILITÉ**

### **Métriques Disponibles**
- **API** : Latence, débit, codes erreur
- **Base de données** : Connexions, requêtes, performances
- **Cache Redis** : Hit rate, mémoire, connexions
- **Extraction audio** : Durée, succès/échecs, queue
- **Système** : CPU, mémoire, disque, réseau

### **Dashboards Grafana**
- **API Overview** : Vue d'ensemble performances API
- **Database Performance** : Monitoring PostgreSQL
- **Audio Processing** : Suivi extractions audio
- **System Resources** : Ressources système
- **User Activity** : Activité utilisateurs

### **Alertes**
- API response time > 2s
- Taux d'erreur > 5%
- Utilisation disque > 85%
- Échec extraction audio > 20%
- Queue Celery > 100 tasks

---

## 🔒 **SÉCURITÉ ET PERFORMANCE**

### **Rate Limiting**
```python
# Par endpoint
@limiter.limit("100/minute")  # Débats généraux
@limiter.limit("50/minute")   # Streaming info
@limiter.limit("10/minute")   # Extraction audio
@limiter.limit("200/minute")  # Health checks
```

### **Cache Strategy**
```python
# Débats : 5 minutes (données changeantes)
# Streaming info : 1 heure (stable)
# Métadonnées : 24 heures (très stable)
# Health checks : 30 secondes (monitoring)
```

### **Validation et Sécurité**
- Validation Pydantic sur tous les inputs
- Sanitisation URLs et paramètres
- Protection CORS configurée
- Headers de sécurité (HSTS, CSP)
- Logging structuré de toutes les requêtes

---

## 🎯 **MÉTRIQUES DE SUCCÈS**

### **Performance**
- ✅ **Latence API** : < 200ms (95e percentile)
- ✅ **Disponibilité** : > 99.5% uptime
- ✅ **Débit** : > 1000 req/sec soutenues
- ✅ **Extraction audio** : < 5 minutes moyenne

### **Qualité**
- ✅ **Couverture tests** : > 90%
- ✅ **Documentation** : 100% endpoints documentés
- ✅ **Monitoring** : Alertes configurées
- ✅ **Logs** : Logging structuré complet

### **Utilisation**
- ✅ **Cache hit rate** : > 80%
- ✅ **Erreurs** : < 1% taux d'erreur
- ✅ **Concurrence** : Support 500+ utilisateurs simultanés
- ✅ **Scaling** : Auto-scaling configuré

---

## 🌟 **VISION PRODUCTION**

**RobianAPI** sera un **backend de référence** pour applications mobiles parlementaires :

### **Excellence Technique**
- **Architecture moderne** FastAPI + PostgreSQL + Redis
- **Performance optimale** avec cache multi-niveaux
- **Observabilité complète** avec métriques et alertes
- **Scalabilité horizontale** avec Docker + Kubernetes
- **Qualité production** avec tests et CI/CD

### **Fiabilité**
- **99.9% uptime** avec monitoring avancé
- **Auto-healing** avec health checks et restart
- **Backup automatique** avec stratégie de récupération
- **Rate limiting** pour protection DDoS
- **Logs centralisés** pour debugging rapide

### **Évolutivité**
- **API versioning** pour compatibilité
- **Plugin architecture** pour extensions
- **Event-driven** avec WebSockets
- **Multi-tenant** ready (utilisateurs)
- **International** avec i18n support

---

## 📞 **NEXT STEPS IMMÉDIATS**

1. **Migration code** : Copier base existante vers RobianAPI
2. **Setup PostgreSQL** : Migration données JSON → DB
3. **Cache Redis** : Implémentation cache multi-niveaux
4. **Tests complets** : Couverture 90%+ avec CI/CD
5. **Documentation** : API docs complète + guides
6. **Containerisation** : Docker production-ready
7. **Monitoring** : Prometheus + Grafana + alertes

**Objectif : API production-ready en 1-2 semaines** 🚀

---

*🌐 FastAPI + 🐘 PostgreSQL + 🔴 Redis = 🚀 High-Performance API*  
*Développé avec ❤️ pour servir l'application RobianAPP et la démocratie participative*
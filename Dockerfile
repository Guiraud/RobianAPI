# =============================================================================
# Dockerfile multi-stage pour RobianAPI
# Compatible Linux (production) et macOS (développement)
# =============================================================================

# =============================================================================
# STAGE 1: Base Python avec dépendances système
# =============================================================================
FROM python:3.11-slim-bullseye as base

# Métadonnées
LABEL maintainer="RobianAPI Team <team@robian-api.com>"
LABEL description="API Backend pour l'application RobianAPP"
LABEL version="1.0.0"

# Variables d'environnement
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    POETRY_VENV_IN_PROJECT=1 \
    POETRY_NO_INTERACTION=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

# Mise à jour du système et installation des dépendances
RUN apt-get update && apt-get install -y \
    # Dépendances de base
    curl \
    wget \
    git \
    # Dépendances pour compilation
    build-essential \
    gcc \
    g++ \
    # Dépendances pour PostgreSQL
    libpq-dev \
    # Dépendances pour audio/vidéo
    ffmpeg \
    # Dépendances pour yt-dlp
    ca-certificates \
    # Outils système
    procps \
    htop \
    # Nettoyage
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /tmp/*

# Création de l'utilisateur non-root pour sécurité
RUN groupadd -r robian && useradd -r -g robian robian

# =============================================================================
# STAGE 2: Installation des dépendances Python
# =============================================================================
FROM base as dependencies

# Installation de Poetry pour la gestion des dépendances
RUN pip install poetry==1.6.1

# Copie des fichiers de dépendances
COPY pyproject.toml poetry.lock* ./

# Installation des dépendances
RUN poetry install --only=main --no-root \
    && rm -rf $POETRY_CACHE_DIR

# =============================================================================
# STAGE 3: Development (avec toutes les dépendances)
# =============================================================================
FROM dependencies as development

# Installation des dépendances de développement
RUN poetry install --no-root

# Répertoire de travail
WORKDIR /app

# Copie du code source
COPY . .

# Propriétaire des fichiers
RUN chown -R robian:robian /app

# Utilisateur non-root
USER robian

# Port d'exposition
EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

# Commande par défaut
CMD ["poetry", "run", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# =============================================================================
# STAGE 4: Production (optimisé)
# =============================================================================
FROM base as production

# Installation directe via pip (plus rapide en production)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Répertoire de travail
WORKDIR /app

# Copie uniquement du code source nécessaire
COPY api/ ./api/
COPY scripts/ ./scripts/
COPY pyproject.toml .
COPY README.md .

# Création des répertoires de données
RUN mkdir -p /app/data/{audio,cache,logs} \
    && mkdir -p /tmp/robian-api \
    && chown -R robian:robian /app \
    && chown -R robian:robian /tmp/robian-api

# Utilisateur non-root
USER robian

# Port d'exposition
EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

# Commande par défaut (production)
CMD ["gunicorn", "api.main:app", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "--workers", "4"]

# =============================================================================
# STAGE 5: Testing (pour CI/CD)
# =============================================================================
FROM development as testing

# Installation des outils de test supplémentaires
RUN poetry install --with test

# Répertoire de travail
WORKDIR /app

# Copie des tests
COPY tests/ ./tests/

# Commande de test
CMD ["poetry", "run", "pytest", "-v", "--cov=api", "--cov-report=html", "--cov-report=term-missing"]

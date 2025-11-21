#!/bin/bash
echo "🚀 Initialisation Git pour RobianAPI"

# Se placer dans le dossier RobianAPI
cd /Users/mguiraud/Documents/gitlab/RobianAPI

# Vérifier si .git existe déjà
if [ -d ".git" ]; then
    echo "📂 Repository Git déjà initialisé"
    git status
else
    echo "🆕 Initialisation nouveau repository Git"
    git init
fi

# Ajouter tous les fichiers
echo "📁 Ajout des fichiers..."
git add .

# Créer le commit initial
echo "💾 Création du commit initial..."
git commit -m "🚀 Initial commit - RobianAPI Backend

✅ Migration depuis Archive/AN-app/RobiAN/backend/
✅ API FastAPI avec endpoints débats, streaming, programme  
✅ Structure projet modernisée
✅ Documentation et prompts optimisés
✅ Scripts d'automatisation includs

Architecture:
- Python FastAPI backend server
- 12+ endpoints REST JSON
- Extraction audio yt-dlp + FFmpeg
- Base pour migration PostgreSQL + Redis
- Prêt pour connexion RobianAPP client

Prêt pour développement production avec PROMPT_ROBIAN_API.md"

echo "✅ Git initialisé pour RobianAPI avec commit initial"
echo "📊 Status git:"
git log --oneline -1
git status --short

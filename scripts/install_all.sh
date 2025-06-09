#!/bin/bash

# Scripts d'installation complète pour AN-droid
# Installe toutes les dépendances nécessaires pour le projet

set -e

echo "🚀 Installation automatique AN-droid"
echo "=" * 60

# Couleurs pour l'affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Fonction pour afficher les étapes
log_step() {
    echo -e "${BLUE}▶ $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️ $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Vérifier que nous sommes dans le bon répertoire
if [[ ! -f "plan.md" ]]; then
    log_error "Ce script doit être exécuté depuis la racine du projet AN-droid"
    exit 1
fi

PROJECT_ROOT=$(pwd)
log_success "Répertoire projet: $PROJECT_ROOT"

# 1. Vérifier Python 3.8+
log_step "Vérification de Python..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    log_success "Python $PYTHON_VERSION détecté"
    
    # Vérifier la version minimale
    if python3 -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)"; then
        log_success "Version Python OK (>= 3.8)"
    else
        log_error "Python 3.8+ requis, version $PYTHON_VERSION détectée"
        exit 1
    fi
else
    log_error "Python 3 non trouvé. Installez Python 3.8+ avant de continuer."
    exit 1
fi

# 2. Créer/activer l'environnement virtuel
log_step "Configuration environnement virtuel..."
if [[ ! -d ".venv" ]]; then
    log_step "Création de l'environnement virtuel..."
    python3 -m venv .venv
    log_success "Environnement virtuel créé"
else
    log_success "Environnement virtuel existant trouvé"
fi

# Activer l'environnement virtuel
log_step "Activation de l'environnement virtuel..."
source .venv/bin/activate
log_success "Environnement virtuel activé"

# 3. Mise à jour pip
log_step "Mise à jour de pip..."
pip install --upgrade pip
log_success "pip mis à jour"

# 4. Installation des dépendances Python
log_step "Installation des dépendances Python..."
if [[ -f "requirements.txt" ]]; then
    pip install -r requirements.txt
    log_success "Dépendances Python installées"
else
    log_warning "requirements.txt non trouvé, installation manuelle..."
    pip install fastapi uvicorn requests beautifulsoup4 lxml yt-dlp pydantic
    log_success "Dépendances de base installées"
fi

# 5. Vérifier yt-dlp
log_step "Vérification de yt-dlp..."
if command -v yt-dlp &> /dev/null; then
    YTDLP_VERSION=$(yt-dlp --version)
    log_success "yt-dlp $YTDLP_VERSION disponible"
else
    log_step "Installation de yt-dlp via pip..."
    pip install yt-dlp
    log_success "yt-dlp installé"
fi

# 6. Vérifier FFmpeg (requis pour yt-dlp)
log_step "Vérification de FFmpeg..."
if command -v ffmpeg &> /dev/null; then
    FFMPEG_VERSION=$(ffmpeg -version | head -n 1 | cut -d' ' -f3)
    log_success "FFmpeg $FFMPEG_VERSION disponible"
else
    log_warning "FFmpeg non détecté."
    echo "FFmpeg est requis pour l'extraction audio avec yt-dlp."
    echo ""
    echo "Installation sur macOS:"
    echo "  brew install ffmpeg"
    echo ""
    echo "Installation sur Ubuntu/Debian:"
    echo "  sudo apt update && sudo apt install ffmpeg"
    echo ""
    echo "Installation sur Fedora/RHEL:"
    echo "  sudo dnf install ffmpeg"
    echo ""
    read -p "Continuer sans FFmpeg? (les extractions audio échoueront) [y/N]: " continue_without_ffmpeg
    if [[ $continue_without_ffmpeg != "y" && $continue_without_ffmpeg != "Y" ]]; then
        log_error "Installation annulée. Installez FFmpeg et relancez ce script."
        exit 1
    fi
fi

# 7. Créer les répertoires nécessaires
log_step "Création des répertoires de travail..."
mkdir -p downloads
mkdir -p logs
mkdir -p cache
log_success "Répertoires créés"

# 8. Configurer le fichier .env
log_step "Configuration de l'environnement..."
if [[ ! -f ".env" ]]; then
    if [[ -f ".env.example" ]]; then
        cp .env.example .env
        log_success "Fichier .env créé depuis .env.example"
    else
        # Créer un .env de base
        cat > .env << EOF
# Configuration AN-droid
DEBUG=true
API_HOST=localhost
API_PORT=8000
LOG_LEVEL=INFO
DOWNLOAD_DIR=downloads
CACHE_DIR=cache
MAX_DURATION=14400
MAX_FILE_SIZE=524288000
RATE_LIMIT=5
EOF
        log_success "Fichier .env de base créé"
    fi
else
    log_success "Fichier .env existant conservé"
fi

# 9. Test de base de l'installation
log_step "Test de l'installation..."

# Test import Python
python3 -c "
import requests
import subprocess
import json
import fastapi
import uvicorn
print('✅ Tous les modules Python importés avec succès')
"

# Test yt-dlp
if command -v yt-dlp &> /dev/null; then
    yt-dlp --version > /dev/null
    log_success "yt-dlp fonctionne"
else
    log_warning "yt-dlp non disponible dans PATH"
fi

# 10. Afficher le résumé
echo ""
echo "=" * 60
log_success "🎉 Installation terminée avec succès!"
echo ""
echo "📋 Résumé de l'installation:"
echo "  • Python: $(python3 --version)"
echo "  • Environnement virtuel: .venv/"
echo "  • Dépendances: installées"
if command -v yt-dlp &> /dev/null; then
    echo "  • yt-dlp: $(yt-dlp --version)"
fi
if command -v ffmpeg &> /dev/null; then
    echo "  • FFmpeg: $(ffmpeg -version | head -n 1 | cut -d' ' -f3)"
fi
echo "  • Répertoires: downloads/, logs/, cache/"
echo "  • Configuration: .env"
echo ""
echo "🚀 Prochaines étapes:"
echo "  1. Vérifiez le fichier .env si nécessaire"
echo "  2. Lancez l'API: ./scripts/deploy_local.sh"
echo "  3. Ou testez l'extraction: python3 final_extractor.py"
echo ""
echo "💡 L'environnement virtuel est activé dans cette session."
echo "   Pour les prochaines sessions, utilisez: source .venv/bin/activate"
echo ""
echo "=" * 60

# Vérifier si nous devons proposer le déploiement
read -p "Voulez-vous lancer le déploiement local maintenant? [y/N]: " launch_deploy
if [[ $launch_deploy == "y" || $launch_deploy == "Y" ]]; then
    log_step "Lancement du déploiement local..."
    if [[ -f "scripts/deploy_local.sh" ]]; then
        bash scripts/deploy_local.sh
    else
        log_warning "scripts/deploy_local.sh non trouvé. Créez-le d'abord."
    fi
fi

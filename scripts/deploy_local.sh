#!/bin/bash

# Script de déploiement local AN-droid
# Lance l'API et configure l'environnement complet

set -e

echo "🚀 Déploiement local AN-droid"
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

# 1. Vérifier l'installation
log_step "Vérification de l'installation..."

if [[ ! -d ".venv" ]]; then
    log_error "Environnement virtuel non trouvé. Lancez d'abord: ./scripts/install_all.sh"
    exit 1
fi

if [[ ! -f ".env" ]]; then
    log_warning "Fichier .env non trouvé, création d'un fichier de base..."
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
    log_success "Fichier .env créé"
fi

# 2. Activer l'environnement virtuel
log_step "Activation de l'environnement virtuel..."
source .venv/bin/activate
log_success "Environnement virtuel activé"

# 3. Charger la configuration
log_step "Chargement de la configuration..."
if [[ -f ".env" ]]; then
    source .env
    log_success "Configuration chargée depuis .env"
else
    # Valeurs par défaut
    API_HOST=${API_HOST:-localhost}
    API_PORT=${API_PORT:-8000}
    LOG_LEVEL=${LOG_LEVEL:-INFO}
    DOWNLOAD_DIR=${DOWNLOAD_DIR:-downloads}
    CACHE_DIR=${CACHE_DIR:-cache}
fi

echo "  • Host: $API_HOST"
echo "  • Port: $API_PORT"
echo "  • Log Level: $LOG_LEVEL"
echo "  • Download Dir: $DOWNLOAD_DIR"
echo "  • Cache Dir: $CACHE_DIR"

# 4. Créer les répertoires nécessaires
log_step "Préparation des répertoires..."
mkdir -p "$DOWNLOAD_DIR"
mkdir -p "$CACHE_DIR"
mkdir -p "logs"
log_success "Répertoires prêts"

# 5. Vérifier les dépendances
log_step "Vérification des dépendances..."

# Test des imports Python critiques
python3 -c "
try:
    import fastapi
    import uvicorn
    import requests
    import subprocess
    print('✅ Modules Python OK')
except ImportError as e:
    print(f'❌ Module manquant: {e}')
    exit(1)
" || {
    log_error "Dépendances Python manquantes. Lancez: ./scripts/install_all.sh"
    exit 1
}

# Test yt-dlp
if ! command -v yt-dlp &> /dev/null; then
    log_warning "yt-dlp non disponible dans PATH"
    # Essayer via Python
    if ! python3 -c "import yt_dlp" 2>/dev/null; then
        log_error "yt-dlp non disponible. Installez-le avec: pip install yt-dlp"
        exit 1
    else
        log_success "yt-dlp disponible via Python"
    fi
else
    log_success "yt-dlp disponible"
fi

# 6. Vérifier que le port est libre
log_step "Vérification du port $API_PORT..."
if command -v lsof &> /dev/null; then
    if lsof -ti:$API_PORT > /dev/null 2>&1; then
        log_warning "Port $API_PORT déjà utilisé"
        PID=$(lsof -ti:$API_PORT)
        echo "  Processus utilisant le port: PID $PID"
        
        read -p "Arrêter le processus et continuer? [y/N]: " kill_process
        if [[ $kill_process == "y" || $kill_process == "Y" ]]; then
            kill $PID 2>/dev/null || true
            sleep 2
            log_success "Processus arrêté"
        else
            log_error "Déploiement annulé"
            exit 1
        fi
    else
        log_success "Port $API_PORT libre"
    fi
fi

# 7. Préparer les logs
LOG_FILE="logs/api_$(date +%Y%m%d_%H%M%S).log"
log_step "Initialisation des logs: $LOG_FILE"

# Créer le fichier de log
touch "$LOG_FILE"
log_success "Fichier de log créé"

# 8. Lancer l'API en arrière-plan
log_step "Lancement de l'API AN-droid..."

# Vérifier que le fichier API existe
if [[ ! -f "api/main.py" ]]; then
    log_error "Fichier api/main.py non trouvé"
    exit 1
fi

# Commande de lancement
API_CMD="uvicorn api.main:app --host $API_HOST --port $API_PORT --log-level $(echo $LOG_LEVEL | tr '[:upper:]' '[:lower:]')"

echo "Commande API: $API_CMD"

# Lancer l'API en arrière-plan
nohup $API_CMD > "$LOG_FILE" 2>&1 &
API_PID=$!

# Sauvegarder le PID
echo $API_PID > .api_pid

log_success "API lancée (PID: $API_PID)"

# 9. Attendre que l'API soit prête
log_step "Attente du démarrage de l'API..."

for i in {1..30}; do
    if curl -s "http://$API_HOST:$API_PORT/health" > /dev/null 2>&1; then
        log_success "API prête et fonctionnelle"
        break
    elif curl -s "http://$API_HOST:$API_PORT/" > /dev/null 2>&1; then
        log_success "API prête"
        break
    fi
    
    echo -n "."
    sleep 1
    
    if [[ $i -eq 30 ]]; then
        log_warning "L'API met du temps à démarrer..."
        echo "Vérifiez les logs: tail -f $LOG_FILE"
    fi
done

# 10. Tests de base
log_step "Tests de base de l'API..."

# Test endpoint de base
if curl -s "http://$API_HOST:$API_PORT/" > /dev/null; then
    log_success "Endpoint racine accessible"
else
    log_warning "Endpoint racine non accessible"
fi

# Test endpoint docs (si disponible)
if curl -s "http://$API_HOST:$API_PORT/docs" > /dev/null; then
    log_success "Documentation Swagger accessible"
fi

# 11. Affichage du résumé
echo ""
echo "=" * 60
log_success "🎉 Déploiement local réussi!"
echo ""
echo "📋 Informations de déploiement:"
echo "  • API URL: http://$API_HOST:$API_PORT"
echo "  • Documentation: http://$API_HOST:$API_PORT/docs"
echo "  • PID de l'API: $API_PID"
echo "  • Fichier de log: $LOG_FILE"
echo "  • Répertoire downloads: $DOWNLOAD_DIR"
echo "  • Répertoire cache: $CACHE_DIR"
echo ""
echo "🔧 Commandes utiles:"
echo "  • Voir les logs: tail -f $LOG_FILE"
echo "  • Arrêter l'API: kill $API_PID"
echo "  • Recharger l'API: kill -HUP $API_PID"
echo "  • Monitoring: ./scripts/monitor_system.py"
echo "  • Health check: ./scripts/health_check.py"
echo ""
echo "🧪 Tests disponibles:"
echo "  • Test extraction: python3 final_extractor.py"
echo "  • Test API: python3 test_api.py"
echo "  • Test yt-dlp: python3 scripts/test_ytdlp.py"
echo ""
echo "⚠️ Pour arrêter complètement:"
echo "   kill \$(cat .api_pid) && rm .api_pid"
echo ""
echo "=" * 60

# Option pour lancer les tests
read -p "Voulez-vous lancer les tests de base maintenant? [y/N]: " run_tests
if [[ $run_tests == "y" || $run_tests == "Y" ]]; then
    log_step "Lancement des tests..."
    
    # Test simple de l'extracteur
    echo ""
    echo "Test de l'extracteur final:"
    python3 -c "
from final_extractor import FinalAudioExtractor
import requests

# Test de base sans téléchargement
extractor = FinalAudioExtractor()
test_url = 'https://videos.assemblee-nationale.fr/video.16905943_682f1c59d8a2c.2eme-seance--droit-a-l-aide-a-mourir-suite-22-mai-2025'

print('🧪 Test extraction URLs m3u8...')
m3u8_urls = extractor.extract_m3u8_urls(test_url)
if m3u8_urls:
    print(f'✅ {len(m3u8_urls)} URL(s) m3u8 trouvée(s)')
else:
    print('❌ Aucune URL m3u8 trouvée')
"
    
    # Test API si accessible
    if curl -s "http://$API_HOST:$API_PORT/" > /dev/null; then
        echo ""
        echo "Test de l'API:"
        curl -s "http://$API_HOST:$API_PORT/" | head -3
    fi
fi

# Garder le script en vie pour monitoring
read -p "Voulez-vous laisser ce terminal ouvert pour le monitoring? [y/N]: " keep_monitoring
if [[ $keep_monitoring == "y" || $keep_monitoring == "Y" ]]; then
    log_step "Mode monitoring activé - Ctrl+C pour quitter"
    
    # Fonction de nettoyage
    cleanup() {
        echo ""
        log_step "Arrêt de l'API..."
        if [[ -f .api_pid ]]; then
            API_PID=$(cat .api_pid)
            kill $API_PID 2>/dev/null || true
            rm .api_pid
            log_success "API arrêtée"
        fi
        log_success "Nettoyage terminé"
        exit 0
    }
    
    # Trappe pour Ctrl+C
    trap cleanup SIGINT SIGTERM
    
    # Boucle de monitoring simple
    echo "Appuyez sur Ctrl+C pour arrêter l'API et quitter"
    echo "Logs en cours: $LOG_FILE"
    echo ""
    
    while true; do
        if ! kill -0 $API_PID 2>/dev/null; then
            log_error "L'API s'est arrêtée de manière inattendue"
            rm -f .api_pid
            break
        fi
        sleep 5
    done
else
    log_success "Déploiement terminé - API en cours d'exécution"
    echo "Pour arrêter: kill \$(cat .api_pid) && rm .api_pid"
fi

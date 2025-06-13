 #!/usr/bin/env python3
"""
Script de démarrage rapide pour RobianAPI
Setup automatique et lancement en mode développement
"""

import os
import sys
import asyncio
import subprocess
import time
import importlib
from pathlib import Path
from dotenv import load_dotenv

# Charger les variables d'environnement depuis le fichier .env
load_dotenv(override=True)

# Afficher les variables de cache pour le débogage
print("CACHE_TTL_DEFAULT:", os.getenv("CACHE_TTL_DEFAULT"))
print("CACHE_TTL_DEBATES:", os.getenv("CACHE_TTL_DEBATES"))
print("CACHE_TTL_STREAMING:", os.getenv("CACHE_TTL_STREAMING"))
print("CACHE_TTL_METADATA:", os.getenv("CACHE_TTL_METADATA"))

# Ajouter le dossier parent au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent))

# Nettoyer le cache de Pydantic
if 'pydantic' in sys.modules:
    import pydantic
    import pydantic_settings
    import pydantic_core
    importlib.reload(pydantic)
    importlib.reload(pydantic_settings)
    importlib.reload(pydantic_core)

from api.config import settings, get_platform_info
import structlog

# Ajouter le dossier parent au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent))

logger = structlog.get_logger(__name__)


def run_command(command: str, cwd: Path = None, check: bool = True):
    """Exécuter une commande shell"""
    logger.info(f"🔧 Exécution: {command}")
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            check=check,
            capture_output=True,
            text=True
        )
        if result.stdout:
            logger.info(f"📤 Sortie: {result.stdout.strip()}")
        return result
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Erreur commande: {e}")
        if e.stderr:
            logger.error(f"📥 Erreur: {e.stderr.strip()}")
        raise


def check_dependencies():
    """Vérifier les dépendances système"""
    logger.info("🔍 Vérification des dépendances...")
    
    # Vérifier Python
    python_version = sys.version_info
    if python_version < (3, 11):
        logger.error(f"❌ Python 3.11+ requis, trouvé {python_version.major}.{python_version.minor}")
        return False
    
    logger.info(f"✅ Python {python_version.major}.{python_version.minor}.{python_version.micro}")
    
    # Vérifier Docker (optionnel)
    try:
        result = run_command("docker --version", check=False)
        if result.returncode == 0:
            logger.info("✅ Docker disponible")
        else:
            logger.warning("⚠️ Docker non disponible (optionnel)")
    except:
        logger.warning("⚠️ Docker non disponible (optionnel)")
    
    # Vérifier Docker Compose (optionnel)
    try:
        result = run_command("docker-compose --version", check=False)
        if result.returncode == 0:
            logger.info("✅ Docker Compose disponible")
        else:
            logger.warning("⚠️ Docker Compose non disponible (optionnel)")
    except:
        logger.warning("⚠️ Docker Compose non disponible (optionnel)")
    
    return True


def setup_environment():
    """Configuration de l'environnement"""
    logger.info("⚙️ Configuration de l'environnement...")
    
    # Créer .env s'il n'existe pas
    env_file = Path(".env")
    env_example = Path(".env.example")
    
    if not env_file.exists() and env_example.exists():
        logger.info("📝 Création du fichier .env depuis .env.example")
        import shutil
        shutil.copy(env_example, env_file)
        logger.warning("⚠️ Pensez à modifier .env selon votre configuration!")
    
    # Créer les dossiers de données
    for path in [settings.paths.data_dir, settings.paths.cache_dir, 
                 settings.paths.audio_dir, settings.paths.logs_dir]:
        path.mkdir(parents=True, exist_ok=True)
        logger.info(f"📁 Dossier créé: {path}")


def install_dependencies():
    """Installation des dépendances Python"""
    logger.info("📦 Installation des dépendances...")
    
    # Vérifier si on est dans un venv
    in_venv = hasattr(sys, 'real_prefix') or (
        hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
    )
    
    if not in_venv:
        logger.warning("⚠️ Vous n'êtes pas dans un environnement virtuel!")
        logger.warning("   Il est recommandé d'utiliser un venv pour éviter les conflits")
        
        response = input("Continuer quand même? (y/N): ")
        if response.lower() != 'y':
            logger.info("❌ Installation annulée")
            return False
    
    # Installer avec pip
    try:
        # Installation en mode éditable avec dépendances de dev
        run_command(f"{sys.executable} -m pip install -e .[dev]")
        logger.info("✅ Dépendances installées avec succès")
        return True
    except Exception as e:
        logger.error(f"❌ Erreur installation dépendances: {e}")
        
        # Fallback sur requirements.txt
        req_file = Path("requirements.txt")
        if req_file.exists():
            logger.info("🔄 Tentative avec requirements.txt...")
            try:
                run_command(f"{sys.executable} -m pip install -r requirements.txt")
                logger.info("✅ Dépendances installées via requirements.txt")
                return True
            except Exception as e2:
                logger.error(f"❌ Erreur avec requirements.txt: {e2}")
        
        return False


def setup_database():
    """Configuration de la base de données"""
    logger.info("🐘 Configuration de la base de données...")
    
    try:
        # Lancer le script de setup
        run_command(f"{sys.executable} scripts/setup_database.py setup")
        logger.info("✅ Base de données configurée")
        return True
    except Exception as e:
        logger.error(f"❌ Erreur setup base de données: {e}")
        logger.info("💡 Assurez-vous que PostgreSQL est démarré")
        logger.info("   Avec Docker: docker-compose up postgres -d")
        return False


def start_services_docker():
    """Démarrer les services avec Docker"""
    logger.info("🐳 Démarrage des services Docker...")
    
    try:
        # Démarrer PostgreSQL et Redis
        run_command("docker-compose up postgres redis -d")
        
        # Attendre que les services soient prêts
        logger.info("⏳ Attente démarrage des services...")
        time.sleep(10)
        
        # Vérifier que les services sont up
        run_command("docker-compose ps")
        
        logger.info("✅ Services Docker démarrés")
        return True
    except Exception as e:
        logger.error(f"❌ Erreur démarrage Docker: {e}")
        return False


def run_tests():
    """Lancer les tests"""
    logger.info("🧪 Lancement des tests...")
    
    try:
        run_command(f"{sys.executable} scripts/test_api.py --services-only")
        logger.info("✅ Tests passés avec succès")
        return True
    except Exception as e:
        logger.error(f"❌ Certains tests ont échoué: {e}")
        return False


def start_api():
    """Démarrer l'API en mode développement"""
    logger.info("🚀 Démarrage de l'API RobianAPI...")
    
    # Afficher les informations de configuration
    platform_info = get_platform_info()
    logger.info("📋 Configuration:")
    logger.info(f"   🖥️ Plateforme: {platform_info['system']}")
    logger.info(f"   🐍 Python: {platform_info['python_version']}")
    logger.info(f"   🌍 Environnement: {settings.app.environment}")
    logger.info(f"   🔧 Debug: {settings.app.debug}")
    logger.info(f"   📂 Données: {settings.paths.data_dir}")
    logger.info(f"   🌐 URL: http://{settings.app.host}:{settings.app.port}")
    logger.info(f"   📚 Docs: http://{settings.app.host}:{settings.app.port}/docs")
    
    try:
        # Lancer l'API avec uvicorn
        run_command(
            f"{sys.executable} -m uvicorn api.main:app "
            f"--host {settings.app.host} "
            f"--port {settings.app.port} "
            f"--reload"
        )
    except KeyboardInterrupt:
        logger.info("🛑 Arrêt de l'API demandé")
    except Exception as e:
        logger.error(f"❌ Erreur démarrage API: {e}")


def main():
    """Point d'entrée principal"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Démarrage rapide RobianAPI")
    parser.add_argument(
        "--skip-deps", 
        action="store_true",
        help="Ignorer l'installation des dépendances"
    )
    parser.add_argument(
        "--skip-docker", 
        action="store_true",
        help="Ne pas démarrer les services Docker"
    )
    parser.add_argument(
        "--skip-db", 
        action="store_true",
        help="Ignorer la configuration de la base de données"
    )
    parser.add_argument(
        "--skip-tests", 
        action="store_true",
        help="Ignorer les tests"
    )
    parser.add_argument(
        "--docker-only", 
        action="store_true",
        help="Utiliser uniquement Docker (pas de setup local)"
    )
    
    args = parser.parse_args()
    
    # Configuration du logging
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    logger.info("🚀 RobianAPI - Démarrage rapide")
    logger.info("=" * 50)
    
    # Mode Docker uniquement
    if args.docker_only:
        logger.info("🐳 Mode Docker uniquement")
        try:
            run_command("docker-compose up --build")
        except KeyboardInterrupt:
            logger.info("🛑 Arrêt demandé")
            run_command("docker-compose down")
        return
    
    # Étapes de setup
    success = True
    
    # 1. Vérifier les dépendances
    if not check_dependencies():
        logger.error("❌ Dépendances système manquantes")
        sys.exit(1)
    
    # 2. Configuration environnement
    setup_environment()
    
    # 3. Installation dépendances Python
    if not args.skip_deps:
        if not install_dependencies():
            logger.error("❌ Échec installation dépendances")
            success = False
    
    # 4. Démarrage services Docker
    if not args.skip_docker:
        if not start_services_docker():
            logger.warning("⚠️ Services Docker non démarrés")
            logger.info("💡 Vous pouvez utiliser une base de données locale")
    
    # 5. Setup base de données
    if not args.skip_db and success:
        if not setup_database():
            logger.warning("⚠️ Setup base de données échoué")
            logger.info("💡 L'API peut fonctionner en mode dégradé")
    
    # 6. Tests
    if not args.skip_tests and success:
        if not run_tests():
            logger.warning("⚠️ Certains tests ont échoué")
    
    # 7. Démarrage de l'API
    if success:
        logger.info("🎉 Setup terminé avec succès!")
        logger.info("=" * 50)
        
        input("Appuyez sur Entrée pour démarrer l'API...")
        start_api()
    else:
        logger.error("💥 Setup échoué - vérifiez les erreurs ci-dessus")
        sys.exit(1)


if __name__ == "__main__":
    main()

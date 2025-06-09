#!/usr/bin/env python3
"""
Script de vérification de santé pour AN-droid
Vérifie l'état de tous les composants du système
"""

import os
import sys
import json
import time
import requests
import subprocess
import psutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging

class ANDroidHealthCheck:
    def __init__(self, config_file=".env"):
        self.config = self.load_config(config_file)
        self.setup_logging()
        
        # Configuration
        self.api_base_url = f"http://{self.config.get('API_HOST', 'localhost')}:{self.config.get('API_PORT', '8000')}"
        self.download_dir = Path(self.config.get('DOWNLOAD_DIR', 'downloads'))
        self.cache_dir = Path(self.config.get('CACHE_DIR', 'cache'))
        self.log_dir = Path("logs")
        
        # Résultats du health check
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'overall_status': 'unknown',
            'checks': {},
            'warnings': [],
            'errors': [],
            'recommendations': []
        }
    
    def load_config(self, config_file):
        """Charger la configuration depuis le fichier .env"""
        config = {}
        if Path(config_file).exists():
            with open(config_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        config[key.strip()] = value.strip()
        return config
    
    def setup_logging(self):
        """Configurer le système de logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[logging.StreamHandler(sys.stdout)]
        )
        self.logger = logging.getLogger(__name__)
    
    def run_check(self, check_name: str, check_function, critical: bool = False) -> Tuple[bool, Dict]:
        """Exécuter une vérification et enregistrer les résultats"""
        self.logger.info(f"🔍 Vérification: {check_name}")
        
        try:
            start_time = time.time()
            success, details = check_function()
            duration = time.time() - start_time
            
            result = {
                'status': 'pass' if success else 'fail',
                'critical': critical,
                'duration': duration,
                'details': details,
                'timestamp': datetime.now().isoformat()
            }
            
            self.results['checks'][check_name] = result
            
            if success:
                self.logger.info(f"  ✅ {check_name}: OK ({duration:.2f}s)")
            else:
                self.logger.error(f"  ❌ {check_name}: ÉCHEC ({duration:.2f}s)")
                if critical:
                    self.results['errors'].append(f"{check_name}: {details.get('error', 'Échec critique')}")
                else:
                    self.results['warnings'].append(f"{check_name}: {details.get('error', 'Problème détecté')}")
            
            return success, result
            
        except Exception as e:
            self.logger.error(f"  ❌ {check_name}: ERREUR - {e}")
            result = {
                'status': 'error',
                'critical': critical,
                'duration': 0,
                'details': {'error': str(e), 'exception': True},
                'timestamp': datetime.now().isoformat()
            }
            
            self.results['checks'][check_name] = result
            self.results['errors'].append(f"{check_name}: Exception - {e}")
            
            return False, result
    
    def check_python_environment(self) -> Tuple[bool, Dict]:
        """Vérifier l'environnement Python"""
        details = {}
        
        # Version Python
        python_version = sys.version_info
        details['python_version'] = f"{python_version.major}.{python_version.minor}.{python_version.micro}"
        
        # Vérifier la version minimale
        if python_version < (3, 8):
            details['error'] = f"Python 3.8+ requis, version {details['python_version']} détectée"
            return False, details
        
        # Environnement virtuel
        in_venv = sys.prefix != sys.base_prefix
        details['virtual_env'] = in_venv
        details['python_path'] = sys.executable
        
        # Modules critiques (simplifiés pour éviter les erreurs)
        critical_modules = ['requests', 'psutil']
        missing_modules = []
        
        for module in critical_modules:
            try:
                __import__(module)
            except ImportError:
                missing_modules.append(module)
        
        details['missing_modules'] = missing_modules
        
        if missing_modules:
            details['error'] = f"Modules manquants: {', '.join(missing_modules)}"
            return False, details
        
        details['status'] = 'Environnement Python OK'
        return True, details
    
    def check_external_tools(self) -> Tuple[bool, Dict]:
        """Vérifier les outils externes (yt-dlp, ffmpeg)"""
        details = {}
        
        # Vérifier yt-dlp
        try:
            result = subprocess.run(['yt-dlp', '--version'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                details['ytdlp_version'] = result.stdout.strip()
                details['ytdlp_available'] = True
            else:
                details['ytdlp_available'] = False
                details['ytdlp_error'] = result.stderr
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            details['ytdlp_available'] = False
            details['ytdlp_error'] = str(e)
        
        # Vérifier FFmpeg
        try:
            result = subprocess.run(['ffmpeg', '-version'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                details['ffmpeg_available'] = True
                details['ffmpeg_version'] = "OK"
            else:
                details['ffmpeg_available'] = False
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            details['ffmpeg_available'] = False
            details['ffmpeg_error'] = str(e)
        
        # Évaluer le succès
        success = details.get('ytdlp_available', False)
        
        if not details.get('ffmpeg_available', False):
            details['warning'] = "FFmpeg non disponible - les extractions audio peuvent échouer"
            self.results['warnings'].append("FFmpeg non disponible")
        
        if not success:
            details['error'] = "yt-dlp non disponible - extraction impossible"
        
        return success, details
    
    def check_directories(self) -> Tuple[bool, Dict]:
        """Vérifier les répertoires nécessaires"""
        details = {}
        
        required_dirs = [
            ('downloads', self.download_dir),
            ('cache', self.cache_dir),
            ('logs', self.log_dir)
        ]
        
        missing_dirs = []
        dir_stats = {}
        
        for name, path in required_dirs:
            if path.exists():
                try:
                    dir_stats[name] = {
                        'exists': True,
                        'path': str(path),
                        'writable': os.access(path, os.W_OK)
                    }
                except Exception as e:
                    dir_stats[name] = {
                        'exists': True,
                        'path': str(path),
                        'error': str(e)
                    }
            else:
                missing_dirs.append(name)
                dir_stats[name] = {
                    'exists': False,
                    'path': str(path)
                }
        
        details['directories'] = dir_stats
        details['missing_directories'] = missing_dirs
        
        # Créer les répertoires manquants si possible
        created_dirs = []
        for name in missing_dirs:
            try:
                path = next(path for n, path in required_dirs if n == name)
                path.mkdir(parents=True, exist_ok=True)
                created_dirs.append(name)
                details['directories'][name]['exists'] = True
                details['directories'][name]['created'] = True
            except Exception as e:
                details['directories'][name]['creation_error'] = str(e)
        
        if created_dirs:
            details['created_directories'] = created_dirs
        
        success = len(missing_dirs) == len(created_dirs)
        
        if not success:
            details['error'] = f"Répertoires manquants: {', '.join(set(missing_dirs) - set(created_dirs))}"
        
        return success, details
    
    def check_api_health(self) -> Tuple[bool, Dict]:
        """Vérifier l'état de l'API"""
        details = {}
        
        # Vérifier si l'API répond
        try:
            response = requests.get(f"{self.api_base_url}/", timeout=5)
            details['api_accessible'] = True
            details['status_code'] = response.status_code
            details['response_time'] = response.elapsed.total_seconds()
            
        except requests.exceptions.RequestException as e:
            details['api_accessible'] = False
            details['connection_error'] = str(e)
        
        success = details.get('api_accessible', False)
        
        if not success:
            details['error'] = "API non accessible"
            self.results['recommendations'].append("Lancez l'API avec: ./scripts/deploy_local.sh")
        
        return success, details
    
    def check_system_resources(self) -> Tuple[bool, Dict]:
        """Vérifier les ressources système"""
        details = {}
        
        # CPU
        cpu_percent = psutil.cpu_percent(interval=1)
        details['cpu'] = {
            'percent': cpu_percent,
            'count': psutil.cpu_count()
        }
        
        # Mémoire
        memory = psutil.virtual_memory()
        details['memory'] = {
            'percent': memory.percent,
            'available_gb': memory.available / 1024**3,
            'total_gb': memory.total / 1024**3
        }
        
        # Le test passe sauf si les ressources sont critiquement faibles
        success = memory.available > 0.2 * 1024**3  # Au moins 200MB libres
        
        if not success:
            details['error'] = "Ressources système critiquement faibles"
        
        return success, details
    
    def run_all_checks(self, quick: bool = False) -> Dict:
        """Exécuter toutes les vérifications"""
        self.logger.info("🏥 Démarrage du Health Check AN-droid")
        self.logger.info("=" * 60)
        
        # Vérifications critiques
        critical_checks = [
            ("Environnement Python", self.check_python_environment, True),
            ("Outils externes", self.check_external_tools, True),
            ("Répertoires", self.check_directories, True),
        ]
        
        # Vérifications non-critiques
        standard_checks = [
            ("API", self.check_api_health, False),
            ("Ressources système", self.check_system_resources, False),
        ]
        
        # Exécuter toutes les vérifications
        all_checks = critical_checks + standard_checks
        passed_checks = 0
        failed_checks = 0
        critical_failures = 0
        
        for check_name, check_function, is_critical in all_checks:
            success, result = self.run_check(check_name, check_function, is_critical)
            
            if success:
                passed_checks += 1
            else:
                failed_checks += 1
                if is_critical:
                    critical_failures += 1
        
        # Déterminer le statut global
        if critical_failures > 0:
            self.results['overall_status'] = 'critical'
        elif failed_checks > 0:
            self.results['overall_status'] = 'warning'
        else:
            self.results['overall_status'] = 'healthy'
        
        # Ajouter des recommandations
        if critical_failures > 0:
            self.results['recommendations'].append("Corrigez les erreurs critiques avant de continuer")
        
        if not self.results['checks'].get('API', {}).get('status') == 'pass':
            self.results['recommendations'].append("Lancez l'API: ./scripts/deploy_local.sh")
        
        # Résumé
        self.results['summary'] = {
            'total_checks': len(all_checks),
            'passed': passed_checks,
            'failed': failed_checks,
            'critical_failures': critical_failures,
            'warnings_count': len(self.results['warnings']),
            'errors_count': len(self.results['errors']),
            'duration': sum(check['duration'] for check in self.results['checks'].values())
        }
        
        self.logger.info("=" * 60)
        self.logger.info(f"🏥 Health Check terminé: {self.results['overall_status'].upper()}")
        self.logger.info(f"📊 {passed_checks}/{len(all_checks)} vérifications réussies")
        
        if self.results['errors']:
            self.logger.error(f"❌ {len(self.results['errors'])} erreurs détectées")
        
        if self.results['warnings']:
            self.logger.warning(f"⚠️ {len(self.results['warnings'])} avertissements")
        
        return self.results


def main():
    """Fonction principale"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Health Check AN-droid")
    parser.add_argument('--quick', '-q', action='store_true',
                        help='Exécution rapide (ignore les tests longs)')
    parser.add_argument('--save', '-s', type=str,
                        help='Sauvegarder le rapport dans un fichier JSON')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Affichage détaillé')
    
    args = parser.parse_args()
    
    health_check = ANDroidHealthCheck()
    
    # Health check complet
    print("🏥 Démarrage du Health Check complet AN-droid")
    
    # Exécuter tous les tests
    results = health_check.run_all_checks(quick=args.quick)
    
    # Affichage résumé
    overall_status = results['overall_status']
    summary = results['summary']
    
    print(f"\n🏥 Résultat: {overall_status.upper()}")
    print(f"📊 {summary['passed']}/{summary['total_checks']} vérifications réussies")
    
    if results['errors']:
        print(f"❌ {len(results['errors'])} erreurs")
        for error in results['errors'][:3]:  # Afficher les 3 premières
            print(f"  • {error}")
        if len(results['errors']) > 3:
            print(f"  ... et {len(results['errors']) - 3} autres")
    
    if results['warnings']:
        print(f"⚠️ {len(results['warnings'])} avertissements")
    
    if results['recommendations']:
        print(f"\n💡 Recommandations principales:")
        for rec in results['recommendations'][:2]:  # Les 2 principales
            print(f"  • {rec}")
    
    # Sauvegarder le rapport si demandé
    if args.save:
        output_path = Path(args.save)
        output_path.parent.mkdir(exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"📄 Rapport sauvegardé: {output_path}")
    
    # Code de sortie basé sur le statut
    if results['overall_status'] == 'critical':
        sys.exit(2)
    elif results['overall_status'] == 'warning':
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()

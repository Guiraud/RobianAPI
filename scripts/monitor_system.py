#!/usr/bin/env python3
"""
Script de monitoring système pour AN-droid
Surveille l'API, l'usage disque, les performances et génère des rapports
"""

import os
import sys
import time
import psutil
import requests
import json
from datetime import datetime, timedelta
from pathlib import Path
import subprocess
import signal
from typing import Dict, List, Optional
import logging

class ANDroidMonitor:
    def __init__(self, config_file=".env"):
        self.config = self.load_config(config_file)
        self.setup_logging()
        self.api_base_url = f"http://{self.config.get('API_HOST', 'localhost')}:{self.config.get('API_PORT', '8000')}"
        self.download_dir = Path(self.config.get('DOWNLOAD_DIR', 'downloads'))
        self.cache_dir = Path(self.config.get('CACHE_DIR', 'cache'))
        self.log_dir = Path("logs")
        
        # Métriques de monitoring
        self.metrics = {
            'start_time': datetime.now(),
            'api_requests': 0,
            'api_errors': 0,
            'extractions': 0,
            'extraction_errors': 0,
            'disk_usage': [],
            'memory_usage': [],
            'cpu_usage': []
        }
        
        # PID de l'API
        self.api_pid = self.get_api_pid()
        
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
        self.log_dir.mkdir(exist_ok=True)
        log_file = self.log_dir / f"monitor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"📊 Monitoring AN-droid démarré - Log: {log_file}")
    
    def get_api_pid(self) -> Optional[int]:
        """Récupérer le PID de l'API depuis le fichier .api_pid"""
        pid_file = Path(".api_pid")
        if pid_file.exists():
            try:
                pid = int(pid_file.read_text().strip())
                # Vérifier que le processus existe
                if psutil.pid_exists(pid):
                    return pid
                else:
                    self.logger.warning(f"⚠️ PID {pid} n'existe plus, suppression du fichier")
                    pid_file.unlink()
            except (ValueError, FileNotFoundError):
                pass
        return None
    
    def check_api_health(self) -> Dict:
        """Vérifier la santé de l'API"""
        try:
            # Test de l'endpoint de base
            response = requests.get(f"{self.api_base_url}/", timeout=5)
            api_alive = response.status_code == 200
            
            # Test de l'endpoint health si disponible
            health_data = {}
            try:
                health_response = requests.get(f"{self.api_base_url}/health", timeout=5)
                if health_response.status_code == 200:
                    health_data = health_response.json()
            except:
                pass
            
            self.metrics['api_requests'] += 1
            
            return {
                'alive': api_alive,
                'status_code': response.status_code,
                'response_time': response.elapsed.total_seconds(),
                'health_data': health_data
            }
            
        except requests.exceptions.RequestException as e:
            self.metrics['api_errors'] += 1
            return {
                'alive': False,
                'error': str(e),
                'response_time': None
            }
    
    def check_api_process(self) -> Dict:
        """Vérifier le processus de l'API"""
        if not self.api_pid:
            return {'running': False, 'reason': 'no_pid_file'}
        
        try:
            process = psutil.Process(self.api_pid)
            return {
                'running': True,
                'pid': self.api_pid,
                'cpu_percent': process.cpu_percent(),
                'memory_percent': process.memory_percent(),
                'memory_info': process.memory_info()._asdict(),
                'num_threads': process.num_threads(),
                'create_time': datetime.fromtimestamp(process.create_time()),
                'status': process.status()
            }
        except psutil.NoSuchProcess:
            return {'running': False, 'reason': 'process_not_found'}
        except psutil.AccessDenied:
            return {'running': True, 'reason': 'access_denied'}
    
    def check_disk_usage(self) -> Dict:
        """Vérifier l'usage disque"""
        stats = {}
        
        # Usage global du système
        disk_usage = psutil.disk_usage('/')
        stats['system'] = {
            'total': disk_usage.total,
            'used': disk_usage.used,
            'free': disk_usage.free,
            'percent': (disk_usage.used / disk_usage.total) * 100
        }
        
        # Usage des répertoires du projet
        for name, path in [('downloads', self.download_dir), ('cache', self.cache_dir), ('logs', self.log_dir)]:
            if path.exists():
                total_size = sum(f.stat().st_size for f in path.rglob('*') if f.is_file())
                file_count = len(list(path.rglob('*')))
                stats[name] = {
                    'size': total_size,
                    'size_mb': total_size / 1024 / 1024,
                    'file_count': file_count
                }
            else:
                stats[name] = {'size': 0, 'size_mb': 0, 'file_count': 0}
        
        return stats
    
    def check_system_resources(self) -> Dict:
        """Vérifier les ressources système"""
        return {
            'cpu': {
                'percent': psutil.cpu_percent(interval=1),
                'count': psutil.cpu_count(),
                'load_avg': os.getloadavg() if hasattr(os, 'getloadavg') else None
            },
            'memory': {
                'percent': psutil.virtual_memory().percent,
                'available': psutil.virtual_memory().available,
                'total': psutil.virtual_memory().total,
                'used': psutil.virtual_memory().used
            },
            'swap': {
                'percent': psutil.swap_memory().percent,
                'total': psutil.swap_memory().total,
                'used': psutil.swap_memory().used
            }
        }
    
    def analyze_logs(self) -> Dict:
        """Analyser les fichiers de logs"""
        log_stats = {}
        
        # Analyser les logs d'API récents
        api_logs = list(self.log_dir.glob("api_*.log"))
        if api_logs:
            latest_log = max(api_logs, key=lambda f: f.stat().st_mtime)
            log_stats['latest_api_log'] = {
                'file': str(latest_log),
                'size': latest_log.stat().st_size,
                'modified': datetime.fromtimestamp(latest_log.stat().st_mtime)
            }
            
            # Compter les erreurs dans les logs récents
            try:
                with open(latest_log, 'r') as f:
                    content = f.read()
                    error_count = content.count('ERROR')
                    warning_count = content.count('WARNING')
                    log_stats['latest_api_log'].update({
                        'error_count': error_count,
                        'warning_count': warning_count
                    })
            except Exception:
                pass
        
        return log_stats
    
    def cleanup_old_files(self, days_old=7) -> Dict:
        """Nettoyer les anciens fichiers"""
        cleanup_stats = {
            'files_removed': 0,
            'space_freed': 0,
            'errors': []
        }
        
        cutoff_date = datetime.now() - timedelta(days=days_old)
        
        # Nettoyer les anciens downloads
        for file_path in self.download_dir.rglob('*'):
            if file_path.is_file():
                file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                if file_time < cutoff_date:
                    try:
                        size = file_path.stat().st_size
                        file_path.unlink()
                        cleanup_stats['files_removed'] += 1
                        cleanup_stats['space_freed'] += size
                        self.logger.info(f"🗑️ Supprimé: {file_path}")
                    except Exception as e:
                        cleanup_stats['errors'].append(f"Erreur suppression {file_path}: {e}")
        
        # Nettoyer les anciens logs
        for file_path in self.log_dir.rglob('*.log'):
            if file_path.is_file():
                file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                if file_time < cutoff_date:
                    try:
                        size = file_path.stat().st_size
                        file_path.unlink()
                        cleanup_stats['files_removed'] += 1
                        cleanup_stats['space_freed'] += size
                    except Exception as e:
                        cleanup_stats['errors'].append(f"Erreur suppression {file_path}: {e}")
        
        if cleanup_stats['files_removed'] > 0:
            self.logger.info(f"🧹 Nettoyage: {cleanup_stats['files_removed']} fichiers supprimés, "
                           f"{cleanup_stats['space_freed'] / 1024 / 1024:.1f} MB libérés")
        
        return cleanup_stats
    
    def generate_report(self) -> Dict:
        """Générer un rapport complet"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'uptime': str(datetime.now() - self.metrics['start_time']),
            'api_health': self.check_api_health(),
            'api_process': self.check_api_process(),
            'disk_usage': self.check_disk_usage(),
            'system_resources': self.check_system_resources(),
            'log_analysis': self.analyze_logs(),
            'metrics': self.metrics.copy()
        }
        
        return report
    
    def print_status(self, report: Dict):
        """Afficher le statut de manière lisible"""
        print("\n" + "="*70)
        print(f"📊 AN-droid Monitoring - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)
        
        # État de l'API
        api_health = report['api_health']
        if api_health['alive']:
            print(f"✅ API: Fonctionnelle ({api_health.get('response_time', 0):.3f}s)")
        else:
            print(f"❌ API: Non accessible ({api_health.get('error', 'unknown')})")
        
        # Processus API
        api_process = report['api_process']
        if api_process['running']:
            print(f"🔄 Processus API: PID {api_process.get('pid', 'N/A')} "
                  f"(CPU: {api_process.get('cpu_percent', 0):.1f}%, "
                  f"RAM: {api_process.get('memory_percent', 0):.1f}%)")
        else:
            print(f"⚠️ Processus API: Non détecté ({api_process.get('reason', 'unknown')})")
        
        # Ressources système
        resources = report['system_resources']
        print(f"💻 Système: CPU {resources['cpu']['percent']:.1f}%, "
              f"RAM {resources['memory']['percent']:.1f}%, "
              f"Swap {resources['swap']['percent']:.1f}%")
        
        # Usage disque
        disk = report['disk_usage']
        print(f"💾 Disque: {disk['system']['percent']:.1f}% utilisé "
              f"({disk['system']['free'] / 1024**3:.1f} GB libres)")
        
        # Répertoires du projet
        print(f"📁 Downloads: {disk['downloads']['file_count']} fichiers "
              f"({disk['downloads']['size_mb']:.1f} MB)")
        print(f"📁 Logs: {disk['logs']['file_count']} fichiers "
              f"({disk['logs']['size_mb']:.1f} MB)")
        
        # Métriques
        metrics = report['metrics']
        print(f"📈 Métriques: {metrics['api_requests']} requêtes API, "
              f"{metrics['api_errors']} erreurs")
        
        print(f"⏰ Uptime: {report['uptime']}")
        print("="*70)
    
    def save_report(self, report: Dict):
        """Sauvegarder le rapport en JSON"""
        reports_dir = Path("logs/reports")
        reports_dir.mkdir(exist_ok=True)
        
        report_file = reports_dir / f"monitor_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        self.logger.info(f"📄 Rapport sauvegardé: {report_file}")
        return report_file
    
    def check_alerts(self, report: Dict) -> List[str]:
        """Vérifier les conditions d'alerte"""
        alerts = []
        
        # API non accessible
        if not report['api_health']['alive']:
            alerts.append("🚨 API non accessible")
        
        # Processus API arrêté
        if not report['api_process']['running']:
            alerts.append("🚨 Processus API arrêté")
        
        # Usage CPU élevé
        if report['system_resources']['cpu']['percent'] > 80:
            alerts.append(f"⚠️ CPU élevé: {report['system_resources']['cpu']['percent']:.1f}%")
        
        # Usage mémoire élevé
        if report['system_resources']['memory']['percent'] > 85:
            alerts.append(f"⚠️ Mémoire élevée: {report['system_resources']['memory']['percent']:.1f}%")
        
        # Disque plein
        if report['disk_usage']['system']['percent'] > 90:
            alerts.append(f"🚨 Disque plein: {report['disk_usage']['system']['percent']:.1f}%")
        
        # Trop de fichiers dans downloads
        if report['disk_usage']['downloads']['file_count'] > 100:
            alerts.append(f"⚠️ Trop de fichiers downloads: {report['disk_usage']['downloads']['file_count']}")
        
        # Logs trop volumineux
        if report['disk_usage']['logs']['size_mb'] > 100:
            alerts.append(f"⚠️ Logs volumineux: {report['disk_usage']['logs']['size_mb']:.1f} MB")
        
        return alerts
    
    def run_monitoring_cycle(self, show_output=True, save_report=True):
        """Exécuter un cycle de monitoring"""
        try:
            report = self.generate_report()
            
            if show_output:
                self.print_status(report)
            
            # Vérifier les alertes
            alerts = self.check_alerts(report)
            if alerts:
                for alert in alerts:
                    self.logger.warning(alert)
                    if show_output:
                        print(alert)
            
            # Sauvegarder le rapport
            if save_report:
                self.save_report(report)
            
            return report
            
        except Exception as e:
            self.logger.error(f"❌ Erreur durant le monitoring: {e}")
            if show_output:
                print(f"❌ Erreur durant le monitoring: {e}")
            return None
    
    def run_continuous_monitoring(self, interval=60):
        """Lancer le monitoring en continu"""
        self.logger.info(f"🔄 Monitoring continu démarré (intervalle: {interval}s)")
        
        def signal_handler(signum, frame):
            self.logger.info("📋 Arrêt du monitoring demandé")
            print("\n📋 Génération du rapport final...")
            final_report = self.generate_report()
            self.save_report(final_report)
            self.print_status(final_report)
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        cycle_count = 0
        
        try:
            while True:
                cycle_count += 1
                self.logger.info(f"🔄 Cycle de monitoring #{cycle_count}")
                
                report = self.run_monitoring_cycle(
                    show_output=(cycle_count % 10 == 1),  # Affichage tous les 10 cycles
                    save_report=(cycle_count % 60 == 1)   # Sauvegarde toutes les heures
                )
                
                if report:
                    # Mettre à jour les métriques
                    self.metrics['cpu_usage'].append(report['system_resources']['cpu']['percent'])
                    self.metrics['memory_usage'].append(report['system_resources']['memory']['percent'])
                    
                    # Garder seulement les 100 dernières valeurs
                    for key in ['cpu_usage', 'memory_usage', 'disk_usage']:
                        if len(self.metrics[key]) > 100:
                            self.metrics[key] = self.metrics[key][-100:]
                
                # Nettoyage automatique quotidien
                if cycle_count % (24 * 60) == 0:  # Une fois par jour si interval=60s
                    self.logger.info("🧹 Nettoyage automatique quotidien")
                    cleanup_stats = self.cleanup_old_files()
                    if cleanup_stats['files_removed'] > 0:
                        self.logger.info(f"🧹 {cleanup_stats['files_removed']} fichiers supprimés")
                
                time.sleep(interval)
                
        except KeyboardInterrupt:
            signal_handler(signal.SIGINT, None)


def main():
    """Fonction principale"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Monitoring système AN-droid")
    parser.add_argument('--interval', '-i', type=int, default=60,
                        help='Intervalle de monitoring en secondes (défaut: 60)')
    parser.add_argument('--once', '-o', action='store_true',
                        help='Exécuter un seul cycle de monitoring')
    parser.add_argument('--cleanup', '-c', action='store_true',
                        help='Nettoyer les anciens fichiers')
    parser.add_argument('--report', '-r', action='store_true',
                        help='Générer et afficher un rapport')
    
    args = parser.parse_args()
    
    monitor = ANDroidMonitor()
    
    if args.cleanup:
        print("🧹 Nettoyage des anciens fichiers...")
        cleanup_stats = monitor.cleanup_old_files()
        print(f"✅ {cleanup_stats['files_removed']} fichiers supprimés, "
              f"{cleanup_stats['space_freed'] / 1024 / 1024:.1f} MB libérés")
        return
    
    if args.once or args.report:
        print("📊 Génération du rapport de monitoring...")
        report = monitor.run_monitoring_cycle(show_output=True, save_report=True)
        if not report:
            sys.exit(1)
        return
    
    # Monitoring continu par défaut
    print(f"🔄 Démarrage du monitoring continu (intervalle: {args.interval}s)")
    print("📋 Appuyez sur Ctrl+C pour générer un rapport final et quitter")
    monitor.run_continuous_monitoring(args.interval)


if __name__ == "__main__":
    main()

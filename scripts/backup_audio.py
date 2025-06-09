#!/usr/bin/env python3
"""
Script de sauvegarde et nettoyage pour AN-droid
Gère la sauvegarde des fichiers audio et le nettoyage automatique
"""

import os
import sys
import shutil
import json
from datetime import datetime, timedelta
from pathlib import Path
import tarfile
import gzip
import hashlib
from typing import Dict, List, Optional, Tuple
import logging

class ANDroidBackupManager:
    def __init__(self, config_file=".env"):
        self.config = self.load_config(config_file)
        self.setup_logging()
        
        # Répertoires
        self.download_dir = Path(self.config.get('DOWNLOAD_DIR', 'downloads'))
        self.cache_dir = Path(self.config.get('CACHE_DIR', 'cache'))
        self.log_dir = Path("logs")
        self.backup_dir = Path(self.config.get('BACKUP_DIR', 'backups'))
        
        # Configuration de nettoyage
        self.max_file_age_days = int(self.config.get('MAX_FILE_AGE_DAYS', '7'))
        self.max_total_size_mb = int(self.config.get('MAX_TOTAL_SIZE_MB', '1000'))
        self.keep_recent_files = int(self.config.get('KEEP_RECENT_FILES', '10'))
        
        # Créer les répertoires nécessaires
        self.backup_dir.mkdir(exist_ok=True)
        
        # Statistiques
        self.stats = {
            'files_processed': 0,
            'files_backed_up': 0,
            'files_cleaned': 0,
            'space_freed': 0,
            'space_backed_up': 0,
            'errors': []
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
        self.log_dir.mkdir(exist_ok=True)
        log_file = self.log_dir / f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"💾 Gestionnaire de sauvegarde AN-droid démarré - Log: {log_file}")
    
    def calculate_file_hash(self, file_path: Path) -> str:
        """Calculer le hash SHA256 d'un fichier"""
        hash_sha256 = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception as e:
            self.logger.error(f"❌ Erreur calcul hash pour {file_path}: {e}")
            return ""
    
    def get_file_info(self, file_path: Path) -> Dict:
        """Obtenir les informations détaillées d'un fichier"""
        try:
            stat = file_path.stat()
            return {
                'path': str(file_path),
                'name': file_path.name,
                'size': stat.st_size,
                'size_mb': stat.st_size / 1024 / 1024,
                'created': datetime.fromtimestamp(stat.st_ctime),
                'modified': datetime.fromtimestamp(stat.st_mtime),
                'hash': self.calculate_file_hash(file_path),
                'extension': file_path.suffix.lower()
            }
        except Exception as e:
            self.logger.error(f"❌ Erreur info fichier {file_path}: {e}")
            return {}
    
    def scan_audio_files(self) -> List[Dict]:
        """Scanner tous les fichiers audio dans le répertoire de téléchargement"""
        audio_extensions = {'.mp3', '.wav', '.m4a', '.ogg', '.flac', '.aac'}
        audio_files = []
        
        self.logger.info(f"🔍 Scan des fichiers audio dans {self.download_dir}")
        
        if not self.download_dir.exists():
            self.logger.warning(f"⚠️ Répertoire {self.download_dir} n'existe pas")
            return []
        
        for file_path in self.download_dir.rglob('*'):
            if file_path.is_file() and file_path.suffix.lower() in audio_extensions:
                file_info = self.get_file_info(file_path)
                if file_info:
                    audio_files.append(file_info)
                    self.stats['files_processed'] += 1
        
        # Trier par date de modification (plus récent en premier)
        audio_files.sort(key=lambda x: x['modified'], reverse=True)
        
        self.logger.info(f"📁 {len(audio_files)} fichiers audio trouvés")
        return audio_files
    
    def create_backup_archive(self, files_to_backup: List[Dict], backup_name: str = None) -> Optional[Path]:
        """Créer une archive de sauvegarde des fichiers spécifiés"""
        if not files_to_backup:
            self.logger.info("📦 Aucun fichier à sauvegarder")
            return None
        
        if not backup_name:
            backup_name = f"android_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        backup_file = self.backup_dir / f"{backup_name}.tar.gz"
        
        self.logger.info(f"📦 Création de l'archive: {backup_file}")
        
        try:
            with tarfile.open(backup_file, "w:gz") as tar:
                # Créer un manifeste avec les métadonnées
                manifest = {
                    'created': datetime.now().isoformat(),
                    'total_files': len(files_to_backup),
                    'total_size': sum(f['size'] for f in files_to_backup),
                    'files': files_to_backup
                }
                
                # Sauvegarder le manifeste
                manifest_file = self.backup_dir / f"{backup_name}_manifest.json"
                with open(manifest_file, 'w') as f:
                    json.dump(manifest, f, indent=2, default=str)
                
                tar.add(manifest_file, arcname=f"{backup_name}_manifest.json")
                
                # Ajouter les fichiers audio
                for file_info in files_to_backup:
                    file_path = Path(file_info['path'])
                    if file_path.exists():
                        # Utiliser un nom relatif dans l'archive
                        arcname = f"audio/{file_path.name}"
                        tar.add(file_path, arcname=arcname)
                        self.stats['files_backed_up'] += 1
                        self.stats['space_backed_up'] += file_info['size']
                        self.logger.info(f"  ✅ Ajouté: {file_path.name}")
                
                # Nettoyer le manifeste temporaire
                manifest_file.unlink()
            
            backup_size = backup_file.stat().st_size
            self.logger.info(f"✅ Archive créée: {backup_file}")
            self.logger.info(f"📊 Taille: {backup_size / 1024 / 1024:.1f} MB")
            self.logger.info(f"📁 {len(files_to_backup)} fichiers sauvegardés")
            
            return backup_file
            
        except Exception as e:
            self.logger.error(f"❌ Erreur création archive: {e}")
            self.stats['errors'].append(f"Erreur création archive: {e}")
            return None
    
    def restore_backup(self, backup_file: Path, restore_dir: Path = None) -> bool:
        """Restaurer une archive de sauvegarde"""
        if not backup_file.exists():
            self.logger.error(f"❌ Archive de sauvegarde non trouvée: {backup_file}")
            return False
        
        if not restore_dir:
            restore_dir = self.download_dir / "restored"
        
        restore_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger.info(f"📥 Restauration de {backup_file} vers {restore_dir}")
        
        try:
            with tarfile.open(backup_file, "r:gz") as tar:
                tar.extractall(path=restore_dir)
            
            self.logger.info(f"✅ Restauration terminée dans {restore_dir}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Erreur restauration: {e}")
            return False
    
    def identify_files_to_clean(self, audio_files: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """Identifier les fichiers à nettoyer et à conserver"""
        now = datetime.now()
        cutoff_date = now - timedelta(days=self.max_file_age_days)
        
        files_to_clean = []
        files_to_keep = []
        
        # Garder toujours les N fichiers les plus récents
        recent_files = audio_files[:self.keep_recent_files]
        recent_paths = {f['path'] for f in recent_files}
        
        total_size = 0
        
        for file_info in audio_files:
            file_path = file_info['path']
            file_date = file_info['modified']
            file_size = file_info['size']
            
            # Garder si c'est un fichier récent protégé
            if file_path in recent_paths:
                files_to_keep.append(file_info)
                total_size += file_size
                continue
            
            # Nettoyer si trop ancien
            if file_date < cutoff_date:
                files_to_clean.append(file_info)
                continue
            
            # Nettoyer si on dépasse la taille totale
            if total_size + file_size > self.max_total_size_mb * 1024 * 1024:
                files_to_clean.append(file_info)
                continue
            
            # Sinon garder
            files_to_keep.append(file_info)
            total_size += file_size
        
        self.logger.info(f"📋 Analyse: {len(files_to_keep)} à garder, {len(files_to_clean)} à nettoyer")
        self.logger.info(f"💾 Taille totale à garder: {total_size / 1024 / 1024:.1f} MB")
        
        return files_to_clean, files_to_keep
    
    def clean_files(self, files_to_clean: List[Dict], create_backup: bool = True) -> bool:
        """Nettoyer les fichiers spécifiés"""
        if not files_to_clean:
            self.logger.info("🧹 Aucun fichier à nettoyer")
            return True
        
        self.logger.info(f"🧹 Nettoyage de {len(files_to_clean)} fichiers")
        
        # Créer une sauvegarde avant nettoyage si demandé
        backup_created = False
        if create_backup:
            backup_name = f"pre_cleanup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            backup_file = self.create_backup_archive(files_to_clean, backup_name)
            backup_created = backup_file is not None
            
            if backup_created:
                self.logger.info(f"💾 Sauvegarde créée avant nettoyage: {backup_file}")
            else:
                self.logger.warning("⚠️ Échec création sauvegarde - Nettoyage annulé")
                return False
        
        # Procéder au nettoyage
        cleaned_count = 0
        space_freed = 0
        
        for file_info in files_to_clean:
            file_path = Path(file_info['path'])
            
            try:
                if file_path.exists():
                    file_size = file_path.stat().st_size
                    file_path.unlink()
                    cleaned_count += 1
                    space_freed += file_size
                    self.stats['files_cleaned'] += 1
                    self.stats['space_freed'] += file_size
                    self.logger.info(f"  🗑️ Supprimé: {file_path.name}")
                
            except Exception as e:
                self.logger.error(f"❌ Erreur suppression {file_path}: {e}")
                self.stats['errors'].append(f"Erreur suppression {file_path}: {e}")
        
        self.logger.info(f"✅ Nettoyage terminé: {cleaned_count} fichiers supprimés")
        self.logger.info(f"💾 Espace libéré: {space_freed / 1024 / 1024:.1f} MB")
        
        return True
    
    def clean_old_logs(self, days_old: int = 30) -> Dict:
        """Nettoyer les anciens fichiers de logs"""
        cutoff_date = datetime.now() - timedelta(days=days_old)
        
        cleanup_stats = {
            'files_removed': 0,
            'space_freed': 0,
            'errors': []
        }
        
        self.logger.info(f"🧹 Nettoyage des logs plus anciens que {days_old} jours")
        
        if not self.log_dir.exists():
            return cleanup_stats
        
        for log_file in self.log_dir.rglob('*.log'):
            try:
                file_time = datetime.fromtimestamp(log_file.stat().st_mtime)
                if file_time < cutoff_date:
                    size = log_file.stat().st_size
                    log_file.unlink()
                    cleanup_stats['files_removed'] += 1
                    cleanup_stats['space_freed'] += size
                    self.logger.info(f"  🗑️ Log supprimé: {log_file.name}")
            
            except Exception as e:
                cleanup_stats['errors'].append(f"Erreur suppression {log_file}: {e}")
        
        if cleanup_stats['files_removed'] > 0:
            self.logger.info(f"✅ {cleanup_stats['files_removed']} logs supprimés, "
                           f"{cleanup_stats['space_freed'] / 1024 / 1024:.1f} MB libérés")
        
        return cleanup_stats
    
    def clean_old_backups(self, max_backups: int = 5) -> Dict:
        """Garder seulement les N sauvegardes les plus récentes"""
        cleanup_stats = {
            'backups_removed': 0,
            'space_freed': 0,
            'errors': []
        }
        
        if not self.backup_dir.exists():
            return cleanup_stats
        
        # Lister toutes les sauvegardes
        backup_files = list(self.backup_dir.glob('*.tar.gz'))
        backup_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        
        # Supprimer les anciennes sauvegardes
        if len(backup_files) > max_backups:
            old_backups = backup_files[max_backups:]
            
            self.logger.info(f"🧹 Suppression de {len(old_backups)} anciennes sauvegardes")
            
            for backup_file in old_backups:
                try:
                    size = backup_file.stat().st_size
                    backup_file.unlink()
                    
                    # Supprimer aussi le manifeste s'il existe
                    manifest_file = backup_file.with_suffix('').with_suffix('') / "_manifest.json"
                    if manifest_file.exists():
                        manifest_file.unlink()
                    
                    cleanup_stats['backups_removed'] += 1
                    cleanup_stats['space_freed'] += size
                    self.logger.info(f"  🗑️ Sauvegarde supprimée: {backup_file.name}")
                
                except Exception as e:
                    cleanup_stats['errors'].append(f"Erreur suppression {backup_file}: {e}")
        
        return cleanup_stats
    
    def run_full_backup_and_cleanup(self, dry_run: bool = False) -> Dict:
        """Exécuter un cycle complet de sauvegarde et nettoyage"""
        self.logger.info("🚀 Démarrage du cycle complet sauvegarde/nettoyage")
        
        if dry_run:
            self.logger.info("🧪 Mode DRY RUN - Aucune modification ne sera effectuée")
        
        # Scanner les fichiers audio
        audio_files = self.scan_audio_files()
        
        if not audio_files:
            self.logger.info("📁 Aucun fichier audio trouvé")
            return self.stats
        
        # Identifier les fichiers à nettoyer
        files_to_clean, files_to_keep = self.identify_files_to_clean(audio_files)
        
        # Afficher le résumé
        self.logger.info("📊 Résumé de l'analyse:")
        self.logger.info(f"  • Total: {len(audio_files)} fichiers")
        self.logger.info(f"  • À conserver: {len(files_to_keep)} fichiers")
        self.logger.info(f"  • À nettoyer: {len(files_to_clean)} fichiers")
        
        if files_to_keep:
            keep_size = sum(f['size'] for f in files_to_keep) / 1024 / 1024
            self.logger.info(f"  • Taille conservée: {keep_size:.1f} MB")
        
        if files_to_clean:
            clean_size = sum(f['size'] for f in files_to_clean) / 1024 / 1024
            self.logger.info(f"  • Taille à libérer: {clean_size:.1f} MB")
        
        # Effectuer le nettoyage si ce n'est pas un dry run
        if files_to_clean and not dry_run:
            success = self.clean_files(files_to_clean, create_backup=True)
            if not success:
                self.logger.error("❌ Échec du nettoyage")
                return self.stats
        
        # Nettoyer les anciens logs
        if not dry_run:
            log_cleanup = self.clean_old_logs()
            self.logger.info(f"🧹 Logs: {log_cleanup['files_removed']} fichiers supprimés")
            
            # Nettoyer les anciennes sauvegardes
            backup_cleanup = self.clean_old_backups()
            self.logger.info(f"🧹 Sauvegardes: {backup_cleanup['backups_removed']} supprimées")
        
        # Résumé final
        self.logger.info("✅ Cycle complet terminé")
        self.logger.info(f"📊 Statistiques finales:")
        self.logger.info(f"  • Fichiers traités: {self.stats['files_processed']}")
        self.logger.info(f"  • Fichiers sauvegardés: {self.stats['files_backed_up']}")
        self.logger.info(f"  • Fichiers nettoyés: {self.stats['files_cleaned']}")
        self.logger.info(f"  • Espace libéré: {self.stats['space_freed'] / 1024 / 1024:.1f} MB")
        self.logger.info(f"  • Espace sauvegardé: {self.stats['space_backed_up'] / 1024 / 1024:.1f} MB")
        
        if self.stats['errors']:
            self.logger.warning(f"⚠️ {len(self.stats['errors'])} erreurs détectées")
        
        return self.stats
    
    def list_backups(self) -> List[Dict]:
        """Lister toutes les sauvegardes disponibles"""
        backups = []
        
        if not self.backup_dir.exists():
            return backups
        
        for backup_file in self.backup_dir.glob('*.tar.gz'):
            try:
                stat = backup_file.stat()
                
                # Chercher le manifeste correspondant
                manifest_data = {}
                manifest_file = backup_file.with_name(backup_file.stem.replace('.tar', '_manifest.json'))
                if manifest_file.exists():
                    try:
                        with open(manifest_file, 'r') as f:
                            manifest_data = json.load(f)
                    except:
                        pass
                
                backup_info = {
                    'file': str(backup_file),
                    'name': backup_file.name,
                    'size': stat.st_size,
                    'size_mb': stat.st_size / 1024 / 1024,
                    'created': datetime.fromtimestamp(stat.st_ctime),
                    'modified': datetime.fromtimestamp(stat.st_mtime),
                    'manifest': manifest_data
                }
                
                backups.append(backup_info)
                
            except Exception as e:
                self.logger.error(f"❌ Erreur lecture sauvegarde {backup_file}: {e}")
        
        # Trier par date de création (plus récent en premier)
        backups.sort(key=lambda x: x['created'], reverse=True)
        
        return backups


def main():
    """Fonction principale"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Gestionnaire de sauvegarde et nettoyage AN-droid")
    parser.add_argument('--backup', '-b', action='store_true',
                        help='Créer une sauvegarde des fichiers audio actuels')
    parser.add_argument('--cleanup', '-c', action='store_true',
                        help='Nettoyer les anciens fichiers (avec sauvegarde)')
    parser.add_argument('--full', '-f', action='store_true',
                        help='Cycle complet: sauvegarde + nettoyage')
    parser.add_argument('--dry-run', '-d', action='store_true',
                        help='Mode test - afficher ce qui serait fait sans le faire')
    parser.add_argument('--list-backups', '-l', action='store_true',
                        help='Lister les sauvegardes disponibles')
    parser.add_argument('--restore', '-r', type=str,
                        help='Restaurer une sauvegarde (nom du fichier)')
    parser.add_argument('--clean-logs', action='store_true',
                        help='Nettoyer les anciens logs uniquement')
    
    args = parser.parse_args()
    
    backup_manager = ANDroidBackupManager()
    
    if args.list_backups:
        print("📦 Sauvegardes disponibles:")
        backups = backup_manager.list_backups()
        if not backups:
            print("  Aucune sauvegarde trouvée")
        else:
            for backup in backups:
                print(f"  • {backup['name']}")
                print(f"    Taille: {backup['size_mb']:.1f} MB")
                print(f"    Créée: {backup['created'].strftime('%Y-%m-%d %H:%M:%S')}")
                if backup['manifest']:
                    manifest = backup['manifest']
                    print(f"    Fichiers: {manifest.get('total_files', 0)}")
                print()
        return
    
    if args.restore:
        backup_file = backup_manager.backup_dir / args.restore
        if not backup_file.exists():
            print(f"❌ Sauvegarde non trouvée: {args.restore}")
            sys.exit(1)
        
        success = backup_manager.restore_backup(backup_file)
        if success:
            print("✅ Restauration terminée")
        else:
            print("❌ Échec de la restauration")
            sys.exit(1)
        return
    
    if args.clean_logs:
        print("🧹 Nettoyage des anciens logs...")
        cleanup_stats = backup_manager.clean_old_logs()
        print(f"✅ {cleanup_stats['files_removed']} logs supprimés")
        return
    
    if args.backup:
        print("📦 Création d'une sauvegarde...")
        audio_files = backup_manager.scan_audio_files()
        if audio_files:
            backup_file = backup_manager.create_backup_archive(audio_files)
            if backup_file:
                print(f"✅ Sauvegarde créée: {backup_file}")
            else:
                print("❌ Échec de la sauvegarde")
                sys.exit(1)
        else:
            print("📁 Aucun fichier à sauvegarder")
        return
    
    if args.cleanup:
        print("🧹 Nettoyage des anciens fichiers...")
        audio_files = backup_manager.scan_audio_files()
        if audio_files:
            files_to_clean, files_to_keep = backup_manager.identify_files_to_clean(audio_files)
            if files_to_clean:
                if args.dry_run:
                    print(f"🧪 DRY RUN: {len(files_to_clean)} fichiers seraient nettoyés")
                else:
                    success = backup_manager.clean_files(files_to_clean)
                    if success:
                        print("✅ Nettoyage terminé")
                    else:
                        print("❌ Échec du nettoyage")
                        sys.exit(1)
            else:
                print("✨ Aucun fichier à nettoyer")
        return
    
    if args.full:
        print("🚀 Cycle complet sauvegarde/nettoyage...")
        stats = backup_manager.run_full_backup_and_cleanup(dry_run=args.dry_run)
        print("✅ Cycle terminé")
        return
    
    # Par défaut, afficher l'aide
    parser.print_help()


if __name__ == "__main__":
    main()

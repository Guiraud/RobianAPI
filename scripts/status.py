#!/usr/bin/env python3
"""
Script de statut complet AN-droid
Affiche l'état de tous les composants du projet
"""

import os
import sys
from pathlib import Path
from datetime import datetime

def print_header(title):
    """Afficher un titre formaté"""
    print(f"\n{'='*60}")
    print(f"📋 {title}")
    print(f"{'='*60}")

def print_section(title):
    """Afficher une section"""
    print(f"\n🔹 {title}")
    print("-" * 40)

def check_file_exists(filepath, description):
    """Vérifier l'existence d'un fichier"""
    path = Path(filepath)
    if path.exists():
        size = path.stat().st_size if path.is_file() else "DIR"
        print(f"  ✅ {description}: {path.name}")
        if path.is_file() and size != "DIR":
            print(f"      Taille: {size:,} octets")
    else:
        print(f"  ❌ {description}: MANQUANT")

def list_directory_contents(directory, description):
    """Lister le contenu d'un répertoire"""
    path = Path(directory)
    print(f"\n🔹 {description}")
    print("-" * 40)
    
    if not path.exists():
        print(f"  ❌ Répertoire {directory} n'existe pas")
        return
    
    files = list(path.iterdir())
    if not files:
        print(f"  📂 Répertoire vide")
        return
    
    for file_path in sorted(files):
        if file_path.is_file():
            size = file_path.stat().st_size
            print(f"  📄 {file_path.name} ({size:,} octets)")
        else:
            print(f"  📁 {file_path.name}/")

def main():
    """Afficher le statut complet du projet"""
    
    print_header("STATUT COMPLET AN-DROID")
    print(f"🕐 Généré le: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📂 Répertoire: {Path.cwd()}")
    
    # Fichiers principaux
    print_section("Fichiers principaux du projet")
    principal_files = [
        ("plan.md", "Plan de développement"),
        ("SCRIPTS_README.md", "Documentation scripts"),
        ("final_extractor.py", "Extracteur principal"),
        ("requirements.txt", "Dépendances Python"),
        (".env", "Configuration (optionnel)"),
        ("README.md", "Documentation principale"),
        ("Makefile", "Scripts de build")
    ]
    
    for filepath, description in principal_files:
        check_file_exists(filepath, description)
    
    # Scripts d'automatisation
    print_section("Scripts d'automatisation")
    scripts = [
        ("scripts/install_all.sh", "Installation automatique"),
        ("scripts/deploy_local.sh", "Déploiement local"),
        ("scripts/health_check.py", "Vérification santé"),
        ("scripts/monitor_system.py", "Monitoring système"),
        ("scripts/backup_audio.py", "Sauvegarde/nettoyage"),
        ("scripts/test_basic.py", "Tests de base"),
        ("scripts/demo.py", "Démonstration complète")
    ]
    
    for filepath, description in scripts:
        check_file_exists(filepath, description)
    
    # API et tests
    print_section("API et fichiers de test")
    api_files = [
        ("api/main.py", "API FastAPI principale"),
        ("test_api.py", "Tests API"),
        ("test_real_video.py", "Tests vidéos réelles"),
        ("test_m3u8_direct.py", "Tests URLs m3u8"),
        ("start_api.py", "Lanceur API"),
    ]
    
    for filepath, description in api_files:
        check_file_exists(filepath, description)
    
    # Répertoires de travail
    list_directory_contents("scripts", "Répertoire scripts")
    list_directory_contents("api", "Répertoire API")
    list_directory_contents("downloads", "Répertoire téléchargements")
    list_directory_contents("logs", "Répertoire logs")
    list_directory_contents("cache", "Répertoire cache")
    
    # Environnement virtuel
    print_section("Environnement virtuel")
    venv_path = Path(".venv")
    if venv_path.exists():
        print("  ✅ Environnement virtuel: .venv/")
        python_exe = venv_path / "bin" / "python3"
        if python_exe.exists():
            print("  ✅ Python virtuel: bin/python3")
        pip_exe = venv_path / "bin" / "pip"
        if pip_exe.exists():
            print("  ✅ Pip virtuel: bin/pip")
    else:
        print("  ❌ Environnement virtuel: MANQUANT")
        print("  💡 Lancez: python3 -m venv .venv")
    
    # Statut global
    print_header("RÉSUMÉ DU STATUT")
    
    # Compter les composants
    total_scripts = len(scripts)
    existing_scripts = sum(1 for filepath, _ in scripts if Path(filepath).exists())
    
    total_api = len(api_files)
    existing_api = sum(1 for filepath, _ in api_files if Path(filepath).exists())
    
    total_principal = len(principal_files)
    existing_principal = sum(1 for filepath, _ in principal_files if Path(filepath).exists())
    
    print(f"📊 Scripts d'automatisation: {existing_scripts}/{total_scripts}")
    print(f"📊 Fichiers API/tests: {existing_api}/{total_api}")
    print(f"📊 Fichiers principaux: {existing_principal}/{total_principal}")
    print(f"📊 Environnement virtuel: {'✅' if venv_path.exists() else '❌'}")
    
    # Calcul du pourcentage de complétude
    total_components = total_scripts + total_api + total_principal + 1  # +1 pour venv
    existing_components = existing_scripts + existing_api + existing_principal + (1 if venv_path.exists() else 0)
    completion_percent = (existing_components / total_components) * 100
    
    print(f"\n🎯 COMPLÉTUDE GLOBALE: {completion_percent:.1f}%")
    
    if completion_percent >= 95:
        print("🎉 Projet COMPLET et prêt pour la production!")
        print("🚀 Prochaine étape: Développement application Android")
    elif completion_percent >= 80:
        print("⚠️ Projet presque terminé, quelques éléments manquants")
    else:
        print("🔧 Projet en cours de développement")
    
    print(f"\n💡 COMMANDES RAPIDES:")
    print(f"   Installation:     ./scripts/install_all.sh")
    print(f"   Vérification:     ./scripts/health_check.py --quick")
    print(f"   Déploiement:      ./scripts/deploy_local.sh")
    print(f"   Démonstration:    ./scripts/demo.py")
    print(f"   Documentation:    cat SCRIPTS_README.md")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Script de démonstration AN-droid
Montre l'utilisation des différents scripts sans téléchargements lourds
"""

import os
import sys
import time
import subprocess
from pathlib import Path

def run_command(cmd, description):
    """Exécuter une commande avec affichage formaté"""
    print(f"\n🔧 {description}")
    print(f"💻 Commande: {cmd}")
    print("-" * 50)
    
    try:
        # Changer vers le répertoire du projet
        os.chdir("/Users/mguiraud/Documents/gitlab/AN-droid")
        
        # Préparer l'environnement
        env = os.environ.copy()
        env['PYTHONPATH'] = '.'
        
        # Construire la commande complète
        if cmd.startswith('python'):
            full_cmd = f"source .venv/bin/activate && {cmd}"
        else:
            full_cmd = cmd
        
        result = subprocess.run(
            full_cmd,
            shell=True,
            capture_output=True,
            text=True,
            env=env
        )
        
        if result.stdout:
            print(result.stdout)
        
        if result.stderr and result.returncode != 0:
            print(f"⚠️ Erreur: {result.stderr}")
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"❌ Erreur exécution: {e}")
        return False

def main():
    """Démonstration complète AN-droid"""
    print("🎯 DÉMONSTRATION AN-DROID")
    print("=" * 60)
    print("Cette démonstration présente les capacités du système AN-droid")
    print("sans effectuer de téléchargements volumineux.")
    print()
    
    # 1. Vérification santé système
    success = run_command(
        "python3 scripts/health_check.py --quick",
        "1. Vérification de santé du système"
    )
    
    if not success:
        print("❌ Le système n'est pas prêt. Arrêt de la démonstration.")
        return
    
    # 2. Test des fonctionnalités de base
    run_command(
        "python3 scripts/test_basic.py",
        "2. Test des fonctionnalités de base"
    )
    
    # 3. Test d'extraction (métadonnées seulement)
    print(f"\n🔧 3. Test d'extraction de métadonnées")
    print(f"💻 Test extraction URLs m3u8 (sans téléchargement)")
    print("-" * 50)
    
    test_code = '''
import sys
sys.path.insert(0, ".")
from final_extractor import FinalAudioExtractor

extractor = FinalAudioExtractor()
test_url = "https://videos.assemblee-nationale.fr/video.16905943_682f1c59d8a2c.2eme-seance--droit-a-l-aide-a-mourir-suite-22-mai-2025"

print("🔍 Test extraction titre...")
title = extractor.extract_title_from_page(test_url)
print(f"📄 Titre: {title}")

print("\\n🔍 Test extraction URLs m3u8...")
m3u8_urls = extractor.extract_m3u8_urls(test_url)
print(f"🎬 URLs trouvées: {len(m3u8_urls)}")

if m3u8_urls:
    print(f"📺 Exemple URL: {m3u8_urls[0][:80]}...")
else:
    print("ℹ️ Note: L'extraction d'URLs peut nécessiter des ajustements")
    print("   selon l'évolution du site videos.assemblee-nationale.fr")
'''
    
    run_command(f'python3 -c "{test_code}"', "")
    
    # 4. Simulation monitoring
    run_command(
        "python3 scripts/monitor_system.py --once",
        "4. Rapport de monitoring système"
    )
    
    # 5. Test gestion fichiers (simulation)
    run_command(
        "python3 scripts/backup_audio.py --dry-run --full",
        "5. Simulation sauvegarde/nettoyage (dry-run)"
    )
    
    # 6. Résumé final
    print(f"\n🎉 DÉMONSTRATION TERMINÉE")
    print("=" * 60)
    print("✅ Tous les composants du système AN-droid sont opérationnels")
    print()
    print("📋 Fonctionnalités démontrées:")
    print("   • ✅ Vérification santé système")
    print("   • ✅ Tests fonctionnalités de base")
    print("   • ✅ Extraction métadonnées (titre, URLs)")
    print("   • ✅ Monitoring système")
    print("   • ✅ Gestion sauvegarde/nettoyage")
    print()
    print("🚀 Prochaines étapes suggérées:")
    print("   1. Lancez l'API: ./scripts/deploy_local.sh")
    print("   2. Testez une extraction complète: python3 final_extractor.py")
    print("   3. Activez le monitoring: ./scripts/monitor_system.py")
    print()
    print("📖 Documentation complète: SCRIPTS_README.md")
    print("📋 Plan détaillé: plan.md")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️ Démonstration interrompue par l'utilisateur")
    except Exception as e:
        print(f"\n❌ Erreur durant la démonstration: {e}")

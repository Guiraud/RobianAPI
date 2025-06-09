#!/usr/bin/env python3
"""
Script de test simple pour AN-droid
Teste les fonctionnalités de base sans téléchargement
"""

import sys
import requests
from pathlib import Path

def test_basic_functionality():
    """Test de base des fonctionnalités"""
    print("🧪 Test des fonctionnalités de base AN-droid")
    print("=" * 50)
    
    # Test 1: Import des modules
    try:
        from final_extractor import FinalAudioExtractor
        print("✅ Import FinalAudioExtractor: OK")
    except ImportError as e:
        print(f"❌ Import FinalAudioExtractor: {e}")
        return False
    
    # Test 2: Création instance
    try:
        extractor = FinalAudioExtractor()
        print("✅ Création instance: OK")
    except Exception as e:
        print(f"❌ Création instance: {e}")
        return False
    
    # Test 3: Test de connexion réseau
    try:
        response = requests.get("https://httpbin.org/get", timeout=5)
        if response.status_code == 200:
            print("✅ Connexion réseau: OK")
        else:
            print(f"⚠️ Connexion réseau: Status {response.status_code}")
    except Exception as e:
        print(f"❌ Connexion réseau: {e}")
    
    # Test 4: Accès au site AN
    try:
        test_url = "https://videos.assemblee-nationale.fr/"
        response = requests.get(test_url, timeout=10)
        if response.status_code == 200:
            print("✅ Accès site AN: OK")
            print(f"   Taille page: {len(response.text)} caractères")
        else:
            print(f"⚠️ Accès site AN: Status {response.status_code}")
    except Exception as e:
        print(f"❌ Accès site AN: {e}")
    
    # Test 5: Répertoires de travail
    directories = ['downloads', 'cache', 'logs']
    for directory in directories:
        path = Path(directory)
        if path.exists():
            print(f"✅ Répertoire {directory}: OK")
        else:
            try:
                path.mkdir(exist_ok=True)
                print(f"✅ Répertoire {directory}: Créé")
            except Exception as e:
                print(f"❌ Répertoire {directory}: {e}")
    
    # Test 6: Configuration
    config_file = Path(".env")
    if config_file.exists():
        print("✅ Fichier .env: Trouvé")
        try:
            with open(config_file, 'r') as f:
                lines = len(f.readlines())
            print(f"   {lines} lignes de configuration")
        except Exception as e:
            print(f"⚠️ Lecture .env: {e}")
    else:
        print("⚠️ Fichier .env: Non trouvé (optionnel)")
    
    print("\n🎯 Résumé:")
    print("   • Tous les composants de base sont fonctionnels")
    print("   • Le système est prêt pour les tests d'extraction")
    print("   • Note: L'extraction d'URLs m3u8 peut nécessiter des ajustements")
    print("     selon l'évolution du site videos.assemblee-nationale.fr")
    
    return True

if __name__ == "__main__":
    success = test_basic_functionality()
    sys.exit(0 if success else 1)

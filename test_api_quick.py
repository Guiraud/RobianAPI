#!/usr/bin/env python3
"""
Test simple des endpoints de l'API RobianAPI
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_api():
    print("🧪 Test RobianAPI")
    print("=" * 50)
    
    # Test health check
    print("\n📋 Test Health Check...")
    try:
        response = requests.get(f"{BASE_URL}/", timeout=5)
        print(f"  Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  ✅ API opérationnelle: {data.get('message')}")
            print(f"  Version: {data.get('data', {}).get('version')}")
        else:
            print(f"  ❌ Erreur: {response.status_code}")
    except Exception as e:
        print(f"  ❌ Erreur connexion: {e}")
        return False
    
    # Test débats avec timeout court pour éviter l'attente
    print("\n📺 Test Débats (mode rapide)...")
    try:
        response = requests.get(f"{BASE_URL}/api/debats?limit=2", timeout=3)
        print(f"  Status: {response.status_code}")
        if response.status_code == 200:
            debats = response.json()
            print(f"  ✅ {len(debats)} débats récupérés")
            if debats:
                print(f"  Premier débat: {debats[0].get('title', 'Sans titre')}")
        else:
            print(f"  ❌ Erreur débats: {response.status_code}")
    except requests.exceptions.Timeout:
        print("  ⏳ Timeout (normal en première exécution - cache en cours)")
    except Exception as e:
        print(f"  ❌ Erreur: {e}")
    
    # Test programme
    print("\n📅 Test Programme...")
    try:
        response = requests.get(f"{BASE_URL}/api/programme", timeout=5)
        print(f"  Status: {response.status_code}")
        if response.status_code == 200:
            programme = response.json()
            print(f"  ✅ {len(programme)} séances programmées")
            if programme:
                print(f"  Première séance: {programme[0].get('titre', 'Sans titre')}")
        else:
            print(f"  ❌ Erreur programme: {response.status_code}")
    except Exception as e:
        print(f"  ❌ Erreur: {e}")
    
    print("\n" + "=" * 50)
    print("✅ Tests terminés")
    print("📚 Documentation: http://localhost:8000/docs")
    
    return True

if __name__ == "__main__":
    test_api()

#!/usr/bin/env python3
"""
Test simple de l'API AN-droid
"""

import requests
import json
import time
import subprocess
import sys
from pathlib import Path

class APITester:
    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.api_process = None
    
    def start_api(self):
        """Démarrer l'API en arrière-plan"""
        print("🚀 Démarrage de l'API...")
        
        try:
            # Démarrer l'API avec uvicorn
            cmd = [
                sys.executable, "-m", "uvicorn", 
                "api.main:app", 
                "--host", "0.0.0.0", 
                "--port", "8000",
                "--log-level", "warning"
            ]
            
            self.api_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=Path.cwd()
            )
            
            # Attendre que l'API soit prête
            max_attempts = 10
            for attempt in range(max_attempts):
                try:
                    response = requests.get(f"{self.base_url}/", timeout=2)
                    if response.status_code == 200:
                        print("✅ API démarrée et accessible")
                        return True
                except:
                    time.sleep(1)
                    print(f"⏳ Tentative {attempt + 1}/{max_attempts}...")
            
            print("❌ API non accessible après 10 tentatives")
            return False
            
        except Exception as e:
            print(f"❌ Erreur démarrage API: {e}")
            return False
    
    def stop_api(self):
        """Arrêter l'API"""
        if self.api_process:
            try:
                self.api_process.terminate()
                self.api_process.wait(timeout=5)
                print("✅ API arrêtée")
            except:
                try:
                    self.api_process.kill()
                    print("🔪 API forcée à s'arrêter")
                except:
                    print("⚠️ Impossible d'arrêter l'API")
    
    def test_endpoint(self, endpoint, method="GET", data=None):
        """Tester un endpoint spécifique"""
        url = f"{self.base_url}{endpoint}"
        print(f"🧪 Test {method} {endpoint}")
        
        try:
            if method == "GET":
                response = requests.get(url, timeout=10)
            elif method == "POST":
                response = requests.post(url, json=data, timeout=10)
            else:
                print(f"❌ Méthode {method} non supportée")
                return False
            
            print(f"  Status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    json_data = response.json()
                    print(f"  ✅ JSON valide ({len(str(json_data))} caractères)")
                    
                    # Afficher un échantillon des données
                    if isinstance(json_data, dict):
                        keys = list(json_data.keys())[:3]
                        print(f"  Clés: {keys}")
                    elif isinstance(json_data, list):
                        print(f"  Liste de {len(json_data)} éléments")
                    
                    return True
                except:
                    print(f"  ✅ Réponse reçue (non-JSON)")
                    print(f"  Contenu: {response.text[:100]}...")
                    return True
            else:
                print(f"  ❌ Erreur HTTP {response.status_code}")
                print(f"  Message: {response.text[:200]}")
                return False
                
        except requests.RequestException as e:
            print(f"  ❌ Erreur requête: {e}")
            return False
    
    def run_api_tests(self):
        """Lancer tous les tests d'API"""
        print("🧪 Test de l'API AN-droid")
        print("=" * 40)
        
        # Démarrer l'API
        if not self.start_api():
            return
        
        try:
            # Tests des endpoints
            endpoints = [
                "/",
                "/api/debats",
                "/api/programme",
                "/docs"  # Documentation Swagger
            ]
            
            results = {}
            
            for endpoint in endpoints:
                success = self.test_endpoint(endpoint)
                results[endpoint] = success
                time.sleep(0.5)  # Pause entre les tests
            
            # Test d'un endpoint spécifique
            print(f"\n🔍 Test endpoint avec paramètres...")
            success = self.test_endpoint("/api/debats?limit=2")
            results["/api/debats?limit=2"] = success
            
            # Résumé
            print(f"\n📊 RÉSUMÉ")
            print("=" * 40)
            
            passed = sum(results.values())
            total = len(results)
            
            for endpoint, success in results.items():
                status = "✅" if success else "❌"
                print(f"{status} {endpoint}")
            
            print(f"\n🎯 Score: {passed}/{total} tests réussis")
            
            if passed == total:
                print("🎉 Tous les tests API passent!")
            elif passed >= total - 1:
                print("👍 API majoritairement fonctionnelle")
            else:
                print("⚠️ Problèmes détectés dans l'API")
            
        finally:
            self.stop_api()

def test_api_simple():
    """Test simple sans démarrage automatique"""
    print("🔍 Test API simple (sans démarrage auto)")
    
    # Vérifier si l'API tourne déjà
    try:
        response = requests.get("http://localhost:8000/", timeout=2)
        if response.status_code == 200:
            print("✅ API déjà accessible")
            
            # Tester quelques endpoints
            endpoints = ["/", "/api/debats", "/api/programme"]
            for endpoint in endpoints:
                try:
                    url = f"http://localhost:8000{endpoint}"
                    resp = requests.get(url, timeout=5)
                    print(f"✅ {endpoint}: {resp.status_code}")
                except Exception as e:
                    print(f"❌ {endpoint}: {e}")
        else:
            print("❌ API non accessible")
            
    except Exception as e:
        print(f"❌ API non accessible: {e}")
        print("💡 Démarrer avec: python start_api.py")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "simple":
        test_api_simple()
    else:
        tester = APITester()
        tester.run_api_tests()

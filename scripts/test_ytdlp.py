#!/usr/bin/env python3
"""
Script de test pour yt-dlp avec les URLs de l'Assemblée nationale
Teste l'extraction audio avec gestion de la longueur des fichiers
"""

import subprocess
import sys
import json
import os
from datetime import datetime
import time

class YTDLPTester:
    def __init__(self):
        self.download_dir = "../downloads"
        self.max_duration = 14400  # 4h en secondes
        self.test_urls = [
            # URLs de test - à remplacer par de vraies URLs découvertes
            "https://videos.assemblee-nationale.fr/",  # Page d'accueil pour test
        ]
        
        # Options yt-dlp optimisées pour l'audio
        self.base_opts = [
            "--extract-audio",
            "--audio-format", "mp3", 
            "--audio-quality", "128K",
            "--output", f"{self.download_dir}/%(title)s.%(ext)s",
            "--user-agent", "AN-droid/1.0 (Compatible crawler)",
            "--sleep-interval", "2",
            "--max-sleep-interval", "5",
            "--ignore-errors",
            "--no-warnings"
        ]
    
    def check_ytdlp_installation(self):
        """Vérifier si yt-dlp est installé"""
        try:
            result = subprocess.run(['yt-dlp', '--version'], 
                                  capture_output=True, text=True)
            print(f"✅ yt-dlp version: {result.stdout.strip()}")
            return True
        except FileNotFoundError:
            print("❌ yt-dlp n'est pas installé")
            print("💡 Installer avec: pip install yt-dlp")
            return False
    
    def get_video_info(self, url):
        """Extraire les informations sans télécharger"""
        print(f"🔍 Extraction des métadonnées: {url}")
        
        cmd = [
            "yt-dlp",
            "--dump-json",
            "--no-download",
            url
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                info = json.loads(result.stdout)
                
                metadata = {
                    'url': url,
                    'title': info.get('title', 'Inconnu'),
                    'duration': info.get('duration'),
                    'uploader': info.get('uploader'),
                    'upload_date': info.get('upload_date'),
                    'formats': len(info.get('formats', [])),
                    'extractable': True
                }
                
                print(f"  📺 Titre: {metadata['title']}")
                print(f"  ⏱️ Durée: {self.format_duration(metadata['duration'])}")
                print(f"  📤 Auteur: {metadata['uploader']}")
                print(f"  🎬 Formats: {metadata['formats']}")
                
                return metadata
            else:
                print(f"  ❌ Erreur: {result.stderr}")
                return {'url': url, 'extractable': False, 'error': result.stderr}
                
        except subprocess.TimeoutExpired:
            print("  ⏰ Timeout lors de l'extraction des métadonnées")
            return {'url': url, 'extractable': False, 'error': 'timeout'}
        except json.JSONDecodeError:
            print("  ❌ Erreur de parsing JSON")
            return {'url': url, 'extractable': False, 'error': 'json_error'}
    
    def format_duration(self, seconds):
        """Formater la durée en format lisible"""
        if not seconds:
            return "Inconnue"
        
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        
        if hours > 0:
            return f"{hours}h{minutes:02d}m{secs:02d}s"
        else:
            return f"{minutes}m{secs:02d}s"
    
    def check_duration_limit(self, duration):
        """Vérifier si la durée est acceptable"""
        if not duration:
            return True, "Durée inconnue - procéder avec prudence"
        
        if duration > self.max_duration:
            return False, f"Durée trop longue: {self.format_duration(duration)} > {self.format_duration(self.max_duration)}"
        
        return True, f"Durée acceptable: {self.format_duration(duration)}"
    
    def download_audio(self, url, info):
        """Télécharger l'audio avec yt-dlp"""
        print(f"⬇️ Téléchargement audio: {info.get('title', 'Sans titre')}")
        
        # Vérifier la durée avant téléchargement
        duration_ok, duration_msg = self.check_duration_limit(info.get('duration'))
        print(f"  {duration_msg}")
        
        if not duration_ok:
            print("  ❌ Téléchargement annulé (durée trop longue)")
            return False
        
        # Créer le dossier de téléchargement
        os.makedirs(self.download_dir, exist_ok=True)
        
        # Commande yt-dlp
        cmd = ["yt-dlp"] + self.base_opts + [url]
        
        try:
            print("  🔄 Démarrage du téléchargement...")
            start_time = time.time()
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)  # 10 min max
            
            download_time = time.time() - start_time
            
            if result.returncode == 0:
                print(f"  ✅ Téléchargement réussi en {download_time:.1f}s")
                print(f"  📁 Fichier sauvé dans: {self.download_dir}")
                return True
            else:
                print(f"  ❌ Échec du téléchargement: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print("  ⏰ Timeout lors du téléchargement")
            return False
    
    def test_single_url(self, url):
        """Tester une URL complètement"""
        print(f"\n{'='*60}")
        print(f"🧪 Test de l'URL: {url}")
        print(f"{'='*60}")
        
        # 1. Extraire les métadonnées
        info = self.get_video_info(url)
        
        if not info.get('extractable', False):
            print("❌ URL non compatible avec yt-dlp")
            return {
                'url': url,
                'success': False,
                'stage': 'metadata_extraction',
                'error': info.get('error', 'unknown')
            }
        
        # 2. Tenter le téléchargement si la durée est OK
        download_success = False
        duration_ok, _ = self.check_duration_limit(info.get('duration'))
        
        if duration_ok:
            download_success = self.download_audio(url, info)
        else:
            print("⚠️ Téléchargement ignoré (durée trop longue)")
        
        return {
            'url': url,
            'success': download_success,
            'metadata': info,
            'duration_acceptable': duration_ok
        }
    
    def run_batch_test(self, urls=None):
        """Tester plusieurs URLs"""
        test_urls = urls or self.test_urls
        
        print("🚀 Démarrage des tests yt-dlp")
        print(f"📁 Dossier de téléchargement: {os.path.abspath(self.download_dir)}")
        
        if not self.check_ytdlp_installation():
            return
        
        results = []
        
        for i, url in enumerate(test_urls, 1):
            print(f"\n📋 Test {i}/{len(test_urls)}")
            result = self.test_single_url(url)
            results.append(result)
            
            # Pause entre les tests pour respecter les serveurs
            if i < len(test_urls):
                print("⏸️ Pause de 5 secondes...")
                time.sleep(5)
        
        # Résumé des résultats
        self.print_summary(results)
        self.save_results(results)
        
        return results
    
    def print_summary(self, results):
        """Afficher un résumé des tests"""
        print(f"\n{'='*60}")
        print("📊 RÉSUMÉ DES TESTS")
        print(f"{'='*60}")
        
        total = len(results)
        successful = sum(1 for r in results if r.get('success'))
        extractable = sum(1 for r in results if r.get('metadata', {}).get('extractable'))
        
        print(f"📈 Tests effectués: {total}")
        print(f"✅ Téléchargements réussis: {successful}/{total}")
        print(f"🔍 URLs extractables: {extractable}/{total}")
        
        if successful > 0:
            print(f"\n✅ URLs qui fonctionnent:")
            for result in results:
                if result.get('success'):
                    metadata = result.get('metadata', {})
                    print(f"  • {metadata.get('title', 'Sans titre')}")
                    print(f"    {result['url']}")
        
        if extractable < total:
            print(f"\n❌ URLs problématiques:")
            for result in results:
                if not result.get('metadata', {}).get('extractable'):
                    print(f"  • {result['url']}")
                    print(f"    Erreur: {result.get('metadata', {}).get('error', 'inconnue')}")
    
    def save_results(self, results):
        """Sauvegarder les résultats des tests"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"ytdlp_test_results_{timestamp}.json"
        
        test_report = {
            'timestamp': datetime.now().isoformat(),
            'total_tests': len(results),
            'successful_downloads': sum(1 for r in results if r.get('success')),
            'extractable_urls': sum(1 for r in results if r.get('metadata', {}).get('extractable')),
            'results': results
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(test_report, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Résultats sauvegardés dans: {filename}")
    
    def test_with_discovered_urls(self, discovery_file):
        """Tester avec les URLs découvertes par le script d'exploration"""
        try:
            with open(discovery_file, 'r', encoding='utf-8') as f:
                discovery_data = json.load(f)
            
            # Extraire les URLs de vidéos des résultats d'exploration
            test_urls = []
            
            for metadata in discovery_data.get('video_metadata', []):
                video_urls = metadata.get('video_urls', [])
                test_urls.extend(video_urls)
            
            # Ajouter les URLs des liens de téléchargement
            for metadata in discovery_data.get('video_metadata', []):
                download_links = metadata.get('download_links', [])
                for link in download_links:
                    if link.get('type') == 'audio':
                        test_urls.append(link['url'])
            
            if test_urls:
                print(f"📋 URLs découvertes à tester: {len(test_urls)}")
                return self.run_batch_test(test_urls[:5])  # Tester seulement les 5 premières
            else:
                print("❌ Aucune URL de vidéo trouvée dans le fichier de découverte")
                
        except FileNotFoundError:
            print(f"❌ Fichier de découverte non trouvé: {discovery_file}")
        except json.JSONDecodeError:
            print(f"❌ Erreur de lecture du fichier JSON: {discovery_file}")

def main():
    tester = YTDLPTester()
    
    # Test avec URLs de base
    print("🎯 Test avec URLs par défaut")
    tester.run_batch_test()
    
    # Si un fichier de découverte existe, l'utiliser aussi
    discovery_files = [f for f in os.listdir('.') if f.startswith('exploration_results_')]
    if discovery_files:
        latest_discovery = sorted(discovery_files)[-1]
        print(f"\n🎯 Test avec découvertes du fichier: {latest_discovery}")
        tester.test_with_discovered_urls(latest_discovery)

if __name__ == "__main__":
    main()

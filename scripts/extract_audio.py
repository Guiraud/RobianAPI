#!/usr/bin/env python3
"""
Script d'extraction audio principal avec fallback JavaScript
Utilise yt-dlp en priorité, puis Selenium si échec
"""

import os
import subprocess
import time
import json
from datetime import datetime
from urllib.parse import urljoin, urlparse
from pathlib import Path

# Optionnel: Selenium pour fallback
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    print("⚠️ Selenium non disponible - fallback JavaScript désactivé")

import requests

class AudioExtractor:
    def __init__(self, download_dir="../downloads"):
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(exist_ok=True)
        
        self.max_duration = 14400  # 4h en secondes
        self.max_file_size = 500 * 1024 * 1024  # 500MB
        
        # Configuration yt-dlp
        self.ytdlp_opts = {
            'format': 'bestaudio/best',
            'outtmpl': str(self.download_dir / '%(title)s.%(ext)s'),
            'extractaudio': True,
            'audioformat': 'mp3',
            'audioquality': '128K',
            'quiet': False,
            'no_warnings': True,
            'user_agent': 'AN-droid/1.0 (Compatible crawler)',
            'sleep_interval': 2,
            'max_sleep_interval': 5
        }
        
        # Configuration Selenium
        self.selenium_timeout = 30
        self.setup_selenium()
    
    def setup_selenium(self):
        """Configuration du driver Selenium"""
        if not SELENIUM_AVAILABLE:
            self.driver = None
            return
        
        chrome_options = Options()
        chrome_options.add_argument('--headless')  # Mode sans interface
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--user-agent=AN-droid/1.0 (Compatible crawler)')
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            print("✅ Driver Selenium configuré")
        except Exception as e:
            print(f"❌ Erreur configuration Selenium: {e}")
            self.driver = None
    
    def extract_with_ytdlp(self, url):
        """Extraction principale avec yt-dlp"""
        print(f"🎵 Extraction yt-dlp: {url}")
        
        try:
            # Étape 1: Vérifier les métadonnées
            info = self.get_video_info_ytdlp(url)
            if not info:
                raise Exception("Impossible d'extraire les métadonnées")
            
            # Étape 2: Vérifier la durée
            duration = info.get('duration', 0)
            if duration > self.max_duration:
                raise Exception(f"Durée trop longue: {duration}s > {self.max_duration}s")
            
            # Étape 3: Télécharger
            cmd = self.build_ytdlp_command(url)
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            
            if result.returncode == 0:
                # Trouver le fichier téléchargé
                downloaded_file = self.find_downloaded_file(info.get('title', 'unknown'))
                if downloaded_file:
                    print(f"✅ yt-dlp réussi: {downloaded_file}")
                    return {
                        'success': True,
                        'method': 'ytdlp',
                        'file_path': downloaded_file,
                        'title': info.get('title'),
                        'duration': duration
                    }
            
            raise Exception(f"yt-dlp échec: {result.stderr}")
            
        except Exception as e:
            print(f"❌ yt-dlp échec: {e}")
            return None
    
    def get_video_info_ytdlp(self, url):
        """Extraire les métadonnées avec yt-dlp"""
        cmd = ["yt-dlp", "--dump-json", "--no-download", url]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                return json.loads(result.stdout)
        except Exception as e:
            print(f"❌ Erreur métadonnées yt-dlp: {e}")
        
        return None
    
    def build_ytdlp_command(self, url):
        """Construire la commande yt-dlp"""
        cmd = [
            "yt-dlp",
            "--extract-audio",
            "--audio-format", "mp3",
            "--audio-quality", "128K",
            "--output", str(self.download_dir / "%(title)s.%(ext)s"),
            "--user-agent", "AN-droid/1.0 (Compatible crawler)",
            "--sleep-interval", "2",
            "--max-sleep-interval", "5",
            url
        ]
        return cmd
    
    def find_downloaded_file(self, title_hint):
        """Trouver le fichier téléchargé récemment"""
        try:
            # Chercher les fichiers .mp3 récents dans le dossier
            mp3_files = list(self.download_dir.glob("*.mp3"))
            if not mp3_files:
                return None
            
            # Prendre le plus récent
            latest_file = max(mp3_files, key=lambda f: f.stat().st_mtime)
            
            # Vérifier qu'il est récent (moins de 5 minutes)
            if time.time() - latest_file.stat().st_mtime < 300:
                return str(latest_file)
                
        except Exception as e:
            print(f"❌ Erreur recherche fichier: {e}")
        
        return None
    
    def extract_with_selenium(self, url):
        """Fallback avec Selenium et XPath"""
        if not self.driver:
            print("❌ Selenium non disponible")
            return None
        
        print(f"🌐 Extraction Selenium: {url}")
        
        try:
            # Charger la page
            self.driver.get(url)
            
            # Attendre que la page se charge
            WebDriverWait(self.driver, self.selenium_timeout).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Chercher le bouton de téléchargement audio
            audio_download_methods = [
                self.find_audio_download_xpath,
                self.find_audio_download_generic,
                self.extract_from_video_element
            ]
            
            for method in audio_download_methods:
                result = method()
                if result:
                    return self.download_direct_audio(result, url)
            
            raise Exception("Aucune méthode d'extraction Selenium n'a fonctionné")
            
        except Exception as e:
            print(f"❌ Selenium échec: {e}")
            return None
    
    def find_audio_download_xpath(self):
        """Rechercher avec le XPath spécifique mentionné"""
        try:
            # XPath fourni dans les spécifications
            xpath = '//*[@id="player_download_sound_icon"]'
            element = self.driver.find_element(By.XPATH, xpath)
            
            url = element.get_attribute('href')
            if url:
                print(f"✅ Trouvé lien audio via XPath: {url}")
                return {
                    'url': url,
                    'method': 'xpath_specific',
                    'element_text': element.text
                }
                
        except Exception as e:
            print(f"❌ XPath spécifique échec: {e}")
        
        return None
    
    def find_audio_download_generic(self):
        """Recherche générique de liens de téléchargement audio"""
        try:
            # Rechercher tous les liens contenant des mots-clés audio
            audio_keywords = ['audio', 'mp3', 'son', 'télécharger', 'download']
            
            links = self.driver.find_elements(By.TAG_NAME, 'a')
            
            for link in links:
                href = link.get_attribute('href')
                text = link.text.lower()
                
                if href and any(keyword in text for keyword in audio_keywords):
                    print(f"✅ Trouvé lien audio générique: {href}")
                    return {
                        'url': href,
                        'method': 'generic_search',
                        'element_text': link.text
                    }
                    
        except Exception as e:
            print(f"❌ Recherche générique échec: {e}")
        
        return None
    
    def extract_from_video_element(self):
        """Extraire depuis l'élément video HTML5"""
        try:
            # Rechercher les éléments video et audio
            media_elements = (
                self.driver.find_elements(By.TAG_NAME, 'video') +
                self.driver.find_elements(By.TAG_NAME, 'audio') +
                self.driver.find_elements(By.TAG_NAME, 'source')
            )
            
            for element in media_elements:
                src = element.get_attribute('src')
                if src and any(ext in src.lower() for ext in ['.mp3', '.mp4', '.m3u8']):
                    print(f"✅ Trouvé source média: {src}")
                    return {
                        'url': src,
                        'method': 'video_element',
                        'element_tag': element.tag_name
                    }
                    
        except Exception as e:
            print(f"❌ Extraction élément vidéo échec: {e}")
        
        return None
    
    def download_direct_audio(self, audio_info, base_url):
        """Télécharger directement un fichier audio"""
        audio_url = audio_info['url']
        
        # Construire l'URL absolue si nécessaire
        if not audio_url.startswith('http'):
            audio_url = urljoin(base_url, audio_url)
        
        print(f"⬇️ Téléchargement direct: {audio_url}")
        
        try:
            # Headers pour sembler légitime
            headers = {
                'User-Agent': 'AN-droid/1.0 (Compatible crawler)',
                'Accept': 'audio/*,*/*;q=0.1',
                'Referer': base_url
            }
            
            response = requests.get(audio_url, headers=headers, stream=True, timeout=30)
            response.raise_for_status()
            
            # Vérifier la taille du fichier
            content_length = response.headers.get('content-length')
            if content_length and int(content_length) > self.max_file_size:
                raise Exception(f"Fichier trop volumineux: {content_length} bytes")
            
            # Générer un nom de fichier
            filename = self.generate_filename(audio_url, audio_info.get('element_text', ''))
            file_path = self.download_dir / filename
            
            # Télécharger
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            print(f"✅ Téléchargement direct réussi: {file_path}")
            
            return {
                'success': True,
                'method': f"selenium_{audio_info['method']}",
                'file_path': str(file_path),
                'url': audio_url
            }
            
        except Exception as e:
            print(f"❌ Téléchargement direct échec: {e}")
            return None
    
    def generate_filename(self, url, hint=""):
        """Générer un nom de fichier approprié"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Essayer d'extraire un nom depuis l'URL ou le hint
        if hint:
            base_name = "".join(c for c in hint if c.isalnum() or c in (' ', '-', '_')).strip()
            base_name = base_name[:50]  # Limiter la longueur
        else:
            parsed = urlparse(url)
            base_name = Path(parsed.path).stem or "audio"
        
        if not base_name:
            base_name = "audio"
        
        return f"{base_name}_{timestamp}.mp3"
    
    def extract_audio(self, url):
        """Méthode principale d'extraction avec fallback"""
        print(f"\n{'='*60}")
        print(f"🎯 Extraction audio: {url}")
        print(f"{'='*60}")
        
        # Méthode 1: yt-dlp (priorité)
        result = self.extract_with_ytdlp(url)
        if result and result.get('success'):
            return result
        
        print("🔄 yt-dlp échec, basculement vers Selenium...")
        
        # Méthode 2: Selenium fallback
        result = self.extract_with_selenium(url)
        if result and result.get('success'):
            return result
        
        print("❌ Toutes les méthodes d'extraction ont échoué")
        return {
            'success': False,
            'error': 'Toutes les méthodes ont échoué',
            'url': url
        }
    
    def cleanup(self):
        """Nettoyer les ressources"""
        if self.driver:
            try:
                self.driver.quit()
                print("✅ Driver Selenium fermé")
            except:
                pass
    
    def __del__(self):
        """Destructor pour nettoyer automatiquement"""
        self.cleanup()

def main():
    """Test du script d'extraction"""
    extractor = AudioExtractor()
    
    # URLs de test
    test_urls = [
        "https://videos.assemblee-nationale.fr/",  # À remplacer par vraies URLs
    ]
    
    try:
        for url in test_urls:
            result = extractor.extract_audio(url)
            
            if result.get('success'):
                print(f"✅ Extraction réussie:")
                print(f"   Méthode: {result.get('method')}")
                print(f"   Fichier: {result.get('file_path')}")
            else:
                print(f"❌ Extraction échec: {result.get('error')}")
            
            print()  # Ligne vide entre les tests
            
    finally:
        extractor.cleanup()

if __name__ == "__main__":
    main()

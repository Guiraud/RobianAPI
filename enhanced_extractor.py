#!/usr/bin/env python3
"""
Extracteur amélioré pour AN-droid
Utilise Selenium pour gérer le JavaScript et extraire automatiquement les URLs m3u8
"""

import requests
import re
import subprocess
import json
import time
from pathlib import Path
from datetime import datetime
from urllib.parse import urljoin, urlparse

# Selenium imports avec gestion d'erreur
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    print("⚠️ Selenium non disponible - installation recommandée: pip install selenium")

class EnhancedAudioExtractor:
    def __init__(self, download_dir="downloads", headless=True):
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(exist_ok=True)
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'AN-droid/1.0 (Compatible crawler)',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8'
        })
        
        # Configuration Selenium
        self.headless = headless
        self.driver = None
        self.setup_selenium()
        
        # Patterns d'URLs m3u8
        self.m3u8_patterns = [
            r'https?://videos-an\.vodalys\.com/[^"\'\s]*\.m3u8[^"\'\s]*',
            r'https?://assemblee-nationale\.akamaized\.net/[^"\'\s]*\.m3u8[^"\'\s]*',
            r'https?://[^"\'\s]*assemblee[^"\'\s]*\.m3u8[^"\'\s]*',
            r'["\']([^"\']*\.m3u8[^"\']*)["\']'
        ]
        
        # Sélecteurs pour les boutons de téléchargement
        self.download_selectors = [
            '#player_download_sound_icon',
            'a[href*="download"]',
            'a[href*="audio"]',
            'a[href*="mp3"]',
            '.download-audio',
            '.audio-download'
        ]
        
        # Limites de sécurité
        self.max_duration = 14400  # 4h
        self.max_file_size = 500 * 1024 * 1024  # 500MB
    
    def setup_selenium(self):
        """Configuration du driver Selenium"""
        if not SELENIUM_AVAILABLE:
            self.driver = None
            return
        
        try:
            chrome_options = Options()
            
            if self.headless:
                chrome_options.add_argument('--headless')
            
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--disable-plugins')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--user-agent=AN-droid/1.0 (Compatible crawler)')
            
            # Désactiver les images pour aller plus vite
            prefs = {
                "profile.managed_default_content_settings.images": 2,
                "profile.default_content_setting_values.notifications": 2
            }
            chrome_options.add_experimental_option("prefs", prefs)
            
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.set_page_load_timeout(30)
            
            print("✅ Driver Selenium configuré")
            
        except Exception as e:
            print(f"❌ Erreur configuration Selenium: {e}")
            print("💡 Vérifiez que ChromeDriver est installé")
            self.driver = None
    
    def extract_title_from_page(self, url):
        """Extraire le titre depuis la page HTML avec Selenium"""
        if not self.driver:
            return self.extract_title_basic(url)
        
        try:
            print(f"📄 Extraction du titre depuis: {url}")
            self.driver.get(url)
            
            # Accepter les cookies si nécessaire
            self.accept_cookies()
            
            # Essayer différents sélecteurs pour le titre
            title_selectors = [
                'h1',
                '.video-title',
                '.main-title',
                '.content-title',
                'title'
            ]
            
            for selector in title_selectors:
                try:
                    element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    title = element.text.strip()
                    if title and len(title) > 5:
                        # Nettoyer le titre
                        title = re.sub(r'\s*-\s*Vidéos de l\'Assemblée nationale.*$', '', title)
                        print(f"✅ Titre trouvé: {title}")
                        return title
                except NoSuchElementException:
                    continue
            
            # Fallback sur le titre de la page
            title = self.driver.title
            if title:
                title = re.sub(r'\s*-\s*Vidéos de l\'Assemblée nationale.*$', '', title)
                return title
                
        except Exception as e:
            print(f"⚠️ Erreur extraction titre avec Selenium: {e}")
            return self.extract_title_basic(url)
        
        return "Debat_AN"
    
    def extract_title_basic(self, url):
        """Extraction basique du titre avec requests"""
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            title_match = re.search(r'<title>([^<]+)</title>', response.text, re.IGNORECASE)
            if title_match:
                title = title_match.group(1).strip()
                title = re.sub(r'\s*-\s*Vidéos de l\'Assemblée nationale.*$', '', title)
                return title
                
        except Exception as e:
            print(f"⚠️ Erreur extraction titre basique: {e}")
        
        return "Debat_AN"
    
    def accept_cookies(self):
        """Accepter les cookies automatiquement"""
        try:
            # Attendre et cliquer sur le bouton OK des cookies
            cookie_selectors = [
                'button:contains("OK")',
                '.cookie-accept',
                '#cookie-accept',
                'button[onclick*="cookie"]',
                'input[value="OK"]'
            ]
            
            for selector in cookie_selectors:
                try:
                    if 'contains' in selector:
                        # XPath pour contient le texte
                        xpath = f"//button[contains(text(), 'OK')]"
                        element = WebDriverWait(self.driver, 3).until(
                            EC.element_to_be_clickable((By.XPATH, xpath))
                        )
                    else:
                        element = WebDriverWait(self.driver, 3).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                        )
                    
                    element.click()
                    print("✅ Cookies acceptés")
                    time.sleep(1)  # Laisser le temps à la page de se mettre à jour
                    return True
                    
                except TimeoutException:
                    continue
                    
        except Exception as e:
            print(f"⚠️ Impossible d'accepter les cookies: {e}")
        
        return False
    
    def extract_m3u8_urls_selenium(self, url):
        """Extraire les URLs m3u8 avec Selenium"""
        if not self.driver:
            print("❌ Selenium non disponible")
            return []
        
        try:
            print(f"🔍 Extraction URLs m3u8 avec Selenium depuis: {url}")
            self.driver.get(url)
            
            # Accepter les cookies
            self.accept_cookies()
            
            # Attendre que la page se charge complètement
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Laisser le temps au JavaScript de s'exécuter
            time.sleep(3)
            
            # Récupérer le HTML après exécution du JavaScript
            page_source = self.driver.page_source
            
            # Rechercher les URLs m3u8 dans le source
            m3u8_urls = []
            
            for pattern in self.m3u8_patterns:
                matches = re.findall(pattern, page_source, re.IGNORECASE)
                for match in matches:
                    if isinstance(match, tuple):
                        url_found = match[0] if match[0] else match[-1]
                    else:
                        url_found = match
                    
                    # Nettoyer l'URL
                    url_found = url_found.strip('"\'')
                    
                    if url_found and url_found not in m3u8_urls:
                        m3u8_urls.append(url_found)
            
            # Chercher aussi dans les éléments video et source
            try:
                video_elements = self.driver.find_elements(By.TAG_NAME, "video")
                source_elements = self.driver.find_elements(By.TAG_NAME, "source")
                
                for element in video_elements + source_elements:
                    src = element.get_attribute("src")
                    if src and ".m3u8" in src:
                        m3u8_urls.append(src)
                        
            except Exception as e:
                print(f"⚠️ Erreur recherche éléments video: {e}")
            
            # Rechercher dans les scripts
            try:
                script_elements = self.driver.find_elements(By.TAG_NAME, "script")
                for script in script_elements:
                    script_content = script.get_attribute("innerHTML")
                    if script_content:
                        for pattern in self.m3u8_patterns:
                            matches = re.findall(pattern, script_content, re.IGNORECASE)
                            for match in matches:
                                if isinstance(match, tuple):
                                    url_found = match[0] if match[0] else match[-1]
                                else:
                                    url_found = match
                                
                                url_found = url_found.strip('"\'')
                                if url_found and url_found not in m3u8_urls:
                                    m3u8_urls.append(url_found)
                                    
            except Exception as e:
                print(f"⚠️ Erreur recherche dans scripts: {e}")
            
            # Nettoyer et déduplicater
            cleaned_urls = []
            for url in m3u8_urls:
                if url.startswith('http') and 'm3u8' in url:
                    cleaned_urls.append(url)
            
            unique_urls = list(set(cleaned_urls))
            
            if unique_urls:
                print(f"✅ URLs m3u8 trouvées avec Selenium: {len(unique_urls)}")
                for i, url in enumerate(unique_urls, 1):
                    print(f"  {i}. {url}")
            else:
                print("❌ Aucune URL m3u8 trouvée avec Selenium")
            
            return unique_urls
            
        except Exception as e:
            print(f"❌ Erreur extraction Selenium: {e}")
            return []
    
    def extract_m3u8_urls_basic(self, url):
        """Extraction basique des URLs m3u8 avec requests"""
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            m3u8_urls = []
            
            for pattern in self.m3u8_patterns:
                matches = re.findall(pattern, response.text, re.IGNORECASE)
                for match in matches:
                    if isinstance(match, tuple):
                        url_found = match[0] if match[0] else match[-1]
                    else:
                        url_found = match
                    
                    url_found = url_found.strip('"\'')
                    
                    if url_found and url_found.startswith('http') and url_found not in m3u8_urls:
                        m3u8_urls.append(url_found)
            
            return m3u8_urls
            
        except Exception as e:
            print(f"❌ Erreur extraction basique: {e}")
            return []
    
    def extract_m3u8_urls(self, url):
        """Méthode principale d'extraction des URLs m3u8"""
        print(f"🔍 Extraction URLs m3u8 depuis: {url}")
        
        # Essayer d'abord avec Selenium (plus efficace)
        if self.driver:
            urls = self.extract_m3u8_urls_selenium(url)
            if urls:
                return urls
        
        # Fallback avec requests basique
        print("🔄 Fallback vers extraction basique...")
        return self.extract_m3u8_urls_basic(url)
    
    def get_video_metadata(self, m3u8_url):
        """Extraire les métadonnées d'une URL m3u8"""
        try:
            cmd = ["yt-dlp", "--dump-json", "--no-download", m3u8_url]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                info = json.loads(result.stdout)
                return {
                    'title': info.get('title', 'Audio_AN'),
                    'duration': info.get('duration', 0),
                    'formats': len(info.get('formats', [])),
                    'audio_formats': len([f for f in info.get('formats', []) if f.get('acodec') != 'none'])
                }
        except Exception as e:
            print(f"⚠️ Erreur métadonnées: {e}")
        
        return None
    
    def extract_audio_from_m3u8(self, m3u8_url, title_hint="", original_url=""):
        """Extraire l'audio depuis une URL m3u8"""
        print(f"🎵 Extraction audio depuis m3u8...")
        
        metadata = self.get_video_metadata(m3u8_url)
        if not metadata:
            return {'success': False, 'reason': 'metadata_failed'}
        
        print(f"📺 Titre: {metadata['title']}")
        print(f"⏱️ Durée: {metadata['duration']} secondes ({metadata['duration']//60}min)")
        print(f"🎵 Formats audio: {metadata['audio_formats']}")
        
        if metadata['duration'] > self.max_duration:
            print(f"⚠️ Durée trop longue: {metadata['duration']}s > {self.max_duration}s")
            return {'success': False, 'reason': 'duration_too_long', 'duration': metadata['duration']}
        
        safe_title = self.sanitize_filename(title_hint or metadata['title'])
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = self.download_dir / f"{safe_title}_{timestamp}.mp3"
        
        cmd = [
            "yt-dlp",
            "--extract-audio",
            "--audio-format", "mp3",
            "--audio-quality", "128K",
            "--output", str(output_file.with_suffix('.%(ext)s')),
            "--no-warnings",
            m3u8_url
        ]
        
        if original_url:
            cmd.extend(["--add-header", f"Referer:{original_url}"])
        
        try:
            print("⬇️ Démarrage téléchargement...")
            start_time = time.time()
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            download_time = time.time() - start_time
            
            if result.returncode == 0:
                created_files = list(self.download_dir.glob(f"{safe_title}_{timestamp}*.mp3"))
                if created_files:
                    audio_file = created_files[0]
                    file_size = audio_file.stat().st_size
                    
                    print(f"✅ Extraction réussie!")
                    print(f"📁 Fichier: {audio_file}")
                    print(f"📊 Taille: {file_size / 1024 / 1024:.1f} MB")
                    print(f"⏱️ Temps: {download_time:.1f}s")
                    
                    return {
                        'success': True,
                        'method': 'm3u8_selenium',
                        'file_path': str(audio_file),
                        'title': metadata['title'],
                        'duration': metadata['duration'],
                        'file_size': file_size,
                        'download_time': download_time
                    }
            
            print(f"❌ Échec extraction: {result.stderr}")
            return {'success': False, 'reason': 'ytdlp_failed', 'error': result.stderr}
            
        except subprocess.TimeoutExpired:
            print("⏰ Timeout lors du téléchargement")
            return {'success': False, 'reason': 'timeout'}
        except Exception as e:
            print(f"❌ Erreur extraction: {e}")
            return {'success': False, 'error': str(e)}
    
    def sanitize_filename(self, filename):
        """Nettoyer un nom de fichier"""
        filename = re.sub(r'[<>:"/\\|?*]', '', filename)
        filename = re.sub(r'\s+', '_', filename)
        filename = filename[:50]
        return filename or 'audio_an'
    
    def extract_audio_complete(self, url):
        """Méthode principale - extraction complète"""
        print(f"\n{'='*70}")
        print(f"🎯 EXTRACTION AUDIO AMÉLIORÉE")
        print(f"🔗 URL: {url}")
        print(f"{'='*70}")
        
        # 1. Extraire le titre
        title = self.extract_title_from_page(url)
        print(f"📄 Titre extrait: {title}")
        
        # 2. Extraire les URLs m3u8
        m3u8_urls = self.extract_m3u8_urls(url)
        
        if not m3u8_urls:
            return {
                'success': False,
                'reason': 'no_m3u8_found',
                'url': url
            }
        
        # 3. Prioriser les URLs (master.m3u8 en premier)
        master_urls = [u for u in m3u8_urls if 'master.m3u8' in u]
        sorted_urls = master_urls + [u for u in m3u8_urls if u not in master_urls]
        
        selected_url = sorted_urls[0]
        print(f"🎬 URL m3u8 sélectionnée: {selected_url}")
        
        # 4. Extraire l'audio
        result = self.extract_audio_from_m3u8(
            selected_url,
            title_hint=title,
            original_url=url
        )
        
        if result.get('success'):
            result['original_url'] = url
            result['m3u8_url'] = selected_url
            result['page_title'] = title
            result['total_m3u8_found'] = len(m3u8_urls)
        
        return result
    
    def cleanup(self):
        """Nettoyer les ressources"""
        if self.driver:
            try:
                self.driver.quit()
                print("✅ Driver Selenium fermé")
            except:
                pass
    
    def __del__(self):
        """Destructor"""
        self.cleanup()

def test_enhanced_extractor():
    """Test de l'extracteur amélioré"""
    
    # URLs de test
    test_urls = [
        "https://videos.assemblee-nationale.fr/video.16905943_682f1c59d8a2c.2eme-seance--droit-a-l-aide-a-mourir-suite-22-mai-2025",
        "https://videos.assemblee-nationale.fr/direct.16816580_6824831acba73"
    ]
    
    print("🎯 TEST DE L'EXTRACTEUR AMÉLIORÉ AN-droid")
    print("=" * 60)
    print("✨ Fonctionnalités:")
    print("  - Selenium pour JavaScript")
    print("  - Acceptation automatique des cookies")
    print("  - Extraction d'URLs m3u8 avancée")
    print("  - Support Akamai et Vodalys")
    print("")
    
    extractor = EnhancedAudioExtractor(headless=True)
    
    if not extractor.driver:
        print("❌ Selenium non disponible - test limité")
        print("💡 Installation: pip install selenium")
        print("💡 ChromeDriver requis")
        return
    
    try:
        for i, url in enumerate(test_urls, 1):
            print(f"\n🧪 Test {i}/{len(test_urls)}")
            
            # Test extraction URLs seulement (pas de téléchargement)
            title = extractor.extract_title_from_page(url)
            m3u8_urls = extractor.extract_m3u8_urls(url)
            
            print(f"📄 Titre: {title}")
            print(f"🔗 URLs m3u8 trouvées: {len(m3u8_urls)}")
            
            for j, m3u8_url in enumerate(m3u8_urls[:3], 1):  # Montrer max 3
                print(f"  {j}. {m3u8_url}")
                
                # Tester les métadonnées
                metadata = extractor.get_video_metadata(m3u8_url)
                if metadata:
                    print(f"     ⏱️ {metadata['duration']}s, 🎵 {metadata['audio_formats']} formats audio")
            
            if m3u8_urls:
                print(f"✅ Extraction possible!")
            else:
                print(f"❌ Aucune URL m3u8 trouvée")
            
            time.sleep(2)  # Pause entre les tests
        
        print(f"\n🎉 Tests terminés!")
        
    finally:
        extractor.cleanup()

if __name__ == "__main__":
    test_enhanced_extractor()

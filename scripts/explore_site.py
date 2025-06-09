#!/usr/bin/env python3
"""
Script d'exploration du site videos.assemblee-nationale.fr
Analyse la structure des pages et identifie les patterns d'URLs
"""

import requests
from bs4 import BeautifulSoup
import re
import time
import json
from urllib.parse import urljoin, urlparse
from datetime import datetime

class ANSiteExplorer:
    def __init__(self):
        self.base_url = "https://videos.assemblee-nationale.fr/"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'AN-droid/1.0 (Compatible crawler for civic app)',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'fr-FR,fr;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive'
        })
        self.discovered_urls = []
        self.video_patterns = []
        
    def rate_limit(self, delay=2):
        """Respecter les serveurs de l'AN avec un délai"""
        time.sleep(delay)
    
    def fetch_page(self, url):
        """Récupérer une page avec gestion d'erreurs"""
        try:
            self.rate_limit()
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            print(f"❌ Erreur lors de la récupération de {url}: {e}")
            return None
    
    def explore_homepage(self):
        """Explorer la page d'accueil pour identifier les liens"""
        print("🔍 Exploration de la page d'accueil...")
        
        response = self.fetch_page(self.base_url)
        if not response:
            return
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Rechercher les liens vers les vidéos
        video_links = []
        
        # Pattern 1: Liens directs vers les vidéos
        for link in soup.find_all('a', href=True):
            href = link['href']
            if any(keyword in href.lower() for keyword in ['video', 'seance', 'commission', 'debat']):
                full_url = urljoin(self.base_url, href)
                video_links.append({
                    'url': full_url,
                    'text': link.get_text(strip=True),
                    'title': link.get('title', '')
                })
        
        print(f"✅ Trouvé {len(video_links)} liens potentiels de vidéos")
        
        # Analyser quelques liens pour identifier les patterns
        for i, link in enumerate(video_links[:5]):
            print(f"📺 Lien {i+1}: {link['text'][:50]}...")
            print(f"    URL: {link['url']}")
            self.analyze_video_page(link['url'])
            
        return video_links
    
    def analyze_video_page(self, url):
        """Analyser une page de vidéo pour extraire les métadonnées"""
        print(f"🔍 Analyse de la page vidéo: {url}")
        
        response = self.fetch_page(url)
        if not response:
            return None
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extraire les métadonnées
        metadata = {
            'url': url,
            'title': self.extract_title(soup),
            'date': self.extract_date(soup),
            'duration': self.extract_duration(soup),
            'video_urls': self.extract_video_urls(soup),
            'download_links': self.extract_download_links(soup),
            'javascript_player': self.find_javascript_player(soup)
        }
        
        print(f"📊 Métadonnées extraites:")
        for key, value in metadata.items():
            if value:
                print(f"    {key}: {value}")
        
        return metadata
    
    def extract_title(self, soup):
        """Extraire le titre de la vidéo"""
        # Essayer différents sélecteurs pour le titre
        selectors = [
            'h1',
            '.video-title',
            'title',
            '.main-title',
            '.content-title'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                return element.get_text(strip=True)
        
        return None
    
    def extract_date(self, soup):
        """Extraire la date de la séance"""
        # Rechercher des patterns de date
        date_patterns = [
            r'(\d{1,2}/\d{1,2}/\d{4})',
            r'(\d{1,2}-\d{1,2}-\d{4})',
            r'(\d{4}-\d{1,2}-\d{1,2})'
        ]
        
        text = soup.get_text()
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        
        return None
    
    def extract_duration(self, soup):
        """Extraire la durée de la vidéo"""
        # Rechercher des patterns de durée
        duration_patterns = [
            r'(\d+:\d+:\d+)',  # HH:MM:SS
            r'(\d+:\d+)',      # MM:SS
            r'Durée[:\s]*(\d+[hm\s]+\d*)',  # Durée: 1h 30m
        ]
        
        text = soup.get_text()
        for pattern in duration_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def extract_video_urls(self, soup):
        """Extraire les URLs des vidéos"""
        video_urls = []
        
        # Rechercher dans les éléments video et source
        for video in soup.find_all(['video', 'source']):
            src = video.get('src')
            if src:
                video_urls.append(urljoin(self.base_url, src))
        
        # Rechercher dans les scripts pour les players JavaScript
        for script in soup.find_all('script'):
            if script.string:
                # Rechercher des URLs de fichiers vidéo/audio
                url_matches = re.findall(r'["\']([^"\']*\.(?:mp4|mp3|m3u8|webm)[^"\']*)["\']', script.string)
                for url in url_matches:
                    video_urls.append(urljoin(self.base_url, url))
        
        return list(set(video_urls))  # Supprimer les doublons
    
    def extract_download_links(self, soup):
        """Rechercher les liens de téléchargement"""
        download_links = []
        
        # Rechercher le bouton de téléchargement audio mentionné
        audio_download = soup.find(id='player_download_sound_icon')
        if audio_download:
            href = audio_download.get('href')
            if href:
                download_links.append({
                    'type': 'audio',
                    'url': urljoin(self.base_url, href),
                    'xpath': '//*[@id="player_download_sound_icon"]'
                })
        
        # Rechercher d'autres liens de téléchargement
        for link in soup.find_all('a', href=True):
            href = link['href']
            text = link.get_text(strip=True).lower()
            
            if any(keyword in text for keyword in ['télécharger', 'download', 'audio', 'mp3']):
                download_links.append({
                    'type': 'download',
                    'url': urljoin(self.base_url, href),
                    'text': link.get_text(strip=True)
                })
        
        return download_links
    
    def find_javascript_player(self, soup):
        """Analyser le player JavaScript"""
        player_info = {}
        
        # Rechercher les scripts du player
        for script in soup.find_all('script'):
            if script.string and any(keyword in script.string.lower() 
                                   for keyword in ['player', 'video', 'audio']):
                
                # Extraire les configurations du player
                config_matches = re.findall(r'(\w+)\s*:\s*["\']([^"\']+)["\']', script.string)
                for key, value in config_matches:
                    if any(keyword in key.lower() for keyword in ['url', 'src', 'file']):
                        player_info[key] = value
        
        return player_info
    
    def test_ytdlp_compatibility(self, urls):
        """Tester si yt-dlp peut extraire ces URLs"""
        print("🧪 Test de compatibilité yt-dlp...")
        
        try:
            import yt_dlp
            
            for url in urls[:3]:  # Tester seulement les 3 premières
                print(f"🔍 Test de {url}")
                
                ydl_opts = {
                    'quiet': True,
                    'no_warnings': True,
                    'extract_flat': True  # Ne pas télécharger, juste extraire les infos
                }
                
                try:
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(url, download=False)
                        print(f"✅ yt-dlp compatible: {info.get('title', 'Sans titre')}")
                        
                except Exception as e:
                    print(f"❌ yt-dlp échec: {e}")
                    
        except ImportError:
            print("⚠️ yt-dlp non installé, skip du test")
    
    def save_results(self, results):
        """Sauvegarder les résultats d'exploration"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"exploration_results_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Résultats sauvegardés dans {filename}")
    
    def run_full_exploration(self):
        """Lancer l'exploration complète"""
        print("🚀 Démarrage de l'exploration du site AN...")
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'base_url': self.base_url,
            'homepage_links': [],
            'video_metadata': [],
            'patterns_discovered': []
        }
        
        # Explorer la page d'accueil
        homepage_links = self.explore_homepage()
        if homepage_links:
            results['homepage_links'] = homepage_links[:10]  # Garder les 10 premiers
            
            # Analyser quelques pages de vidéos
            for link in homepage_links[:3]:
                metadata = self.analyze_video_page(link['url'])
                if metadata:
                    results['video_metadata'].append(metadata)
            
            # Tester yt-dlp sur les URLs découvertes
            video_urls = []
            for metadata in results['video_metadata']:
                video_urls.extend(metadata.get('video_urls', []))
            
            if video_urls:
                self.test_ytdlp_compatibility(video_urls)
        
        # Sauvegarder les résultats
        self.save_results(results)
        
        print("✅ Exploration terminée!")
        return results

if __name__ == "__main__":
    explorer = ANSiteExplorer()
    results = explorer.run_full_exploration()

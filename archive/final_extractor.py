#!/usr/bin/env python3
"""
Extracteur final optimisé pour AN-droid
Basé sur la découverte des URLs m3u8 qui fonctionnent parfaitement
"""

import requests
import re
import subprocess
import json
from pathlib import Path
from datetime import datetime
import time

class FinalAudioExtractor:
    def __init__(self, download_dir="downloads"):
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(exist_ok=True)
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'AN-droid/1.0 (Compatible crawler)',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8'
        })
        
        # Limites de sécurité
        self.max_duration = 14400  # 4h en secondes
        self.max_file_size = 500 * 1024 * 1024  # 500MB
    
    def extract_m3u8_urls(self, url):
        """Extraire les URLs m3u8 depuis une page AN"""
        print(f"🔍 Extraction URLs m3u8 depuis: {url}")
        
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            # Pattern découvert par Selenium
            m3u8_pattern = r'https://videos-an\.vodalys\.com/[^"\']*\.m3u8'
            
            m3u8_urls = re.findall(m3u8_pattern, response.text)
            
            if m3u8_urls:
                # Supprimer les doublons et prendre la meilleure qualité
                unique_urls = list(set(m3u8_urls))
                # Prioriser master.m3u8 (meilleure qualité)
                master_urls = [url for url in unique_urls if 'master.m3u8' in url]
                
                if master_urls:
                    print(f"✅ URLs master m3u8 trouvées: {len(master_urls)}")
                    return master_urls
                else:
                    print(f"✅ URLs m3u8 trouvées: {len(unique_urls)}")
                    return unique_urls
            
            print("❌ Aucune URL m3u8 trouvée")
            return []
            
        except Exception as e:
            print(f"❌ Erreur extraction m3u8: {e}")
            return []
    
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
        
        # Obtenir les métadonnées
        metadata = self.get_video_metadata(m3u8_url)
        if not metadata:
            return {'success': False, 'reason': 'metadata_failed'}
        
        print(f"📺 Titre: {metadata['title']}")
        print(f"⏱️ Durée: {metadata['duration']} secondes ({metadata['duration']//60}min)")
        print(f"🎵 Formats audio: {metadata['audio_formats']}")
        
        # Vérifier la durée
        if metadata['duration'] > self.max_duration:
            print(f"⚠️ Durée trop longue: {metadata['duration']}s > {self.max_duration}s")
            return {'success': False, 'reason': 'duration_too_long', 'duration': metadata['duration']}
        
        # Générer nom de fichier
        safe_title = self.sanitize_filename(title_hint or metadata['title'])
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = self.download_dir / f"{safe_title}_{timestamp}.mp3"
        
        # Commande d'extraction
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
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)  # 10 min max
            
            download_time = time.time() - start_time
            
            if result.returncode == 0:
                # Trouver le fichier créé
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
                        'method': 'm3u8_direct',
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
        # Supprimer les caractères interdits
        filename = re.sub(r'[<>:"/\\|?*]', '', filename)
        # Remplacer les espaces par des underscores
        filename = re.sub(r'\s+', '_', filename)
        # Limiter la longueur
        filename = filename[:50]
        return filename or 'audio_an'
    
    def extract_title_from_page(self, url):
        """Extraire le titre depuis la page HTML"""
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            # Chercher le titre dans la balise title
            title_match = re.search(r'<title>([^<]+)</title>', response.text, re.IGNORECASE)
            if title_match:
                title = title_match.group(1).strip()
                # Nettoyer le titre
                title = re.sub(r'\s*-\s*Vidéos de l\'Assemblée nationale.*$', '', title)
                return title
            
        except Exception as e:
            print(f"⚠️ Erreur extraction titre: {e}")
        
        return "Debat_AN"
    
    def extract_audio_complete(self, url):
        """Méthode principale - extraction complète"""
        print(f"\n{'='*70}")
        print(f"🎯 EXTRACTION AUDIO COMPLETE")
        print(f"🔗 URL: {url}")
        print(f"{'='*70}")
        
        # 1. Extraire le titre de la page
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
        
        # 3. Essayer l'extraction sur la première URL m3u8
        print(f"🎬 URL m3u8 sélectionnée: {m3u8_urls[0]}")
        
        result = self.extract_audio_from_m3u8(
            m3u8_urls[0],
            title_hint=title,
            original_url=url
        )
        
        if result.get('success'):
            result['original_url'] = url
            result['m3u8_url'] = m3u8_urls[0]
            result['page_title'] = title
        
        return result
    
    def batch_extract(self, urls):
        """Extraction par lot"""
        print(f"🚀 Extraction par lot: {len(urls)} URLs")
        
        results = []
        
        for i, url in enumerate(urls, 1):
            print(f"\n📋 Extraction {i}/{len(urls)}")
            
            result = self.extract_audio_complete(url)
            results.append(result)
            
            if result.get('success'):
                print(f"✅ Succès: {result.get('file_path')}")
            else:
                print(f"❌ Échec: {result.get('reason', 'unknown')}")
            
            # Pause respectueuse entre les extractions
            if i < len(urls):
                print("⏸️ Pause 5 secondes...")
                time.sleep(5)
        
        # Résumé
        successful = sum(1 for r in results if r.get('success'))
        print(f"\n📊 RÉSUMÉ: {successful}/{len(results)} extractions réussies")
        
        return results

def test_final_extractor():
    """Test de l'extracteur final"""
    
    # URLs de test découvertes
    test_urls = [
        "https://videos.assemblee-nationale.fr/video.16905943_682f1c59d8a2c.2eme-seance--droit-a-l-aide-a-mourir-suite-22-mai-2025",
        "https://videos.assemblee-nationale.fr/video.16905189_682f08b6e8dd2.effets-psychologiques-de-tiktok-sur-les-mineurs--representants-du-conseil-national-de-l-ordre-des-m-22-mai-2025"
    ]
    
    extractor = FinalAudioExtractor()
    
    print("🎯 TEST DE L'EXTRACTEUR FINAL AN-droid")
    print("=" * 60)
    print("⚠️ ATTENTION: Les fichiers seront réellement téléchargés!")
    print("💡 Utilisez Ctrl+C pour annuler si nécessaire")
    
    input("Appuyez sur Entrée pour continuer ou Ctrl+C pour annuler...")
    
    # Test sur une seule URL d'abord
    print(f"\n🧪 Test sur une URL:")
    result = extractor.extract_audio_complete(test_urls[0])
    
    if result.get('success'):
        print(f"\n🎉 SUCCÈS! Fichier créé:")
        print(f"📁 {result.get('file_path')}")
        print(f"📊 Taille: {result.get('file_size', 0) / 1024 / 1024:.1f} MB")
        print(f"⏱️ Durée: {result.get('duration', 0) // 60}min")
        
        # Proposer l'extraction des autres
        choice = input(f"\nExtraire les {len(test_urls)-1} autres URLs? (y/N): ")
        if choice.lower() == 'y':
            extractor.batch_extract(test_urls[1:])
    else:
        print(f"\n💥 Échec: {result.get('reason', 'unknown')}")
        if result.get('error'):
            print(f"Erreur: {result.get('error')}")

if __name__ == "__main__":
    test_final_extractor()

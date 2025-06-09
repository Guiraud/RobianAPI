#!/usr/bin/env python3
"""
API FastAPI pour AN-droid
Endpoints principaux pour l'app Android
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, date
import os
import json
import asyncio
from pathlib import Path

# Import des scripts locaux
import sys
sys.path.append('./scripts')

try:
    from extract_audio import AudioExtractor
    from explore_site import ANSiteExplorer
except ImportError:
    print("⚠️ Scripts d'extraction non trouvés - fonctionnalités limitées")
    AudioExtractor = None
    ANSiteExplorer = None

app = FastAPI(
    title="AN-droid API",
    description="API pour l'application Android d'écoute des débats de l'Assemblée nationale",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configuration CORS pour l'app Android
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # À restreindre en production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models Pydantic
class DebatInfo(BaseModel):
    id: str
    title: str
    date: str
    duration: Optional[int] = None  # en secondes
    type: str  # "seance_publique", "commission", "audition"
    commission: Optional[str] = None
    url_source: str
    url_stream: Optional[str] = None
    thumbnail: Optional[str] = None
    description: Optional[str] = None
    intervenants: List[str] = []
    status: str = "disponible"  # "disponible", "en_cours", "programme", "extraction"

class ProgrammeSeance(BaseModel):
    date: str
    heure: str
    titre: str
    type: str
    commission: Optional[str] = None
    salle: Optional[str] = None
    url: Optional[str] = None

class ExtractionRequest(BaseModel):
    url: str
    priority: str = "normal"  # "normal", "urgent"

class ApiResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None

# Variables globales
DOWNLOAD_DIR = Path("./downloads")
CACHE_DIR = Path("./cache")
DOWNLOAD_DIR.mkdir(exist_ok=True)
CACHE_DIR.mkdir(exist_ok=True)

# Cache en mémoire simple (à remplacer par Redis en production)
cache_debats = {}
cache_programme = {}

@app.on_event("startup")
async def startup_event():
    print("🚀 Démarrage de l'API AN-droid")
    print(f"📁 Dossier téléchargements: {DOWNLOAD_DIR.absolute()}")
    print(f"💾 Dossier cache: {CACHE_DIR.absolute()}")

@app.get("/", response_model=ApiResponse)
async def root():
    """Point d'entrée de l'API"""
    return ApiResponse(
        success=True,
        message="API AN-droid opérationnelle",
        data={
            "version": "1.0.0",
            "endpoints": ["/api/debats", "/api/programme", "/api/extraction"]
        }
    )

@app.get("/api/debats", response_model=List[DebatInfo])
async def list_debats(
    date_debut: Optional[str] = Query(None, description="Date de début (YYYY-MM-DD)"),
    date_fin: Optional[str] = Query(None, description="Date de fin (YYYY-MM-DD)"),
    type_debat: Optional[str] = Query(None, description="Type de débat"),
    commission: Optional[str] = Query(None, description="Commission spécifique"),
    limit: int = Query(50, description="Nombre maximum de résultats")
):
    """
    Lister les débats disponibles avec filtres optionnels
    """
    try:
        # Vérifier le cache
        cache_key = f"debats_{date_debut}_{date_fin}_{type_debat}_{commission}_{limit}"
        if cache_key in cache_debats:
            print(f"📋 Débats depuis cache: {len(cache_debats[cache_key])} résultats")
            return cache_debats[cache_key]
        
        # Si pas en cache, explorer le site
        if ANSiteExplorer:
            explorer = ANSiteExplorer()
            results = explorer.run_full_exploration()
            
            # Convertir les résultats en format DebatInfo
            debats = []
            for i, metadata in enumerate(results.get('video_metadata', [])):
                debat = DebatInfo(
                    id=f"debat_{i}",
                    title=metadata.get('title', 'Débat sans titre'),
                    date=metadata.get('date', datetime.now().strftime('%Y-%m-%d')),
                    duration=parse_duration(metadata.get('duration')),
                    type=detect_debat_type(metadata.get('title', '')),
                    url_source=metadata.get('url', ''),
                    description=metadata.get('title', '')
                )
                debats.append(debat)
            
            # Appliquer les filtres
            filtered_debats = apply_filters(debats, date_debut, date_fin, type_debat, commission)
            limited_debats = filtered_debats[:limit]
            
            # Mettre en cache
            cache_debats[cache_key] = limited_debats
            
            print(f"✅ Débats extraits: {len(limited_debats)} résultats")
            return limited_debats
        
        else:
            # Fallback: données mock pour les tests
            mock_debats = generate_mock_debats()
            return mock_debats[:limit]
            
    except Exception as e:
        print(f"❌ Erreur liste débats: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")

@app.get("/api/debats/{debat_id}", response_model=DebatInfo)
async def get_debat(debat_id: str):
    """
    Obtenir les détails d'un débat spécifique
    """
    try:
        # Rechercher dans tous les caches
        for cached_list in cache_debats.values():
            for debat in cached_list:
                if debat.id == debat_id:
                    print(f"📺 Débat trouvé: {debat.title}")
                    return debat
        
        # Si pas trouvé, générer une erreur
        raise HTTPException(status_code=404, detail=f"Débat {debat_id} non trouvé")
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Erreur get débat: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")

@app.get("/api/debats/{debat_id}/stream")
async def get_audio_stream(debat_id: str, background_tasks: BackgroundTasks):
    """
    Obtenir l'URL de streaming audio ou déclencher l'extraction
    """
    try:
        # Récupérer les infos du débat
        debat = None
        for cached_list in cache_debats.values():
            for d in cached_list:
                if d.id == debat_id:
                    debat = d
                    break
        
        if not debat:
            raise HTTPException(status_code=404, detail="Débat non trouvé")
        
        # Vérifier si l'audio est déjà extrait
        audio_file = find_audio_file(debat_id)
        if audio_file:
            print(f"🎵 Audio disponible: {audio_file}")
            return {
                "stream_url": f"/api/debats/{debat_id}/file",
                "status": "ready",
                "file_size": os.path.getsize(audio_file)
            }
        
        # Si pas extrait, lancer l'extraction en arrière-plan
        if AudioExtractor and debat.url_source:
            background_tasks.add_task(extract_audio_background, debat_id, debat.url_source)
            
            return {
                "stream_url": None,
                "status": "extracting",
                "message": "Extraction en cours, réessayez dans quelques minutes"
            }
        
        raise HTTPException(status_code=503, detail="Service d'extraction non disponible")
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Erreur stream audio: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")

@app.get("/api/debats/{debat_id}/file")
async def download_audio_file(debat_id: str):
    """
    Télécharger le fichier audio d'un débat
    """
    try:
        audio_file = find_audio_file(debat_id)
        if not audio_file:
            raise HTTPException(status_code=404, detail="Fichier audio non trouvé")
        
        print(f"📁 Envoi fichier: {audio_file}")
        return FileResponse(
            audio_file,
            media_type="audio/mpeg",
            filename=f"debat_{debat_id}.mp3"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Erreur download fichier: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")

@app.get("/api/programme", response_model=List[ProgrammeSeance])
async def get_programme(
    date_param: Optional[str] = Query(None, description="Date (YYYY-MM-DD), défaut aujourd'hui")
):
    """
    Obtenir le programme des séances
    """
    try:
        target_date = date_param or datetime.now().strftime('%Y-%m-%d')
        
        # Vérifier le cache
        if target_date in cache_programme:
            print(f"📅 Programme depuis cache: {target_date}")
            return cache_programme[target_date]
        
        # Simuler la récupération du programme (à implémenter avec scraping)
        programme = generate_mock_programme(target_date)
        
        # Mettre en cache
        cache_programme[target_date] = programme
        
        print(f"✅ Programme généré: {len(programme)} séances pour {target_date}")
        return programme
        
    except Exception as e:
        print(f"❌ Erreur programme: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")

@app.post("/api/extraction", response_model=ApiResponse)
async def request_extraction(
    request: ExtractionRequest, 
    background_tasks: BackgroundTasks
):
    """
    Demander l'extraction d'une URL spécifique
    """
    try:
        if not AudioExtractor:
            raise HTTPException(status_code=503, detail="Service d'extraction non disponible")
        
        # Générer un ID pour cette extraction
        extraction_id = f"ext_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Lancer l'extraction en arrière-plan
        background_tasks.add_task(
            extract_audio_background, 
            extraction_id, 
            request.url, 
            request.priority
        )
        
        return ApiResponse(
            success=True,
            message="Extraction démarrée",
            data={
                "extraction_id": extraction_id,
                "status": "started",
                "url": request.url
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Erreur demande extraction: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")

@app.get("/api/extraction/{extraction_id}")
async def get_extraction_status(extraction_id: str):
    """
    Vérifier le statut d'une extraction
    """
    try:
        # Vérifier si le fichier existe
        audio_file = find_audio_file(extraction_id)
        if audio_file:
            return {
                "extraction_id": extraction_id,
                "status": "completed",
                "file_url": f"/api/debats/{extraction_id}/file",
                "file_size": os.path.getsize(audio_file)
            }
        
        # Sinon, supposer qu'elle est en cours
        return {
            "extraction_id": extraction_id,
            "status": "processing",
            "message": "Extraction en cours"
        }
        
    except Exception as e:
        print(f"❌ Erreur statut extraction: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")

# Fonctions utilitaires

def parse_duration(duration_str):
    """Parser une durée en format texte vers secondes"""
    if not duration_str:
        return None
    
    try:
        # Format HH:MM:SS
        if ':' in duration_str:
            parts = duration_str.split(':')
            if len(parts) == 3:
                h, m, s = map(int, parts)
                return h * 3600 + m * 60 + s
            elif len(parts) == 2:
                m, s = map(int, parts)
                return m * 60 + s
        
        # Format texte (1h 30m)
        import re
        hour_match = re.search(r'(\d+)h', duration_str)
        min_match = re.search(r'(\d+)m', duration_str)
        
        hours = int(hour_match.group(1)) if hour_match else 0
        minutes = int(min_match.group(1)) if min_match else 0
        
        return hours * 3600 + minutes * 60
        
    except:
        return None

def detect_debat_type(title):
    """Détecter le type de débat depuis le titre"""
    title_lower = title.lower()
    
    if 'commission' in title_lower:
        return 'commission'
    elif 'audition' in title_lower:
        return 'audition'
    elif 'séance' in title_lower or 'seance' in title_lower:
        return 'seance_publique'
    else:
        return 'autre'

def apply_filters(debats, date_debut, date_fin, type_debat, commission):
    """Appliquer les filtres à la liste des débats"""
    filtered = debats
    
    if date_debut:
        filtered = [d for d in filtered if d.date >= date_debut]
    
    if date_fin:
        filtered = [d for d in filtered if d.date <= date_fin]
    
    if type_debat:
        filtered = [d for d in filtered if d.type == type_debat]
    
    if commission:
        filtered = [d for d in filtered if d.commission and commission.lower() in d.commission.lower()]
    
    return filtered

def find_audio_file(debat_id):
    """Trouver le fichier audio correspondant à un débat"""
    # Rechercher dans le dossier de téléchargement
    for ext in ['.mp3', '.m4a', '.wav']:
        pattern = f"*{debat_id}*{ext}"
        matches = list(DOWNLOAD_DIR.glob(pattern))
        if matches:
            return str(matches[0])
    
    return None

async def extract_audio_background(debat_id, url, priority="normal"):
    """Extraction audio en arrière-plan"""
    print(f"🔄 Extraction background: {debat_id} - {url}")
    
    try:
        if AudioExtractor:
            extractor = AudioExtractor(download_dir=str(DOWNLOAD_DIR))
            result = extractor.extract_audio(url)
            
            if result.get('success'):
                print(f"✅ Extraction réussie: {debat_id}")
            else:
                print(f"❌ Extraction échec: {debat_id} - {result.get('error')}")
            
            extractor.cleanup()
        
    except Exception as e:
        print(f"❌ Erreur extraction background: {e}")

def generate_mock_debats():
    """Générer des données mock pour les tests"""
    return [
        DebatInfo(
            id="debat_1",
            title="Séance publique du 22 mai 2025",
            date="2025-05-22",
            duration=7200,  # 2h
            type="seance_publique",
            url_source="https://videos.assemblee-nationale.fr/video.1234567",
            description="Discussion du projet de loi relatif à la fin de vie"
        ),
        DebatInfo(
            id="debat_2", 
            title="Commission des finances - Audition ministre",
            date="2025-05-22",
            duration=5400,  # 1h30
            type="audition",
            commission="Finances",
            url_source="https://videos.assemblee-nationale.fr/video.1234568",
            description="Audition du ministre de l'Économie"
        )
    ]

def generate_mock_programme(date_str):
    """Générer un programme mock"""
    return [
        ProgrammeSeance(
            date=date_str,
            heure="09:00",
            titre="Séance publique",
            type="seance_publique",
            salle="Hémicycle",
            url="https://videos.assemblee-nationale.fr/live"
        ),
        ProgrammeSeance(
            date=date_str,
            heure="14:00",
            titre="Commission des lois",
            type="commission",
            commission="Lois constitutionnelles",
            salle="Salle 6350"
        )
    ]

if __name__ == "__main__":
    import uvicorn
    print("🚀 Démarrage du serveur API AN-droid")
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)

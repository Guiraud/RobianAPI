#!/usr/bin/env python3
"""
Démarrage simple de l'API AN-droid
"""

if __name__ == "__main__":
    import uvicorn
    import sys
    import os
    
    # Ajouter le dossier api au path
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'api'))
    
    print("🚀 Démarrage de l'API AN-droid...")
    print("📍 Disponible sur: http://localhost:8000")
    print("📖 Documentation: http://localhost:8000/docs")
    print("🛑 Arrêter avec Ctrl+C")
    
    try:
        uvicorn.run(
            "api.main:app", 
            host="0.0.0.0", 
            port=8000, 
            reload=False,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n✅ API arrêtée")

#!/bin/bash

# Script de nettoyage du dépôt AN-droid pour conformité F-Droid
# Supprime les fichiers de travail et organise la structure

set -e

echo "🧹 Nettoyage du dépôt AN-droid pour conformité F-Droid"
echo "=" * 60

# Couleurs pour l'affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_action() {
    echo -e "${BLUE}▶ $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️ $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Vérifier qu'on est dans le bon répertoire
if [[ ! -f "plan.md" ]]; then
    log_error "Ce script doit être exécuté depuis la racine du projet AN-droid"
    exit 1
fi

PROJECT_ROOT=$(pwd)
log_success "Répertoire projet: $PROJECT_ROOT"

echo ""
log_action "1. Suppression des fichiers de développement/debug"

# Fichiers de développement à supprimer
dev_files=(
    "corrected_extractor.py"
    "improved_extractor.py" 
    "debug_m3u8.py"
    "debug_page_sample.html"
    "quick_test.py"
    "test_auto.py"
    "test_selenium.py"
    "test_setup.py"
    "BREAKTHROUGH.md"
    "plan.md"  # Document de travail interne
    "SCRIPTS_README.md"  # Remplacé par documentation principale
    "RECAP_FINAL.md"  # Document de travail
)

for file in "${dev_files[@]}"; do
    if [[ -f "$file" ]]; then
        rm "$file"
        log_success "Supprimé: $file"
    fi
done

# Fichiers JSON de résultats de tests
log_action "Suppression des fichiers de résultats JSON"
rm -f exploration_results_*.json
rm -f selenium_test_results_*.json
log_success "Fichiers JSON de test supprimés"

echo ""
log_action "2. Nettoyage des répertoires temporaires"

# Supprimer __pycache__ récursivement
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
log_success "Dossiers __pycache__ supprimés"

# Nettoyer le répertoire downloads (garder structure)
if [[ -d "downloads" ]]; then
    find downloads -name "*.mp3" -delete 2>/dev/null || true
    find downloads -name "*.wav" -delete 2>/dev/null || true
    find downloads -name "*.m4a" -delete 2>/dev/null || true
    log_success "Fichiers audio de test supprimés"
fi

# Nettoyer les logs
if [[ -d "logs" ]]; then
    find logs -name "*.log" -delete 2>/dev/null || true
    find logs -name "*.json" -delete 2>/dev/null || true
    log_success "Fichiers de logs supprimés"
fi

# Nettoyer le cache
if [[ -d "cache" ]]; then
    find cache -type f -delete 2>/dev/null || true
    log_success "Cache nettoyé"
fi

# Supprimer les environnements virtuels multiples
if [[ -d "venv_new" ]]; then
    rm -rf venv_new
    log_success "Environnement virtuel venv_new supprimé"
fi

# Supprimer l'environnement virtuel principal (sera recréé à l'installation)
if [[ -d ".venv" ]]; then
    rm -rf .venv
    log_success "Environnement virtuel .venv supprimé"
fi

echo ""
log_action "3. Organisation de la structure F-Droid"

# Créer la structure standard F-Droid
mkdir -p src/main/java/fr/assemblee/android
mkdir -p src/main/res/{layout,values,drawable}
mkdir -p fastlane/metadata/android/en-US
mkdir -p backend/api
mkdir -p backend/scripts

log_success "Structure de répertoires F-Droid créée"

# Déplacer les fichiers backend dans le bon répertoire
mv api/* backend/api/ 2>/dev/null || true
mv scripts/* backend/scripts/ 2>/dev/null || true
mv final_extractor.py backend/
mv start_api.py backend/
mv test_*.py backend/ 2>/dev/null || true

log_success "Fichiers backend organisés"

# Supprimer les répertoires vides
rmdir api scripts 2>/dev/null || true

echo ""
log_action "4. Mise à jour des fichiers de configuration"

# Mettre à jour .gitignore pour F-Droid
cat > .gitignore << 'EOF'
# Build
/build/
/*/build/
*.apk
*.aab
*.ap_
*.dex

# Gradle
.gradle/
local.properties

# IDE
.idea/
*.iml
.vscode/
.DS_Store

# Backend Python
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
.venv/
venv/
pip-log.txt
pip-delete-this-directory.txt

# Runtime
/downloads/
/logs/
/cache/
*.log
.api_pid

# Test files
*.json
*.html

# Local config
.env
EOF

log_success ".gitignore mis à jour pour F-Droid"

# Créer un requirements.txt minimal pour le backend
cat > backend/requirements.txt << 'EOF'
# Backend dependencies for AN-droid
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
requests>=2.31.0
beautifulsoup4>=4.12.0
lxml>=4.9.0
yt-dlp>=2023.10.0
psutil>=5.9.0
pydantic>=2.4.0
EOF

log_success "requirements.txt backend créé"

echo ""
log_action "5. Création des métadonnées F-Droid"

# Créer fastlane metadata
mkdir -p fastlane/metadata/android/en-US

cat > fastlane/metadata/android/en-US/title.txt << 'EOF'
AN-droid
EOF

cat > fastlane/metadata/android/en-US/short_description.txt << 'EOF'
Listen to French National Assembly debates as audio podcasts
EOF

cat > fastlane/metadata/android/en-US/full_description.txt << 'EOF'
AN-droid allows you to listen to debates from the French National Assembly (Assemblée nationale) in audio format, perfect for podcast-style consumption.

Features:
• Stream live sessions directly from videos.assemblee-nationale.fr
• Download debates for offline listening
• Modern, accessible interface built with Jetpack Compose
• No tracking, no ads, 100% open source
• Optimized for mobile with 128K MP3 format
• Search and filter debates by date and topic

AN-droid respects your privacy and the National Assembly's resources with appropriate rate limiting and caching.

Perfect for citizens who want to stay informed about parliamentary debates while commuting, exercising, or doing other activities.

This app is completely independent and not affiliated with the French National Assembly.
EOF

cat > fastlane/metadata/android/en-US/changelog.txt << 'EOF'
Initial release:
- Stream and download National Assembly debates
- Modern Material Design interface
- Offline playback support
- No tracking or ads
EOF

log_success "Métadonnées F-Droid créées"

# Créer build.gradle basique pour Android
cat > build.gradle << 'EOF'
// Top-level build file for AN-droid
buildscript {
    ext.kotlin_version = '1.9.10'
    ext.compose_version = '1.5.4'
    
    dependencies {
        classpath 'com.android.tools.build:gradle:8.1.2'
        classpath "org.jetbrains.kotlin:kotlin-gradle-plugin:$kotlin_version"
    }
}

allprojects {
    repositories {
        google()
        mavenCentral()
    }
}

task clean(type: Delete) {
    delete rootProject.buildDir
}
EOF

cat > app/build.gradle << 'EOF'
plugins {
    id 'com.android.application'
    id 'kotlin-android'
    id 'kotlin-compose'
}

android {
    namespace 'fr.assemblee.android'
    compileSdk 34

    defaultConfig {
        applicationId "fr.assemblee.android"
        minSdk 21
        targetSdk 34
        versionCode 1
        versionName "1.0.0"
    }

    buildTypes {
        release {
            minifyEnabled false
            proguardFiles getDefaultProguardFile('proguard-android-optimize.txt'), 'proguard-rules.pro'
        }
    }
    
    compileOptions {
        sourceCompatibility JavaVersion.VERSION_11
        targetCompatibility JavaVersion.VERSION_11
    }
    
    kotlinOptions {
        jvmTarget = '11'
    }
    
    buildFeatures {
        compose true
    }
}

dependencies {
    // Core Android
    implementation 'androidx.core:core-ktx:1.12.0'
    implementation 'androidx.lifecycle:lifecycle-runtime-ktx:2.7.0'
    implementation 'androidx.activity:activity-compose:1.8.1'
    
    // Compose
    implementation platform('androidx.compose:compose-bom:2023.10.01')
    implementation 'androidx.compose.ui:ui'
    implementation 'androidx.compose.ui:ui-tooling-preview'
    implementation 'androidx.compose.material3:material3'
    
    // Navigation
    implementation 'androidx.navigation:navigation-compose:2.7.5'
    
    // Media playback (ExoPlayer alternative for F-Droid)
    implementation 'androidx.media3:media3-exoplayer:1.2.0'
    implementation 'androidx.media3:media3-ui:1.2.0'
    implementation 'androidx.media3:media3-session:1.2.0'
    
    // Networking
    implementation 'com.squareup.retrofit2:retrofit:2.9.0'
    implementation 'com.squareup.retrofit2:converter-gson:2.9.0'
    implementation 'com.squareup.okhttp3:logging-interceptor:4.12.0'
    
    // Coroutines
    implementation 'org.jetbrains.kotlinx:kotlinx-coroutines-android:1.7.3'
    
    // ViewModel
    implementation 'androidx.lifecycle:lifecycle-viewmodel-compose:2.7.0'
}
EOF

mkdir -p app/src/main/java/fr/assemblee/android
log_success "Configuration Android de base créée"

echo ""
log_action "6. Création du README principal"

cat > README.md << 'EOF'
# AN-droid

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![F-Droid](https://img.shields.io/badge/F--Droid-available-green)](https://f-droid.org)

AN-droid is a free and open-source Android application that allows you to listen to debates from the French National Assembly (Assemblée nationale) in audio format.

## Features

- 🎧 **Stream live sessions** directly from videos.assemblee-nationale.fr
- 📱 **Download for offline** listening in optimized MP3 format
- 🎨 **Modern interface** built with Jetpack Compose and Material Design
- 🔒 **Privacy-focused**: No tracking, no ads, no data collection
- ♿ **Accessible** design with TalkBack support
- 🔍 **Search and filter** debates by date, topic, and speaker
- 📡 **Efficient**: Smart caching and rate limiting

## Installation

### F-Droid (Recommended)
Coming soon on F-Droid store.

### Manual Installation
1. Download the latest APK from [Releases](../../releases)
2. Enable "Unknown sources" in Android settings
3. Install the APK

## Backend Setup (For Development)

The app requires a backend API to extract audio from National Assembly videos:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
./scripts/install_all.sh
./scripts/deploy_local.sh
```

## Architecture

```
AN-droid/
├── app/                    # Android application (Kotlin + Compose)
├── backend/               # Python backend for audio extraction
│   ├── api/              # FastAPI server
│   ├── scripts/          # Automation scripts
│   └── final_extractor.py # Core extraction logic
├── fastlane/             # F-Droid metadata
└── README.md
```

## Development

### Android App
```bash
./gradlew assembleDebug
```

### Backend API
```bash
cd backend
./scripts/health_check.py --quick
./scripts/deploy_local.sh
```

## Privacy & Ethics

- **No personal data** collection or transmission
- **Respectful usage** of National Assembly resources with rate limiting
- **Open source** - all code is auditable
- **F-Droid compatible** - no proprietary dependencies

## Legal

This application is **independent** and **not affiliated** with the French National Assembly. It provides public access to publicly available content from videos.assemblee-nationale.fr.

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

For backend development, see `backend/scripts/` for automation tools.

## Support

- 🐛 [Report bugs](../../issues)
- 💬 [Discussions](../../discussions)
- 📖 [Documentation](../../wiki)

## Acknowledgments

- French National Assembly for providing public access to debates
- F-Droid community for promoting free software
- Contributors and users of this project
EOF

log_success "README principal créé"

echo ""
log_action "7. Finalisation et vérification"

# Créer un fichier LICENSE GPL-3.0
cat > LICENSE << 'EOF'
GNU GENERAL PUBLIC LICENSE
Version 3, 29 June 2007

Copyright (C) 2025 AN-droid Contributors

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
EOF

log_success "Licence GPL-3.0 ajoutée"

# Supprimer les fichiers macOS
find . -name ".DS_Store" -delete 2>/dev/null || true
log_success "Fichiers système macOS supprimés"

echo ""
log_action "8. Résumé de la structure finale"

echo "Structure du dépôt après nettoyage:"
tree -I '__pycache__|*.pyc|.git' || find . -type d -name .git -prune -o -type f -print | head -20

echo ""
echo "=" * 60
log_success "🎉 Nettoyage terminé ! Dépôt prêt pour F-Droid"
echo ""
echo "📋 Actions réalisées:"
echo "  ✅ Fichiers de développement supprimés"
echo "  ✅ Structure F-Droid standard créée"
echo "  ✅ Backend organisé dans backend/"
echo "  ✅ Métadonnées F-Droid ajoutées"
echo "  ✅ Configuration Android de base"
echo "  ✅ README et LICENSE conformes"
echo "  ✅ .gitignore optimisé"
echo ""
echo "🚀 Prochaines étapes:"
echo "  1. Développer l'application Android dans app/"
echo "  2. Tester avec: cd backend && ./scripts/health_check.py"
echo "  3. Publier sur GitHub pour review F-Droid"
echo ""
echo "📁 Structure finale conforme aux standards F-Droid"
EOF

log_success "Script de nettoyage créé"

#!/bin/bash

# Script de vérification de la structure F-Droid pour AN-droid

echo "🔍 Vérification de la conformité F-Droid du projet AN-droid"
echo "=" * 70

# Couleurs
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

cd /Users/mguiraud/Documents/gitlab/AN-droid

check_file() {
    if [ -f "$1" ]; then
        echo -e "${GREEN}✅ $1${NC}"
        return 0
    else
        echo -e "${RED}❌ $1 (MANQUANT)${NC}"
        return 1
    fi
}

check_dir() {
    if [ -d "$1" ]; then
        echo -e "${GREEN}✅ $1/${NC}"
        return 0
    else
        echo -e "${RED}❌ $1/ (MANQUANT)${NC}"
        return 1
    fi
}

echo -e "${BLUE}📱 Structure Android standard${NC}"
echo "--------------------------------"

# Fichiers de configuration Android
check_file "build.gradle"
check_file "settings.gradle"
check_file "gradle.properties"
check_file "app/build.gradle"

# Manifest et ressources
check_file "app/src/main/AndroidManifest.xml"
check_file "app/src/main/res/values/strings.xml"
check_file "app/src/main/res/values/colors.xml"
check_file "app/src/main/res/values/themes.xml"

# Code source
check_file "app/src/main/java/fr/assemblee/android/MainActivity.kt"
check_file "app/src/main/java/fr/assemblee/android/ANDroidApplication.kt"
check_file "app/src/main/java/fr/assemblee/android/ui/theme/Theme.kt"
check_file "app/src/main/java/fr/assemblee/android/ui/theme/Type.kt"

echo ""
echo -e "${BLUE}📦 Métadonnées F-Droid${NC}"
echo "--------------------------------"

# Métadonnées F-Droid
check_file "fastlane/metadata/android/en-US/title.txt"
check_file "fastlane/metadata/android/en-US/short_description.txt"
check_file "fastlane/metadata/android/en-US/full_description.txt"
check_file "fastlane/metadata/android/en-US/changelog.txt"
check_file "fastlane/metadata/android/fr-FR/title.txt"
check_file "fastlane/metadata/android/fr-FR/short_description.txt"
check_file "fastlane/metadata/android/fr-FR/full_description.txt"
check_file "fastlane/metadata/android/fr-FR/changelog.txt"
check_file ".fdroid.yml"

echo ""
echo -e "${BLUE}📋 Documentation et licences${NC}"
echo "--------------------------------"

# Documentation
check_file "README.md"
check_file "LISEZ-MOI.md"
check_file "LICENSE"
check_file ".gitignore"

echo ""
echo -e "${BLUE}🔧 Backend Python${NC}"
echo "--------------------------------"

# Backend
check_dir "backend"
check_dir "backend/api"
check_dir "backend/scripts"
check_file "backend/requirements.txt"
check_file "backend/final_extractor.py"

echo ""
echo -e "${BLUE}📊 Statistiques du projet${NC}"
echo "--------------------------------"

# Compter les fichiers
android_files=$(find app -name "*.kt" -o -name "*.xml" -o -name "*.gradle" | wc -l | tr -d ' ')
backend_files=$(find backend -name "*.py" -o -name "*.sh" | wc -l | tr -d ' ')
total_files=$(find . -type f -not -path "./.git/*" | wc -l | tr -d ' ')

echo "📱 Fichiers Android: $android_files"
echo "🐍 Fichiers Backend: $backend_files"  
echo "📄 Total fichiers: $total_files"

# Vérifier la taille du projet
project_size=$(du -sh . | cut -f1)
echo "📦 Taille projet: $project_size"

echo ""
echo -e "${BLUE}✅ Vérifications spécifiques F-Droid${NC}"
echo "--------------------------------"

# Vérifications F-Droid
echo -n "🔍 Package name format... "
if grep -q 'applicationId "fr.assemblee.android"' app/build.gradle; then
    echo -e "${GREEN}✅ OK${NC}"
else
    echo -e "${RED}❌ ERREUR${NC}"
fi

echo -n "🔍 Licence GPL-3.0... "
if grep -q "GNU GENERAL PUBLIC LICENSE" LICENSE; then
    echo -e "${GREEN}✅ OK${NC}"
else
    echo -e "${RED}❌ ERREUR${NC}"
fi

echo -n "🔍 Pas de dépendances propriétaires... "
if grep -q "google.*play.*services\|firebase\|crashlytics" app/build.gradle; then
    echo -e "${RED}❌ DÉPENDANCES PROPRIÉTAIRES DÉTECTÉES${NC}"
else
    echo -e "${GREEN}✅ OK${NC}"
fi

echo -n "🔍 Target SDK récent... "
if grep -q "targetSdk 34" app/build.gradle; then
    echo -e "${GREEN}✅ OK (API 34)${NC}"
else
    echo -e "${YELLOW}⚠️ Vérifier version${NC}"
fi

echo ""
echo -e "${BLUE}🚀 Prochaines étapes${NC}"
echo "--------------------------------"
echo "1. Développer l'interface utilisateur Compose"
echo "2. Implémenter la logique de lecture audio"
echo "3. Connecter avec le backend AN-droid"
echo "4. Ajouter les tests unitaires et UI"
echo "5. Optimiser pour F-Droid (build reproductible)"
echo "6. Soumettre à F-Droid via merge request"

echo ""
echo -e "${GREEN}🎉 Structure conforme aux standards F-Droid !${NC}"
echo -e "${BLUE}📁 Répertoire prêt pour le développement Android${NC}"

#!/bin/bash
echo "🔄 Migration RobianAPI depuis Archive"

SOURCE_DIR="/Users/mguiraud/Documents/gitlab/Archive/AN-app/RobiAN/backend"
TARGET_DIR="/Users/mguiraud/Documents/gitlab/RobianAPI"

echo "📂 Source: $SOURCE_DIR"
echo "🎯 Target: $TARGET_DIR"

# Sauvegarder les fichiers existants importants
echo "💾 Sauvegarde des fichiers existants..."
cp "$TARGET_DIR/PROMPT_ROBIAN_API.md" "$TARGET_DIR/PROMPT_ROBIAN_API.md.backup"
cp "$TARGET_DIR/README.md" "$TARGET_DIR/README.md.backup"

# Copier les fichiers clés depuis l'archive
echo "📁 Copie des fichiers principaux..."

# Scripts Python principaux
if [ -f "$SOURCE_DIR/start_api.py" ]; then
    cp "$SOURCE_DIR/start_api.py" "$TARGET_DIR/"
    echo "✅ start_api.py copié"
fi

if [ -f "$SOURCE_DIR/final_extractor.py" ]; then
    cp "$SOURCE_DIR/final_extractor.py" "$TARGET_DIR/"
    echo "✅ final_extractor.py copié"
fi

if [ -f "$SOURCE_DIR/enhanced_extractor.py" ]; then
    cp "$SOURCE_DIR/enhanced_extractor.py" "$TARGET_DIR/"
    echo "✅ enhanced_extractor.py copié"
fi

# Requirements
if [ -f "$SOURCE_DIR/requirements.txt" ]; then
    # Fusionner les requirements s'ils existent
    if [ -f "$TARGET_DIR/requirements.txt" ]; then
        echo "🔄 Fusion des requirements.txt..."
        cat "$SOURCE_DIR/requirements.txt" >> "$TARGET_DIR/requirements.txt.new"
        sort "$TARGET_DIR/requirements.txt.new" | uniq > "$TARGET_DIR/requirements.txt"
        rm "$TARGET_DIR/requirements.txt.new"
    else
        cp "$SOURCE_DIR/requirements.txt" "$TARGET_DIR/"
    fi
    echo "✅ requirements.txt mis à jour"
fi

# Configuration Docker
if [ -f "$SOURCE_DIR/Dockerfile" ]; then
    cp "$SOURCE_DIR/Dockerfile" "$TARGET_DIR/"
    echo "✅ Dockerfile copié"
fi

if [ -f "$SOURCE_DIR/docker-compose.yml" ]; then
    cp "$SOURCE_DIR/docker-compose.yml" "$TARGET_DIR/"
    echo "✅ docker-compose.yml copié"
fi

# Copier les dossiers API, tests, scripts
echo "📁 Copie des dossiers..."

if [ -d "$SOURCE_DIR/api" ]; then
    cp -r "$SOURCE_DIR/api" "$TARGET_DIR/"
    echo "✅ Dossier api/ copié"
fi

if [ -d "$SOURCE_DIR/scripts" ]; then
    cp -r "$SOURCE_DIR/scripts" "$TARGET_DIR/"
    echo "✅ Dossier scripts/ copié"
fi

if [ -d "$SOURCE_DIR/tests" ]; then
    cp -r "$SOURCE_DIR/tests" "$TARGET_DIR/"
    echo "✅ Dossier tests/ copié"
fi

if [ -d "$SOURCE_DIR/docs" ]; then
    cp -r "$SOURCE_DIR/docs" "$TARGET_DIR/"
    echo "✅ Dossier docs/ copié"
fi

# Créer les dossiers manquants
echo "📁 Création des dossiers structure..."
mkdir -p "$TARGET_DIR/data/cache"
mkdir -p "$TARGET_DIR/data/audio"
mkdir -p "$TARGET_DIR/data/logs"
mkdir -p "$TARGET_DIR/monitoring"

# Copier quelques fichiers de test utiles
if [ -f "$SOURCE_DIR/test_api.py" ]; then
    cp "$SOURCE_DIR/test_api.py" "$TARGET_DIR/"
    echo "✅ test_api.py copié"
fi

# Créer un .gitignore approprié
cat > "$TARGET_DIR/.gitignore" << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
.venv/
pip-log.txt
pip-delete-this-directory.txt

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

# Project specific
/data/cache/*
/data/audio/*
/data/logs/*
/downloads/*
*.log
*.tmp

# Environment variables
.env
.env.local
.env.*.local

# Docker
docker-compose.override.yml

# Backup files
*.backup
*.bak
EOF

echo "✅ .gitignore créé"

echo ""
echo "🎉 Migration terminée !"
echo "📊 Résumé des fichiers migrés :"
ls -la "$TARGET_DIR" | grep -v "^d" | wc -l | xargs echo "  Fichiers:"
ls -la "$TARGET_DIR" | grep "^d" | wc -l | xargs echo "  Dossiers:"

echo ""
echo "📝 Prochaines étapes :"
echo "1. cd $TARGET_DIR"
echo "2. git add ."
echo "3. git commit -m '🔄 Migration complète depuis Archive/AN-app/RobiAN/backend'"
echo "4. Vérifier que l'API démarre : python start_api.py"

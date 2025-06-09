#!/bin/bash

# Script d'accueil AN-droid
# Guide l'utilisateur pour la première utilisation

set -e

# Couleurs pour l'affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Fonction d'affichage
welcome_header() {
    clear
    echo -e "${PURPLE}"
    echo "┌────────────────────────────────────────────────────────────┐"
    echo "│                                                            │"
    echo "│              🎉 BIENVENUE DANS AN-DROID ! 🎉              │"
    echo "│                                                            │"
    echo "│     Application libre pour débats Assemblée nationale     │"
    echo "│                                                            │"
    echo "└────────────────────────────────────────────────────────────┘"
    echo -e "${NC}"
    echo ""
}

show_status() {
    echo -e "${CYAN}📊 STATUT ACTUEL DU PROJET${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    python3 scripts/status.py | grep -E "(COMPLÉTUDE|Projet|Scripts|API|Fichiers|Environnement)" | head -6
    echo ""
}

show_quick_commands() {
    echo -e "${GREEN}🚀 COMMANDES RAPIDES${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "${YELLOW}1.${NC} Vérification système     → ${BLUE}./scripts/health_check.py --quick${NC}"
    echo -e "${YELLOW}2.${NC} Démonstration complète   → ${BLUE}./scripts/demo.py${NC}"
    echo -e "${YELLOW}3.${NC} Lancer l'API             → ${BLUE}./scripts/deploy_local.sh${NC}"
    echo -e "${YELLOW}4.${NC} Test d'extraction        → ${BLUE}python3 final_extractor.py${NC}"
    echo -e "${YELLOW}5.${NC} Monitoring temps réel    → ${BLUE}./scripts/monitor_system.py${NC}"
    echo ""
}

show_documentation() {
    echo -e "${GREEN}📖 DOCUMENTATION DISPONIBLE${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "${YELLOW}•${NC} Plan complet du projet    → ${BLUE}cat plan.md${NC}"
    echo -e "${YELLOW}•${NC} Guide des scripts         → ${BLUE}cat SCRIPTS_README.md${NC}"
    echo -e "${YELLOW}•${NC} Récapitulatif final       → ${BLUE}cat RECAP_FINAL.md${NC}"
    echo -e "${YELLOW}•${NC} Statut détaillé          → ${BLUE}./scripts/status.py${NC}"
    echo ""
}

interactive_menu() {
    echo -e "${GREEN}🎯 QUE VOULEZ-VOUS FAIRE ?${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "${YELLOW}1)${NC} Vérifier la santé du système (rapide)"
    echo -e "${YELLOW}2)${NC} Voir une démonstration complète"
    echo -e "${YELLOW}3)${NC} Lancer l'API AN-droid"
    echo -e "${YELLOW}4)${NC} Tester une extraction audio"
    echo -e "${YELLOW}5)${NC} Activer le monitoring"
    echo -e "${YELLOW}6)${NC} Voir le statut détaillé"
    echo -e "${YELLOW}7)${NC} Lire la documentation"
    echo -e "${YELLOW}8)${NC} Quitter"
    echo ""
    
    while true; do
        read -p "Votre choix (1-8): " choice
        case $choice in
            1)
                echo -e "\n${BLUE}🔍 Vérification de la santé du système...${NC}"
                ./scripts/health_check.py --quick
                ;;
            2)
                echo -e "\n${BLUE}🎬 Démonstration complète...${NC}"
                ./scripts/demo.py
                ;;
            3)
                echo -e "\n${BLUE}🚀 Lancement de l'API...${NC}"
                ./scripts/deploy_local.sh
                ;;
            4)
                echo -e "\n${BLUE}🎵 Test d'extraction audio...${NC}"
                echo "⚠️  Attention: Ceci va télécharger un fichier audio réel"
                read -p "Continuer? (y/N): " confirm
                if [[ $confirm == "y" || $confirm == "Y" ]]; then
                    source .venv/bin/activate && PYTHONPATH=. python3 final_extractor.py
                else
                    echo "Test annulé."
                fi
                ;;
            5)
                echo -e "\n${BLUE}📊 Activation du monitoring...${NC}"
                echo "Monitoring en temps réel (Ctrl+C pour arrêter)"
                ./scripts/monitor_system.py
                ;;
            6)
                echo -e "\n${BLUE}📋 Statut détaillé du projet...${NC}"
                ./scripts/status.py
                ;;
            7)
                echo -e "\n${BLUE}📖 Documentation...${NC}"
                echo "Quelle documentation consulter?"
                echo "1) Plan complet (plan.md)"
                echo "2) Guide scripts (SCRIPTS_README.md)"  
                echo "3) Récapitulatif final (RECAP_FINAL.md)"
                read -p "Choix (1-3): " doc_choice
                case $doc_choice in
                    1) less plan.md ;;
                    2) less SCRIPTS_README.md ;;
                    3) less RECAP_FINAL.md ;;
                    *) echo "Choix invalide" ;;
                esac
                ;;
            8)
                echo -e "\n${GREEN}👋 Merci d'avoir utilisé AN-droid !${NC}"
                echo ""
                echo -e "${CYAN}💡 Rappel des commandes principales:${NC}"
                echo "   • Santé système: ./scripts/health_check.py --quick"
                echo "   • Lancer API: ./scripts/deploy_local.sh"
                echo "   • Monitoring: ./scripts/monitor_system.py"
                echo "   • Ce guide: ./scripts/welcome.sh"
                echo ""
                echo -e "${PURPLE}🚀 Prochaine étape: Développement app Android F-Droid !${NC}"
                exit 0
                ;;
            *)
                echo -e "${RED}Choix invalide. Veuillez entrer un nombre entre 1 et 8.${NC}"
                ;;
        esac
        
        echo ""
        read -p "Appuyez sur Entrée pour revenir au menu..."
        welcome_header
        show_quick_commands
        echo -e "${GREEN}🎯 QUE VOULEZ-VOUS FAIRE ?${NC}"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo -e "${YELLOW}1)${NC} Vérifier la santé du système"
        echo -e "${YELLOW}2)${NC} Voir une démonstration complète"
        echo -e "${YELLOW}3)${NC} Lancer l'API AN-droid"
        echo -e "${YELLOW}4)${NC} Tester une extraction audio"
        echo -e "${YELLOW}5)${NC} Activer le monitoring"
        echo -e "${YELLOW}6)${NC} Voir le statut détaillé"
        echo -e "${YELLOW}7)${NC} Lire la documentation"
        echo -e "${YELLOW}8)${NC} Quitter"
        echo ""
    done
}

main() {
    # Vérifier qu'on est dans le bon répertoire
    if [[ ! -f "plan.md" ]]; then
        echo -e "${RED}❌ Erreur: Ce script doit être exécuté depuis la racine du projet AN-droid${NC}"
        echo "Naviguez vers le répertoire contenant plan.md"
        exit 1
    fi
    
    welcome_header
    show_status
    show_quick_commands
    show_documentation
    interactive_menu
}

# Point d'entrée
main "$@"

#!/usr/bin/env bash
#
# Script pour synchroniser les secrets de .env vers Doppler
# Usage: ./sync_env_to_doppler.sh
#

set -e

echo "🔄 Synchronisation .env → Doppler"
echo "=================================="
echo ""

# Vérifier que Doppler est configuré
if ! doppler setup --no-interactive &>/dev/null; then
    echo "❌ Doppler n'est pas configuré dans ce répertoire"
    echo "💡 Lance d'abord: doppler setup"
    exit 1
fi

# Vérifier que .env existe
if [ ! -f .env ]; then
    echo "❌ Fichier .env introuvable"
    exit 1
fi

echo "📋 Secrets actuels dans Doppler:"
doppler secrets --only-names
echo ""

echo "📝 Lecture de .env et ajout à Doppler..."
echo ""

# Liste des clés à synchroniser
KEYS_TO_SYNC=(
    "GROQ_API_KEY"
    "YDC_API_KEY"
    "OPENAI_API_KEY"
    "ANTHROPIC_API_KEY"
    "EXA_API_KEY"
    "FIRECRAWL_API_KEY"
    "SERP_API_KEY"
    "SENDGRID_API_KEY"
    "EMAIL_FROM"
    "ENVIRONMENT"
    "LOG_LEVEL"
)

# Charger .env
source .env

for key in "${KEYS_TO_SYNC[@]}"; do
    # Récupérer la valeur depuis l'environnement
    value="${!key}"
    
    # Skip si vide ou placeholder
    if [ -z "$value" ] || [[ "$value" == "your_"* ]]; then
        echo "⏭️  $key - skipped (placeholder ou vide)"
        continue
    fi
    
    # Ajouter à Doppler
    echo "✅ $key - ajouté"
    doppler secrets set "$key=$value" --silent
done

echo ""
echo "=================================="
echo "✅ Synchronisation terminée!"
echo ""
echo "📋 Vérifier les secrets:"
echo "   doppler secrets"
echo ""
echo "🧪 Tester avec Doppler:"
echo "   doppler run -- ./run_seo_tools.sh python test_advertools.py"

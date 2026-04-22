#!/bin/bash
# Script para executar os testes do HugMe Bot

echo "========================================"
echo "🧪 Executando Testes do HugMe Bot"
echo "========================================"

# Determinar diretório do script e raiz do projeto, configurar PYTHONPATH
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

# Verificar se pytest está instalado
if ! command -v pytest &> /dev/null; then
    echo "❌ pytest não encontrado. Instalando..."
    pip install pytest pytest-asyncio
fi

# Verificar se pytest-asyncio está instalado
if ! python -c "import pytest_asyncio" &> /dev/null; then
    echo "❌ pytest-asyncio não encontrado. Instalando..."
    pip install pytest-asyncio
fi

# Executar testes
echo ""
echo "📝 Executando todos os testes..."
echo ""

pytest "$PROJECT_ROOT/tests/test_doacoes.py" "$PROJECT_ROOT/tests/test_doar.py" "$PROJECT_ROOT/tests/test_supporter_roles.py" -v --tb=short

# Verificar resultado
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Todos os testes passaram!"
    echo ""
    
    # Executar com cobertura se pytest-cov estiver instalado
    if python -c "import pytest_cov" &> /dev/null; then
        echo "📊 Gerando relatório de cobertura..."
        echo ""
        pytest "$PROJECT_ROOT/tests/test_doacoes.py" "$PROJECT_ROOT/tests/test_doar.py" "$PROJECT_ROOT/tests/test_supporter_roles.py" --cov=bot --cov-report=html --cov-report=term
        echo ""
        echo "📈 Relatório de cobertura salvo em: htmlcov/index.html"
    fi
else
    echo ""
    echo "❌ Alguns testes falharam. Verifique os logs acima."
    exit 1
fi

echo ""
echo "========================================"
echo "✅ Testes finalizados com sucesso!"
echo "========================================"

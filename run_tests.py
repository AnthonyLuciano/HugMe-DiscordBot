#!/usr/bin/env python3
"""
Script para executar testes unitários do HugMe Discord Bot
"""

import subprocess
import sys
import os

def run_tests():
    """Executa todos os testes"""
    print("🚀 Executando testes unitários...")

    # Mudar para o diretório do projeto
    project_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_dir)

    # Comando para executar pytest
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/",
        "-v",
        "--tb=short",
        "--asyncio-mode=auto"
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)

        print("STDOUT:")
        print(result.stdout)

        if result.stderr:
            print("STDERR:")
            print(result.stderr)

        print(f"\nCódigo de saída: {result.returncode}")

        return result.returncode == 0

    except Exception as e:
        print(f"Erro ao executar testes: {e}")
        return False

def run_tests_with_coverage():
    """Executa testes com coverage (se disponível)"""
    print("📊 Executando testes com coverage...")

    try:
        import pytest_cov
        has_coverage = True
    except ImportError:
        has_coverage = False
        print("⚠️  pytest-cov não instalado. Instalando...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pytest-cov"], check=True)

    project_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_dir)

    cmd = [
        sys.executable, "-m", "pytest",
        "tests/",
        "--cov=bot",
        "--cov-report=html",
        "--cov-report=term-missing",
        "-v"
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)

        print("STDOUT:")
        print(result.stdout)

        if result.stderr:
            print("STDERR:")
            print(result.stderr)

        print(f"\nCódigo de saída: {result.returncode}")

        if result.returncode == 0:
            print("✅ Relatório HTML gerado em htmlcov/index.html")

        return result.returncode == 0

    except Exception as e:
        print(f"Erro ao executar testes com coverage: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--coverage":
        success = run_tests_with_coverage()
    else:
        success = run_tests()

    sys.exit(0 if success else 1)
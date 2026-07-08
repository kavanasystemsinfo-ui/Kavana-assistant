"""Tests del módulo LLM."""
import pytest
from unittest.mock import patch, MagicMock
from src.llm import LLMClient


@pytest.fixture
def llm():
    return LLMClient(api_key="sk-test")


class TestLLMContext:
    """Formateo de contexto para el prompt."""

    def test_formats_context_correctly(self, llm):
        context = [
            {"machine": "Perfiladora", "section": "errors", "code": "E-101",
             "content": "Código: E-101\nTítulo: Error de prueba\nSoluciones: solución 1"},
        ]
        result = llm._format_context(context)
        assert "Perfiladora" in result
        assert "E-101" in result
        assert "solución 1" in result

    def test_handles_empty_context(self, llm):
        result = llm._format_context([])
        assert result == ""

    def test_includes_multiple_entries(self, llm):
        context = [
            {"machine": "M1", "section": "errors", "content": "A"},
            {"machine": "M2", "section": "tips", "content": "B"},
        ]
        result = llm._format_context(context)
        assert "[1]" in result
        assert "[2]" in result


class TestLLMAnalyze:
    """Análisis de preguntas."""

    def test_detects_rag_question(self, llm):
        with patch.object(llm, 'analyze_question', return_value={"type": "rag", "reason": "pregunta sobre error"}):
            result = llm.analyze_question("¿Qué significa el error E-101?")
            assert result["type"] == "rag"

    def test_detects_tool_question(self, llm):
        with patch.object(llm, 'analyze_question', return_value={"type": "tool", "reason": "consulta stock"}):
            result = llm.analyze_question("¿Cuántos rodillos quedan?")
            assert result["type"] == "tool"

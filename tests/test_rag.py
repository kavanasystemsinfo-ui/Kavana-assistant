"""Tests del sistema RAG — módulo central del asistente."""
import pytest
import json
from pathlib import Path
from src.rag import RAGEngine


@pytest.fixture
def sample_manual():
    """Carga un manual de ejemplo para tests."""
    path = Path(__file__).resolve().parent.parent / "data" / "manuals" / "perfiladora-pf2000.json"
    with open(path) as f:
        return json.load(f)


@pytest.fixture
def rag(tmp_path):
    """Motor RAG con base de datos vectorial temporal única."""
    db_path = tmp_path / "chroma"
    db_path.mkdir(parents=True, exist_ok=True)
    engine = RAGEngine(persist_dir=str(db_path))
    yield engine
    # Limpiar después del test
    import shutil
    if db_path.exists():
        shutil.rmtree(db_path)


class TestManualIndexing:
    """Indexar manuales en la base vectorial."""

    def test_loads_manual_entries(self, sample_manual):
        import tempfile
        rag = RAGEngine(persist_dir=tempfile.mkdtemp())
        count = rag.index_manual(sample_manual)
        assert count == 13  # 7 errores + 4 mantenimiento + 4 tips

    def test_each_entry_has_id(self, sample_manual):
        rag = RAGEngine(persist_dir="/tmp/test_chroma_ids")
        count = rag.index_manual(sample_manual)
        # Each entry debe tener un ID único
        entries = rag._extract_entries(sample_manual)
        ids = [rag._entry_id(e) for e in entries]
        assert len(set(ids)) == len(ids)  # Todos los IDs son únicos

    def test_indexing_is_idempotent(self, sample_manual):
        rag = RAGEngine(persist_dir="/tmp/test_chroma")
        rag.index_manual(sample_manual)
        count2 = rag.index_manual(sample_manual)
        assert count2 == 0  # No debe duplicar


class TestQuery:
    """Consultar al sistema RAG."""

    def test_finds_relevant_entries(self, rag, sample_manual):
        rag.index_manual(sample_manual)
        results = rag.query("desviación de perfil hacia arriba")
        assert len(results) > 0
        assert any("rodillos superiores" in r["content"].lower() for r in results)

    def test_returns_sorted_by_relevance(self, rag, sample_manual):
        rag.index_manual(sample_manual)
        results = rag.query("error E-101 en perfiladora")
        assert len(results) > 0
        # ChromaDB devuelve por distancia ascendente (menor = más similar)
        assert results[0]["score"] <= results[-1]["score"]

    def test_handles_unknown_query(self, rag, sample_manual):
        rag.index_manual(sample_manual)
        results = rag.query("zxkpqrst")
        # ChromaDB siempre devuelve k resultados; los scores altos indican poca relevancia
        for r in results:
            assert r["score"] > 0.5  # Todas deberían tener baja similitud

    def test_limits_results(self, rag, sample_manual):
        rag.index_manual(sample_manual)
        results = rag.query("error", k=3)
        assert len(results) <= 3

    def test_searches_across_all_sections(self, rag, sample_manual):
        rag.index_manual(sample_manual)
        results = rag.query("lubricación")
        sections = set(r["section"] for r in results)
        assert "maintenance" in sections or "errors" in sections

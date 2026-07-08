"""Motor RAG — Indexación y consulta de manuales técnicos."""
from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger("kavana.assistant.rag")


class RAGEngine:
    """Sistema de Retrieval-Augmented Generation sobre ChromaDB.
    
    Indexa manuales técnicos y permite consultas semánticas.
    """

    def __init__(self, persist_dir: str = "/app/chromadb"):
        self.persist_dir = persist_dir
        self._client = None
        self._collection = None

    @property
    def client(self):
        if self._client is None:
            import chromadb
            self._client = chromadb.PersistentClient(path=self.persist_dir)
        return self._client

    @property
    def collection(self):
        if self._collection is None:
            self._collection = self.client.get_or_create_collection(
                name="machine_manuals",
                metadata={"hnsw:space": "cosine"},
            )
        return self._collection

    def index_manual(self, manual: dict) -> int:
        """Indexa todas las entradas de un manual en ChromaDB.
        
        Returns:
            Número de nuevas entradas indexadas (0 si ya existían).
        """
        entries = self._extract_entries(manual)
        if not entries:
            return 0

        # Generar IDs y verificar duplicados
        existing = set(self.collection.get()["ids"])
        new_entries = [(e, self._entry_id(e)) for e in entries if self._entry_id(e) not in existing]

        if not new_entries:
            return 0

        ids = [eid for _, eid in new_entries]
        documents = [self._entry_text(e) for e, _ in new_entries]
        metadatas = [self._entry_metadata(e, manual) for e, _ in new_entries]

        self.collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids,
        )
        return len(new_entries)

    def query(self, question: str, k: int = 5) -> list[dict]:
        """Busca las entradas más relevantes para una consulta.
        
        Returns:
            Lista de dicts con 'content', 'section', 'machine', 'score'.
        """
        if self.collection.count() == 0:
            return []

        results = self.collection.query(
            query_texts=[question],
            n_results=min(k, self.collection.count()),
        )

        output = []
        for i in range(len(results["ids"][0])):
            output.append({
                "content": results["documents"][0][i],
                "section": results["metadatas"][0][i].get("section", ""),
                "machine": results["metadatas"][0][i].get("machine", ""),
                "code": results["metadatas"][0][i].get("code", ""),
                "score": results["distances"][0][i] if results.get("distances") else 0,
            })
        return output

    def _extract_entries(self, manual: dict) -> list[dict]:
        """Extrae todas las entradas indexables de un manual."""
        entries = []
        machine = manual.get("machine", "")
        for section in manual.get("sections", []):
            section_id = section.get("id", "")
            for entry in section.get("entries", []):
                entry["_section"] = section_id
                entry["_machine"] = machine
                entries.append(entry)
        return entries

    def _entry_id(self, entry: dict) -> str:
        """Genera un ID único para una entrada basado en su contenido."""
        unique = f"{entry.get('code', '')}::{entry.get('title', '')}::{entry.get('_machine', '')}"
        return hashlib.md5(unique.encode()).hexdigest()

    def _entry_text(self, entry: dict) -> str:
        """Convierte una entrada en texto plano para indexación."""
        parts = [f"Código: {entry.get('code', '')}", f"Título: {entry.get('title', '')}"]
        if entry.get("symptoms"):
            parts.append(f"Síntomas: {entry['symptoms']}")
        if entry.get("causes"):
            parts.append(f"Causas: {'; '.join(entry['causes'])}")
        if entry.get("solutions"):
            parts.append(f"Soluciones: {'; '.join(entry['solutions'])}")
        if entry.get("details"):
            parts.append(f"Detalle: {entry['details']}")
        if entry.get("task"):
            parts.append(f"Tarea: {entry['task']}")
        if entry.get("solution"):
            parts.append(f"Solución: {entry['solution']}")
        if entry.get("problem"):
            parts.append(f"Problema: {entry['problem']}")
        return "\n".join(parts)

    def _entry_metadata(self, entry: dict, manual: dict) -> dict:
        """Metadatos para filtrado."""
        return {
            "machine": entry.get("_machine", manual.get("machine", "")),
            "section": entry.get("_section", ""),
            "code": entry.get("code", ""),
            "category": manual.get("category", ""),
        }

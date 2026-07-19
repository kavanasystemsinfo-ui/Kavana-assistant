"""Evaluación de calidad RAG — KAVANA Assistant.

Mide precisión del recuperador (ChromaDB) con preguntas reales
de operarios sobre los manuales indexados.

Uso:
    python -m eval.rag_eval
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

# Añadir raíz del proyecto al path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.rag import RAGEngine

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("eval")

# ── Preguntas de prueba con fragmentos esperados ──────────────────────────
# Cada entrada: (pregunta, fragmento_clave_que_debe_aparecer, máquina_esperada)
TEST_QUESTIONS = [
    (
        "La perfiladora da error E-CAT-01 ¿qué hago?",
        "E-CAT-01",
        "perfiladora-pf2000",
    ),
    (
        "Cómo calibrar la plegadora después de un cambio de herramienta",
        "calibrar",
        "plegadora-ph100t",
    ),
    (
        "Se ha parado la perfiladora y no arranca",
        "no arranca",
        "perfiladora-pf2000",
    ),
    (
        "Qué aceite usa la plegadora",
        "aceite",
        "plegadora-ph100t",
    ),
    (
        "Error de alineación en la perfiladora",
        "alineación",
        "perfiladora-pf2000",
    ),
    (
        "Cambio de matriz en plegadora",
        "matriz",
        "plegadora-ph100t",
    ),
    (
        "La plegadora no alcanza la presión nominal",
        "presión",
        "plegadora-ph100t",
    ),
    (
        "Cómo hacer mantenimiento semanal a la perfiladora",
        "mantenimiento",
        "perfiladora-pf2000",
    ),
    (
        "Código de error E-HYD-03 en plegadora",
        "E-HYD-03",
        "plegadora-ph100t",
    ),
    (
        "La perfiladora vibra demasiado al cortar",
        "vibraciones",
        "perfiladora-pf2000",
    ),
]


def evaluate(rag: RAGEngine, k: int = 5) -> dict:
    """Ejecuta evaluación: recall@k y precisión por máquina."""
    if rag.collection.count() == 0:
        logger.warning("[EVAL] Colección vacía. Indexa manuales primero.")
        return {"error": "empty_collection"}

    total = len(TEST_QUESTIONS)
    hits = 0
    by_machine = {}
    results = []

    for question, expected, machine in TEST_QUESTIONS:
        docs = rag.query(question, k=k)
        if not docs:
            results.append({"question": question, "hit": False, "reason": "sin resultados"})
            continue

        # Verificar si el fragmento esperado aparece en algún resultado
        hit = any(expected.lower() in d.get("content", "").lower() for d in docs)

        # Verificar que la máquina correcta está entre los resultados
        machine_ok = any(machine.lower() in d.get("machine", "").lower() for d in docs)

        if hit:
            hits += 1

        by_machine.setdefault(machine, {"total": 0, "hits": 0})
        by_machine[machine]["total"] += 1
        if hit:
            by_machine[machine]["hits"] += 1

        results.append({
            "question": question,
            "expected": expected,
            "machine": machine,
            "hit": hit,
            "machine_found": machine_ok,
            "top_score": round(docs[0].get("score", 0), 4) if docs else None,
        })

    recall = hits / total if total > 0 else 0

    # Métricas por máquina
    machine_metrics = {}
    for m, v in by_machine.items():
        machine_metrics[m] = {
            "recall": round(v["hits"] / v["total"], 2) if v["total"] else 0,
            "total": v["total"],
            "hits": v["hits"],
        }

    return {
        "recall_at_k": round(recall, 2),
        "total_questions": total,
        "hits": hits,
        "k": k,
        "by_machine": machine_metrics,
        "results": results,
    }


def print_report(metrics: dict):
    """Imprime informe legible."""
    if "error" in metrics:
        logger.error(f"[EVAL] Error: {metrics['error']}")
        return

    logger.info("=" * 60)
    logger.info("  EVALUACIÓN RAG — KAVANA Assistant")
    logger.info("=" * 60)
    logger.info(f"  Preguntas:    {metrics['total_questions']}")
    logger.info(f"  Aciertos:     {metrics['hits']}")
    logger.info(f"  Recall@{metrics['k']}: {metrics['recall_at_k']}")
    logger.info("-" * 60)

    for m, v in metrics.get("by_machine", {}).items():
        bar = "█" * int(v["recall"] * 20) + "░" * (20 - int(v["recall"] * 20))
        logger.info(f"  {m:25s} {bar} {v['recall']:.0%} ({v['hits']}/{v['total']})")

    logger.info("-" * 60)
    for r in metrics.get("results", []):
        status = "✅" if r["hit"] else "❌"
        logger.info(f"  {status} {r['question'][:60]}")
    logger.info("=" * 60)


def main():
    """Indexa manuales y ejecuta evaluación."""
    rag = RAGEngine(persist_dir="/tmp/chromadb_eval")
    logger.info("[EVAL] Indexando manuales...")

    manuals_dir = Path(__file__).resolve().parent.parent / "data" / "manuals"
    if not manuals_dir.exists():
        logger.error(f"[EVAL] No se encuentra data/manuals/ en {manuals_dir}")
        sys.exit(1)

    total_indexed = 0
    for fpath in sorted(manuals_dir.glob("*.json")):
        with open(fpath) as f:
            manual = json.load(f)
        n = rag.index_manual(manual)
        total_indexed += n
        logger.info(f"  → {fpath.name}: {n} entradas nuevas")

    logger.info(f"  Total indexado: {total_indexed} entradas\n")

    metrics = evaluate(rag)
    print_report(metrics)

    # Guardar resultados como JSON
    out_path = Path(__file__).resolve().parent / "eval_results.json"
    with open(out_path, "w") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)
    logger.info(f"\n[EVAL] Resultados guardados en {out_path}")


if __name__ == "__main__":
    main()

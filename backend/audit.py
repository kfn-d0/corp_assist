"""
Audit and observability module.
Logs all queries, ingestion events, and system metrics for traceability.
"""

import os
import json
from datetime import datetime, timezone
from typing import Optional

from backend.config import settings


def log_query(
    question: str,
    answer: str,
    user_role: str,
    sources: list[dict],
    latency_ms: float,
    tokens_used: int,
    model_used: str,
):
    """
    Log a user query and its response to the audit log.
    Each entry is a JSON line in a daily log file.
    """
    log_entry = {
        "type": "query",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "question": question,
        "answer": answer[:500],
        "user_role": user_role,
        "sources": [
            {
                "document": s.get("document", ""),
                "page": s.get("page", 0),
            }
            for s in sources
        ],
        "sources_count": len(sources),
        "latency_ms": round(latency_ms, 2),
        "tokens_used": tokens_used,
        "model_used": model_used,
    }

    _write_log(log_entry)


def log_ingestion(
    document_name: str,
    department: str,
    chunk_count: int,
    file_type: str,
    status: str,
    message: str = "",
):
    """Log a document ingestion event."""
    log_entry = {
        "type": "ingestion",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "document_name": document_name,
        "department": department,
        "chunk_count": chunk_count,
        "file_type": file_type,
        "status": status,
        "message": message,
    }

    _write_log(log_entry)


def log_error(
    operation: str,
    error_message: str,
    details: Optional[dict] = None,
):
    """Log an error event."""
    log_entry = {
        "type": "error",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "operation": operation,
        "error": error_message,
        "details": details or {},
    }

    _write_log(log_entry)


def get_query_history(limit: int = 50) -> list[dict]:
    """
    Retrieve recent query logs for the history view.
    Reads from today's log file and returns the most recent entries.
    """
    log_dir = settings.log_dir
    all_queries = []


    try:
        log_files = sorted(
            [f for f in os.listdir(log_dir) if f.startswith("audit_") and f.endswith(".jsonl")],
            reverse=True,
        )
    except FileNotFoundError:
        return []

    for log_file in log_files[:7]:
        file_path = os.path.join(log_dir, log_file)
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        if entry.get("type") == "query":
                            all_queries.append(entry)
                    except json.JSONDecodeError:
                        continue
        except FileNotFoundError:
            continue

        if len(all_queries) >= limit:
            break


    all_queries.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return all_queries[:limit]


def _write_log(log_entry: dict):
    """Write a log entry to the daily audit log file."""
    os.makedirs(settings.log_dir, exist_ok=True)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log_file = os.path.join(settings.log_dir, f"audit_{today}.jsonl")

    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

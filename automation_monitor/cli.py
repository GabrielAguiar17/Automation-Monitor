from __future__ import annotations

import argparse
import json

from .monitor import AutomationMonitor, since_days


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Monitora execuções de automações em SQLite.")
    parser.add_argument("--database", default="automation_monitor.db", help="Caminho do arquivo SQLite.")
    commands = parser.add_subparsers(dest="command", required=True)

    record = commands.add_parser("record", help="Registra uma execução já concluída.")
    record.add_argument("name", help="Nome da automação.")
    record.add_argument("--status", choices=("success", "failed"), default="success")
    record.add_argument("--error", help="Mensagem da falha.")
    record.add_argument("--metadata", default="{}", help="Metadados em JSON.")

    summary = commands.add_parser("summary", help="Exibe o resumo das execuções.")
    summary.add_argument("--name", help="Filtra por automação.")
    summary.add_argument("--days", type=int, help="Considera apenas os últimos N dias.")

    recent = commands.add_parser("recent", help="Lista execuções recentes.")
    recent.add_argument("--limit", type=int, default=20)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    monitor = AutomationMonitor(args.database)

    if args.command == "record":
        try:
            metadata = json.loads(args.metadata)
        except json.JSONDecodeError as error:
            raise SystemExit(f"--metadata deve ser um JSON válido: {error}") from error
        execution_id = monitor.start(args.name, metadata)
        execution = monitor.finish(
            execution_id,
            status=args.status,
            error=RuntimeError(args.error) if args.status == "failed" and args.error else None,
        )
        print(json.dumps({"id": execution.id, "status": execution.status}, ensure_ascii=False))
    elif args.command == "summary":
        since = since_days(args.days) if args.days is not None else None
        result = monitor.summary(args.name, since)
        print(json.dumps({
            "total": result.total,
            "successful": result.successful,
            "failed": result.failed,
            "running": result.running,
            "success_rate": result.success_rate,
            "average_duration_seconds": result.average_duration_seconds,
        }, ensure_ascii=False))
    else:
        for execution in monitor.recent(args.limit):
            print(json.dumps({
                "id": execution.id,
                "automation_name": execution.automation_name,
                "status": execution.status,
                "started_at": execution.started_at.isoformat(),
                "finished_at": execution.finished_at.isoformat() if execution.finished_at else None,
                "error": execution.error_message,
            }, ensure_ascii=False))
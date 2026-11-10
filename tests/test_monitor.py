import sqlite3
import tempfile
import unittest
from pathlib import Path

from automation_monitor import AutomationMonitor


class AutomationMonitorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.monitor = AutomationMonitor(str(Path(self.directory.name) / "monitor.db"))

    def tearDown(self) -> None:
        self.directory.cleanup()

    def test_registra_execucao_bem_sucedida_com_metadados(self) -> None:
        execution_id = self.monitor.start("sincronizar_pedidos", {"origem": "erp"})
        execution = self.monitor.finish(execution_id)

        self.assertEqual(execution.status, "success")
        self.assertEqual(execution.metadata, {"origem": "erp"})
        self.assertIsNotNone(execution.duration_seconds)

    def test_context_manager_marca_falha_e_preserva_excecao(self) -> None:
        with self.assertRaises(RuntimeError):
            with self.monitor.track("importar_clientes"):
                raise RuntimeError("serviço indisponível")

        execution = self.monitor.recent(1)[0]
        self.assertEqual(execution.status, "failed")
        self.assertEqual(execution.error_type, "RuntimeError")
        self.assertEqual(execution.error_message, "serviço indisponível")

    def test_summary_agrega_status_e_taxa_de_sucesso(self) -> None:
        successful_id = self.monitor.start("job")
        self.monitor.finish(successful_id)
        failed_id = self.monitor.start("job")
        self.monitor.finish(failed_id, status="failed")
        self.monitor.start("job")

        summary = self.monitor.summary("job")
        self.assertEqual(summary.total, 3)
        self.assertEqual(summary.successful, 1)
        self.assertEqual(summary.failed, 1)
        self.assertEqual(summary.running, 1)
        self.assertEqual(summary.success_rate, 0.5)

    def test_schema_e_dados_persistem_em_nova_instancia(self) -> None:
        execution_id = self.monitor.start("persistencia")
        self.monitor.finish(execution_id)
        other_monitor = AutomationMonitor(self.monitor.database)

        self.assertEqual(other_monitor.get(execution_id).status, "success")

    def test_database_tem_tabela_de_execucoes(self) -> None:
        connection = sqlite3.connect(self.monitor.database)
        try:
            table = connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'executions'"
            ).fetchone()
        finally:
            connection.close()
        self.assertIsNotNone(table)


if __name__ == "__main__":
    unittest.main()
# Monitor de automações

Monitor local, sem dependências externas, que usa SQLite para registrar execuções
de automações, duração, metadados e detalhes de falhas.

## Uso como biblioteca

```python
from automation_monitor import AutomationMonitor

monitor = AutomationMonitor("automation_monitor.db")

with monitor.track("sincronizar_pedidos", {"origem": "erp"}):
	sincronizar_pedidos()

resumo = monitor.summary()
print(resumo.total, resumo.failed, resumo.success_rate)
```

Se o bloco lançar uma exceção, a execução será gravada com status `failed`, tipo
e mensagem da exceção. A exceção continua sendo propagada para o chamador.

Para controle manual, use `start()` e `finish()`. Uma execução pode ficar com
status `running` enquanto o processo está em andamento.

## CLI

Execute os comandos a partir da raiz do projeto:

```text
python -m automation_monitor --database dados/monitor.db record importar_clientes --metadata '{"origem":"crm"}'
python -m automation_monitor --database dados/monitor.db record enviar_email --status failed --error "SMTP indisponível"
python -m automation_monitor --database dados/monitor.db summary --days 7
python -m automation_monitor --database dados/monitor.db summary --name importar_clientes
python -m automation_monitor --database dados/monitor.db recent --limit 10
```

O banco e a tabela `executions` são criados automaticamente. O SQLite atende
ao uso local; para múltiplos processos distribuídos, a camada de persistência
deve ser substituída por um banco servidor.

## Testes

```text
python -m unittest discover -s tests -v
```
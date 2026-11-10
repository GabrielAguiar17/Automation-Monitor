# Automation Monitor

Monitor local para registrar e consultar execuções de automações. O projeto usa Python e SQLite, sem dependências externas.

## Funcionalidades

- Registra execuções com status `running`, `success` ou `failed`.
- Armazena horários, metadados e informações de exceções.
- Calcula a duração de cada execução.
- Gera resumos com totais, falhas, execuções em andamento, taxa de sucesso e duração média.
- Filtra resumos por nome da automação e período.
- Lista execuções recentes.
- Oferece uma interface de linha de comando (CLI) e uma API Python.

## Requisitos

- Python 3.10 ou superior.
- SQLite, incluído na biblioteca padrão do Python.

## Uso como biblioteca

Execute o exemplo a partir da pasta raiz do projeto:

```python
from automation_monitor import AutomationMonitor

monitor = AutomationMonitor("automation_monitor.db")

with monitor.track("sincronizar_pedidos", {"origem": "erp"}):
    # Execute aqui a automação que deseja acompanhar.
    print("Sincronizando pedidos...")

resumo = monitor.summary()

print(f"Execuções: {resumo.total}")
print(f"Falhas: {resumo.failed}")
print(f"Taxa de sucesso: {resumo.success_rate:.0%}")
```

O método `track()` registra a execução. Se ocorrer uma exceção dentro do bloco, ela é armazenada como falha e continua sendo propagada ao código chamador.

## Uso pela linha de comando

Execute os comandos abaixo na pasta raiz do projeto.

### Registrar uma execução com sucesso

```bash
python -m automation_monitor --database automation_monitor.db record importar_clientes --metadata '{"origem":"crm"}'
```

### Registrar uma falha

```bash
python -m automation_monitor --database automation_monitor.db record enviar_email --status failed --error "Servidor SMTP indisponível"
```

### Consultar um resumo dos últimos sete dias

```bash
python -m automation_monitor --database automation_monitor.db summary --days 7
```

### Filtrar o resumo por automação

```bash
python -m automation_monitor --database automation_monitor.db summary --name importar_clientes
```

### Listar execuções recentes

```bash
python -m automation_monitor --database automation_monitor.db recent --limit 10
```

O arquivo do banco e a tabela `executions` são criados automaticamente.

## Dados registrados

Cada execução armazena identificador único, nome da automação, horários de início e término, status, metadados em JSON, informações da exceção quando houver e duração calculada.

## Testes

Execute a suíte de testes com:

```bash
python -m unittest discover -s tests -v
```

## Escopo

Este projeto é um monitor local com persistência em SQLite e consultas pela CLI ou pela API Python. Não envia alertas nem inclui painel web. Para uso com vários processos ou servidores, a camada de persistência deve ser adaptada para um banco de dados servidor.
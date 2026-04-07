# Профили деплоймента

## 4 профиля и DeploymentRole

Микросервис поддерживает 4 профиля деплоймента. Каждый процесс знает свою **роль** через параметр `DeploymentRole`.

### DeploymentRole

| Роль | Что регистрирует | Когда используется |
|------|-----------------|-------------------|
| `All` | Command Store + EventBus + Read Store + Projections | Single, BudgetCqrs |
| `Command` | Command Store + EventBus (publish) | Cqrs, Ceqrs — деплоймент команд |
| `Event` | EventBus (subscribe) + Read Store + Projections | Ceqrs — деплоймент событий |
| `Query` | Read Store (только чтение) | Cqrs, Ceqrs — деплоймент запросов |

### Профили

| # | Профиль | Деплойменты (роли) | Command DB | Read DB | EventBus |
|---|---------|-------------------|------------|---------|----------|
| 1 | **Single** | 1 (All) | PostgreSQL | та же БД | InMemory |
| 2 | **BudgetCqrs** | 1 (All) | PostgreSQL | PostgreSQL (схема ReadModel) | InMemory |
| 3 | **Cqrs** | 2 (Command + Query) | MongoDB | PostgreSQL (отдельная БД) | Postgres Outbox |
| 4 | **Ceqrs** | 3 (Command + Event + Query) | MongoDB | ScyllaDB | Kafka |

## Выбор профиля

| Вопрос | → Профиль |
|--------|----------|
| Локальная разработка, MVP? | **Single** |
| Продакшен, бюджет ограничен? | **BudgetCqrs** |
| Разные паттерны Command/Read? | **Cqrs** |
| Высокая нагрузка, масштабирование? | **Ceqrs** |

## Из секций 8-9 Aggregate Design Canvas

| Throughput | Size / Lifecycle | → Стратегия | → Профиль |
|-----------|-----------------|------------|----------|
| < 100 tps | Короткий, < 50 событий | FullEventSourcing | Single / BudgetCqrs |
| 100-1000 tps | Средний, 50-500 событий | SnapshotAfterN | Cqrs |
| > 1000 tps | Длинный, > 500 событий | SnapshotAfterN | Ceqrs |
| Любой | История не нужна | StateOnly | Single / BudgetCqrs |

## Конфигурация appsettings.{Profile}.json

```jsonc
{
  "DeploymentProfile": "Single|BudgetCqrs|Cqrs|Ceqrs",
  "CommandStore": {
    "Provider": "Postgres|Mongo",
    "Postgres": { /* EF Core connection */ },
    "Mongo": { "ConnectionString": "...", "DatabaseName": "..." }
  },
  "ReadStore": {
    "Provider": "Postgres|Redis|Scylla",
    "SchemaName": "ReadModel",
    "Redis": { "ConnectionString": "...", "KeyPrefix": "...", "DefaultTtlMinutes": 30 },
    "Scylla": { "ContactPoints": ["..."], "Keyspace": "..." }
  },
  "EventBus": {
    "Strategy": "InMemory|Kafka|Postgres",
    "Kafka": { "BootstrapServers": "...", "TopicPrefix": "...", "GroupId": "..." },
    "Postgres": { "ConnectionString": "...", "TableName": "domain_events_outbox" }
  }
}
```

## Program.cs — логика DeploymentRole

Program.cs содержит условные блоки на основе `DeploymentRole`:

```csharp
var deploymentRole = builder.Configuration["DeploymentRole"] ?? "All";

// Command Store — только для Command и All
if (deploymentRole is "Command" or "All") { /* AddEventStorePostgres / AddEventStoreMongo */ }

// EventBus — для Command (publish), Event (subscribe), All. НЕ для Query.
if (deploymentRole is not "Query") { /* AddEventBusInMemory / AddEventBusKafka / AddEventBusPostgres */ }

// Read Store — для Event, Query и All. НЕ для Command.
if (deploymentRole is "Event" or "Query" or "All") { /* AddReadStorePostgres / AddReadStoreRedis / AddReadStoreScylla */ }

// Projection Handler — только для Event и All
if (deploymentRole is "Event" or "All") { /* ChatProjectionHandler, IRebuildService */ }
```

## Docker

```dockerfile
FROM mcr.microsoft.com/dotnet/aspnet:8.0 AS base
# ...
ARG DEPLOYMENT_PROFILE=Single
ENV ASPNETCORE_ENVIRONMENT=${DEPLOYMENT_PROFILE}
```

NuGet-пакеты DigiTFactory.Libraries опубликованы на **nuget.org** — дополнительная аутентификация не требуется.

### CI matrix build

CI собирает 4 Docker-образа через GitHub Actions matrix:

```yaml
strategy:
  matrix:
    profile:
      - { name: Single, tag: single }
      - { name: BudgetCqrs, tag: budget-cqrs }
      - { name: Cqrs, tag: cqrs }
      - { name: Ceqrs, tag: ceqrs }
```

Теги: `ghcr.io/{owner}/{context}:{profile-tag}` + `ghcr.io/{owner}/{context}:latest` (= Single).

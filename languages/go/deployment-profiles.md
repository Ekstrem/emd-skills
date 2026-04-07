# Профили деплоймента

## 3 профиля и DeploymentRole

Микросервис поддерживает 3 профиля деплоймента. Каждый процесс знает свою **роль** через переменную `DEPLOYMENT_ROLE`.

### DeploymentRole

| Роль | Что инициализирует | Когда используется |
|------|-------------------|-------------------|
| `All` | Command Store + EventBus + Read Store + Projections | Single |
| `Command` | Command Store + EventBus (publish) | Cqrs, Ceqrs |
| `Event` | EventBus (subscribe) + Read Store + Projections | Ceqrs |
| `Query` | Read Store (только чтение) | Cqrs, Ceqrs |

### Профили

| # | Профиль | Деплойменты (роли) | Event Bus | Подходит для |
|---|---------|-------------------|-----------|-------------|
| 1 | **Single** | 1 (All) | InMemory | Dev, демо, MVP |
| 2 | **CQRS** | 2 (Command + Query) | Postgres Outbox | Средняя нагрузка |
| 3 | **CEQRS** | 3 (Command + Event + Query) | Kafka | Высокая нагрузка |

## Выбор профиля

| Вопрос | → Профиль |
|--------|----------|
| Локальная разработка, MVP? | **Single** |
| Разделение read/write, до 1000 tps? | **CQRS** |
| Высокая нагрузка, масштабирование? | **CEQRS** |

## Из секций 8-9 Aggregate Design Canvas

| Throughput | Size / Lifecycle | → Стратегия | → Профиль |
|-----------|-----------------|------------|----------|
| < 100 tps | Короткий, < 50 событий | FullEventSourcing | Single |
| 100-1000 tps | Средний | SnapshotAfterN | CQRS |
| > 1000 tps | Длинный | SnapshotAfterN | CEQRS |

## Конфигурация через env

```bash
# Роль процесса
DEPLOYMENT_ROLE=All|Command|Event|Query

# HTTP
SERVER_PORT=8080

# Command Store (Event Store)
COMMAND_STORE_CONNECTION=postgres://postgres:postgres@localhost:5432/chat?sslmode=disable
COMMAND_STORE_SCHEMA=commands

# Event Bus
EVENT_BUS_STRATEGY=InMemory|Kafka|Postgres
EVENT_BUS_CONNECTION=postgres://...            # для Postgres Outbox
EVENT_BUS_KAFKA_BOOTSTRAP=localhost:9092
EVENT_BUS_KAFKA_TOPIC_PREFIX=chat-events
EVENT_BUS_KAFKA_GROUP_ID=chat-group

# Read Store
READ_STORE_CONNECTION=                         # если пусто — используется COMMAND_STORE_CONNECTION
READ_STORE_SCHEMA=read_model
```

## main.go — логика DeploymentRole

```go
role := cfg.DeploymentRole // из env DEPLOYMENT_ROLE

// Command Store — только для Command и All
if role == "Command" || role == "All" {
    cmdPool, _ := pgxpool.New(ctx, cfg.CommandStore.ConnectionString)
    cmdrepo.InitializeSchema(ctx, cmdPool, opts, logger)
    eventStore = storage.NewEventStoreRepository(cmdPool, opts, logger)
}

// EventBus — для Command (publish), Event (subscribe), All. НЕ для Query.
if role != "Query" {
    switch cfg.EventBus.Strategy {
    case "Kafka":
        bus = kafka.New(kafkaOpts, logger)
    case "Postgres":
        bus = pgbus.New(busPool, pgbusOpts, logger)
    default:
        bus = inmemory.New(logger)
    }
}

// Read Store — для Event, Query и All
if role == "Event" || role == "Query" || role == "All" {
    readPool, _ := pgxpool.New(ctx, readConnStr)
    readmodel.InitializeReadSchema(ctx, readPool, cfg.ReadStore.SchemaName)
    projectionHandler = readmodel.NewProjectionHandler(readPool, cfg.ReadStore.SchemaName, logger)
    if bus != nil {
        bus.Subscribe({Context}BoundedContext, projectionHandler)
    }
}
```

## Dockerfile

```dockerfile
FROM golang:1.23-alpine AS builder
RUN apk add --no-cache git
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -o /{ctx}-api ./cmd/{ctx}/

FROM alpine:3.19
RUN apk add --no-cache ca-certificates tzdata
COPY --from=builder /{ctx}-api /{ctx}-api
ARG DEPLOYMENT_PROFILE=Single
ENV DEPLOYMENT_ROLE=All
ENV SERVER_PORT=8080
EXPOSE 8080
ENTRYPOINT ["/{ctx}-api"]
```

## Docker Compose

### Single (docker-compose.single.yml)

```yaml
services:
  {ctx}-app:
    image: ghcr.io/{owner}/{ctx}-go:single
    ports: ["8080:8080"]
    environment:
      DEPLOYMENT_ROLE: All
      EVENT_BUS_STRATEGY: InMemory
      COMMAND_STORE_CONNECTION: postgres://postgres:postgres@postgres:5432/{ctx}?sslmode=disable
    depends_on:
      postgres: {condition: service_healthy}

  postgres:
    image: postgres:16-alpine
    environment: {POSTGRES_USER: postgres, POSTGRES_PASSWORD: postgres, POSTGRES_DB: {ctx}}
    healthcheck: {test: ["CMD-SHELL", "pg_isready -U postgres"], interval: 5s, retries: 5}
```

### CQRS (docker-compose.cqrs.yml)

```yaml
services:
  {ctx}-command:
    environment: {DEPLOYMENT_ROLE: Command, EVENT_BUS_STRATEGY: Postgres}
    ports: ["8080:8080"]

  {ctx}-query:
    environment: {DEPLOYMENT_ROLE: Query}
    ports: ["8081:8080"]

  postgres: ...
```

### CEQRS (docker-compose.ceqrs.yml)

```yaml
services:
  {ctx}-command:
    environment: {DEPLOYMENT_ROLE: Command, EVENT_BUS_STRATEGY: Kafka}

  {ctx}-event:
    environment: {DEPLOYMENT_ROLE: Event, EVENT_BUS_STRATEGY: Kafka}

  {ctx}-query:
    environment: {DEPLOYMENT_ROLE: Query}

  zookeeper: {image: confluentinc/cp-zookeeper:7.5.0}
  kafka: {image: confluentinc/cp-kafka:7.5.0}
  postgres: ...
```

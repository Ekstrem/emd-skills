# CEQRS — потоки данных

## Архитектура

CEQRS (Command Event Query Responsibility Segregation) — три деплоймента одного микросервиса.
Шина событий — центральный порт. БД — адаптер. Событие — источник истины.

## Деплоймент 1: Command (приём и исполнение команд)

```
Client → POST /api/{context}
  → ChatHandler.{Command}(w, r)
    → json.Decode(r.Body) → Request DTO
    → {Command}Handler.Handle(ctx, cmd)
      → AggregateProvider.GetAggregate(ctx, id)
        → eventStore.GetByID(ctx, id) — READ (восстановление агрегата)
        → NewAggregate(scope) + обернуть в Notifier
      → notifier.Execute(ctx, opName, model, cmdData)
        → aggregate.Operations[opName].Handle(model, cmd, scope)
          → result.NewOperationData(old, new)
          → invariants.ValidateCommand(data, bc, specs...)
            → Assertions → Validators → AggregateResult
        → busAdapter.OnResult(ctx, aggResult)
          → eventStore.SaveEvent(ctx, entry) — WRITE Event Store
          → eventBus.Publish(ctx, domainEvent) — PUBLISH
    → json.Encode → ChatOperationResult
  → 200 OK / 400 Bad Request
```

**Критично:** BusAdapter сохраняет событие в Event Store И публикует в шину.

## Деплоймент 2: Event (обработка событий)

```
EventBus → DomainEvent (async)
  → ProjectionHandler.HandleEvent(ctx, event)
    ├── 1. Read Model Projector → Upsert → Read Store (WRITE)
    └── 2. Outbound Handler → HTTP / Saga / другие микросервисы (если нужно)
```

**Проецирование:** событие распаковывается → changedVOs → applyEvent → upsert в Read Store.

## Деплоймент 3: Query (чтение проекций)

```
Client → GET /api/{context}/{id}
  → ChatHandler.Get{Context}ById(w, r)
    → GetChatByIdHandler.Handle(ctx, id)
      → eventStore.GetByID(ctx, id) → Event Store (READ)
  → 200 OK (массив событий)
```

**Критично:** Query Side читает из Event Store или Read Store — НЕ из Domain.

## Реализации инфраструктуры

### Event Bus

| Реализация | Конструктор | Назначение |
|-----------|------------|-----------|
| InMemory | `inmemory.New(logger)` | Dev, тесты |
| Kafka | `kafka.New(options, logger)` | Продакшен, высокая нагрузка |
| Postgres | `postgres.New(pool, options, logger)` | Outbox, транзакционная гарантия |

### Command DB (Event Store)

| Реализация | Конструктор | Стратегии |
|-----------|------------|----------|
| PostgreSQL | `cmdrepo.NewFullEventSourcingRepository(pool, opts, logger)` | FullEventSourcing, SnapshotAfterN, StateOnly |
| MongoDB | `mongorepo.NewFullEventSourcingRepository(db, opts, logger)` | FullEventSourcing, SnapshotAfterN, StateOnly |

### Read Store

| Реализация | Конструктор | Назначение |
|-----------|------------|-----------|
| PostgreSQL | `pgquery.NewReadRepository[T](pool, tableName, logger)` | SQL, JOIN, транзакции |
| Redis | `redisquery.NewReadRepository[T](client, keyPrefix, logger)` | Key-value, TTL, субмс |
| ScyllaDB | `scyllaquery.NewReadRepository[T](session, opts, modelType, logger)` | Горизонтальное масштабирование |

## PACELC и eventual consistency

При разделении на деплойменты — eventual consistency между Command и Query.
Стратегии митигации:
- Оптимистичная блокировка через Version (составной ключ Id + Version)
- Идемпотентность проекций (version check)

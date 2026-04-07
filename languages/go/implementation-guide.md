# Руководство по реализации — слои, зависимости, паттерны

## Пакеты DigiTFactory.Go.Libraries

**ВАЖНО:** При генерации кода ВСЕГДА используй import paths из этой таблицы.

### seedworks (ядро)

| import | Что содержит |
|--------|-------------|
| `seedworks/characteristics` | `HasKey[K]`, `HasGuidKey`, `HasVersion[T]`, `HasInt64Version`, `HasCorrelationToken[T]`, `HasGuidCorrelationToken`, `HasValueObjects`, `CommandSubject`, `CommandToAggregate`, `ComplexKey`, `Paging`, `PagingParams`, `Versioning` |
| `seedworks/definition` | `BoundedContextDescription`, `InteractionOfBoundedContexts` |
| `seedworks/events` | `CommandToAggregateData`, `DomainEvent`, `EventBus`, `EventBusProducer`, `EventBusConsumer`, `DomainEventHandler`, `DomainEventNotifier`, `NewCommandToAggregate()`, `NewCommandToAggregateNow()`, `NewDomainEvent()`, `NewDomainEventFromResult()` |
| `seedworks/invariants` | `BusinessOperationSpecification`, `BusinessOperationAssertion`, `BusinessOperationValidatorSpec`, `SpecificationValidator`, `ValidateCommand()` |
| `seedworks/result` | `DomainOperationResult` (Success/WithWarnings/Exception), `OperationData`, `AggregateResult`, `NewOperationData()`, `NewAggregateResultSuccess()`, `NewAggregateResultException()`, `NewAggregateResultWithWarnings()` |
| `seedworks/tacticalpatterns` | `ValueObject`, `Entity`, `ReadModel`, `AnemicModel`, `BaseAnemicModel`, `NewBaseAnemicModel()`, `Aggregate`, `NewAggregate()`, `BoundedContextScope`, `AggregateBusinessOperation`, `AggregateProvider`, `ValueObjectWrapper[T]` |
| `seedworks/monads` | `Result[TSuccess, TFailure]`, `NewSuccess()`, `NewFailure()`, `PipeTo()`, `Do()`, `Either()` |
| `seedworks/lifecycle` | `GetValueObjects()` — извлечение VO через рефлексию |
| `seedworks/reactive` | `Unsubscriber[T]` |
| `seedworks/repository` | `CommandRepository[T]`, `QueryRepository[T]`, `AnemicModelRepository[T]`, `ReadRepository[T]`, `ReadModelStore[T]`, `RebuildService`, `UnitOfWork[T]`, `Transaction` |

### Инфраструктурные пакеты

| import | Что содержит |
|--------|-------------|
| `commandrepository/postgres` | `DomainEventEntry`, `SnapshotEntry`, `Options`, `DefaultOptions()`, `FullEventSourcingRepository`, `SnapshotRepository`, `StateOnlyRepository`, `EventStoreRepository` (interface), `InitializeSchema()` |
| `commandrepository/mongo` | MongoDB Event Store (аналогичные типы) |
| `eventbus/inmemory` | `EventBus`, `New(logger)` |
| `eventbus/kafka` | `Options`, `DefaultOptions()`, `EventBus`, `New(options, logger)`, `Producer`, `Consumer`, `Serialize()`, `Deserialize()` |
| `eventbus/postgres` | `Options`, `DefaultOptions()`, `EventBus`, `New(pool, options, logger)`, `InitializeOutbox()` |
| `queryrepository/postgres` | `ReadRepository[T]`, `NewReadRepository[T](pool, tableName, logger)`, `ReadModelStore`, `NewReadModelStore(pool, tableName, logger)` |
| `queryrepository/redis` | `ReadRepository[T]`, `ReadModelStore`, Redis-реализации |
| `queryrepository/scylla` | `ReadRepository[T]`, `ReadModelStore`, ScyllaDB-реализации |

---

## Граф зависимостей (import)

```
cmd/{ctx}/main.go
     └── internal/api, internal/config, internal/storage, internal/domainservices,
         internal/application/commands, internal/application/queries

internal/domain
     └── seedworks/* ТОЛЬКО

internal/domainservices
     ├── internal/domain
     └── commandrepository/postgres, seedworks/events, seedworks/result

internal/application/commands
     ├── internal/domain
     ├── internal/domainservices
     └── seedworks/events, seedworks/result

internal/application/queries
     └── commandrepository/postgres (для GetByID)

internal/storage
     └── commandrepository/*, internal/domain

internal/api
     └── internal/application/*, internal/storage/readmodel
```

## Правила зависимостей

| Слой | Зависит от | НЕ зависит от |
|------|-----------|--------------|
| domain | seedworks | Всех остальных |
| domainservices | domain, seedworks, commandrepository | api, application |
| application | domain, domainservices, seedworks | api, storage |
| storage | domain, commandrepository, queryrepository | api, application |
| api | application, storage/readmodel | domain, domainservices |
| cmd (main.go) | Все (точка композиции) | — |

## Слой domain — паттерны кода

### BoundedContext и константы

```go
package domain

import "github.com/Ekstrem/DigiTFactory.Go.Libraries/seedworks/definition"

var {Context}BoundedContext = definition.BoundedContextDescription{
    ContextName:         "{Context}",
    MicroserviceVersion: 1,
}

// Enums — typed int constants
type MessageType int
const (
    MessageTypeText  MessageType = iota
    MessageTypeVoice
    MessageTypeVideo
)
func (m MessageType) String() string { /* switch */ }

// Operation name constants
const (
    Op{Command1} = "{Command1}"
    Op{Command2} = "{Command2}"
)

// Value Object key constants
const (
    VoRoot    = "Root"
    VoMessage = "Messages"
    VoActor   = "Actor"
)
```

### Value Objects (иммутабельные structs)

```go
// Value Objects — простые structs с JSON-тегами
type {Context}Root struct {
    UserId    uuid.UUID `json:"UserId"`
    SessionId int       `json:"SessionId"`
}

type {Context}Message struct {
    Type int    `json:"Type"`
    Text string `json:"Text"`
}
```

### AnemicModel

```go
package domain

import (
    "github.com/Ekstrem/DigiTFactory.Go.Libraries/seedworks/tacticalpatterns"
    "github.com/google/uuid"
)

type {Context}AnemicModel struct {
    tacticalpatterns.BaseAnemicModel
    cmdName  string
    subjName string
}

func New{Context}AnemicModel(id uuid.UUID, version int64, corrToken uuid.UUID, cmdName, subjName string, vos map[string]any) *{Context}AnemicModel {
    key := &complexKey{id: id, version: version, corrToken: corrToken}
    base := tacticalpatterns.NewBaseAnemicModel(key, vos)
    return &{Context}AnemicModel{BaseAnemicModel: base, cmdName: cmdName, subjName: subjName}
}

func NewDefault{Context}AnemicModel(id uuid.UUID) *{Context}AnemicModel {
    return New{Context}AnemicModel(id, 0, uuid.Nil, "", "", nil)
}

// CommandName, SubjectName — реализуют characteristics.CommandSubject
func (m *{Context}AnemicModel) CommandName() string  { return m.cmdName }
func (m *{Context}AnemicModel) SubjectName() string  { return m.subjName }

// Root, Actor, Message — типизированные getter-ы Value Objects
func (m *{Context}AnemicModel) Root() *{Context}Root {
    return extractVO[{Context}Root](m.GetValueObjects(), VoRoot)
}

// complexKey — реализует characteristics.ComplexKey
type complexKey struct {
    id        uuid.UUID
    version   int64
    corrToken uuid.UUID
}
func (k *complexKey) ID() uuid.UUID               { return k.id }
func (k *complexKey) Version() int64               { return k.version }
func (k *complexKey) CorrelationToken() uuid.UUID  { return k.corrToken }
```

### Aggregate (бизнес-операции)

```go
package domain

import (
    "github.com/Ekstrem/DigiTFactory.Go.Libraries/seedworks/events"
    "github.com/Ekstrem/DigiTFactory.Go.Libraries/seedworks/invariants"
    "github.com/Ekstrem/DigiTFactory.Go.Libraries/seedworks/result"
    "github.com/Ekstrem/DigiTFactory.Go.Libraries/seedworks/tacticalpatterns"
)

// {Context}Scope реализует tacticalpatterns.BoundedContextScope
type {Context}Scope struct{}

func (s *{Context}Scope) GetOperations() map[string]tacticalpatterns.AggregateBusinessOperation {
    return map[string]tacticalpatterns.AggregateBusinessOperation{
        Op{Command1}: &{command1}Operation{},
        Op{Command2}: &{command2}Operation{},
    }
}

func (s *{Context}Scope) GetValidators() map[string][]invariants.BusinessOperationSpecification {
    return map[string][]invariants.BusinessOperationSpecification{
        Op{Command1}: {specifications.New{Spec1}()},
        Op{Command2}: {specifications.New{Spec2}(), specifications.New{Spec3}()},
    }
}

// Бизнес-операция
type {command1}Operation struct{}

func (op *{command1}Operation) Handle(model tacticalpatterns.AnemicModel, cmd *events.CommandToAggregateData, scope tacticalpatterns.BoundedContextScope) *result.AggregateResult {
    // 1. Привести model к конкретному типу
    m := model.(*{Context}AnemicModel)
    // 2. Создать новую модель с обновлёнными VO
    newVos := map[string]any{
        VoRoot: {Context}Root{...},
        VoMessage: {Context}Message{...},
    }
    newModel := New{Context}AnemicModel(m.ID(), cmd.Version(), cmd.CorrelationToken(), cmd.CommandName(), cmd.SubjectName(), newVos)
    // 3. Валидировать через ValidateCommand
    data := result.NewOperationData(m, newModel)
    validators := scope.GetValidators()[cmd.CommandName()]
    return invariants.ValidateCommand(data, {Context}BoundedContext, validators...)
}
```

### Specification (инвариант)

```go
package specifications

import "github.com/Ekstrem/DigiTFactory.Go.Libraries/seedworks/result"

type Is{Rule} struct{}

func NewIs{Rule}() *Is{Rule} { return &Is{Rule}{} }

func (s *Is{Rule}) IsSatisfiedBy(data *result.OperationData) bool {
    return data.Aggregate.Version() == 0 // пример
}

func (s *Is{Rule}) Reason() string {
    return "Описание причины отказа"
}

func (s *Is{Rule}) DomainResult() result.DomainOperationResult {
    return result.Exception
}
```

## Слой application — CQRS

### Command struct

```go
type {Command}Command struct {
    AggregateID uuid.UUID
    // входные данные из Request DTO
}
```

### Command Handler

```go
type {Command}Handler struct {
    notifier *domainservices.Notifier
    provider *domainservices.AggregateProvider
}

func (h *{Command}Handler) Handle(ctx context.Context, cmd {Command}Command) *application.ChatOperationResult {
    // 1. Загрузить или создать агрегат
    notifier, err := h.provider.GetAggregate(ctx, cmd.AggregateID)
    // 2. Создать CommandToAggregateData
    cmdData := events.NewCommandToAggregateNow(uuid.New(), 0, Op{Command}, "Subject")
    // 3. Создать AnemicModel с входными VO
    model := NewDefault{Context}AnemicModel(cmd.AggregateID)
    // ... заполнить VO из cmd
    // 4. Выполнить операцию через Notifier
    aggResult, err := notifier.Execute(ctx, Op{Command}, model, cmdData)
    // 5. Маппинг в ChatOperationResult
}
```

### Query Handler

```go
type Get{Context}ByIdHandler struct {
    eventStore cmdrepo.EventStoreRepository
}

func (h *Get{Context}ByIdHandler) Handle(ctx context.Context, id uuid.UUID) ([]ChatEventDTO, error) {
    entries, err := h.eventStore.GetByID(ctx, id)
    // маппинг DomainEventEntry → ChatEventDTO
}
```

## Слой domainservices — оркестрация

Каркасные файлы (копируются с подстановкой {Context}):

- **AggregateProvider** — загружает все события из EventStore, реконструирует AnemicModel, оборачивает в Notifier
- **Notifier** — декоратор, вызывает `aggregate.Operations[opName].Handle()`, при успехе вызывает `busAdapter.OnResult()`
- **BusAdapter** — создаёт `DomainEventEntry`, сохраняет в EventStore, публикует `DomainEvent` в EventBus

## Слой storage — проекции и Read Model

### Read Model struct

```go
type {Context}ReadModel struct {
    ID        uuid.UUID `json:"id"`
    // колонки из артефакта 5
    Version   int64     `json:"version"`
    UpdatedAt time.Time `json:"updatedAt"`
}
```

### Read Schema (DDL)

```go
func InitializeReadSchema(ctx context.Context, pool *pgxpool.Pool, schema string) error {
    ddl := fmt.Sprintf(`
        CREATE SCHEMA IF NOT EXISTS %s;
        CREATE TABLE IF NOT EXISTS %s.{ctx}_projections (
            id UUID PRIMARY KEY,
            -- колонки из артефакта 5
            version BIGINT,
            created_at TIMESTAMPTZ,
            updated_at TIMESTAMPTZ
        );
        CREATE INDEX IF NOT EXISTS ix_{ctx}_projections_{field} ON %s.{ctx}_projections({field});
    `, schema, schema, schema)
    _, err := pool.Exec(ctx, ddl)
    return err
}
```

### Projection Handler

```go
type ProjectionHandler struct {
    pool   *pgxpool.Pool
    schema string
}

// HandleEvent реализует events.DomainEventHandler
func (h *ProjectionHandler) HandleEvent(ctx context.Context, event *events.DomainEvent) error {
    // 1. Загрузить текущую проекцию (если есть)
    // 2. Проверить идемпотентность: skip если version >= event.Version
    // 3. Применить: applyEvent(model, changedVOs, commandName)
    // 4. Upsert в PostgreSQL
}
```

### Rebuild Service

```go
type RebuildService struct {
    eventStore cmdrepo.EventStoreRepository
    pool       *pgxpool.Pool
    handler    *ProjectionHandler
}

func (s *RebuildService) Rebuild(ctx context.Context) error {
    // 1. TRUNCATE TABLE
    // 2. SELECT DISTINCT id FROM commands.domain_events
    // 3. Для каждого агрегата: загрузить все события, применить каждое
}
```

## Слой api — HTTP и DI

### Router (chi)

```go
func NewRouter(chatHandler *ChatHandler, adminHandler *AdminHandler) *chi.Mux {
    r := chi.NewRouter()
    r.Use(middleware.Logger)
    r.Use(middleware.Recoverer)
    r.Use(middleware.SetHeader("Content-Type", "application/json"))

    r.Route("/api", func(r chi.Router) {
        r.Route("/{ctx}", func(r chi.Router) {
            r.Post("/", chatHandler.{CreateCommand})
            r.Get("/{id}", chatHandler.Get{Context}ById)
            r.Post("/{id}/{action}", chatHandler.{ActionCommand})
        })
        r.Route("/admin", func(r chi.Router) {
            r.Post("/rebuild-projections", adminHandler.RebuildProjections)
        })
    })
    return r
}
```

### main.go — точка композиции

```go
func main() {
    cfg := config.Load()
    role := cfg.DeploymentRole // "All", "Command", "Event", "Query"

    // Command Store — для Command и All
    if role == "Command" || role == "All" {
        // pgxpool.New(), InitializeSchema(), NewEventStoreRepository()
    }

    // EventBus — НЕ для Query
    if role != "Query" {
        // inmemory.New() / kafka.New() / postgres.New()
    }

    // Read Store — для Event, Query, All
    if role == "Event" || role == "Query" || role == "All" {
        // pgxpool, InitializeReadSchema(), NewProjectionHandler()
        // eventBus.Subscribe(boundedContext, projectionHandler)
    }

    // HTTP handlers
    // chi router
    // http.ListenAndServe с graceful shutdown
}
```

## Тесты

Паттерн:
1. Создать данные через Builder (`test/builders.go`)
2. `NewDefault{Context}AnemicModel(id)` → `NewAggregate(scope)`
3. Вызвать бизнес-операцию через `aggregate.Operations[op].Handle(model, cmd, scope)`
4. `assert result.Result() == result.Success`

Обязательно тестировать:
- Happy path каждого бизнес-метода
- Провал каждого инварианта
- Порядок вызовов (state machine)

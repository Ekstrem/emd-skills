# Руководство по реализации — слои, зависимости, паттерны

## Пространства имён DigiTFactory.Libraries

**ВАЖНО:** При генерации кода ВСЕГДА используй пространства имён из этой таблицы. Корневое пространство — `DigiTFactory.Libraries.SeedWorks`.

### SeedWorks (ядро)

| using | Что содержит |
|-------|-------------|
| `DigiTFactory.Libraries.SeedWorks.TacticalPatterns` | `IValueObject`, `IAggregateRoot<T>`, `IAnemicModel<T>`, `AnemicModel<T>`, `Aggregate<T>`, `IAggregate<T>`, `IAggregateProvider<T>`, `IReadModel<T>`, `IEntity`, `IBoundedContextScope<T>`, `IAggregateBusinessOperation<T>`, `ValueObjectWrapper<T>` |
| `DigiTFactory.Libraries.SeedWorks.TacticalPatterns.Repository` | `ICommandRepository<T,M>`, `IQueryRepository<T,M>`, `IUnitOfWork<T,M>`, `ITransaction`, `IPaging`, `ISqlProgrammability`, `IReadRepository<T,M>`, `IReadModelStore<T,M>`, `IRebuildService<T>`, `SingleReadMode` |
| `DigiTFactory.Libraries.SeedWorks.Events` | `IDomainEvent<T>`, `DomainEvent<T>`, `DomainEventNotifier<T>`, `CommandToAggregate`, `IEventBus`, `IEventBusProducer`, `IEventBusConsumer`, `IDomainEventHandler<T>` |
| `DigiTFactory.Libraries.SeedWorks.Invariants` | `BusinessOperationData<T,M>`, `IBusinessOperationSpecification`, `IBusinessOperationValidator<T,M>`, `IBusinessOperationAssertion` |
| `DigiTFactory.Libraries.SeedWorks.Result` | `AggregateResult<T,M>`, `AggregateResultSuccess<T,M>`, `AggregateResultException<T,M>`, `AggregateResultWithWarnings<T,M>`, `DomainOperationResultEnum`, `ValidateCommand` (extension) |
| `DigiTFactory.Libraries.SeedWorks.Characteristics` | `IHasKey<T>`, `IHasVersion<T>`, `IHasCorrelationToken<T>`, `ICommandSubject`, `ICommandToAggregate`, `IComplexKey`, `ComplexKey` |
| `DigiTFactory.Libraries.SeedWorks.Monads` | `PipeTo`, `Do`, `Either` (extension methods), `Result<TSuccess, TFailure>` |
| `DigiTFactory.Libraries.SeedWorks.Definition` | `IBoundedContext`, `IBoundedContextDescription`, `BoundedContext<T>`, `InteractionOfBoundedContextsEnum` |
| `DigiTFactory.Libraries.SeedWorks.Reactive` | `Unsubscriber<T>` |
| `DigiTFactory.Libraries.SeedWorks.LifeCircle` | `ValueObjectHelper` (GetValueObjects рефлексия) |

### Инфраструктурные пакеты (DI extension methods)

| using | Метод | Что регистрирует |
|-------|-------|-----------------|
| `DigiTFactory.Libraries.EventBus.InMemory.Extensions` | `AddEventBusInMemory()` | `IEventBus` (InMemory) |
| `DigiTFactory.Libraries.EventBus.Kafka.Extensions` | `AddEventBusKafka(options)` | `IEventBus` (Kafka) |
| `DigiTFactory.Libraries.EventBus.Postgres.Extensions` | `AddEventBusPostgres(options)` | `IEventBus` (Outbox) |
| `DigiTFactory.Libraries.CommandRepository.Mongo.Extensions` | `AddEventStoreMongo<T,M>(options)` | `IAnemicModelRepository<T,M>` (Mongo) |
| `DigiTFactory.Libraries.CommandRepository.Postgres.Extensions` | `AddEventStorePostgres<T,M>(conn, options)` | `IAnemicModelRepository<T,M>` (Postgres) |
| `DigiTFactory.Libraries.ReadRepository.Postgres.Extensions` | `AddReadStorePostgres<T,M,Ctx>(conn, options)` | `IReadRepository<T,M>`, `IReadModelStore<T,M>` |
| `DigiTFactory.Libraries.ReadRepository.Redis.Extensions` | `AddReadStoreRedis<T,M>(options)` | `IReadRepository<T,M>`, `IReadModelStore<T,M>` |
| `DigiTFactory.Libraries.ReadRepository.Scylla.Extensions` | `AddReadStoreScylla<T,M>(options)` | `IReadRepository<T,M>`, `IReadModelStore<T,M>` |

---

## Граф зависимостей

```
{Context}.Api
     └── {Context}.Application

{Context}.DomainServices
     ├── {Context}.Domain
     └── {Context}.InternalContracts

{Context}.Storage
     ├── {Context}.DomainServices
     └── {Context}.InternalContracts

{Context}.Domain.Tests
     └── {Context}.Domain

Все проекты → DigiTFactory.Libraries.SeedWorks (NuGet)
```

## Правила зависимостей

| Слой | Зависит от | НЕ зависит от |
|------|-----------|--------------|
| Domain | SeedWorks | Всех остальных |
| DomainServices | Domain, InternalContracts | Api, Application, Storage |
| Application | Domain, DomainServices, InternalContracts | Api, Storage |
| Storage | Domain, InternalContracts, SeedWorks | Api, Application, DomainServices |
| Api | Все (точка композиции) | — |

## Слой Domain — паттерны кода

### Bounded Context маркер
```csharp
using DigiTFactory.Libraries.SeedWorks.Definition;

// I{Context}.cs
public interface I{Context} : IBoundedContext { }
public class {Context}BoundedContextDescription : IBoundedContextDescription
{
    public string ContextName => "{Context}";
    public int MicroserviceVersion => 1;
}
```

### Value Object (иммутабельный, фабричный метод)
```csharp
using DigiTFactory.Libraries.SeedWorks.TacticalPatterns;

// Abstraction/I{Context}{VO}.cs
public interface I{Context}{VO} : IValueObject
{
    string Property1 { get; }
    Guid Property2 { get; }
}

// Implementation/{Context}{VO}.cs
public class {Context}{VO} : I{Context}{VO}
{
    private {Context}{VO}(string p1, Guid p2) { Property1 = p1; Property2 = p2; }
    public string Property1 { get; }
    public Guid Property2 { get; }
    public static {Context}{VO} CreateInstance(string p1, Guid p2) => new(p1, p2);
}
```

### Aggregate Root
```csharp
using DigiTFactory.Libraries.SeedWorks.TacticalPatterns;

// Abstraction/I{Context}Root.cs
public interface I{Context}Root : IAggregateRoot<I{Context}> { /* свойства */ }
```

### Anemic Model
```csharp
using DigiTFactory.Libraries.SeedWorks.TacticalPatterns;
using DigiTFactory.Libraries.SeedWorks.Characteristics;

// Abstraction/I{Context}AnemicModel.cs
public interface I{Context}AnemicModel : IAnemicModel<I{Context}>
{
    I{Context}Root Root { get; }
    // другие Value Objects
}
```

### Aggregate (бизнес-методы)
```csharp
using DigiTFactory.Libraries.SeedWorks.Invariants;
using DigiTFactory.Libraries.SeedWorks.Result;
using DigiTFactory.Libraries.SeedWorks.Monads;

// Implementation/Aggregate.cs
public class Aggregate : I{Context}Aggregate
{
    private readonly I{Context}AnemicModel _anemicModel;
    private Aggregate(I{Context}AnemicModel m) => _anemicModel = m;
    public static Aggregate Create(I{Context}AnemicModel m) => new(m);

    public AggregateResult<I{Context}, I{Context}AnemicModel> {Command}(I{Context}AnemicModel model)
        => BusinessOperationData.Commit(_anemicModel, model)
            .ValidateCommand(new {Invariant}Validator());
}
```

### Specification (инвариант)
```csharp
using DigiTFactory.Libraries.SeedWorks.Invariants;
using DigiTFactory.Libraries.SeedWorks.Result;

// Specifications/{Name}Validator.cs
public class {Name}Validator : IBusinessOperationValidator<I{Context}, I{Context}AnemicModel>
{
    public bool IsSatisfiedBy(BusinessOperationData<I{Context}, I{Context}AnemicModel> obj)
        => /* условие */;
    public string Reason => "Описание причины отказа.";
    public DomainOperationResultEnum DomainResult => DomainOperationResultEnum.Exception;
}
```

## Слой Application — CQRS через MediatR

### Command
```csharp
using MediatR;

public class {Command}Command : IRequest<{Context}OperationResult>
{
    public Guid AggregateId { get; set; }
    // входные данные
}
```

### Command Handler
```csharp
using MediatR;
using DigiTFactory.Libraries.SeedWorks.Events;
using DigiTFactory.Libraries.SeedWorks.Result;

public class {Command}Handler : IRequestHandler<{Command}Command, {Context}OperationResult>
{
    private readonly I{Context}AggregateProvider _provider;
    public async Task<{Context}OperationResult> Handle({Command}Command request, CancellationToken ct)
    {
        var aggregate = await _provider.GetAggregateAsync(request.AggregateId, ct);
        var command = CommandToAggregate.Commit(Guid.NewGuid(), nameof({Command}), ...);
        var model = AnemicModel.Create(request.AggregateId, command, /* VOs */);
        var result = aggregate.{BusinessMethod}(model, command);
        return new {Context}OperationResult { /* маппинг */ };
    }
}
```

### Query
```csharp
using MediatR;

public class Get{Context}ByIdQuery : IRequest<List<I{Context}AnemicModel>>
{
    public Guid AggregateId { get; init; }
}
```

## Слой DomainServices — оркестрация

Каркасные файлы (копируются с подстановкой {Context}):
- `AggregateProvider` — загружает из репозитория, оборачивает в Notifier. Using: `DigiTFactory.Libraries.SeedWorks.TacticalPatterns`, `DigiTFactory.Libraries.SeedWorks.Events`
- `Notifier` — декоратор, проксирует бизнес-методы, рассылает результат подписчикам. Using: `DigiTFactory.Libraries.SeedWorks.Events`, `DigiTFactory.Libraries.SeedWorks.Reactive`
- `BusAdapter` — `IObserver<AggregateResult>`, публикует в `IEventBus`. Using: `DigiTFactory.Libraries.SeedWorks.Events`, `DigiTFactory.Libraries.SeedWorks.Result`
- `RegisterDependencies` — Autofac-модуль

## Слой Storage — проекции и Read Model

### Read Model
```csharp
using DigiTFactory.Libraries.SeedWorks.TacticalPatterns;

public class {Context}ReadModel : IReadModel<I{Context}>
{
    public Guid Id { get; set; }
    // колонки из артефакта 5 (Materialized Views)
    public long Version { get; set; }       // idempotency key
    public DateTimeOffset UpdatedAt { get; set; }
}
```

### Projection Handler
```csharp
using DigiTFactory.Libraries.SeedWorks.Events;
using DigiTFactory.Libraries.SeedWorks.TacticalPatterns;
using DigiTFactory.Libraries.SeedWorks.TacticalPatterns.Repository;

public class {Context}ProjectionHandler : IDomainEventHandler<I{Context}>, IObserver<IDomainEvent<I{Context}>>
{
    private readonly IReadModelStore<I{Context}, {Context}ReadModel> _store;
    private readonly IReadRepository<I{Context}, {Context}ReadModel> _reader;
    // проецирование из DomainEvent в ReadModel
}
```

### Rebuild Service
```csharp
using DigiTFactory.Libraries.SeedWorks.TacticalPatterns.Repository;

public class {Context}RebuildService : IRebuildService<I{Context}>
{
    // читает все события из Command DB → прогоняет через ProjectionHandler
}
```

## Слой Api — контроллеры и DI

```csharp
using MediatR;
using Microsoft.AspNetCore.Mvc;

[ApiController]
[Route("api/[controller]")]
public class {Context}Controller : ControllerBase
{
    private readonly IMediator _mediator;
    // POST → IMediator.Send(command) → Ok/BadRequest
    // GET  → IMediator.Send(query) → Ok
}
```

### Program.cs — DI регистрация
```csharp
// EventBus — из пакетов DigiTFactory.Libraries
using DigiTFactory.Libraries.EventBus.InMemory.Extensions;   // AddEventBusInMemory()
using DigiTFactory.Libraries.EventBus.Kafka.Extensions;      // AddEventBusKafka()
using DigiTFactory.Libraries.EventBus.Postgres.Extensions;   // AddEventBusPostgres()

// Command Store — из пакетов DigiTFactory.Libraries
using DigiTFactory.Libraries.CommandRepository.Mongo.Extensions;    // AddEventStoreMongo()
using DigiTFactory.Libraries.CommandRepository.Postgres.Extensions; // AddEventStorePostgres()

// Read Store — из пакетов DigiTFactory.Libraries
using DigiTFactory.Libraries.ReadRepository.Postgres.Extensions;  // AddReadStorePostgres()
using DigiTFactory.Libraries.ReadRepository.Redis.Extensions;     // AddReadStoreRedis()
using DigiTFactory.Libraries.ReadRepository.Scylla.Extensions;    // AddReadStoreScylla()

// Подписка Projection Handler на EventBus
using DigiTFactory.Libraries.SeedWorks.Events; // IEventBus
```

## Тесты

Паттерн:
1. Создать данные через Builder
2. `DefaultAnemicModel.Create(id)` → `Aggregate.Create(model)`
3. Вызвать бизнес-метод
4. `Assert.Equal(DomainOperationResultEnum.Success, result.Result)`

```csharp
using DigiTFactory.Libraries.SeedWorks.Result;
using DigiTFactory.Libraries.SeedWorks.Monads;
```

Обязательно тестировать:
- Happy path каждого бизнес-метода
- Провал каждого инварианта
- Порядок вызовов (state machine)

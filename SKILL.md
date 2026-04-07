
# EDM .NET — событийно-управляемые микросервисы на .NET

## Обзор

Этот навык помогает проектировать и генерировать событийно-управляемые микросервисы (EDM) на платформе **.NET** на основе:
- **DigiTFactory.Libraries** — фреймворк тактических паттернов DDD (пространство имён `DigiTFactory.Libraries.SeedWorks.*`)
- **CEQRS** (Command Event Query Responsibility Segregation) — архитектура с тремя деплойментами
- **Event Sourcing** — событие как источник истины, шина — центральный порт

Платформа: **.NET 8, C#, ASP.NET Core, MediatR, EF Core, Autofac**

Reference-проект: [Chat](https://github.com/Ekstrem/Chat)

> Это .NET-версия навыка. Этапы проектирования (1–5) платформонезависимы — канвасы, Command/Query API и Materialized Views одинаковы для любой платформы. Этапы реализации (6–10) специфичны для .NET + DigiTFactory.Libraries.

## Процесс работы

Проектирование микросервиса проходит через **5 артефактов проектирования**, затем генерацию кода, настройку инфраструктуры и деплоймент. Артефакты сохраняются в `Docs/Discovery/` репозитория микросервиса.

Определи на каком этапе находится пользователь и помоги продвинуться дальше:

```
ПРОЕКТИРОВАНИЕ (5 артефактов → Docs/Discovery/)
  1. Bounded Context Canvas    → references/bounded-context-canvas.md
  2. Aggregate Design Canvas   → references/aggregate-design-canvas.md
  3. Command API               → references/command-api.md
  4. Query API                 → references/query-api.md
  5. Materialized Views        → references/materialized-views.md

РЕАЛИЗАЦИЯ
  6. Генерация кода            → references/implementation-guide.md
  7. Инфраструктура            → references/ceqrs-data-flows.md
  8. Деплоймент                → references/deployment-profiles.md
  9. CI/CD                     → references/github-actions.md
  10. Интеграционные тесты     → references/integration-tests.md
  11. Верификация              → dotnet build + test перед коммитом
```

### Корреляция артефактов

Артефакты связаны сквозной цепочкой — названия и атрибуты коррелируют:

```
Артефакт 1               Артефакт 2                 Артефакт 3
Bounded Context   ──►    Aggregate Design    ──►    Command API
Canvas                   Canvas                     
  Inbound comm.            Секция 6:                  Эндпоинты POST
  Ubiquitous Lang.         Handled Commands           Request DTO (из входных VO)
  Business Rules           Секция 7:                  Response DTO (единый)
                           Created Events             Цепочка: Request → Command → Aggregate → Event
                           │
                           │
                           ▼
                         Артефакт 5                 Артефакт 4
                         Materialized    ──►        Query API
                         Views                      
                           Проекции из событий        Эндпоинты GET
                           Колонки таблиц             Response DTO (из колонок MV)
                           INSERT/UPDATE/DELETE       Один-к-одному: колонка MV → поле DTO
```

Ключевой принцип: **Command API → порождает события → проецируются в MV → отдаются через Query API**. Атрибуты коррелируют по всей цепочке.

---

### Этап 1 — Bounded Context Canvas

**Когда:** Пользователь описывает предметную область, бизнес-процесс, или просит «создать микросервис для X».

**Действия:**
1. Прочитай `references/bounded-context-canvas.md`
2. Помоги заполнить канвас через диалог — задавай вопросы по секциям
3. Результат: файл `Docs/Discovery/1-bounded-context-canvas.md`

**Выход артефакта:** границы контекста, Inbound/Outbound коммуникация, Ubiquitous Language, бизнес-правила.

### Этап 2 — Aggregate Design Canvas

**Когда:** Ограниченный контекст определён (артефакт 1 заполнен).

**Действия:**
1. Прочитай `references/aggregate-design-canvas.md`
2. Проведи через 9 секций канваса
3. Результат: файл `Docs/Discovery/2-aggregate-design-canvas.md`

**Маппинг секций:**
- Секции 1-2 (Name, Description) → имя контекста, Value Objects, Aggregate Root
- Секция 3 (State transitions) → логика бизнес-методов, валидаторы переходов
- Секция 4 (Enforced invariants) → `IBusinessOperationValidator` в Specifications/
- Секция 5 (Corrective policies) → Saga / Process Manager (если нужны)
- Секция 6 (Handled commands) → **вход для артефакта 3 (Command API)**
- Секция 7 (Created events) → **вход для артефакта 5 (Materialized Views)**
- Секции 8-9 (Throughput, Size) → выбор стратегии Event Store и профиля деплоймента

### Этап 3 — Command API

**Когда:** Aggregate Canvas заполнен. Секция 6 (Handled Commands) — входные данные.

**Действия:**
1. Прочитай `references/command-api.md`
2. Из каждой Handled Command определи:
   - HTTP-эндпоинт: `POST /api/v1/{context}` (создание) или `POST /api/v1/{context}/{id}/{action}` (действие)
   - Request DTO — из входных Value Objects команды (атрибуты коррелируют с VO)
   - Response DTO — единый `{Context}OperationResponse` для всех команд
3. Определи входящие события из шины (команды от других сервисов)
4. Результат: файл `Docs/Discovery/3-command-api.md`

**Выход артефакта:** таблица эндпоинтов, Request/Response DTO, цепочка Request → MediatR Command → метод агрегата → доменное событие. Названия коррелируют по всей цепочке.

### Этап 4 — Query API

**Когда:** Command API определён (артефакт 3). Materialized Views определены (артефакт 5) — или проектируются параллельно.

**Действия:**
1. Прочитай `references/query-api.md`
2. Для каждого потребителя (UI абонента, UI оператора, дашборд) определи:
   - HTTP-эндпоинт: `GET /api/v1/{context}/{id}`, `GET /api/v1/{context}?filter=...`
   - Response DTO — атрибуты один-к-одному с колонками Materialized View
3. Результат: файл `Docs/Discovery/4-query-api.md`

**Выход артефакта:** таблица GET-эндпоинтов, Response DTO с аннотацией «какая колонка какой MV». Query Side НЕ обращается к Domain и Event Store — только к Read Store.

### Этап 5 — Materialized Views

**Когда:** Aggregate Canvas заполнен (секция 7 — Created Events). Проектируется параллельно с Query API (артефакт 4) или перед ним.

**Действия:**
1. Прочитай `references/materialized-views.md`
2. Для каждого сценария чтения (UI абонента, очередь оператора, дашборд) определи:
   - Таблицу проекции с колонками
   - Маппинг: какое событие → какое действие (INSERT/UPDATE/DELETE) → какие колонки
   - Read Model класс: `{Name}ReadModel : IReadModel<I{Context}>`
3. Результат: файл `Docs/Discovery/5-materialized-views.md`

**Выход артефакта:** схема таблиц Read Store, проекционные правила (событие → действие), корреляция колонок с Query API Response DTO.

---

### Этап 6 — Генерация кода

**Когда:** Все 5 артефактов заполнены и смодерированы.

**Действия:**
1. Прочитай `references/implementation-guide.md` для правил слоёв и зависимостей
2. Генерируй слои в порядке:
   - **Domain**: из артефактов 1-2 → `I{Context}.cs`, Abstraction/, Implementation/, Specifications/
   - **DomainServices**: каркас → AggregateProvider, Notifier, BusAdapter, RegisterDependencies
   - **InternalContracts**: DTO команд, `IQueryRepository`
   - **Application**: из артефакта 3 → Commands/, из артефакта 4 → Queries/ (через MediatR)
   - **Api**: из артефактов 3-4 → Controllers, Request/Response DTO, версионирование
   - **Storage**: из артефакта 5 → CommandDbContext, Read Model классы, маппинг
   - **Tests**: AggregateTest, Builders

**Критические правила:**
- Domain зависит ТОЛЬКО от `DigiTFactory.Libraries.SeedWorks`
- Все доменные классы ИММУТАБЕЛЬНЫ: приватные конструкторы, фабричные методы
- Каждый бизнес-метод возвращает `AggregateResult<I{Context}, I{Context}AnemicModel>`
- Команда публикуется ТОЛЬКО в шину (IEventBus), НЕ напрямую в Event Store
- Event Consumer проецирует на три направления: Command DB, Read Store, Outbound handlers

### Этап 7 — Инфраструктура и потоки данных

**Когда:** Код написан, нужно настроить хранилища и шину.

**Действия:**
1. Прочитай `references/ceqrs-data-flows.md`
2. Помоги выбрать реализации:
   - **Command DB**: Postgres (EF Core) или MongoDB
   - **Event Bus**: InMemory (dev), Kafka (prod), Postgres Outbox (транзакционная гарантия)
   - **Read Store**: Postgres (SQL), Redis (кэш), ScyllaDB (масштаб)
3. Сгенерируй конфигурацию `appsettings.json` и DI в `Program.cs`

### Этап 8 — Деплоймент

**Когда:** Нужно выбрать профиль и настроить Docker/K8s.

**Действия:**
1. Прочитай `references/deployment-profiles.md`
2. Помоги выбрать профиль: Single → BudgetCqrs → Cqrs → Ceqrs
3. Сгенерируй Dockerfile и docker-compose

### Этап 9 — CI/CD (GitHub Actions)

**Когда:** Код и Dockerfile готовы. Всегда генерируется по умолчанию.

**Действия:**
1. Прочитай `references/github-actions.md`
2. Сгенерируй `.github/workflows/ci.yml` из шаблона с подстановкой `{Context}`
3. Сгенерируй `src/nuget.config` с источником GitHub Packages для DigiTFactory.Libraries
4. Пайплайн: build-and-test (каждый push/PR) → docker (push в main → GHCR)

### Этап 10 — Интеграционные тесты

**Когда:** Command API и Query API реализованы. Всегда генерируется по умолчанию.

**Действия:**
1. Прочитай `references/integration-tests.md`
2. Создай проект `{Context}.IntegrationTests` с зависимостью на `{Context}.Api` и `Microsoft.AspNetCore.Mvc.Testing`
3. Создай `{Context}WebApplicationFactory` с профилем Single (InMemory EventBus)
4. Сгенерируй тестовые классы из артефактов:
   - **Из State Transitions** (Aggregate Canvas секция 3) → `FullLifecycleTests` — сквозные цепочки состояний
   - **Из Handled Commands** (секция 6) → по одному классу на команду: позитивный + негативный сценарий
   - **Из Enforced Invariants** (секция 4) → `InvariantViolationTests` — каждый инвариант → тест на отказ
   - **Из Business Decisions** (BC Canvas секция 8) → тесты бизнес-правил
   - **Из Query API** (артефакт 4) → `QueryApiTests` — проверка проекций после команд
5. Каждый тест следует паттерну **Command → Query → Assert**: отправить команду через POST, прочитать через GET, проверить проекцию
6. Добавь шаг интеграционных тестов в `.github/workflows/ci.yml`

**Никаких моков инфраструктуры** — используются реальные реализации DigiTFactory.Libraries (InMemory EventBus, in-memory или тестовая БД).

### Этап 11 — Верификация (перед коммитом)

**Когда:** Код сгенерирован. ОБЯЗАТЕЛЬНО перед финальным коммитом. Также рекомендуется после каждого крупного этапа (6, 10).

**Действия:**
1. Спроси пользователя: **«Хотите собрать проект и прогнать тесты локально перед коммитом?»**
2. Если да — выполни последовательно:

```bash
# Шаг 1: Сборка
dotnet build src/{Context}.sln --configuration Release
# Если ошибки — исправь и повтори. НЕ переходи к тестам до успешной сборки.

# Шаг 2: Unit-тесты домена
dotnet test src/{Context}.Domain.Tests/{Context}.Domain.Tests.csproj --no-build --configuration Release --verbosity normal
# Если падают — исправь. Каждый тест должен быть зелёным.

# Шаг 3: Интеграционные тесты
dotnet test src/{Context}.IntegrationTests/{Context}.IntegrationTests.csproj --no-build --configuration Release --verbosity normal
# Если падают — исправь. Проверь что WebApplicationFactory использует профиль Single.
```

3. При ошибках сборки — **исправь и повтори**, не предлагай закоммитить с ошибками
4. При падении тестов — проанализируй причину, исправь код или тест, повтори
5. Только после зелёной сборки и всех тестов — предложи коммит

**Типичные ошибки при генерации:**
- Неправильные пространства имён → сверься с картой в `references/implementation-guide.md`
- Отсутствующие NuGet-пакеты → проверь .csproj зависимости
- Несовпадение сигнатур интерфейсов → проверь актуальную версию DigiTFactory.Libraries
- Projection Handler не подписан на EventBus → проверь Program.cs (DeploymentRole)

---

## Структура репозитория микросервиса

```
{Context}/
├── .github/
│   └── workflows/
│       └── ci.yml                            ← этап 9: CI/CD пайплайн
├── Docs/
│   └── Discovery/                            ← 5 артефактов проектирования
│       ├── 1-bounded-context-canvas.md
│       ├── 2-aggregate-design-canvas.md
│       ├── 3-command-api.md
│       ├── 4-query-api.md
│       └── 5-materialized-views.md
├── src/
│   ├── nuget.config                          ← NuGet + GitHub Packages
│   ├── {Context}.Domain/                     ← из артефактов 1-2
│   ├── {Context}.DomainServices/             ← каркас
│   ├── {Context}.InternalContracts/          ← DTO
│   ├── {Context}.Application/                ← из артефактов 3-4
│   ├── {Context}.Storage/                    ← из артефакта 5
│   ├── {Context}.Api/                        ← из артефактов 3-4
│   ├── {Context}.Domain.Tests/               ← unit-тесты домена
│   └── {Context}.IntegrationTests/           ← этап 10: интеграционные тесты
│       ├── Infrastructure/                   ← WebApplicationFactory, fixtures
│       ├── Scenarios/                        ← тесты из артефактов
│       └── Contracts/                        ← Request/Response DTO для тестов
├── Dockerfile
└── docker-compose.*.yml
```

## Ключевые принципы (всегда соблюдай)

1. **Домен в центре.** Domain не зависит ни от чего, кроме SeedWorks.
2. **Событие как источник истины.** Шина событий — центральный порт. БД — адаптер.
3. **Иммутабельность.** Никаких setter'ов в доменных моделях. Только фабричные методы.
4. **CEQRS.** Три потока: Command → Event Bus, Event Bus → Command DB + Read Store + Outbound, Query → Read Store.
5. **Трёхуровневая валидация.** Assertions → Validators → Success/Exception/Warnings.
6. **Корреляция артефактов.** Названия и атрибуты прослеживаются от канваса до колонки БД.

## КРИТИЧНО: использование DigiTFactory.Libraries

**Все инфраструктурные интерфейсы и базовые классы берутся ТОЛЬКО из NuGet-пакетов `DigiTFactory.Libraries.*`.**

**Пространства имён:** При генерации кода ВСЕГДА сверяйся с картой пространств имён в `references/implementation-guide.md`. Корневое пространство — `DigiTFactory.Libraries.SeedWorks`. Каждый шаблон кода в implementation-guide.md содержит правильные `using`-блоки — копируй их.

Цель проекта DigiTFactory.Libraries — вынести повторяющуюся логику в общие библиотеки, чтобы команды сосредоточились на доменном моделировании. Использование носит **обязательный** характер.

### ЗАПРЕЩЕНО

- **НЕ создавать** собственные реализации `IEventBus`, `IEventBusProducer`, `IEventBusConsumer` — использовать `EventBus.InMemory`, `EventBus.Kafka` или `EventBus.Postgres`
- **НЕ создавать** собственные реализации `IAnemicModelRepository` — использовать `CommandRepository.Postgres` или `CommandRepository.Mongo`
- **НЕ создавать** собственные реализации `IReadRepository`, `IReadModelStore` — использовать `ReadRepository.Postgres`, `ReadRepository.Redis` или `ReadRepository.Scylla`
- **НЕ создавать** обёртки, адаптеры, прокси вокруг интерфейсов SeedWorks
- **НЕ создавать** заглушки (stubs) для `IValueObject`, `IAggregateRoot`, `IAnemicModel`, `IAggregate`, `IBoundedContext`, `IBusinessOperationValidator`, `AggregateResult`, `BusinessOperationData`, `DomainEvent`, `CommandToAggregate` — всё это уже есть в `SeedWorks`
- **НЕ переопределять** `ValidateCommand`, `DomainEventNotifier`, `Unsubscriber`, монады (`PipeTo`, `Do`, `Either`, `Result<T,E>`) — использовать из SeedWorks
- **НЕ писать** свой DI-регистратор для EventBus/Repository/ReadStore — использовать extension-методы из пакетов: `AddEventBusInMemory()`, `AddEventBusKafka(options)`, `AddEventStorePostgres(...)`, `AddReadStoreRedis(...)` и т.д.

### РАЗРЕШЕНО создавать в микросервисе

Только то, что **уникально для данного ограниченного контекста**:

| Что создаётся в микросервисе | Пример |
|------------------------------|--------|
| `I{Context} : IBoundedContext` | `IChat : IBoundedContext` |
| Value Objects (интерфейсы + реализации) | `IChatMessage : IValueObject`, `ChatMessage` |
| Aggregate Root | `IChatRoot : IAggregateRoot<IChat>` |
| Anemic Model (интерфейс + реализация) | `IChatAnemicModel : IAnemicModel<IChat>` |
| Aggregate (бизнес-методы) | `Aggregate : IChatAggregate` |
| Specifications (валидаторы) | `IsNewSubscriberRequestValidator : IBusinessOperationValidator<IChat, IChatAnemicModel>` |
| MediatR Commands и Queries | `SubscriberRequestQuestionCommand : IRequest<...>` |
| Command/Query Handlers | `SubscriberRequestQuestionHandler : IRequestHandler<...>` |
| REST Controllers | `ChatController : ControllerBase` |
| Request/Response DTO | `SubscriberRequestQuestionRequest`, `ChatOperationResponse` |
| Read Model классы | `ChatSessionReadModel : IReadModel<IChat>` |
| Projection Handlers | Маппинг DomainEvent → ReadModel |
| Notifier (декоратор агрегата) | Проксирование бизнес-методов + Observer |
| BusAdapter | `IObserver<AggregateResult>` → `IEventBus.Publish` |
| AggregateProvider | Загрузка агрегата из репозитория |
| Тесты | `AggregateTest`, Builders |

### Граф NuGet-зависимостей микросервиса

```
{Context}.Domain.csproj
    → DigiTFactory.Libraries.SeedWorks

{Context}.DomainServices.csproj
    → DigiTFactory.Libraries.SeedWorks
    → {Context}.Domain
    → {Context}.InternalContracts

{Context}.Storage.csproj
    → DigiTFactory.Libraries.CommandRepository.Postgres  (или .Mongo)
    → DigiTFactory.Libraries.ReadRepository.Postgres     (или .Redis / .Scylla)
    → {Context}.DomainServices
    → {Context}.InternalContracts

{Context}.Api.csproj
    → DigiTFactory.Libraries.EventBus.InMemory           (или .Kafka / .Postgres)
    → {Context}.Application
```

**Если интерфейс существует в DigiTFactory.Libraries — используй его. Если реализация существует в одном из пакетов — подключи пакет. Никогда не дублируй.**

**Пакеты опубликованы на nuget.org** — дополнительная аутентификация не требуется. `dotnet restore` работает из коробки.

## Библиотеки DigiTFactory

| Пакет | Назначение |
|-------|-----------|
| `SeedWorks` | Ядро: интерфейсы, базовые классы, монады |
| `CommandRepository.Postgres` | Event Store на PostgreSQL |
| `CommandRepository.Mongo` | Event Store на MongoDB |
| `EventBus.InMemory` | Шина для dev/тестов |
| `EventBus.Kafka` | Шина для продакшена |
| `EventBus.Postgres` | Шина через Outbox-таблицу |
| `ReadRepository.Postgres` | Read Store на PostgreSQL |
| `ReadRepository.Redis` | Read Store на Redis |
| `ReadRepository.Scylla` | Read Store на ScyllaDB |

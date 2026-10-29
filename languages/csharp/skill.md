---
name: ddd-microservice-csharp
description: "Use when designing or implementing an event-driven microservice on .NET/C# with DDD, Event Sourcing and CEQRS on DigiTFactory.Libraries (событийно-управляемые микросервисы на .NET). Covers the five design canvases, Command/Query API, Materialized Views, layer and namespace rules, deployment profiles, Kubernetes, CI/CD and the improvement roadmap."
---

# EDM .NET — событийно-управляемые микросервисы на .NET

Навык ведёт микросервис от предметной области до задеплоенного кода. Пять этапов
проектирования платформонезависимы, дальше — .NET-специфика.

Платформа: **.NET 8, C#, ASP.NET Core, MediatR, EF Core, Autofac, DigiTFactory.Libraries**.

Reference-проект: [Chat](https://github.com/Ekstrem/Chat)

## Маршрут по этапам

| # | Шаг | Читай |
|---|-----|-------|
| 1 | Bounded Context Canvas — границы контекста, inbound/outbound, ubiquitous language | `references/bounded-context-canvas.md` |
| 2 | Aggregate Design Canvas — состояние, инварианты, handled commands, created events | `references/aggregate-design-canvas.md` |
| 3 | Command API — POST-эндпоинты, Request/Response DTO, цепочка Request → Command → Aggregate → Event | `references/command-api.md` |
| 4 | Query API — GET-эндпоинты и Response DTO строго из колонок Materialized View | `references/query-api.md` |
| 5 | Materialized Views — таблицы Read Store и правила проекции событий | `references/materialized-views.md` |
| 6 | Реализация на C# — слои, пространства имён, шаблоны кода | `references/implementation-guide.md` |
| 7 | Инфраструктура и потоки данных — Command DB, Event Store, Read Store, шина | `references/ceqrs-data-flows.md` |
| 8 | Профили деплоймента — Single → BudgetCqrs → Cqrs → Ceqrs, Dockerfile | `references/deployment-profiles.md` |
| 9 | Kubernetes — Kustomize-манифесты под выбранный профиль | `references/kubernetes.md` |
| 10 | CI/CD — `.github/workflows/ci.yml`, сборка, тесты, образ в GHCR | `references/github-actions.md` |
| 11 | Roadmap улучшений CEQRS — обсуждение, не для генерации кода | `references/roadmap.md` |

Читай `references/*.md` по мере надобности, а не все сразу: файлы крупные, и каждый
относится к своему этапу. Пути резолвь от каталога навыка.

## Порядок работы

1. Определи, на каком этапе пользователь: он описывает предметную область (этап 1),
   есть канвас контекста (2), есть канвас агрегата (3), нужен код (6), инфраструктура (7+).
2. Не перескакивай через проектирование: без канвасов код получится нерелевантным.
   Исключение — явная просьба «просто покажи пример».
3. Артефакты проектирования сохраняй в `Docs/Discovery/` репозитория микросервиса
   (`1-bounded-context-canvas.md` … `5-materialized-views.md`).
4. Названия и атрибуты коррелируют по всей цепочке: канвас → Command API → событие →
   проекция → колонка БД → поле Response DTO. Расхождение — баг проектирования.
5. Перед коммитом сгенерированного кода собери и прогони тесты
   (`dotnet build`, `dotnet test`), при ошибках исправь и повтори, а не предлагай
   коммитить как есть.

## Ключевые принципы

1. **Домен в центре.** Domain зависит ТОЛЬКО от `DigiTFactory.Libraries.SeedWorks`.
2. **Событие — источник истины.** Шина событий — центральный порт, БД — адаптер.
3. **Иммутабельность.** Приватные конструкторы и фабричные методы, никаких установщиков.
4. **CEQRS — три потока.** Command → Event Bus; Event Bus → Command DB + Read Store + outbound;
   Query → только Read Store.
5. **Трёхуровневая валидация.** Assertions → Validators → Success/Exception/Warnings.
6. **Никаких самодельных реализаций** `IEventBus`, `IAnemicModelRepository`, `IReadRepository`,
   обёрток и заглушек вокруг SeedWorks. Всё инфраструктурное берётся из NuGet-пакетов
   `DigiTFactory.Libraries.*`: `EventBus.InMemory`/`Kafka`/`Postgres`,
   `CommandRepository.Postgres`/`Mongo`, `ReadRepository.Postgres`/`Redis`/`Scylla`.
   Пакеты опубликованы на nuget.org, `dotnet restore` работает без токена.
7. **Своё пишем только уникальное для контекста**: `I{Context}`/`{Context}`, VO, агрегат,
   anemic model, спецификации, команды/запросы MediatR, контроллеры, DTO, read models,
   проекции, тесты. Точные пространства имён — в `references/implementation-guide.md`.

---
name: edm-go
description: "Use when designing or implementing an event-driven microservice on Go with DDD, Event Sourcing and CEQRS on DigiTFactory.Go.Libraries (событийно-управляемые микросервисы). Covers the five design canvases, Command/Query API, Materialized Views, Go layering and package graph, deployment profiles, Kubernetes, CI/CD, domain tests and the service README template."
---

# EDM на Go — событийно-управляемые микросервисы

Навык ведёт микросервис от предметной области до задеплоенного кода. Пять этапов
проектирования платформонезависимы, дальше — Go-специфика.

Платформа: **Go 1.22+, DigiTFactory.Go.Libraries, Kafka/InMemory EventBus, PostgreSQL**.

## Маршрут по этапам

| # | Шаг | Читай |
|---|-----|-------|
| 1 | Bounded Context Canvas — границы контекста, inbound/outbound, ubiquitous language | `references/bounded-context-canvas.md` |
| 2 | Aggregate Design Canvas — состояние, инварианты, handled commands, created events | `references/aggregate-design-canvas.md` |
| 3 | Command API — POST-эндпоинты, Request/Response DTO, цепочка Request → Command → Aggregate → Event | `references/command-api.md` |
| 4 | Query API — GET-эндпоинты и Response DTO строго из колонок Materialized View | `references/query-api.md` |
| 5 | Materialized Views — таблицы Read Store и правила проекции событий | `references/materialized-views.md` |
| 6 | Реализация на Go — слои, граф пакетов, шаблоны кода | `references/implementation-guide.md` |
| 7 | Инфраструктура и потоки данных — Command DB, Event Store, Read Store, шина | `references/ceqrs-data-flows.md` |
| 8 | Профили деплоймента — Single → BudgetCqrs → Cqrs → Ceqrs, Dockerfile | `references/deployment-profiles.md` |
| 9 | Kubernetes — Kustomize-манифесты под выбранный профиль | `references/kubernetes.md` |
| 10 | CI/CD — `.github/workflows/ci.yml`, сборка, тесты, образ в registry | `references/github-actions.md` |
| 11 | Тесты домена — unit-тесты агрегата без инфраструктуры | `references/domain-tests.md` |
| 12 | README сервиса — шаблон документации по артефактам | `references/readme-template.md` |
| 13 | Roadmap улучшений CEQRS — обсуждение, не для генерации кода | `references/roadmap.md` |

Читай `references/*.md` по мере надобности, а не все сразу: файлы крупные, и каждый
относится к своему этапу. Пути резолвь от каталога навыка.

## Порядок работы

1. Определи, на каком этапе пользователь: он описал предметную область (этап 1),
   уже есть канвас (2), есть канвас агрегата (3), нужен код (6) или инфраструктура (7+).
2. Не перескакивай через проектирование: без канваса контекста и агрегата код
   получится нерелевантным. Исключение — явная просьба «просто покажи пример».
3. Артефакты проектирования сохраняй в `Docs/Discovery/` репозитория микросервиса
   (`1-bounded-context-canvas.md` … `5-materialized-views.md`).
4. Названия и атрибуты коррелируют по всей цепочке: канвас → Command API → событие →
   проекция → колонка БД → поле Response DTO. Расхождение — баг проектирования.
5. Перед коммитом сгенерированного кода собери и прогони тесты (`go build ./...`,
   `go test ./... -v`), при ошибках исправь и повтори, а не предлагай коммитить как есть.

## Ключевые принципы

1. **Домен в центре.** Domain не зависит ни от чего, кроме `seedworks`.
2. **Событие — источник истины.** Шина событий — центральный порт, БД — адаптер.
3. **Иммутабельность.** Никаких установщиков полей в доменных моделях, только фабричные функции.
4. **CEQRS — три потока.** Command → Event Bus; Event Bus → Command DB + Read Store + outbound;
   Query → только Read Store.
5. **Трёхуровневая валидация.** Assertions → Validators → Success/Exception/Warnings.
6. **Никаких самодельных адаптеров.** Интерфейсы и реализации — только из
   `DigiTFactory.Go.Libraries` (`seedworks`, `eventbus-*`, `commandrepository-postgres`,
   `readrepository-postgres`/`-redis`/`-scylla`). Своё пишем только то, что уникально для
   контекста: VO, агрегат, anemic model, спецификации, команды/запросы, контроллеры, DTO,
   read models, проекции, тесты. Точные import paths — в `references/implementation-guide.md`.

---
name: edm-kotlin
description: "Use when designing or implementing an event-driven microservice on Kotlin/JVM with DDD, Event Sourcing and CEQRS on DigiTFactory.Kotlin.Libraries (событийно-управляемые микросервисы на Kotlin). Covers the five design canvases, Command/Query API, Materialized Views, Gradle module graph, deployment profiles, Kubernetes, integration tests with JUnit 5 and Ktor."
---

# EDM Kotlin/JVM — событийно-управляемые микросервисы

Навык ведёт микросервис от предметной области до задеплоенного кода. Пять этапов
проектирования платформонезависимы, дальше — Kotlin/JVM-специфика.

Платформа: **Kotlin 2.x, Ktor 3, Koin, Exposed, JUnit 5, DigiTFactory.Kotlin.Libraries**.

## Маршрут по этапам

| # | Шаг | Читай |
|---|-----|-------|
| 1 | Bounded Context Canvas — границы контекста, inbound/outbound, ubiquitous language | `references/bounded-context-canvas.md` |
| 2 | Aggregate Design Canvas — состояние, инварианты, handled commands, created events | `references/aggregate-design-canvas.md` |
| 3 | Command API — POST-эндпоинты, Request/Response DTO, цепочка Request → Command → Aggregate → Event | `references/command-api.md` |
| 4 | Query API — GET-эндпоинты и Response DTO строго из колонок Materialized View | `references/query-api.md` |
| 5 | Materialized Views — таблицы Read Store и правила проекции событий | `references/materialized-views.md` |
| 6 | Реализация на Kotlin — модули, Gradle-каталог версий, шаблоны кода | `references/implementation-guide.md` |
| 7 | Инфраструктура и потоки данных — Command DB, Event Store, Read Store, шина | `references/ceqrs-data-flows.md` |
| 8 | Профили деплоймента — Single → BudgetCqrs → Cqrs → Ceqrs, Dockerfile | `references/deployment-profiles.md` |
| 9 | Kubernetes — Kustomize-манифесты под выбранный профиль | `references/kubernetes.md` |
| 10 | Интеграционные тесты — JUnit 5, Builder, Ktor `testApplication` | `references/integration-tests.md` |
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
5. Перед коммитом сгенерированного кода собери и прогони тесты (`gradle build`),
   при ошибках исправь и повтори, а не предлагай коммитить как есть.

## Ключевые принципы

1. **Домен в центре.** Модуль `*-domain` не зависит ни от чего, кроме `seedworks`.
2. **Событие — источник истины.** Шина событий — центральный порт, БД — адаптер.
3. **Иммутабельность.** `data class` без `var`, состояние меняется через фабричные методы.
4. **CEQRS — три потока.** Command → Event Bus; Event Bus → Command DB + Read Store + outbound;
   Query → только Read Store.
5. **Трёхуровневая валидация.** Assertions → Validators → Success/Exception/Warnings.
6. **Никаких самодельных реализаций** шины, репозиториев и read store. Всё инфраструктурное
   берётся из Maven-артефактов `io.github.ekstrem`: `seedworks`, `eventbus-inmemory`,
   `eventbus-kafka`, `eventbus-postgres`, `commandrepository-postgres`,
   `readrepository-postgres`. Своё пишем только уникальное для контекста: VO, агрегат,
   anemic model, спецификации, команды/запросы, контроллеры, DTO, read models, проекции,
   тесты. Точные координаты и граф модулей — в `references/implementation-guide.md`.

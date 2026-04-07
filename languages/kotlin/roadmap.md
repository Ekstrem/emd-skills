# Roadmap: улучшения CEQRS-архитектуры

> Сохранено для обсуждения. Все пункты потенциально спорны и требуют ревью.

---

## 1. Конкурентный доступ к агрегату

**Статус:** ⚠️ Спорный — требует обсуждения подхода

**Что есть:**
- Оптимистичная блокировка через `Version` (Unix timestamp) — составной ключ `(Id, Version)` в Event Store
- `FOR UPDATE SKIP LOCKED` в Postgres EventBus Consumer для конкурентного чтения outbox

**Чего не хватает:**
- Нет пессимистичной блокировки агрегата при обработке команды — если два запроса одновременно загрузят один агрегат, оба создадут события с разными версиями, и конфликт не обнаружится
- Нет `ConcurrencyException` и retry-логики
- Нет распределённой блокировки (Redis distributed lock / advisory lock в PostgreSQL)

**Варианты решения:**
- `SELECT FOR UPDATE` при загрузке агрегата из Postgres
- Advisory lock по `AggregateId` в PostgreSQL
- Redis distributed lock для Mongo-профилей
- `ConcurrencyException` с автоматическим retry в `CommandHandler`

**Открытые вопросы:**
- Нужна ли пессимистичная блокировка, если Version-based optimistic concurrency достаточна?
- Как это влияет на throughput при высокой конкурентности?

---

## 2. Регидратация проекций

**Статус:** 🟡 Запланирован к реализации

**Что есть:**
- Инфраструктура снапшотов: `SnapshotRepository` (Postgres/Mongo), стратегии `FullEventSourcing` / `SnapshotAfterN` / `StateOnly`
- `IReadModelStore.UpsertAsync()` для обновления проекций из событий

**Чего не хватает:**
- `TODO: Десериализовать snapshot` — код снапшотов не реализован до конца
- Нет команды **Rebuild** — перестроить все проекции из Event Store
- Нет идемпотентности проекций (повторная обработка события может создать дубли)
- Нет catch-up подписки (при запуске нового Read Store — догнать историю)

**План:**
- Реализовать `IRebuildService` — читает все события из Command DB в хронологическом порядке, прогоняет через Projection Handler
- Добавить idempotency key (Version) в Read Model для безопасного повторного проецирования
- Catch-up подписка при первом старте нового Read Store

---

## 3. Оптимизация сериализации

**Статус:** 🟡 Запланирован к реализации

**Что есть:**
- `System.Text.Json` в инфраструктуре (EventBus.Kafka, EventBus.Postgres, ReadRepository.Redis/Scylla)
- `Newtonsoft.Json` в Chat.DomainServices (BusAdapter, Extension)

**Проблемы:**
- Несогласованность: два сериализатора в одном приложении
- JSON — текстовый формат, избыточен для высоких нагрузок
- Нет schema versioning / upcasting при изменении формата событий

**План:**
1. **Краткосрочно:** Унифицировать на `System.Text.Json` (убрать Newtonsoft из Chat.DomainServices)
2. **Среднесрочно:** Ввести `IEventSerializer` абстракцию в SeedWorks, с реализациями Json / MessagePack / Protobuf
3. **Долгосрочно:** Event versioning — добавить `SchemaVersion` в `DomainEventEnvelope`, реализовать upcaster для миграции старых событий

---

## 4. Нагрузка на Read DB / Кэширование

**Статус:** ⚠️ Спорный — IMemoryCache нарушает Cloud Native / K8s принципы

**Что есть:**
- 3 варианта Read Store (Postgres / Redis / ScyllaDB)
- TTL в Redis для автоматического истечения кэша
- ScyllaDB для горизонтального масштабирования

**Проблема IMemoryCache:**
- В K8s каждый pod имеет свой экземпляр in-memory кэша
- Инвалидация между подами требует дополнительной координации (pub/sub)
- Противоречит stateless-принципу Cloud Native
- При скейлинге — cold start каждого нового пода

**Альтернативный подход (Cloud Native):**
- Redis как единственный кэш-уровень (уже реализован как Read Store)
- ScyllaDB для горизонтального масштабирования чтения
- CDN / API Gateway кэширование для GET-запросов
- Правильный выбор профиля деплоймента решает проблему нагрузки

**Вывод:** Пункт закрыт выбором правильного Read Store профиля (Redis/ScyllaDB). IMemoryCache не нужен.

---

## Приоритеты

| Приоритет | Задача | Влияние | Статус |
|-----------|--------|---------|--------|
| 🔴 Высокий | Унифицировать сериализацию (убрать Newtonsoft) | Стабильность | Запланирован |
| 🔴 Высокий | Конкурентный доступ к агрегату | Целостность данных | Спорный |
| 🟡 Средний | Rebuild проекций из Event Store | Операционная надёжность | Запланирован |
| 🟡 Средний | Кэширование Read Store | Перформанс | Закрыт (Redis/ScyllaDB) |
| 🟢 Низкий | MessagePack/Protobuf сериализация | Оптимизация | Будущее |
| 🟢 Низкий | Event versioning / upcasting | Эволюция схемы | Будущее |

---

*Документ создан: 2026-03-14*
*Контекст: Chat микросервис + DigiTFactory.Libraries (Hive)*

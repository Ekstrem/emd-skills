# Roadmap: улучшения Go CEQRS-архитектуры

> Сохранено для обсуждения. Все пункты потенциально спорны и требуют ревью.

---

## 1. Health endpoint

**Статус:** 🔴 Требуется немедленно

Kubernetes liveness/readiness probes ожидают `GET /health`. Текущая реализация Chat.Go не включает этот эндпоинт.

**Решение:** Добавить в router:
```go
r.Get("/health", func(w http.ResponseWriter, r *http.Request) {
    w.WriteHeader(http.StatusOK)
    json.NewEncoder(w).Encode(map[string]string{"status": "ok"})
})
```

---

## 2. Конкурентный доступ к агрегату

**Статус:** ⚠️ Спорный

- Оптимистичная блокировка через Version (Id + Version) в Event Store
- Нет пессимистичной блокировки при обработке команды
- Нет `ConcurrencyException` и retry-логики

**Варианты:**
- `SELECT FOR UPDATE` в PostgreSQL
- Advisory lock по AggregateId
- Redis distributed lock

---

## 3. Регидратация проекций

**Статус:** 🟡 Частично реализован

- RebuildService существует (admin endpoint)
- Идемпотентность через version check
- Нет catch-up подписки при первом старте нового Read Store

---

## 4. Graceful shutdown для EventBus consumers

**Статус:** 🟡 Запланирован

Kafka consumer должен корректно останавливаться при SIGTERM:
- Дождаться обработки текущего батча
- Закоммитить offsets
- Закрыть соединение

---

## 5. Structured logging

**Статус:** 🟢 Реализован

Go 1.23+ — `log/slog` используется повсеместно. Рассмотреть JSON-формат для K8s.

---

## Приоритеты

| Приоритет | Задача | Влияние | Статус |
|-----------|--------|---------|--------|
| 🔴 Высокий | Health endpoint | K8s probes | Немедленно |
| 🔴 Высокий | Конкурентный доступ | Целостность | Спорный |
| 🟡 Средний | Catch-up подписка | Надёжность | Запланирован |
| 🟡 Средний | Graceful shutdown Kafka | Стабильность | Запланирован |
| 🟢 Низкий | JSON logging | Observability | Реализован |

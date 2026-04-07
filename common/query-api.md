# Query API — проектирование

> API для потребителей, запрашивающих состояние.
> Вход: Materialized Views (артефакт 5).
> Атрибуты Response DTO один-к-одному с колонками MV.
> Query Side НЕ обращается к Domain и Event Store — только к Read Store.

## Принцип проектирования

Каждый GET-эндпоинт обслуживает конкретный сценарий чтения конкретного потребителя. Response DTO отражает колонки Materialized View — не доменную модель.

| Тип запроса | HTTP-метод | URI-паттерн |
|------------|-----------|-------------|
| Получение по ID | `GET` | `/api/{context}/{id}` |
| Получение списка с фильтром | `GET` | `/api/{context}?filter=value` |
| Специализированный запрос | `GET` | `/api/{context}/{id}/{aspect}` |

## Response DTO

**Правила:**
- Каждое поле Response DTO соответствует колонке конкретной Materialized View
- Аннотируй корреляцию: `поле ← MV: таблица.колонка`
- Response для списков включает `items[]` + `total`

## Потребители

Определи, кто читает данные, и создай эндпоинты под их сценарии:

| Потребитель | Что ему нужно | MV-источник |
|------------|--------------|-------------|
| UI клиента | Свои сессии, история | {ctx}_sessions |
| UI оператора | Очередь, работа с сессией | {ctx}_queue |
| Дашборд | Статистика | {ctx}_stats |

## Цепочка: MV → QueryHandler → Response

```
GET /api/{context}/{id}
  → GetChatByIdHandler.Handle(ctx, id)
    → eventStore.GetByID(ctx, id) или readStore.GetByIDAsync(ctx, id)
      → SELECT * FROM read_model.{table} WHERE id = @id
```

QueryHandler максимально простой — один вызов к Read Store.

## Шаблон артефакта

```markdown
# Query API: {Context}

## HTTP-эндпоинты

| # | Метод | URI | Описание | Response DTO | MV-источник |
|---|-------|-----|----------|-------------|------------|
| 1 | GET | /api/{ctx}/{id} | Детали | {Detail}Response | {table} |
| 2 | GET | /api/{ctx}?filter= | Список | {List}Response | {table} |

## Response DTO

### {Detail}Response
```go
type {Detail}Response struct {
    Field1 type `json:"field1"` // ← MV: {table}.{column}
    Field2 type `json:"field2"` // ← MV: {table}.{column}
}
```

## Потребители

| Потребитель | Эндпоинты | Назначение |
|------------|-----------|-----------|
```

## Как заполнять через диалог

1. «Кто будет читать данные? Перечислите потребителей (UI, дашборд, интеграции).»
2. «Для каждого потребителя: какие данные ему нужны? В каком формате?»
3. «Нужны ли фильтры, пагинация, сортировка?»
4. «Нужна ли агрегированная статистика?»

Артефакты 4 и 5 проектируются параллельно: Query API определяет ЧТО нужно показать, Materialized Views определяют КАК это хранить.

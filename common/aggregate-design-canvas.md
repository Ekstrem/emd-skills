# Aggregate Design Canvas — шаблон и инструкция

## Назначение

Aggregate Design Canvas — тактический артефакт. Один файл на агрегат.
Описывает КАК устроен агрегат внутри. Заполняется после Bounded Context Canvas.

## Шаблон канваса

```markdown
# Aggregate Design Canvas: {AggregateName}

## 1. Name (Имя)
Название агрегата и его жизненный цикл.
- Имя: {AggregateName}
- Создаётся когда: {условие}
- Завершается когда: {условие}

## 2. Description (Описание)
Назначение и границы агрегата. Какие данные он защищает.

Value Objects:
- **Root** ({Context}Root): {свойства корня}
- **{VO1}**: {свойства}
- **{VO2}**: {свойства}

## 3. State Transitions (Переходы состояний)
{Состояние A} → [Команда] → {Состояние B}

## 4. Enforced Invariants (Обязательные инварианты)
- Инвариант 1: {описание}
- Инвариант 2: {описание}

## 5. Corrective Policies (Компенсирующие действия)
- Политика 1: если {условие}, то {действие}

## 6. Handled Commands (Обрабатываемые команды)
| Команда | Входные VO | Описание |
|---------|-----------|----------|
| {CommandName} | Root, {VO} | {что делает} |

## 7. Created Events (Порождаемые события)
| Событие | Изменённые VO | Когда порождается |
|---------|--------------|-------------------|
| {EventName} | Root, {VO} | После {CommandName} |

## 8. Throughput (Пропускная способность)
- Ожидаемая частота команд: {N} tps
- Конкурентность: {описание}
- Один клиент — один агрегат? Да/Нет

## 9. Size (Размер)
- Ожидаемое количество событий за жизнь: {N}
- Время жизни агрегата: {часы/дни/годы}
- Необходимость снапшотов: Да/Нет
```

## Как заполнять через диалог

1. «Как называется агрегат? Когда он создаётся и когда завершает жизненный цикл?» → секция 1
2. «Какие данные агрегат содержит? Перечислите свойства.» → секция 2 (Value Objects)
3. «Через какие состояния проходит агрегат?» → секция 3
4. «Какие правила ОБЯЗАТЕЛЬНО должны соблюдаться?» → секция 4
5. «Если что-то пошло не так — какие компенсирующие действия?» → секция 5
6. «Какие команды агрегат принимает? Что каждая делает?» → секция 6
7. «Какие события порождаются после каждой команды?» → секция 7
8. «Какая ожидаемая нагрузка? Сколько запросов в секунду?» → секция 8
9. «Сколько событий за жизнь агрегата? Как долго он живёт?» → секция 9

## Маппинг на Go-код DigiTFactory.Go.Libraries

| Секция | Артефакт в коде |
|--------|----------------|
| 1. Name | `var {Context}BoundedContext = definition.BoundedContextDescription{...}`, имя `{Context}Aggregate` |
| 2. Description → VOs | Structs в `internal/domain/{ctx}.go`: `{Context}Root`, `{Context}Message` и т.д. |
| 2. Description → Root | `{Context}Root` struct с ключевыми полями |
| 3. State transitions | Логика внутри `AggregateBusinessOperation.Handle()`, спецификации |
| 4. Invariants | Structs в `internal/domain/specifications/`: реализации `invariants.BusinessOperationSpecification` |
| 5. Corrective policies | Saga / Process Manager — Outbound Handler в Event Consumer |
| 6. Commands | Операции в `Aggregate.Operations` map + Command structs в `internal/application/commands/` |
| 7. Events | `events.DomainEvent`, `ChangedValueObjects` в `AggregateResult` |
| 8. Throughput | Выбор профиля деплоймента (Single → Ceqrs) |
| 9. Size | Стратегия Event Store: FullEventSourcing / SnapshotAfterN / StateOnly |

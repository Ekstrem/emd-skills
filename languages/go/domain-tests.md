# Тесты домена

## Назначение

Unit-тесты проверяют бизнес-логику агрегата без инфраструктуры.
Файлы: `test/aggregate_test.go`, `test/builders.go`.

## Структура

```
test/
├── aggregate_test.go     # Тестовые сценарии
└── builders.go           # Builder-ы для создания тестовых данных
```

## Builders (test/builders.go)

Builders создают тестовые данные для каждой операции агрегата.

```go
package test

import (
    "github.com/google/uuid"
    "{module}/internal/domain"
    "github.com/Ekstrem/DigiTFactory.Go.Libraries/seedworks/events"
    "github.com/Ekstrem/DigiTFactory.Go.Libraries/seedworks/tacticalpatterns"
)

// Scope и Aggregate — переиспользуемые
func newScope() *domain.{Context}Scope {
    return &domain.{Context}Scope{}
}

func newAggregate() *tacticalpatterns.Aggregate {
    return tacticalpatterns.NewAggregate(newScope())
}

// Builder для каждой операции
func build{Command}Model(id uuid.UUID) *domain.{Context}AnemicModel {
    vos := map[string]any{
        domain.VoRoot:    domain.{Context}Root{UserId: uuid.New(), SessionId: 1},
        domain.VoMessage: domain.{Context}Message{Type: 0, Text: "Test message"},
    }
    return domain.New{Context}AnemicModel(id, 0, uuid.Nil, "", "", vos)
}

func build{Command}Cmd() *events.CommandToAggregateData {
    return events.NewCommandToAggregateNow(uuid.New(), 0, domain.Op{Command}, "Subject")
}

// Helpers для цепочек операций
func executeOperation(agg *tacticalpatterns.Aggregate, opName string, model tacticalpatterns.AnemicModel, cmd *events.CommandToAggregateData) *result.AggregateResult {
    scope := newScope()
    op := agg.Operations[opName]
    return op.Handle(model, cmd, scope)
}
```

## Тестовые сценарии (test/aggregate_test.go)

### Паттерн теста

```go
func Test{Command}_Success(t *testing.T) {
    // Arrange
    id := uuid.New()
    agg := newAggregate()
    model := build{Command}Model(id)
    cmd := build{Command}Cmd()

    // Act
    res := executeOperation(agg, domain.Op{Command}, model, cmd)

    // Assert
    assert.Equal(t, result.Success, res.Result())
}
```

### Обязательные сценарии

Из артефактов проектирования генерируются следующие тесты:

#### 1. Happy path каждой операции

Из секции 6 (Handled Commands) Aggregate Canvas — по одному тесту на каждую команду:

```go
func TestSubscriberRequestQuestion_Success(t *testing.T) { ... }
func TestOperatorDequeueRequest_Success(t *testing.T) { ... }
func TestOperatorRepliedToMessage_Success(t *testing.T) { ... }
func TestSessionEndingByTrigger_Success(t *testing.T) { ... }
```

#### 2. Провал каждого инварианта

Из секции 4 (Enforced Invariants) — тест на отказ:

```go
func TestSubscriberRequestQuestion_OnExistingAggregate_Fails(t *testing.T) {
    // Arrange: создать агрегат с version > 0
    id := uuid.New()
    agg := newAggregate()
    model := buildSubscriberRequestQuestionModel(id)
    // подменить version на > 0 чтобы эмулировать существующий агрегат
    existingModel := domain.New{Context}AnemicModel(id, 1, uuid.New(), "prev", "prev", model.GetValueObjects())
    cmd := buildSubscriberRequestQuestionCmd()

    // Act
    res := executeOperation(agg, domain.OpSubscriberRequestQuestion, existingModel, cmd)

    // Assert
    assert.Equal(t, result.Exception, res.Result())
    assert.Contains(t, res.Reason(), "допустим только для нового агрегата")
}
```

#### 3. Цепочка операций (state machine)

Из секции 3 (State Transitions) — сквозной тест:

```go
func TestFullLifecycle_QuestionToClose(t *testing.T) {
    id := uuid.New()
    agg := newAggregate()

    // 1. Создание (New → Active)
    model1 := buildSubscriberRequestQuestionModel(id)
    cmd1 := buildSubscriberRequestQuestionCmd()
    res1 := executeOperation(agg, domain.OpSubscriberRequestQuestion, model1, cmd1)
    assert.Equal(t, result.Success, res1.Result())

    // 2. Оператор берёт (Active → InProgress)
    // ... используем changedVOs из res1 для восстановления модели
    model2 := buildOperatorDequeueRequestModel(id, /* version */ 1)
    cmd2 := buildOperatorDequeueRequestCmd()
    res2 := executeOperation(agg, domain.OpOperatorDequeueRequest, model2, cmd2)
    assert.Equal(t, result.Success, res2.Result())

    // 3. Закрытие (InProgress → Closed)
    model3 := buildSessionEndingByTriggerModel(id, /* version */ 2)
    cmd3 := buildSessionEndingByTriggerCmd()
    res3 := executeOperation(agg, domain.OpSessionEndingByTrigger, model3, cmd3)
    assert.Equal(t, result.Success, res3.Result())
}
```

## Алгоритм генерации тестов

1. **Из секции 6 (Handled Commands):** каждая команда → `Test{Command}_Success`
2. **Из секции 4 (Enforced Invariants):** каждый инвариант → `Test{Command}_{Invariant}_Fails`
3. **Из секции 3 (State Transitions):** каждая цепочка → `TestFullLifecycle_{Scenario}`

## Запуск

```bash
go test ./test/... -v
```

---
name: event-sourcing-template
description: Microservicio con Event Sourcing, CQRS y Event Store para trazabilidad completa
trigger: "event sourcing, cqrs, event store, eventos, aggregates"
---

# Event Sourcing Template Skill

Crea un microservicio con Event Sourcing + CQRS para casos donde se requiere trazabilidad completa.

## Estructura

```
MyService/
├── src/
│   ├── MyService.Domain/
│   │   ├── Aggregates/
│   │   ├── Events/
│   │   └── ValueObjects/
│   ├── MyService.Application/
│   │   ├── Commands/
│   │   ├── Queries/
│   │   ├── Handlers/
│   │   └── Services/
│   ├── MyService.Infrastructure/
│   │   ├── EventStore/
│   │   │   ├── EventStore.cs
│   │   │   └── MongoEventStore.cs
│   │   ├── Projections/
│   │   └── Repositories/
│   └── MyService.API/
└── tests/
```

## Event Sourcing Conceptos

### Agregate Root con Eventos

```csharp
public class Order : AggregateRoot
{
    public OrderStatus Status { get; private set; }
    
    // Event sourcing: reconstruct from events
    public Order(IEnumerable<IDomainEvent> events) : base(events)
    {
    }
    
    public void PlaceOrder()
    {
        Apply(new OrderPlacedEvent(Id, DateTime.UtcNow));
    }
    
    protected override void When(IDomainEvent @event)
    {
        switch (@event)
        {
            case OrderPlacedEvent e:
                Status = OrderStatus.Placed;
                break;
        }
    }
}
```

### Event Store

```csharp
public interface IEventStore
{
    Task<IEnumerable<IDomainEvent>> GetEventsAsync(Guid aggregateId);
    Task AppendAsync(Guid aggregateId, IEnumerable<IDomainEvent> events);
    Task<IEnumerable<T>> GetProjectionsAsync<T>(string projectionName);
}
```

## CQRS en Event Sourcing

### Commands (Writes)
- Generan nuevos eventos
- Validan business rules
- Aplican al aggregate

### Queries (Reads)
- Proyecciones desde event store
- Materialized views
- Dapper para reads optimizados

## Skills Auto-invocados

- `ddd-aggregate` - Aggregates
- `clean-arch-design` - Arquitectura
- `cqrs` - CQRS pattern
- `event-sourcing` - Event sourcing concepts

## Cuándo Usar Event Sourcing

**Pros:**
- Completa trazabilidad
- Audit trail automático
- Replay de eventos
- Time-travel debugging

**Cons:**
- Eventual consistency
- Complejidad adicional
- Proyecciones asíncronas

## Pasos

1. Diseñar aggregate con eventos
2. Implementar Event Store (MongoDB/EventStoreDB)
3. Crear projectors para reads
4. Implementar CQRS handlers
5. Agregar tests
6. Verificar: `dotnet build && dotnet test`

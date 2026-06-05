---
name: adr-generator
description: Genera Architecture Decision Records (ADRs) para documentar decisiones técnicas importantes
trigger: "adr, architecture decision, decision record, documenting decisions"
---

# ADR Generator Skill

Genera Architecture Decision Records (ADRs) para documentar decisiones técnicas significativas.

## Qué es un ADR

Un ADR documenta una decisión arquitectónica significativa:
- **Contexto**: Por qué se tomó la decisión
- **Decisión**: Qué se decidió
- **Consecuencias**: Qué implica esta decisión

## Formato ADR

```markdown
# ADR-001: Usar Event Sourcing para Orders

## Estado
Aceptado

## Fecha
2026-05-08

## Context
Necesitamos audit trail completo para órdenes debido a compliance.
El volumen预期 es 10k órdenes/día.

## Decisión
Usar Event Sourcing con EventStoreDB para el servicio de Orders.
Proyecciones para reads con CQRS.

## Consecuencias
### Positivas
- Audit trail automático
- Time-travel debugging
- Replay de eventos para nuevos features

### Negativas
- Complejidad adicional en código
- Eventual consistency
- Proyecciones asíncronas

## Alternativas Consideradas
1. **Traditional logging**: No soporta replay
2. **Snapshots**: No audit trail completo
```

## Auto-invocados

- `clean-arch-design` - Diseñar arquitectura
- `domain-analysis` - Analizar bounded context
- `writing-plans` - Planificar implementación

## Reglas

1. **Una decisión por ADR**
2. **Consecuencias completas** - positivas y negativas
3. **Alternativas documentadas** - qué más se consideró
4. **Contexto suficiente** - por qué importa la decisión

## Output Location

```
docs/adr/
├── ADR-001-titulo.md
├── ADR-002-titulo.md
└── README.md  # Índice
```

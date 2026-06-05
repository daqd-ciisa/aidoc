---
name: template-list
description: Lista todos los templates de scaffolding disponibles en el DevKit
---

# Template List Command

Lista todos los templates de scaffolding disponibles para crear nuevos proyectos.

## Uso

```
/template-list
```

## Templates Disponibles

### ✅ Disponibles

| Template | Descripción | Status |
|----------|--------------|--------|
| `clean-arch-microservices` | Base para microservicios con Clean Architecture + DDD + CQRS | Stable |
| `monolith-to-microservices` | Guía paso a paso para migrar monolito a microservicios | Stable |

### 🚧 En Desarrollo

| Template | Descripción | Status |
|----------|--------------|--------|
| `saas-starter` | Proyecto SaaS multi-tenant completo con auth y billing | Planned |
| `api-gateway` | Solo YARP Gateway con auth centralizada | Planned |
| `blazor-dashboard` | Dashboard administrativo con MudBlazor | Planned |
| `event-sourcing` | Microservicio con Event Sourcing + CQRS | Planned |

## Ejemplo de Output

```
📦 Templates de Scaffolding PSW DevKit

DISPONIBLES:
━━━━━━━━━━━━
1. clean-arch-microservices
   → Base para microservicios Clean Architecture + DDD + CQRS
   → Location: scaffolding/clean-arch-microservices

2. monolith-to-microservices
   → Guía para extraer bounded contexts del monolito
   → Location: scaffolding/monolith-to-microservices


EN DESARROLLO:
━━━━━━━━━━━━━━
3. saas-starter (proximamente)
4. api-gateway (proximamente)
5. blazor-dashboard (proximamente)
6. event-sourcing (proximamente)


USO:
----
Para usar un template:
1. Lee el README.md del template
2. Ejecuta los comandos de scaffold
3. Personaliza según tu proyecto
```

## Detalle de Template

Para ver detalles de un template específico:

```
/template-list clean-arch-microservices
```

Output:
```
📦 Template: clean-arch-microservices

Descripción: Base para microservicios Clean Architecture + DDD + CQRS

Estructura:
├── src/
│   ├── [Service].Services.Identity/
│   ├── [Service].Services.[BoundedContext]/
│   ├── [Service].API.Gateway/
│   ├── [Service].Client.Blazor/
│   └── [Service].Shared/
└── tests/

Technologías:
- .NET 10
- Entity Framework Core
- Dapr
- YARP
- Blazor WASM

Commands:
- dotnet new classlib ...
```

## Skills Involucrados

- `scaffolding` - Para crear proyectos desde template
- `clean-arch-design` - Para diseñar arquitectura

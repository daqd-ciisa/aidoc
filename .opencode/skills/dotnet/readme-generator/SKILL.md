---
name: readme-generator
description: Genera README.md completo por microservicio con badges, setup, arquitectura y ejemplos
trigger: "readme, documentation, badges, setup, project readme"
---

# README Generator Skill

Genera README.md completo y profesional para cada microservicio.

## Estructura Típica

```markdown
# MyService

[![Build](https://img.shields.io/github/actions/workflow/status/org/repo/ci.yml?branch=main)](https://github.com/org/repo/actions)
[![Coverage](https://img.shields.io/badge/coverage-85%25-brightgreen)](src/MyService.Tests)
[![.NET](https://img.shields.io/badge/.NET-10.0-blue)](https://dotnet.microsoft.com/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

Breve descripción del servicio.

## Arquitectura

[Diagrama C4 simplificado]

## Quick Start

```bash
# Clone y setup
git clone https://github.com/org/my-service.git
cd my-service

# Build
dotnet build

# Test
dotnet test

# Run
dotnet run --project src/MyService.API
```

## Características

- Feature 1
- Feature 2
- Feature 3

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/health | Health check |
| GET | /api/orders | List orders |
| POST | /api/orders | Create order |

## Configuración

```yaml
ConnectionStrings:
  Default: "Server=localhost;Database=MyDb"

App:
  Host: "0.0.0.0"
  Port: 5000
```

## Desarrollo

### Requisitos
- .NET 10 SDK
- SQL Server 2022+ o PostgreSQL 15+
- Docker Desktop

### Setup Local
```bash
dotnet restore
dotnet ef database update
dotnet run
```

### Tests
```bash
dotnet test --verbosity normal
```

## Proyecto Structure

```
MyService/
├── src/
│   ├── MyService.Domain/
│   ├── MyService.Application/
│   ├── MyService.Infrastructure/
│   └── MyService.API/
└── tests/
    └── MyService.Tests/
```

## Links

- [Documentación completa](./docs/)
- [API Docs](./docs/openapi.yaml)
- [Changelog](./CHANGELOG.md)
```

## Badges Típicos

| Badge | URL |
|-------|-----|
| Build | GitHub Actions |
| Coverage | Coveralls/Codecov |
| .NET Version | Custom |
| License | License URL |
| NuGet | NuGet.org |

## Skills Auto-invocados

- `clean-arch-design` - Arquitectura
- `c4-generator` - Diagrama de arquitectura
- `api-docs-generator` - API docs
- `dotnet-best-practices` - Best practices

## Reglas

1. **Badges actuales** - links que funcionan
2. **Quick start funcional** - comandos que funcionan
3. **Estructura clara** - secciones bien definidas
4. **Ejemplos concretos** - código de ejemplo real

---
name: onboarding-dev
description: Guía automática para nuevos desarrolladores del equipo - setup, arquitectura y primeros pasos
trigger: "onboarding, nuevo developer, setup, welcome, primeros pasos"
---

# Onboarding Dev Skill

Guía a nuevos desarrolladores del equipo con setup completo y contexto de arquitectura.

## Flujo de Onboarding

```
1. Setup de entorno
2. Configuración de tools
3. Arquitectura del sistema
4. Primer proyecto de práctica
5. Recursos y contacto
```

## Paso 1: Setup de Entorno

### Requisitos
- .NET 10 SDK
- Docker Desktop
- VS Code o Rider
- Git

### Instalación

```bash
# .NET
winget install Microsoft.dotnet.SDK.10

# Docker
winget install Docker.DockerDesktop

# VS Code extensions
code --install-extension ms-dotnettools.csharp
code --install-extension ms-azuretools.vs-code-docker
code --install-extension redhat.vscode-yaml
```

## Paso 2: Configuración Personal

```bash
# Git config
git config --global user.name "Tu Nombre"
git config --global user.email "tu@email.com"

# SSH key (si no tienes)
ssh-keygen -t ed25519 -C "tu@email.com"
```

## Paso 3: Arquitectura del Sistema

### Microservicios
- **Identity Service**: Auth, users, roles
- **Tenant Service**: Multi-tenant management
- **Gateway**: YARP routing

### Stack
- .NET 10 + C# 12
- Clean Architecture + DDD + CQRS
- Blazor WASM (frontend)
- SQL Server / PostgreSQL
- Dapr (distributed runtime)

### Repo Structure
```
my-project/
├── src/
│   ├── MyService.API/
│   ├── MyService.Application/
│   ├── MyService.Domain/
│   └── MyService.Infrastructure/
├── tests/
└── .opencode/
```

## Paso 4: Primer Proyecto de Práctica

1. Clonar repo base
2. Crear feature branch
3. Implementar "Hello World" endpoint
4. Escribir tests
5. Hacer PR

## Paso 5: Recursos

### Documentación
- `.opencode/context/enterprise.yaml` - Contexto empresarial
- `.opencode/agents/orchestrator.md` - Orchestrator
- `docs/` - Documentación adicional

### Contacto
- Dev Team: devteam@psw.example.com
- Tech Lead: techlead@psw.example.com
- Slack: #dev-team

### Skills Recomendados
- `brainstorming` - Metodología de diseño
- `test-driven-development` - TDD
- `scaffolding` - Crear proyectos

## Comandos de Verificación

```bash
# Verificar setup
dotnet --version  # Debe ser 10.0+
docker --version
git --version

# Build del template
cd scaffolding/clean-arch-microservices
dotnet build

# Run tests
dotnet test
```

## Reglas del Equipo

1. **TDD siempre** - tests antes de código
2. **Brainstorming** - diseño antes de implementar
3. **Code review** - todo PR necesita review
4. **conventional commits** - formato de commits

## Skills Auto-invocados

- `scaffolding` - Setup inicial
- `clean-arch-design` - Arquitectura
- `test-driven-development` - TDD

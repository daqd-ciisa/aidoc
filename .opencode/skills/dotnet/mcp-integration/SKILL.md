---
name: mcp-integration
description: Integra MCPs (Model Context Protocol) con el stack .NET del equipo
trigger: "mcp, model context protocol, nuget, github, postgres, docker, fetch"
---

# MCP Integration Skill

Integra MCPs con el desarrollo .NET para obtener datos externos en tiempo real.

## MCPs Disponibles

| MCP | Comando de uso | Cuando usarlo |
|-----|---------------|---------------|
| **nuget** | `@nuget search <paquete>` | Antes de agregar un paquete NuGet |
| **github** | `@github search-issues <query>` | Buscar issues/PRs relacionados |
| **postgresql** | `@postgres query <sql>` | Verificar schema de base de datos |
| **docker** | `@docker ps` | Verificar contenedores en ejecucion |
| **fetch** | `@fetch <url>` | Probar APIs externas |
| **filesystem** | `@filesystem read <path>` | Leer archivos de config |

## Flujo de trabajo tipico

### Antes de agregar un paquete NuGet
```
1. @nuget search MediatR
2. Revisar versiones disponibles y dependencias
3. Verificar compatibilidad con .NET 9
4. dotnet add package MediatR --version <version>
```

### Antes de crear una migracion
```
1. @postgres query "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'orders'"
2. Revisar schema actual
3. Disenar migracion basada en datos reales
```

### Debug de microservicio
```
1. @docker ps --filter "name=identity"
2. @docker logs identity-api
3. @fetch http://localhost:5000/health
```

## Reglas

1. **Verificar siempre** antes de actuar - usar MCPs para obtener datos reales
2. **No asumir** - consultar schema real, no suponer estructura
3. **Documentar** - si un MCP revela informacion importante, documentarla
4. **Seguridad** - nunca exponer tokens o secrets en prompts

## Instalacion de MCPs

```bash
# Instalar MCP individual
opencode mcp add nuget
opencode mcp add github
opencode mcp add postgresql

# Ver MCPs instalados
opencode mcp list

# Configurar en .mcp.json
{
  "mcpServers": {
    "nuget": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-nuget"]
    }
  }
}
```

## Skills Auto-invocados

- `nuget-manager` - Gestion de paquetes
- `sql-code-review` - Revision de SQL
- `dotnet-best-practices` - Best practices
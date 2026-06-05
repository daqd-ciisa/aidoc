---
name: mcp
description: Gestiona MCPs (Model Context Protocol) del equipo - instalar, listar, configurar
---

# MCP Command

Gestiona MCPs recomendados para el desarrollo .NET.

## Uso

```
/mcp list              → Listar MCPs recomendados e instalados
/mcp install <nombre>  → Instalar un MCP
/mcp config            → Mostrar configuración de .mcp.json
/mcp docs              → Documentación de MCPs útiles
```

## MCPs Recomendados para .NET

| MCP | Instalación | Uso principal |
|-----|-------------|---------------|
| nuget | `opencode mcp add nuget` | Buscar paquetes NuGet |
| github | `opencode mcp add github` | Issues, PRs, releases |
| postgresql | `opencode mcp add postgresql` | Schema introspection |
| docker | `opencode mcp add docker` | Contenedores |
| fetch | `opencode mcp add fetch` | HTTP requests |
| filesystem | `opencode mcp add filesystem` | Filesystem seguro |

## Configuración

Para usar MCPs, crear archivo `.mcp.json` en la raíz del proyecto:

```json
{
  "mcpServers": {
    "nuget": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-nuget"]
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_TOKEN}"
      }
    }
  }
}
```

## Skills relacionados

- `mcp-integration` - Integración de MCPs con .NET
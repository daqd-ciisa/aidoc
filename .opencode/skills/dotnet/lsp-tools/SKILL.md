---
name: lsp-tools
description: Usa herramientas LSP nativas de OpenCode para navegacion, refactoring y analisis de codigo
trigger: "lsp, goto definition, find references, rename, refactor, diagnostics, symbol"
---

# LSP Tools Skill

Usa herramientas LSP (Language Server Protocol) para navegar y refactorizar codigo .NET.

## Herramientas LSP disponibles en OpenCode

OpenCode expone estas herramientas LSP automaticamente cuando detecta un proyecto .NET:

| Herramienta | Uso | Comando equivalente |
|-------------|-----|---------------------|
| `lsp_goto_definition` | Saltar a la definicion de un simbolo | F12 en VS Code |
| `lsp_find_references` | Encontrar todas las referencias | Shift+F12 |
| `lsp_diagnostics` | Ver errores y warnings del compilador | Ctrl+Shift+M |
| `lsp_rename` | Renombrar simbolo globalmente | F2 |
| `lsp_hover` | Ver informacion de un simbolo | Hover mouse |
| `lsp_document_symbol` | Listar simbolos del archivo | Ctrl+Shift+O |
| `lsp_workspace_symbol` | Buscar simbolos en todo el workspace | Ctrl+T |
| `lsp_code_action` | Aplicar quick fixes | Ctrl+. |
| `lsp_format_document` | Formatear archivo | Shift+Alt+F |

## Flujos de trabajo

### Refactorizar una entidad
```
1. Usar lsp_find_references en la entidad
2. Revisar todos los usos
3. Usar lsp_rename para renombrar
4. Verificar con lsp_diagnostics que no hay errores
```

### Entender codigo legacy
```
1. Usar lsp_goto_definition en metodos desconocidos
2. Usar lsp_document_symbol para ver estructura del archivo
3. Usar lsp_find_references para ver impacto
```

### Corregir errores de compilacion
```
1. Usar lsp_diagnostics para ver todos los errores
2. Usar lsp_code_action para aplicar fixes automaticos
3. Usar lsp_goto_definition para entender el contexto
```

## Reglas

1. **Navegar antes de modificar** - entender el impacto con find_references
2. **Renombrar con LSP** - nunca renombrar manualmente, usar lsp_rename
3. **Validar despues** - siempre verificar diagnostics despues de cambios
4. **Formato automatico** - usar lsp_format_document antes de commit

## Integracion con skills existentes

- `systematic-debugging` - Usar diagnostics para encontrar errores
- `fix-errors` - Aplicar code actions automaticas
- `dotnet-design-pattern-review` - Usar document_symbol para revisar estructura
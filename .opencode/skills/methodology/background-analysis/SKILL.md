---
name: background-analysis
description: Ejecuta analisis en paralelo usando Task tool mientras el desarrollador trabaja en otra tarea
trigger: "analisis en paralelo, background, concurrente, paralelo, mientras tanto"
---

# Background Analysis Skill

Ejecuta analisis en background usando Task tool para no bloquear el flujo principal.

## Concepto

Mientras el desarrollador trabaja en una tarea (ej: implementar un feature), el agente puede ejecutar analisis paralelos:
- Analisis de arquitectura del codigo existente
- Busqueda de vulnerabilidades de seguridad
- Revision de cobertura de tests
- Analisis de dependencias obsoletas

## Uso del Task Tool

OpenCode permite ejecutar tareas en paralelo con el Task tool:

```
Task: Analizar arquitectura del servicio actual
- Revisar capas de Clean Architecture
- Verificar dependencias entre proyectos
- Detectar violaciones de DDD

Task: Revisar seguridad del codigo
- Buscar secrets hardcodeados
- Verificar validacion de inputs
- Revisar configuracion de JWT
```

## Analisis en background recomendados

### 1. Analisis de Arquitectura
```
Task: architecture-review
- Revisar que Domain no tenga dependencias externas
- Verificar que Application solo referencie Domain
- Validar que Infrastructure referencie Application + Domain
- Detectar referencias circulares
- Verificar database-per-service
```

### 2. Analisis de Seguridad
```
Task: security-scan
- Buscar connection strings en codigo
- Revisar archivos appsettings.Development.json
- Verificar que no haya passwords hardcodeados
- Revisar configuracion CORS
- Validar rate limiting
```

### 3. Analisis de Calidad
```
Task: quality-analysis
- Ejecutar dotnet format --verify-no-changes
- Revisar cobertura de tests
- Detectar code smells (metodos largos, clases grandes)
- Verificar complejidad ciclomatica
```

### 4. Analisis de Dependencias
```
Task: dependency-check
- Ejecutar dotnet list package --outdated
- Revisar vulnerabilidades conocidas (dotnet list package --vulnerable)
- Verificar paquetes deprecados
```

## Reglas

1. **No bloquear** - los analisis en background no deben detener el flujo principal
2. **Reportar al final** - presentar resultados cuando el usuario lo solicite o al finalizar la tarea
3. **Priorizar** - ejecutar solo analisis relevantes al contexto actual
4. **Respetar recursos** - no ejecutar mas de 3 tareas en paralelo

## Integracion con el flujo de trabajo

```
Usuario: Implementa el feature de orders

Agente (flujo principal):
1. Brainstorming
2. Planning
3. Implementacion con TDD

Agente (background, paralelo):
Task 1: Revisar arquitectura del servicio Orders
Task 2: Verificar seguridad de endpoints nuevos

Al finalizar:
Agente: "Feature implementado. Resultados del analisis en background:
- Arquitectura: sin violaciones
- Seguridad: falta rate limiting en POST /orders"
```

## Skills Auto-invocados

- `compliance-check` - Validacion de calidad
- `security-specialist` - Revision de seguridad
- `dotnet-design-pattern-review` - Analisis de patrones
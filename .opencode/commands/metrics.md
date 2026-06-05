---
name: metrics
description: Ver métricas del equipo - lead time, cycle time, coverage, defect escape rate
---

# Metrics Command

Muestra las métricas ágiles y de calidad del equipo de desarrollo.

## Uso

```
/metrics [periodo]
```

## Periodos Disponibles

| Periodo | Descripción |
|---------|-------------|
| `day` | Últimas 24 horas |
| `week` | Última semana |
| `month` | Último mes |
| `quarter` | Último trimestre |

## Métricas Mostradas

### Flow
- Lead Time promedio
- Cycle Time promedio
- Deployment Frequency
- PRs mergeados

### Quality
- Code Coverage %
- Defect Escape Rate
- Bug count por severity
- Tech debt (horas)

### Efficiency
- Build Success Rate
- PR Review Time promedio
- MTTR (Mean Time To Recovery)

## Ejemplo de Output

```
📊 Métricas PSW Dev Team - Semana actual

🚚 Flow
   Lead Time: 3.2 días
   Cycle Time: 1.8 días
   Deploys: 14

🎯 Quality
   Coverage: 84%
   Defect Escape: 7%
   Bugs: 3 (1 crítico, 2 medios)

⚡ Efficiency
   Build Success: 97%
   PR Review Time: 4.2 horas
   MTTR: 52 minutos
```

## Data Sources

- **Git**: Commits, PRs, deployments
- **CI/CD**: Build success, test results
- **SonarQube**: Coverage, code smells
- **Jira/Azure DevOps**: Bugs, story points

## Skills Involucrados

- `metrics-tracker` - Skill principal de métricas
- `verification-before-completion` - Verificación de calidad

## Nota

Algunas métricas requieren acceso a:
- SonarQube project
- CI/CD pipeline logs
- Azure DevOps / Jira

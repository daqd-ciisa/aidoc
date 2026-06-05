---
name: metrics-tracker
description: Tracking de métricas de equipo - lead time, cycle time, defect escape rate, coverage trend
trigger: "métricas, metrics, kpi, tracking, lead time, cycle time, coverage trend"
---

# Metrics Tracker Skill

Tracking de métricas ágiles y de calidad del equipo de desarrollo.

## Métricas Principales

### Flow Metrics
| Métrica | Descripción | Target |
|---------|-------------|--------|
| Lead Time | Tiempo desde idea hasta producción | < 1 semana |
| Cycle Time | Tiempo desde start hasta merge | < 3 días |
| Deployment Frequency | Deploys por semana | Daily |

### Quality Metrics
| Métrica | Descripción | Target |
|---------|-------------|--------|
| Code Coverage | Porcentaje cubierto por tests | >= 80% |
| Defect Escape Rate | Bugs en producción / total bugs | < 10% |
| Tech Debt | Deuda técnica en días | < 5 días |

### Efficiency Metrics
| Métrica | Descripción | Target |
|---------|-------------|--------|
| PR Review Time | Tiempo hasta primer review | < 24h |
| MTTR | Mean Time To Recovery | < 1 hora |
| Build Success Rate | Porcentaje builds exitosos | > 95% |

## Recolección de Datos

### Git Metrics
```bash
# Lead time
git log --after="2026-01-01" --format="%H %s" --reverse

# Cycle time por PR
gh pr list --state=closed --json=createdAt,mergedAt,title
```

### Test Coverage
```bash
dotnet test --collect:"XPlat Code Coverage"
reportgenerator -reports:coverage/*.xml -targetdir:coverage-report
```

### SonarQube
```bash
sonar-scanner -Dsonar.projectKey=my-project
```

## Dashboard

Generar reporte semanal:

```markdown
# Métricas Semanales - PSW Dev Team

## Esta Semana
- **Lead Time**: 4.2 días (target: 7 días) ✅
- **Cycle Time**: 2.1 días (target: 3 días) ✅
- **Deployments**: 12 (target: daily) ✅
- **Coverage**: 84% (target: 80%) ✅

## Incidentes
- 2 bugs escaparon a producción (defect escape rate: 8%)
- MTTR: 45 minutos

## Acciones
- [ ] Review de pipeline de CI/CD
- [ ] Incrementar coverage en Domain layer
```

## Skills Auto-invocados

- `verification-before-completion` - Verificación de calidad
- `compliance-check` - Validación de standards

## Reglas

1. **Medir no adivinar** - datos objetivos
2. **Trend sobre snapshot** - tendencias importan más
3. **Actionable insights** - métricas sin acción = ruido
4. **Transparency** - métricas visibles para todo el equipo

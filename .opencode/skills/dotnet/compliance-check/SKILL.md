---
name: compliance-check
description: Valida arquitectura, coverage, seguridad, secrets y conformance al contexto empresarial
trigger: "compliance, validacion, quality gates, security scan, coverage"
---

# Compliance Check Skill

Valida que el codigo cumple con las reglas del equipo antes de merge/PR.

## Checklist de Validacion

### Arquitectura
- [ ] Clean Architecture layers respetados
- [ ] Domain sin dependencias externas
- [ ] Application solo referencia Domain e Infrastructure
- [ ] Infrastructure referencia Application y Domain
- [ ] API referencia Application
- [ ] Database-per-service respetado
- [ ] Ningun microservicio referencia Domain de otro servicio

### Codigo
- [ ] Coverage >= 80%
- [ ] Cyclomatic complexity <= 10
- [ ] No code smells criticos
- [ ] Tests pasando
- [ ] Sin warnings de compilacion

### Seguridad
- [ ] No secrets en codigo (usar git secrets --scan)
- [ ] JWT validation configurado
- [ ] Input validation en APIs (FluentValidation)
- [ ] SQL injection prevention (queries parametrizadas)
- [ ] CORS configurado

### Convenciones
- [ ] Naming convention respetada (PascalCase para clases, camelCase para metodos)
- [ ] File organization correcta
- [ ] Documentation actualizada (XML comments en APIs publicas)
- [ ] ADRs actualizados para decisiones arquitectonicas

## Comandos de Verificacion

```bash
# Build
dotnet build --no-incremental

# Test con coverage
dotnet test --verbosity normal --collect:"XPlat Code Coverage"

# Security scan (secrets)
git secrets --scan 2>/dev/null || echo "git-secrets no instalado"

# Dependency check
dotnet list package --include-transitive --outdated

# Verificar formato
dotnet format --verify-no-changes
```

## Skills Auto-invocados

- `verification-before-completion` - Gate de calidad
- `test-driven-development` - TDD validation
- `sql-code-review` - SQL validation
- `dotnet-best-practices` - Best practices check

## Integracion CI/CD

```yaml
# GitHub Actions example
- name: Compliance Check
  run: |
    dotnet build --no-incremental
    dotnet test --verbosity normal --collect:"XPlat Code Coverage"
    dotnet format --verify-no-changes
```

## Reglas

1. **Todo debe pasar** - sin excepciones
2. **Evidence** - logs como evidencia
3. **Bloquear merge** si no pasa compliance
4. **Report** - generar reporte de compliance

## Pasos

1. Ejecutar `dotnet build --no-incremental`
2. Ejecutar `dotnet test --verbosity normal`
3. Verificar coverage >= 80%
4. Ejecutar `dotnet format --verify-no-changes`
5. Verificar arquitectura (capas correctas)
6. Generar reporte de compliance
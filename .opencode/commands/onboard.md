---
name: onboard
description: Onboarding de nuevo desarrollador - setup completo y guía de arquitectura
---

# Onboard Command

Inicia el proceso de onboarding para nuevos desarrolladores del equipo.

## Uso

```
/onboard
```

## Flujo

1. **Verificar entorno**
   - .NET 10 SDK instalado
   - Docker Desktop ejecutándose
   - Git configurado

2. **Setup personal**
   - Git credentials
   - SSH keys
   - Editor/IDE configurado

3. **Arquitectura overview**
   - Stack tecnológico
   - Estructura de microservicios
   - Convenciones del equipo

4. **Hands-on lab**
   - Clonar repo de práctica
   - Implementar "Hello World" feature
   - Primer PR

5. **Recursos**
   - Documentación relevante
   - Contactos del equipo
   - Slack channels

## Prerequisites

Verificar con:
```bash
dotnet --version  # >= 10.0
docker --version
git --version
```

## Skills Involucrados

- `onboarding-dev` - Skill principal de onboarding
- `scaffolding` - Setup de proyecto
- `clean-arch-design` - Arquitectura

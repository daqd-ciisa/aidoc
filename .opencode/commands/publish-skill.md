---
name: publish-skill
description: Publicar skill personalizado al marketplace/registry interno del equipo
---

# Publish Skill Command

Publica un skill personalizado en el registry interno del equipo.

## Uso

```
/publish-skill [nombre-del-skill]
```

## Ejemplo

```
/publish-skill api-versioning
```

## Flujo

1. **Verificar skill existe**
   - Skill en `.opencode/skills/custom/`
   - Estructura válida (SKILL.md con frontmatter)

2. **Validar contenido**
   - Frontmatter completo (name, description, trigger)
   - Contenido no vacío
   - Sin duplicados de skills existentes

3. **Generar documentación**
   - README para el skill
   - Ejemplos de uso
   - Changelog

4. **Publicar al registry**
   - Copiar a folder compartido
   - Actualizar índice de skills
   - Notificar al equipo

## Validación

```bash
# Estructura correcta
ls -la .opencode/skills/custom/mi-skill/
# Debe tener: SKILL.md

# Frontmatter válido
head -10 .opencode/skills/custom/mi-skill/SKILL.md
# name: debe estar
```

## Skills Involucrados

- `skill-publisher` - Skill principal de publicación
- `writing-skills` - Cómo escribir skills
- `find-skills` - Verificar no duplicado

## Registry Location

Skills internos se guardan en:
```
.opencode/skills/custom/
```

## Reglas

1. **Nombre único** - no duplicar skills existentes
2. **Descripción clara** - que otros entiendan el propósito
3. **Triggers definidos** - palabras que lo disparan
4. **Ejemplos incluidos** - cómo usar el skill

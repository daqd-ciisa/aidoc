---
name: skill-publisher
description: Permite al equipo publicar skills personalizados internamente en el registry del equipo
trigger: "publish skill, compartir skill, internal registry, skill custom"
---

# Skill Publisher Skill

Permite a miembros del equipo crear y publicar skills personalizados en el registry interno.

## Anatomía de un Skill

```
skills/
└── custom/
    └── mi-skill/
        ├── SKILL.md           # Obligatorio
        └── references/        # Opcional
            └── extra.md
```

## SKILL.md Estructura

```markdown
---
name: mi-skill
description: Descripción corta del skill
trigger: "palabras,trigger,separadas,por,comas"
---

# Mi Skill

Contenido del skill con:
- Conceptos a aplicar
- Pasos específicos
- Reglas del skill
- Auto-invocados a otros skills
```

## Frontmatter

| Campo | Requerido | Descripción |
|-------|-----------|-------------|
| name | Sí | Nombre único del skill |
| description | Sí | Descripción corta |
| trigger | No | Palabras que disparan el skill |

## Proceso de Publicación

### 1. Crear Skill
```bash
mkdir -p .opencode/skills/custom/mi-skill
```

### 2. Escribir SKILL.md
```markdown
---
name: mi-skill
description: Mi primer skill personalizado
trigger: "mi skill, custom, prueba"
---

# Mi Skill Personalizado

[Contenido...]
```

### 3. Validar
```bash
# Verificar estructura
ls -la .opencode/skills/custom/mi-skill/

# Verificar frontmatter
head -10 .opencode/skills/custom/mi-skill/SKILL.md
```

### 4. Compartir
- Agregar al repo shared del equipo
- Documentar en wiki
- Compartir en Slack #dev-skills

## Guidelines

### Buenas Prácticas
1. **Focus limitado** - un skill, una responsabilidad
2. **Trigger claros** - palabras que lo disparan
3. **Reglas específicas** - pasos claros
4. **Auto-invocados** - linking a skills relacionados

### Evitar
- Skills demasiado genéricos
- Duplicar skills existentes
- Skills sin trigger
- Skills sin ejemplos

## Registry Interno

Skills disponibles en `.opencode/skills/custom/`:

```
custom/
├── api-versioning/      # Versionado de APIs
├── blazor-state/         # State management
├── grpc-integration/     # gRPC con .NET
└── azure-functions/      # Azure Functions
```

## Skills Auto-invocados

- `writing-skills` - Cómo escribir skills
- `find-skills` - Encontrar skills relacionados

## Reglas

1. **No duplicar** - verificar que no existe
2. **Naming convention** -kebab-case
3. **Documentar** - ejemplos claros
4. **Versionar** - Semantic versioning

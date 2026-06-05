---
name: blazor-dashboard-template
description: Dashboard administrativo con MudBlazor, gráficos, métricas y gestión de entidades
trigger: "dashboard, admin, mudblazor, UI admin, métricas"
---

# Blazor Dashboard Template Skill

Crea un dashboard administrativo con MudBlazor seguindo las reglas del equipo.

## Estructura

```
MyDashboard.Client/
├── Pages/
│   ├── Dashboard.razor
│   ├── Users/
│   │   ├── UserList.razor
│   │   └── UserEdit.razor
│   └── Settings/
├── Components/
│   ├── MetricCard.razor
│   ├── DataGrid.razor
│   └── LoadingOverlay.razor
├── Services/
│   ├── IDashboardService.cs
│   └── DashboardService.cs
├── Layout/
│   ├── MainLayout.razor
│   ├── NavMenu.razor
│   └── AppBar.razor
└── Program.cs
```

## Características

### Dashboard
- Metric cards con gráficos
- Recent activity feed
- System health indicators
- Quick actions

### User Management
- DataGrid con paginación
- CRUD operations
- Role assignment
- Audit trail

### Settings
- Tenant configuration
- User preferences
- Theme settings

## Design System (del contexto empresarial)

```css
/* Colors */
--primary: #594AE2;
--secondary: #717171;

/* Typography */
--font-family: 'Segoe UI', Roboto, sans-serif;

/* Spacing */
--spacing-unit: 8px;
--border-radius: 4px;
```

## Skills Auto-invocados

- `blazor-component` - Componentes
- `blazor-authentication` - Auth client-side
- `frontend-design` - Diseño
- `fluentui-blazor` - Alternativa FluentUI

## Reglas Blazor WASM

1. **HttpClient tipado SIEMPRE**
2. **NUNCA ProjectReference al backend** - API Gateway only
3. **Lazy loading** para páginas pesadas
4. **Cascading authentication state**

## Pasos

1. Crear proyecto Blazor WASM
2. Configurar MudBlazor
3. Crear layout con NavMenu
4. Implementar páginas con servicios
5. Agregar autenticación JWT
6. Verificar: `dotnet build`

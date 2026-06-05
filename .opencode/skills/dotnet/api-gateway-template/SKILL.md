---
name: api-gateway-template
description: Template de API Gateway YARP con autenticación centralizada, rate limiting y routing avanzado
trigger: "api gateway, yarp, gateway, routing, proxy"
---

# API Gateway Template Skill

Crea un API Gateway con YARP que sirve como único punto de entrada con autenticación centralizada.

## Estructura

```
MyGateway.API/
├── Program.cs
├── appsettings.json
├── Configuration/
│   ├── GatewayConfig.cs
│   ├── AuthenticationConfig.cs
│   └── RateLimitConfig.cs
├── Middleware/
│   ├── TenantMiddleware.cs
│   └── CorrelationMiddleware.cs
├── Extensions/
│   └── ServiceCollectionExtensions.cs
└── clusters.json
```

## Características

### Routing
- Route-based routing a microservicios
- Cluster discovery dinámico
- Health check routing
- Weighted routing para blue-green

### Autenticación Centralizada
- JWT validation en gateway
- Claims propagation a servicios downstream
- Tenant resolution desde JWT
- Anonymous routes configurables

### Rate Limiting
- Per-tenant rate limits
- Global rate limits
- Sliding window algorithm
- Redis-backed para distributed limiting

### Observabilidad
- OpenTelemetry tracing
- Correlation IDs
- Request/response logging
- Metrics para Prometheus

## Configuración Típica

```csharp
// Program.cs
var builder = WebApplication.CreateBuilder();

builder.Services.AddGatewayConfig()
    .AddAuthentication(JwtBearerDefaults.AuthenticationScheme)
    .AddRateLimiting();

var app = builder.Build();

app.UseAuthentication();
app.UseAuthorization();
app.MapHub<GatewayHub>("/gateway");

app.Run();
```

## Skills Auto-invocados

- `yarp-config` - Configuración YARP
- `jwt-auth` - JWT validation
- `rate-limiting` - Rate limits
- `clean-arch-design` - Arquitectura

## Reglas

1. **Gateway = Solo routing** - sin lógica de negocio
2. **Stateless** - no estado en el gateway
3. **Health checks** - verificar servicios downstream
4. **Timeout configurable** - para servicios lentos

## Pasos

1. Crear proyecto ASP.NET Core
2. Configurar YARP con clusters
3. Agregar JWT validation middleware
4. Implementar rate limiting
5. Configurar telemetry
6. Verificar: `dotnet build`

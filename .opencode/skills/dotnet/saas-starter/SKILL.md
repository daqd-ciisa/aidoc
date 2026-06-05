---
name: saas-starter
description: Scaffold completo de SaaS multi-tenant con auth, billing, admin y arquitectura lista para produccion
trigger: "nuevo proyecto saas, crear saas, multi-tenant, billing, subscription"
---

# SaaS Starter Skill

Crea un proyecto SaaS multi-tenant completo. Este skill genera codigo real ejecutable.

## Estructura Generada

```
MySaas/
├── MySaas.sln
├── src/
│   ├── Services.Identity/
│   │   ├── Services.Identity.Domain/
│   │   ├── Services.Identity.Application/
│   │   ├── Services.Identity.Infrastructure/
│   │   └── Services.Identity.API/
│   ├── Services.Tenant/
│   │   ├── Services.Tenant.Domain/
│   │   ├── Services.Tenant.Application/
│   │   ├── Services.Tenant.Infrastructure/
│   │   └── Services.Tenant.API/
│   ├── Services.Billing/
│   │   ├── Services.Billing.Domain/
│   │   ├── Services.Billing.Application/
│   │   ├── Services.Billing.Infrastructure/
│   │   └── Services.Billing.API/
│   ├── API.Gateway/
│   └── Client.Blazor/
├── tests/
│   ├── Services.Identity.Tests/
│   ├── Services.Tenant.Tests/
│   └── Services.Billing.Tests/
└── docker-compose.yml
```

## Comandos de Scaffolding (Ejecutar en orden)

### Paso 1: Crear Solution
```bash
dotnet new sln -n MySaas
```

### Paso 2: Crear Identity Service
```bash
# Domain (puro C#, sin dependencias)
dotnet new classlib -n Services.Identity.Domain -o src/Services.Identity/Services.Identity.Domain

# Application (referencia Domain)
dotnet new classlib -n Services.Identity.Application -o src/Services.Identity/Services.Identity.Application
dotnet add src/Services.Identity/Services.Identity.Application reference src/Services.Identity/Services.Identity.Domain

# Infrastructure (referencia Application + Domain)
dotnet new classlib -n Services.Identity.Infrastructure -o src/Services.Identity/Services.Identity.Infrastructure
dotnet add src/Services.Identity/Services.Identity.Infrastructure reference src/Services.Identity/Services.Identity.Application
dotnet add src/Services.Identity/Services.Identity.Infrastructure reference src/Services.Identity/Services.Identity.Domain

# API (referencia Application)
dotnet new webapi -n Services.Identity.API -o src/Services.Identity/Services.Identity.API
dotnet add src/Services.Identity/Services.Identity.API reference src/Services.Identity/Services.Identity.Application
```

### Paso 3: Agregar paquetes NuGet
```bash
# Application
dotnet add src/Services.Identity/Services.Identity.Application package MediatR --version 12.4.1
dotnet add src/Services.Identity/Services.Identity.Application package FluentValidation --version 11.11.0
dotnet add src/Services.Identity/Services.Identity.Application package AutoMapper --version 13.0.1

# Infrastructure
dotnet add src/Services.Identity/Services.Identity.Infrastructure package Microsoft.EntityFrameworkCore --version 9.0.0
dotnet add src/Services.Identity/Services.Identity.Infrastructure package Npgsql.EntityFrameworkCore.PostgreSQL --version 9.0.1
dotnet add src/Services.Identity/Services.Identity.Infrastructure package Dapr.Client --version 1.14.0

# API
dotnet add src/Services.Identity/Services.Identity.API package Swashbuckle.AspNetCore --version 7.2.0
dotnet add src/Services.Identity/Services.Identity.API package Microsoft.AspNetCore.Authentication.JwtBearer --version 9.0.0
dotnet add src/Services.Identity/Services.Identity.API package OpenTelemetry.Extensions.Hosting --version 1.10.0
```

### Paso 4: Crear proyectos de test
```bash
dotnet new xunit -n Services.Identity.Tests -o tests/Services.Identity.Tests
dotnet add tests/Services.Identity.Tests reference src/Services.Identity/Services.Identity.Domain
dotnet add tests/Services.Identity.Tests reference src/Services.Identity/Services.Identity.Application
dotnet add tests/Services.Identity.Tests package FluentAssertions --version 7.0.0
dotnet add tests/Services.Identity.Tests package NSubstitute --version 5.3.0
```

### Paso 5: Agregar al solution
```bash
dotnet sln add src/Services.Identity/Services.Identity.Domain/Services.Identity.Domain.csproj
dotnet sln add src/Services.Identity/Services.Identity.Application/Services.Identity.Application.csproj
dotnet sln add src/Services.Identity/Services.Identity.Infrastructure/Services.Identity.Infrastructure.csproj
dotnet sln add src/Services.Identity/Services.Identity.API/Services.Identity.API.csproj
dotnet sln add tests/Services.Identity.Tests/Services.Identity.Tests.csproj
```

### Paso 6: Crear archivos base

Crear `src/Services.Identity/Services.Identity.Domain/Primitives/Entity.cs`:
```csharp
namespace Services.Identity.Domain.Primitives;

public abstract class Entity
{
    public Guid Id { get; protected set; }

    protected Entity() => Id = Guid.NewGuid();

    public override bool Equals(object? obj)
    {
        if (obj is not Entity other) return false;
        if (ReferenceEquals(this, other)) return true;
        if (GetType() != other.GetType()) return false;
        return Id == other.Id;
    }

    public override int GetHashCode() => Id.GetHashCode();
}
```

Crear `src/Services.Identity/Services.Identity.Domain/Primitives/AggregateRoot.cs`:
```csharp
namespace Services.Identity.Domain.Primitives;

public abstract class AggregateRoot : Entity
{
    private readonly List<DomainEvent> _domainEvents = new();
    public IReadOnlyCollection<DomainEvent> DomainEvents => _domainEvents.AsReadOnly();

    protected void AddDomainEvent(DomainEvent eventItem) => _domainEvents.Add(eventItem);
    public void ClearDomainEvents() => _domainEvents.Clear();
}

public abstract record DomainEvent
{
    public Guid Id { get; init; } = Guid.NewGuid();
    public DateTime OccurredOn { get; init; } = DateTime.UtcNow;
}
```

Crear `src/Services.Identity/Services.Identity.Application/DependencyInjection.cs`:
```csharp
using Microsoft.Extensions.DependencyInjection;
using System.Reflection;

namespace Services.Identity.Application;

public static class DependencyInjection
{
    public static IServiceCollection AddApplication(this IServiceCollection services)
    {
        services.AddMediatR(cfg =>
            cfg.RegisterServicesFromAssembly(Assembly.GetExecutingAssembly()));
        services.AddAutoMapper(Assembly.GetExecutingAssembly());
        return services;
    }
}
```

Crear `src/Services.Identity/Services.Identity.API/Program.cs`:
```csharp
using Services.Identity.Application;
using Services.Identity.Infrastructure;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddApplication().AddInfrastructure(builder.Configuration);
builder.Services.AddControllers();
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen();

var app = builder.Build();

if (app.Environment.IsDevelopment())
{
    app.UseSwagger();
    app.UseSwaggerUI();
}

app.UseHttpsRedirection();
app.UseAuthorization();
app.MapControllers();

app.Run();
```

### Paso 7: Verificar
```bash
dotnet build
dotnet test
```

## Reglas

1. **Repetir pasos 2-5** para Tenant Service y Billing Service
2. **Clean Architecture** en cada microservicio
3. **Database-per-service** - cada servicio su propia DB
4. **CQRS** - EF Core writes, Dapper reads
5. **TDD** - tests para cada feature

## Skills Auto-invocados

- `scaffolding` - Base del scaffold
- `clean-arch-design` - Arquitectura
- `jwt-auth` - Autenticacion
- `blazor-dashboard-template` - UI admin
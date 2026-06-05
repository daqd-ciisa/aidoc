---
name: api-docs-generator
description: Genera documentación de API con Swagger, ejemplos y testing commands
trigger: "api docs, swagger, openapi, documentation, api specification"
---

# API Docs Generator Skill

Genera documentación completa de API usando Swagger/OpenAPI con ejemplos y comandos de test.

## Componentes Generados

### 1. Swagger/OpenAPI Spec
```csharp
// Program.cs
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen(c =>
{
    c.SwaggerDoc("v1", new OpenApiInfo
    {
        Title = "My API",
        Version = "v1",
        Description = "API for MyService"
    });
});
```

### 2. XML Comments
```csharp
/// <summary>
/// Get an order by ID
/// </summary>
/// <param name="id">The order GUID</param>
/// <returns>The order if found</returns>
/// <response code="404">Order not found</response>
[HttpGet("{id:guid}")]
[ProducesResponseType(typeof(OrderDto), 200)]
[ProducesResponseType(404)]
public async Task<IResult> GetOrder(Guid id)
```

### 3. Ejemplos de Request/Response
```json
// GET /api/orders/123e4567-e89b-12d3-a456-426614174000

// Response 200
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "customerId": "...",
  "status": "Pending",
  "items": [...],
  "totalAmount": 99.99
}
```

### 4. Postman/HTTP Files
```http
### Get Order
GET {{baseUrl}}/api/orders/123e4567-e89b-12d3-a456-426614174000
Authorization: Bearer {{token}}

### Create Order
POST {{baseUrl}}/api/orders
Content-Type: application/json

{
  "customerId": "...",
  "items": [...]
}
```

## Estructura de Docs

```
MyService.API/
├── docs/
│   ├── openapi.yaml
│   ├── examples/
│   │   ├── order-get.json
│   │   └── order-create.json
│   └── test-requests/
│       └──.http
└── README.md  # Links a docs
```

## Skills Auto-invocados

- `clean-arch-design` - Diseño de endpoints
- `scaffolding` - Estructura de proyecto
- `dotnet-best-practices` - Best practices API

## Reglas

1. **OpenAPI 3.0+** - usar versión actual
2. **Ejemplos completos** - request y response
3. **Authentication docs** - cómo autenticar
4. **Error codes** - todos los códigos de error
5. **Try it out** - configurar Swagger UI

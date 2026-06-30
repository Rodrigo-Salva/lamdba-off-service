# Registro Cloud Innovation Day — Serverless en AWS

Aplicación serverless para registrar, listar, consultar y eliminar estudiantes inscritos al evento académico **Cloud Innovation Day** (Tecsup Cloud Academy).

**Stack:** AWS Lambda (Node.js 20.x) + Amazon API Gateway + Amazon DynamoDB + IAM + CloudWatch

---

## Arquitectura

```
Cliente / Postman
        |
        v
Amazon API Gateway (EstudiantesAPI - stage: dev)
        |
        v
   AWS Lambda (gestion-estudiantes)
        |              |
        v              v
   DynamoDB       CloudWatch Logs
(EstudiantesEvento)
```

---

## Paso 1: Crear la tabla en DynamoDB

1. Consola de AWS → buscar **DynamoDB**.
2. Panel izquierdo → **Tables** → **Create table**.
3. **Table name:** `EstudiantesEvento`
4. **Partition key:** `id`, tipo `String`.
5. No agregar Sort key.
6. **Table settings:** dejar en "Default settings" (capacidad on-demand).
7. **Create table** y esperar a que el status pase a `Active`.

**Resultado:** tabla `EstudiantesEvento` con clave primaria `id (String)`, región `us-east-1`.

---

## Paso 2: Crear el rol IAM para Lambda

1. Consola de AWS → buscar **IAM** → **Roles** → **Create role**.
2. **Trusted entity type:** AWS service → **Use case:** Lambda.
3. Adjuntar las políticas necesarias para que la función pueda:
   - Insertar datos en DynamoDB (`PutItem`)
   - Leer datos desde DynamoDB (`GetItem`, `Scan`)
   - Eliminar datos de DynamoDB (`DeleteItem`)
   - Escribir logs en CloudWatch (`CreateLogGroup`, `CreateLogStream`, `PutLogEvents`)
4. Se puede usar la política administrada `AmazonDynamoDBFullAccess` + `AWSLambdaBasicExecutionRole` para el lab, o crear una política personalizada con permisos mínimos solo sobre la tabla `EstudiantesEvento`.
5. **Role name:** `lambda-estudiantes-rol`
6. **Create role**.

---

## Paso 3: Crear la función Lambda

1. Consola de AWS → buscar **Lambda** → **Create function**.
2. **Function name:** `gestion-estudiantes`
3. **Runtime:** Node.js 20.x
4. **Architecture:** x86_64
5. **Permissions:** Use an existing role → seleccionar `lambda-estudiantes-rol`.
6. **Create function**.
7. En el editor de código (o subiendo un `.zip`), pegar el contenido de `index.js` (ver más abajo).
8. Si se usa el SDK v3 de AWS (`@aws-sdk/client-dynamodb`, `@aws-sdk/lib-dynamodb`), ya viene incluido en el runtime de Node.js 20.x de Lambda, no requiere capa adicional.
9. **Deploy** para guardar los cambios.

### Código fuente (`index.js`)

```javascript
const { DynamoDBClient } = require("@aws-sdk/client-dynamodb");
const {
  DynamoDBDocumentClient, PutCommand, ScanCommand,
  GetCommand, DeleteCommand
} = require("@aws-sdk/lib-dynamodb");

const client = new DynamoDBClient({});
const docClient = DynamoDBDocumentClient.from(client);
const TABLE_NAME = "EstudiantesEvento";

exports.handler = async (event) => {
  const method = event.httpMethod || event.requestContext?.http?.method || "";
  const path = event.path || event.rawPath || "";
  const pathParams = event.pathParameters || {};

  try {
    if (method === "POST" && path.endsWith("/estudiantes")) {
      return await registrarEstudiante(event);
    } else if (method === "GET" && path.endsWith("/estudiantes")) {
      return await listarEstudiantes();
    } else if (method === "GET" && pathParams.id) {
      return await buscarEstudiante(pathParams.id);
    } else if (method === "DELETE" && pathParams.id) {
      return await eliminarEstudiante(pathParams.id);
    } else {
      return respuesta(404, { mensaje: "Ruta no encontrada" });
    }
  } catch (error) {
    return respuesta(500, { error: error.message });
  }
};

async function registrarEstudiante(event) {
  const body = JSON.parse(event.body || "{}");
  const campos = ["id", "nombres", "apellidos", "correo", "carrera", "ciclo", "fechaRegistro"];
  for (const campo of campos) {
    if (!(campo in body)) {
      return respuesta(400, { mensaje: `Falta el campo: ${campo}` });
    }
  }
  await docClient.send(new PutCommand({ TableName: TABLE_NAME, Item: body }));
  return respuesta(201, { mensaje: "Estudiante registrado correctamente", id: body.id });
}

async function listarEstudiantes() {
  const result = await docClient.send(new ScanCommand({ TableName: TABLE_NAME }));
  return respuesta(200, result.Items || []);
}

async function buscarEstudiante(id) {
  const result = await docClient.send(new GetCommand({ TableName: TABLE_NAME, Key: { id } }));
  if (!result.Item) {
    return respuesta(404, { mensaje: "No se encontró el estudiante solicitado" });
  }
  return respuesta(200, result.Item);
}

async function eliminarEstudiante(id) {
  await docClient.send(new DeleteCommand({ TableName: TABLE_NAME, Key: { id } }));
  return respuesta(200, { mensaje: "Estudiante eliminado correctamente" });
}

function respuesta(statusCode, body) {
  return {
    statusCode,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  };
}
```

**Configuración adicional:**
- Handler: `index.handler`
- Timeout: 3 segundos (default, suficiente para este caso)
- Memoria: 128 MB (default)

---

## Paso 4: Configurar API Gateway

1. Consola de AWS → buscar **API Gateway** → **Create API**.
2. Elegir **REST API** (o HTTP API) → **Build**.
3. **API name:** `EstudiantesAPI`
4. Crear los recursos y métodos:

| Método | Recurso | Integración |
|--------|---------|--------------|
| POST | `/estudiantes` | Lambda `gestion-estudiantes` |
| GET | `/estudiantes` | Lambda `gestion-estudiantes` |
| GET | `/estudiantes/{id}` | Lambda `gestion-estudiantes` |
| DELETE | `/estudiantes/{id}` | Lambda `gestion-estudiantes` |

5. Para cada método, usar **Lambda Proxy Integration** (activar el checkbox "Use Lambda Proxy integration") para que el `event` completo llegue a la función tal como lo espera el código.
6. Habilitar **CORS** si se va a probar desde un frontend web.
7. **Deploy API** → crear un nuevo **stage**: `dev`.
8. Anotar la **URL base** generada, con el formato:
   `https://{api-id}.execute-api.us-east-1.amazonaws.com/dev`

---

## Paso 5: Probar los endpoints

Usar Postman, Thunder Client o Insomnia contra la URL base + el endpoint correspondiente.

**Registrar estudiante — POST /estudiantes**
```json
{
  "id": "E001",
  "nombres": "Luis Ángel",
  "apellidos": "Campos Valenzuela",
  "correo": "luis.campos@tecsup.edu.pe",
  "carrera": "Diseño y Desarrollo de Software",
  "ciclo": "5",
  "fechaRegistro": "2026-06-30"
}
```
Respuesta esperada (201): `{ "mensaje": "Estudiante registrado correctamente", "id": "E001" }`

**Listar estudiantes — GET /estudiantes**
Respuesta esperada (200): array con todos los estudiantes registrados.

**Consultar por ID — GET /estudiantes/{id}**
Respuesta esperada (200) si existe, o (404) `{ "mensaje": "No se encontró el estudiante solicitado" }` si no existe.

**Eliminar — DELETE /estudiantes/{id}**
Respuesta esperada (200): `{ "mensaje": "Estudiante eliminado correctamente" }`

---

## Paso 6: Verificar logs en CloudWatch

1. Consola de AWS → buscar **CloudWatch** → **Log groups**.
2. Buscar el grupo `/aws/lambda/gestion-estudiantes`.
3. Cada invocación genera un log stream con:
   - `START RequestId: ... Version: $LATEST`
   - `END RequestId: ...`
   - `REPORT RequestId: ... Duration: X ms Billed Duration: X ms Memory Size: 128 MB Max Memory Used: XX MB`

---

## Paso 7: Diagrama de arquitectura

Diagrama elaborado en **draw.io** (https://app.diagrams.net) usando la librería oficial de íconos AWS4, mostrando el flujo: Cliente → API Gateway → Lambda → DynamoDB, y Lambda → CloudWatch (logs) / IAM Role (permisos).

---

## Limpieza de recursos (al finalizar)

Para evitar costos innecesarios, eliminar en este orden:

1. **API Gateway:** eliminar la API `EstudiantesAPI`.
2. **Lambda:** eliminar la función `gestion-estudiantes`.
3. **DynamoDB:** eliminar la tabla `EstudiantesEvento`.
4. **IAM:** eliminar el rol `lambda-estudiantes-rol`.
5. **CloudWatch:** eliminar el log group `/aws/lambda/gestion-estudiantes` (opcional, se elimina solo o se puede borrar manualmente).

---

## Resumen de recursos creados

| Recurso | Nombre | Detalle |
|---------|--------|---------|
| Tabla DynamoDB | `EstudiantesEvento` | PK: `id` (String), on-demand |
| Rol IAM | `lambda-estudiantes-rol` | Acceso a DynamoDB + CloudWatch Logs |
| Función Lambda | `gestion-estudiantes` | Node.js 20.x, handler `index.handler` |
| API Gateway | `EstudiantesAPI` | Stage `dev`, Lambda Proxy Integration |
| Región | `us-east-1` | Norte de Virginia |

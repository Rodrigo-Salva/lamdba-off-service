import json
import boto3

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('EstudiantesEvento')

def lambda_handler(event, context):
    # Soporte para REST API y HTTP API de API Gateway
    method = event.get('httpMethod') or event.get('requestContext', {}).get('http', {}).get('method', '')
    path = event.get('path') or event.get('rawPath', '')
    path_params = event.get('pathParameters') or {}

    try:
        if method == 'POST' and path.endswith('/estudiantes'):
            return registrar_estudiante(event)
        elif method == 'GET' and path.endswith('/estudiantes'):
            return listar_estudiantes()
        elif method == 'GET' and path_params.get('id'):
            return buscar_estudiante(path_params.get('id'))
        elif method == 'DELETE' and path_params.get('id'):
            return eliminar_estudiante(path_params.get('id'))
        else:
            return respuesta(404, {'mensaje': 'Ruta no encontrada', 'debug': {'method': method, 'path': path}})
    except Exception as e:
        return respuesta(500, {'error': str(e)})

def registrar_estudiante(event):
    body = json.loads(event.get('body', '{}'))
    campos = ['id', 'nombres', 'apellidos', 'correo', 'carrera', 'ciclo', 'fechaRegistro']
    for campo in campos:
        if campo not in body:
            return respuesta(400, {'mensaje': f'Falta el campo: {campo}'})
    table.put_item(Item=body)
    return respuesta(201, {'mensaje': 'Estudiante registrado correctamente', 'id': body['id']})

def listar_estudiantes():
    result = table.scan()
    return respuesta(200, result.get('Items', []))

def buscar_estudiante(student_id):
    result = table.get_item(Key={'id': student_id})
    item = result.get('Item')
    if not item:
        return respuesta(404, {'mensaje': 'No se encontró el estudiante solicitado'})
    return respuesta(200, item)

def eliminar_estudiante(student_id):
    table.delete_item(Key={'id': student_id})
    return respuesta(200, {'mensaje': 'Estudiante eliminado correctamente'})

def respuesta(status_code, body):
    return {
        'statusCode': status_code,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps(body, ensure_ascii=False)
    }
import os
import json
from flask import Flask, request, jsonify
from pymongo import MongoClient

# --- 1. Configuración de Flask ---
app = Flask(__name__)

# --- 2. Conexión a MongoDB Atlas ---
# La variable MONGO_URI se lee desde las variables de entorno de Render
MONGO_URI = os.environ.get("MONGO_URI")

# Inicialización de las variables de la base de datos
mongo_client = None
CATALOG_COLLECTION = None

# Intento de conexión al iniciar el servidor
if MONGO_URI:
    try:
        # Intento de conexión con un timeout razonable (5 segundos)
        # Se usa la URI simplificada para evitar errores de configuración
        mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        
        # Probar la conexión forzando una operación (ping)
        mongo_client.admin.command('ping')
        
        # Selecciona la base de datos y la colección verificadas
        db = mongo_client['Rog']
        CATALOG_COLLECTION = db['Rog1']
        
        print("INFO: Conexión a MongoDB Atlas establecida con éxito.")
        
    # Corrección del error de sintaxis: se debe especificar la excepción
    except Exception as e: 
        CATALOG_COLLECTION = None
        # Imprime el error específico para la depuración en Render logs
        print(f"ERROR: Fallo de conexión a MongoDB al iniciar el servidor. Detalle: {e}")
else:
    print("ADVERTENCIA: La variable MONGO_URI no está definida.")

# --- 3. Endpoint para Subir el Catálogo (POST) ---
@app.route('/upload', methods=['POST'])
def upload_catalog():
    # Verifica si la conexión a la base de datos fue exitosa al inicio
    if CATALOG_COLLECTION is None:
        # Devuelve un error 500 si la conexión falló
        return jsonify({"message": "ERROR 500: Fallo de conexión a MongoDB al intentar subir."}), 500
    
    try:
        # Obtener los datos JSON del cuerpo de la solicitud
        data = request.get_json(force=True)
        
        # Asume que los datos contienen una lista de productos
        productos = data.get('productos', [])

        if not isinstance(productos, list):
            return jsonify({"message": "El formato de datos es incorrecto. Se espera una lista de productos."}), 400

        # --- Operación crítica: Borrar y Reemplazar ---
        
        # 1. Borrar todos los documentos existentes
        CATALOG_COLLECTION.delete_many({})
        
        # 2. Insertar los nuevos productos solo si la lista no está vacía
        if productos:
            CATALOG_COLLECTION.insert_many(productos)
            
        print(f"INFO: Catálogo actualizado. Productos recibidos: {len(productos)}")

        # Respuesta exitosa
        return jsonify({"message": "Catálogo actualizado con éxito."}), 200

    except Exception as e:
        # Captura cualquier otro error durante el proceso de borrado/inserción
        print(f"ERROR: Fallo interno durante la subida del catálogo. Detalle: {e}")
        return jsonify({"message": "ERROR 500: Fallo interno del servidor durante la operación de datos."}), 500

# --- 4. Endpoint para Obtener el Catálogo (GET) ---
@app.route('/catalog', methods=['GET'])
def get_catalog():
    if CATALOG_COLLECTION is None:
        return jsonify({"message": "ERROR 500: Fallo de conexión a MongoDB."}), 500
    
    try:
        # Consulta todos los documentos en la colección y los convierte a lista
        productos = list(CATALOG_COLLECTION.find({}, {'_id': 0})) # '_id': 0 excluye el ID de MongoDB
        
        print(f"INFO: Catálogo solicitado. Productos enviados: {len(productos)}")
        
        return jsonify({"productos": productos}), 200
        
    except Exception as e:
        print(f"ERROR: Fallo al obtener el catálogo. Detalle: {e}")
        return jsonify({"message": "ERROR 500: Fallo al consultar la base de datos."}), 500


if __name__ == '__main__':
    # Render usa la variable de entorno PORT. Si no existe, usa 5000 (para pruebas locales)
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
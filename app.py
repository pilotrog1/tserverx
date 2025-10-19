# app.py (o server.py) - Backend de Gestión en Render

from flask import Flask, jsonify, request
from flask_cors import CORS
from pymongo import MongoClient
import os
import json

# ----------------------------------------------------------------------
# 1. CONFIGURACIÓN INICIAL
# ----------------------------------------------------------------------

app = Flask(__name__)
# Permitir peticiones desde cualquier origen (necesario para la App Kivy)
CORS(app) 

# Variables de conexión globales, inicializadas a None
mongo_client = None 
db = None 
# Asume que esta es tu colección principal de productos
CATALOG_COLLECTION = None 

# ----------------------------------------------------------------------
# 2. LÓGICA DE CONEXIÓN ROBUSTA A MONGODB (Anti-NoneType)
# ----------------------------------------------------------------------

def initialize_mongo():
    """Establece o restablece la conexión a MongoDB usando la URI de Render."""
    global mongo_client, db, CATALOG_COLLECTION
    
    # Render usa variables de entorno para la URI de la base de datos
    # Asegúrate que esta variable (MONGO_URI) esté configurada en Render
    MONGO_URI = os.environ.get("MONGO_URI") 
    
    if not MONGO_URI:
        print("ERROR CRÍTICO: MONGO_URI no configurada en el entorno de Render.")
        return False
        
    try:
        # Intento de conexión con un timeout razonable
        mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        
        # Probar la conexión forzando una operación (opcional pero bueno)
        mongo_client.admin.command('ping') 
        
        # Selecciona la base de datos y la colección
        # REEMPLAZA 'tu_db_nombre' y 'catalogo_productos' CON TUS NOMBRES REALES
        db = mongo_client['Rog'] 
        CATALOG_COLLECTION = db['Rog1']
        
        print("INFO: Conexión a MongoDB Atlas establecida con éxito.")
        return True
    except Exception as e:
        print(f"ERROR al conectar a MongoDB: {e}")
        # Si falla, aseguramos que la variable de la colección sea None
        CATALOG_COLLECTION = None 
        return False

# Inicializar la conexión al arrancar el servidor
initialize_mongo()

# ----------------------------------------------------------------------
# 3. ENDPOINT DE GESTIÓN/ACTUALIZACIÓN (POST /update_catalogo)
# ----------------------------------------------------------------------

@app.route('/update_catalogo', methods=['POST'])
def update_catalog():
    """
    Recibe el JSON del catálogo de la App de Gestión y lo sube a MongoDB.
    Este endpoint también sirve como el 'ping' de reactivación.
    """
    global CATALOG_COLLECTION
    
    # 1. VERIFICACIÓN CRÍTICA DEL ESTADO DE LA CONEXIÓN
    if CATALOG_COLLECTION is None:
        print("ADVERTENCIA: Conexión a MongoDB perdida. Intentando reconectar...")
        if not initialize_mongo():
            # Devuelve un error 500 si la reconexión falla
            return jsonify({"estado": "error", "message": "ERROR 500: Fallo de conexión a MongoDB al intentar subir."}), 500

    try:
        data = request.get_json()
        catalogo_data = data.get('catalogo', {})
        
        # Si el POST es solo el ping de Kivy, no hagas nada (pero ya despertaste el server)
        if catalogo_data.get("operation") == "ping_wakeup":
             return jsonify({"estado": "ok", "message": "Servidor activo. Ping recibido."}), 200

        # --- Lógica de Subida Real ---
        
        # Convertir el diccionario de productos a una lista de documentos de MongoDB
        productos_a_insertar = []
        for product_id, product_data in catalogo_data.items():
            # Asegúrate de incluir el ID para futura referencia
            product_data['_id'] = product_id 
            productos_a_insertar.append(product_data)
        
        if productos_a_insertar:
            # 2. Borrar el catálogo anterior y subir el nuevo
            CATALOG_COLLECTION.delete_many({}) 
            CATALOG_COLLECTION.insert_many(productos_a_insertar)
        
        print(f"INFO: Catálogo actualizado con {len(productos_a_insertar)} productos.")
        return jsonify({"estado": "ok", "message": "Catálogo actualizado con éxito."}), 200
        
    except Exception as e:
        print(f"ERROR FATAL al subir el catálogo: {e}")
        return jsonify({"estado": "error", "message": f"ERROR 500: Fallo interno al procesar/subir datos: {str(e)}"}), 500

# ----------------------------------------------------------------------
# 4. ENDPOINT DE OBTENCIÓN DE DATOS (GET /catalogo)
# ----------------------------------------------------------------------

@app.route('/catalogo', methods=['GET'])
def get_catalog():
    """
    Devuelve el catálogo completo de MongoDB para la App de Kivy.
    """
    global CATALOG_COLLECTION
    
    # 1. VERIFICACIÓN CRÍTICA DEL ESTADO DE LA CONEXIÓN
    if CATALOG_COLLECTION is None:
        print("ADVERTENCIA: Conexión a MongoDB perdida. Intentando reconectar...")
        if not initialize_mongo():
            # Devuelve una respuesta vacía válida (pero con código 503) si la reconexión falla
            return jsonify({"catalogo": {}, "error": "Servidor inactivo o sin conexión a DB."}), 503 

    try:
        # 2. Consulta y Construcción del JSON
        cursor = CATALOG_COLLECTION.find({})
        catalogo_dict = {}
        
        for doc in cursor:
            # Elimina el ID interno de MongoDB para que el JSON sea limpio
            doc.pop('_id', None) 
            # Usa el 'id' original como clave si lo incluiste, o genera uno si es necesario
            product_id = doc.get('id') or doc.get('ID') or str(doc['nombre']) 
            catalogo_dict[product_id] = doc
            
        print(f"INFO: Enviando catálogo con {len(catalogo_dict)} productos.")
        return jsonify({"catalogo": catalogo_dict}), 200
        
    except Exception as e:
        print(f"ERROR FATAL al leer el catálogo: {e}")
        # En caso de error de lectura, devuelve un catálogo vacío para no crashear Kivy
        return jsonify({"catalogo": {}, "error": f"Error interno: {str(e)}"}), 500

# ----------------------------------------------------------------------
# 5. INICIO DE LA APLICACIÓN
# ----------------------------------------------------------------------

if __name__ == '__main__':
    # Usar el puerto proporcionado por Render, o 5000 por defecto
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

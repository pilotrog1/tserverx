# -*- coding: utf-8 -*-
import os # Importación de 'os' es crucial
import json
import atexit
from datetime import datetime
from flask import Flask, jsonify, request, send_from_directory, abort
from flask_cors import CORS
import threading
import time

# ⬇️ IMPORTACIÓN DE MONGODB
from pymongo import MongoClient
# from bson.objectid import ObjectId # Ya no es necesario si solo usas el ID de producto 'P1'

# ======================================================================
# CONFIGURACIÓN DE PERSISTENCIA (MONGODB)
# ======================================================================

# 🛑 ¡SEGURO! Leemos el valor de la variable de entorno MONGO_URI.
# Si no está definida (ej. desarrollo local), usa 'mongodb://localhost:27017/'
MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/') 
DB_NAME = 'tiendita_catalogo'
COLLECTION_NAME = 'productos'

IMAGE_FOLDER = 'images'
AUTO_SAVE_INTERVAL = 600

# Variables globales para la conexión
client = None
db = None
productos_collection = None

# ======================================================================
# FUNCIONES DE CONEXIÓN Y MANTENIMIENTO
# ======================================================================

def connect_to_mongo():
    """Establece la conexión inicial a MongoDB."""
    global client, db, productos_collection
    try:
        print(f"INFO: Conectando a MongoDB...")
        # Usamos el MONGO_URI que viene del entorno (Render) o el fallback local
        client = MongoClient(MONGO_URI)
        client.admin.command('ping') 
        db = client[DB_NAME]
        productos_collection = db[COLLECTION_NAME]
        
        print(f"INFO: Conexión a MongoDB exitosa. Usando DB: {DB_NAME}")
        
        if productos_collection.count_documents({}) == 0:
            print("INFO: Colección de productos vacía. Cargando datos de ejemplo.")
            initialize_sample_data()
            
        return True
    except Exception as e:
        print(f"ERROR: No se pudo conectar a MongoDB: {e}")
        return False

def initialize_sample_data():
    """Inserta datos de ejemplo si la colección está vacía."""
    sample_data = {
        'P1': {'name': 'LECHITA', 'price': '25', 'offer': '22', 'image': 'leche.jpg', 'description': 'LECHE FRESCA ENTERA.'},
        'P2': {'name': 'ACEITE', 'price': '35', 'offer': '29', 'image': 'aceite.jpg', 'description': 'ACEITE DE COCINA VEGETAL.'},
        'P3': {'name': 'MARUCHAN', 'price': '20', 'offer': '17', 'image': 'maruchan.jpg', 'description': 'SOPA INSTANTÁNEA SABOR POLLO.'},
    }
    
    products_to_insert = [
        {**data, 'id': prod_id} for prod_id, data in sample_data.items()
    ]
    
    productos_collection.insert_many(products_to_insert)
    print("INFO: Datos de ejemplo insertados en MongoDB.")

def auto_save_worker():
    """Trabajador para tareas periódicas (mantenimiento)."""
    while True:
        time.sleep(AUTO_SAVE_INTERVAL)
        pass

def start_auto_save():
    """Inicia el hilo de tareas automáticas."""
    auto_save_thread = threading.Thread(target=auto_save_worker, daemon=True)
    auto_save_thread.start()
    print("INFO: Sistema de mantenimiento automático iniciado")

def cleanup_on_exit():
    """Función de limpieza al salir."""
    print("INFO: Cerrando servidor - cerrando conexión a MongoDB...")
    if client:
        client.close()
    print("INFO: Servidor cerrado correctamente")

# ======================================================================
# CONFIGURACIÓN DE FLASK
# ======================================================================

if not os.path.exists(IMAGE_FOLDER):
    os.makedirs(IMAGE_FOLDER)

app = Flask(__name__)
CORS(app)

# ======================================================================
# RUTAS DE LA API
# ======================================================================

@app.route('/')
def home():
    """RUTA INICIAL PARA VERIFICACIÓN DEL SERVIDOR"""
    server_info = {
        "status": "SERVIDOR DE CATÁLOGO ACTIVO",
        "endpoints": {
            "/catalogo": "GET - Obtener catálogo completo",
            "/update_catalogo": "POST - Actualizar catálogo",
            "/images/<filename>": "GET - Servir imágenes"
        },
        "stats": {
            "productos": productos_collection.count_documents({}),
            "ultima_actualizacion": datetime.now().isoformat()
        }
    }
    return jsonify(server_info)

@app.route('/catalogo', methods=['GET'])
def get_catalogo():
    """OBTIENE EL CATÁLOGO COMPLETO desde MongoDB."""
    try:
        productos_cursor = productos_collection.find({})
        
        catalogo = {}
        for doc in productos_cursor:
            prod_id = doc.get('id')
            if prod_id:
                doc.pop('_id', None) 
                catalogo[prod_id] = doc

        response_data = {
            "catalogo": catalogo, 
            "metadata": {
                "total_productos": len(catalogo),
                "ultima_actualizacion": datetime.now().isoformat(),
                "estado": "ok"
            }
        }
        return jsonify(response_data)
    except Exception as e:
        error_response = {
            "error": "Error interno del servidor al obtener catálogo",
            "detalles": str(e),
            "estado": "error"
        }
        return jsonify(error_response), 500

@app.route('/update_catalogo', methods=['POST'])
def update_catalogo():
    """ACTUALIZA y PERSISTE el catálogo completo en MongoDB."""
    
    if not request.json:
        return jsonify({"message": "FALTA CUERPO JSON EN LA PETICIÓN", "estado": "error"}), 400

    new_catalogo = request.json
    
    if not isinstance(new_catalogo, dict):
        return jsonify({"message": "EL CATÁLOGO DEBE SER UN DICCIONARIO DE PRODUCTOS", "estado": "error"}), 400

    try:
        old_count = productos_collection.count_documents({})
        # 1. ELIMINAR TODOS
        productos_collection.delete_many({}) 
        
        products_to_insert = []
        for prod_id, data in new_catalogo.items():
            # 2. Re-insertar con el ID del producto (P1, P2)
            products_to_insert.append({**data, 'id': prod_id})

        # 3. INSERTAR NUEVOS
        if products_to_insert:
            productos_collection.insert_many(products_to_insert)
        
        new_count = productos_collection.count_documents({})
        
        print("=== CATÁLOGO ACTUALIZADO EN MONGODB ===")
        print(f"Productos anteriores: {old_count}")
        print(f"Productos nuevos: {new_count}")
        
        success_response = {
            "message": "CATÁLOGO ACTUALIZADO CON ÉXITO EN MONGODB",
            "count": new_count,
            "previous_count": old_count,
            "estado": "ok"
        }
        return jsonify(success_response), 200

    except Exception as e:
        error_response = {
            "message": f"ERROR INTERNO AL ACTUALIZAR CATÁLOGO EN MONGODB: {str(e)}",
            "estado": "error"
        }
        return jsonify(error_response), 500

@app.route('/images/<path:filename>')
def serve_image(filename):
    """SIRVE IMÁGENES ESTÁTICAS DESDE LA CARPETA 'IMAGES'."""
    try:
        safe_filename = filename.lower().strip()
        return send_from_directory(IMAGE_FOLDER, safe_filename)
    except FileNotFoundError:
        abort(404) 
    except Exception as e:
        return jsonify({"error": f"Error sirviendo imagen {filename}", "detalles": str(e), "estado": "error"}), 500

# ======================================================================
# INICIO DE LA APLICACIÓN
# ======================================================================
if __name__ == '__main__':
    print("=== INICIANDO SERVIDOR DE CATÁLOGO (MONGODB) ===")
    
    if not connect_to_mongo():
        print("¡ERROR FATAL: NO SE PUDO CONECTAR A MONGODB!")
        exit(1)
        
    start_auto_save()
    atexit.register(cleanup_on_exit)
    
    print("=== SERVIDOR INICIADO CORRECTAMENTE ===")
    
    # Render usará gunicorn o su propio servidor, pero esto es para desarrollo local
    app.run(debug=True, host='0.0.0.0', port=5000)

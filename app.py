# -*- coding: utf-8 -*-
import os
import json
from flask import Flask, request, jsonify
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ConfigurationError

# --- 1. Configuración de Flask ---
app = Flask(__name__)

# --- 2. Conexión a MongoDB Atlas ---
MONGO_URI = os.environ.get("MONGO_URI")

mongo_client = None
CATALOG_COLLECTION = None
DB_NAME = 'Rog'  
COLLECTION_NAME = 'Rog1' 

# Intento de conexión al iniciar el servidor
if MONGO_URI:
    try:
        # Intento de conexión con un timeout razonable (5 segundos)
        mongo_client = MongoClient(
            MONGO_URI, 
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000
        )
        
        # Probar la conexión forzando una operación (ping)
        mongo_client.admin.command('ping')
        
        # Selecciona la base de datos y la colección
        db = mongo_client[DB_NAME]
        CATALOG_COLLECTION = db[COLLECTION_NAME]
        
        print(f"INFO: Conexión a MongoDB Atlas establecida con éxito en DB: {DB_NAME}.")
        
    except (ConnectionFailure, ConfigurationError) as e: 
        CATALOG_COLLECTION = None
        print(f"ERROR 500: Fallo de conexión o configuración de MongoDB. Detalle: {e}")
    except Exception as e:
        CATALOG_COLLECTION = None
        print(f"ERROR 500: Fallo de conexión desconocido. Detalle: {e}")
else:
    print("ADVERTENCIA: La variable MONGO_URI no está definida. El servidor funcionará sin DB.")

# --- 3. Endpoint para Subir el Catálogo (POST) ---
# Este endpoint también funciona como "ping" (wake-up) si no envía datos.
@app.route('/upload', methods=['POST'])
def upload_catalog():
    if CATALOG_COLLECTION is None:
        return jsonify({"message": "ERROR 503: Servicio de base de datos no disponible."}), 503
    
    try:
        # Obtener los datos JSON. silent=True evita errores si el cuerpo está vacío (ping)
        data = request.get_json(silent=True)
        
        # Manejar el ping de despertar (no hay datos)
        if not data:
             print("INFO: Recibido POST de ping/despertar.")
             return jsonify({"message": "Servidor activo. Operación de subida omitida (datos nulos)."}), 200

        # Asume que los datos contienen una lista de productos
        productos = data.get('productos', [])

        if not isinstance(productos, list):
            return jsonify({"message": "El formato de datos es incorrecto. Se espera una lista de productos."}), 400

        # Si se reciben datos, realizar la sobrescritura
        # 1. Borrar todos los documentos existentes
        CATALOG_COLLECTION.delete_many({})
        
        # 2. Insertar los nuevos productos
        if productos:
            CATALOG_COLLECTION.insert_many(productos)
            
        print(f"INFO: Catálogo actualizado. Productos recibidos: {len(productos)}")

        # Respuesta exitosa
        return jsonify({"message": "Catálogo actualizado con éxito."}), 200

    except Exception as e:
        print(f"ERROR 500: Fallo interno durante la subida del catálogo. Detalle: {e}")
        return jsonify({"message": "ERROR 500: Fallo interno del servidor durante la operación de datos."}), 500

# --- 4. Endpoint para Obtener el Catálogo (GET) ---
@app.route('/catalog', methods=['GET'])
def get_catalog():
    if CATALOG_COLLECTION is None:
        return jsonify({"message": "ERROR 503: Servicio de base de datos no disponible."}), 503
    
    try:
        # Se asegura que solo se obtengan los campos necesarios para el cliente
        productos_list = list(CATALOG_COLLECTION.find({}, {'_id': 0}))
        
        # Convertir la lista a un diccionario {ID: datos_producto}
        catalog_dict = {
            item['id']: {k: v for k, v in item.items() if k != 'id'}
            for item in productos_list if 'id' in item
        }
        
        print(f"INFO: Catálogo solicitado. Productos enviados: {len(catalog_dict)}")
        
        # Devolver el diccionario mapeado con la clave "catalogo"
        return jsonify({"catalogo": catalog_dict}), 200
        
    except Exception as e:
        print(f"ERROR 500: Fallo al obtener el catálogo. Detalle: {e}")
        return jsonify({"message": "ERROR 500: Fallo al consultar la base de datos."}), 500

# --- 5. Punto de entrada para el servidor ---
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

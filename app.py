# -*- coding: utf-8 -*-
import os
import json
from flask import Flask, request, jsonify
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ConfigurationError
from bson.errors import InvalidId

# --- 1. Configuración de Flask ---
# CRÍTICO: El módulo principal DEBE llamarse 'app' para que Gunicorn lo encuentre.
app = Flask(__name__)

# --- 2. Conexión a MongoDB Atlas ---
# La URI debe estar configurada en las variables de entorno de Render (MONGO_URI)
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

# --- 3. Endpoint para Subir/Actualizar el Catálogo (POST) ---
# CRÍTICO: Renombrado a /upload para unificar con la app cliente
@app.route('/upload', methods=['POST'])
def upload_catalog():
    if CATALOG_COLLECTION is None:
        return jsonify({"message": "ERROR 503: Servicio de base de datos no disponible."}), 503
    
    try:
        data = request.get_json(silent=True)
        
        # Manejar el ping de despertar (no hay datos o solo datos vacíos)
        if not data or (isinstance(data, dict) and 'productos' not in data):
             print("INFO: Recibido POST de ping/despertar o con datos nulos.")
             return jsonify({"message": "Servidor activo. Operación de subida omitida (datos nulos)."}), 200

        # CRÍTICO: El gestor envía una lista de productos en la clave 'productos'.
        productos = data.get('productos', [])

        if not isinstance(productos, list):
            return jsonify({"message": "El formato de datos es incorrecto. Se espera una lista de productos en la clave 'productos'."}), 400

        # Implementación de sobrescritura total (Truncate and Insert)
        # 1. Borrar todos los documentos existentes
        CATALOG_COLLECTION.delete_many({})
        
        # 2. Insertar los nuevos productos
        if productos:
            # MongoDB usa _id por defecto. Si el cliente envía 'id', lo mapeamos/renombramos 
            # para evitar conflictos, manteniendo el campo 'id' para el cliente Kivy.
            productos_a_insertar = []
            for item in productos:
                # Asegura que no se envíen IDs de MongoDB (aunque deberían ser String)
                if '_id' in item:
                     item.pop('_id') 
                productos_a_insertar.append(item)

            CATALOG_COLLECTION.insert_many(productos_a_insertar)
            
        print(f"INFO: Catálogo actualizado por sobrescritura. Productos insertados: {len(productos)}")

        # Respuesta exitosa
        return jsonify({"message": "Catálogo actualizado con éxito."}), 200

    except Exception as e:
        print(f"ERROR 500: Fallo interno durante la subida del catálogo. Detalle: {e}")
        return jsonify({"message": f"ERROR 500: Fallo interno del servidor durante la operación de datos. Detalle: {e}"}), 500

# --- 4. Endpoint para Obtener el Catálogo (GET) ---
# CRÍTICO: Renombrado a /catalog para unificar con la app cliente
@app.route('/catalog', methods=['GET'])
def get_catalog():
    if CATALOG_COLLECTION is None:
        return jsonify({"message": "ERROR 503: Servicio de base de datos no disponible."}), 503
    
    try:
        # Se obtienen todos los campos
        productos_list = list(CATALOG_COLLECTION.find({}))
        
        # Convertir la lista a un diccionario {ID: datos_producto}
        catalog_dict = {}
        for item in productos_list:
            # MongoDB usa ObjectId por defecto, lo quitamos para el cliente.
            if '_id' in item:
                item.pop('_id')
            
            # Usamos la clave 'id' para mapear, si existe. Si no, lo omitimos.
            prod_id = item.get('id')
            if prod_id:
                # Quitamos la clave 'id' del cuerpo del producto para evitar redundancia
                item.pop('id')
                catalog_dict[prod_id] = item

        print(f"INFO: Catálogo solicitado. Productos enviados: {len(catalog_dict)}")
        
        # Devolver el diccionario mapeado con la clave "catalogo"
        return jsonify(catalog_dict), 200
        
    except Exception as e:
        print(f"ERROR 500: Fallo al obtener el catálogo. Detalle: {e}")
        return jsonify({"message": "ERROR 500: Fallo al consultar la base de datos."}), 500

# --- 5. Punto de entrada para el servidor ---
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

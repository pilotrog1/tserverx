# -*- coding: utf-8 -*-
import os
import json
from flask import Flask, request, jsonify, send_from_directory
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ConfigurationError, OperationFailure
from bson.errors import InvalidId

# --- 1. Configuración de Flask ---
app = Flask(__name__)

# --- 2. Variables de Entorno y Configuración de DB ---
MONGO_URI = os.environ.get("MONGO_URI")

# Nombres de las colecciones
CATALOG_COLLECTION_NAME = os.environ.get('CATALOG_COLLECTION', 'Rog1') 
AD_COLLECTION_NAME = os.environ.get('AD_COLLECTION', 'Advertisement') # NUEVA COLECCIÓN

mongo_client = None
CATALOG_COLLECTION = None
AD_COLLECTION = None # NUEVA REFERENCIA

# Intento de conexión al iniciar el servidor
if MONGO_URI:
    try:
        mongo_client = MongoClient(
            MONGO_URI, 
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000
        )
        
        mongo_client.admin.command('ping')
        
        # Selecciona la base de datos y las colecciones
        db = mongo_client[os.environ.get('DATABASE_NAME', 'Rog')]
        CATALOG_COLLECTION = db[CATALOG_COLLECTION_NAME]
        AD_COLLECTION = db[AD_COLLECTION_NAME] # ASIGNACIÓN DE LA NUEVA COLECCIÓN
        
        print(f"INFO: Conexión a MongoDB Atlas establecida con éxito en DB: {db.name}.")
        
    except OperationFailure as e:
        CATALOG_COLLECTION = None
        AD_COLLECTION = None
        print(f"ERROR 500: Fallo de autenticación o configuración de MongoDB. Detalle: {e.errmsg}")
    except (ConnectionFailure, ConfigurationError) as e: 
        CATALOG_COLLECTION = None
        AD_COLLECTION = None
        print(f"ERROR 500: Fallo de conexión o configuración de MongoDB. Detalle: {e}")
    except Exception as e:
        CATALOG_COLLECTION = None
        AD_COLLECTION = None
        print(f"ERROR 500: Fallo de conexión desconocido. Detalle: {e}")
else:
    print("ADVERTENCIA: La variable MONGO_URI no está definida. El servidor funcionará sin DB.")


# ====================================================================
# --- 3. RUTA: Servir Archivos Estáticos (Imágenes) ---
# ====================================================================
@app.route('/images/<filename>')
def serve_image(filename):
    IMAGE_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'images')
    try:
        return send_from_directory(IMAGE_FOLDER, filename)
    except FileNotFoundError:
        print(f"ADVERTENCIA: Imagen no encontrada en el servidor: {filename}")
        return jsonify({"error": "Imagen no encontrada"}), 404
    except Exception as e:
        print(f"ERROR 500: Fallo interno al servir la imagen {filename}: {e}")
        return jsonify({"error": "Error interno del servidor al obtener la imagen"}), 500


# --- 4. Endpoint para Subir/Actualizar (Catálogo y Anuncio) (POST) ---
@app.route('/upload', methods=['POST'])
def upload_catalog():
    if CATALOG_COLLECTION is None or AD_COLLECTION is None:
        return jsonify({"message": "ERROR 503: Servicio de base de datos no disponible."}), 503
    
    try:
        data = request.get_json(silent=True)
        
        # Manejar el ping de despertar o datos nulos
        if not data or (isinstance(data, dict) and 'productos' not in data and 'anuncio' not in data):
             print("INFO: Recibido POST de ping/despertar o con datos nulos. Servidor activo.")
             return jsonify({"message": "Servidor activo. Operación de subida omitida (datos nulos)."}), 200

        # --- GESTIÓN DEL CATÁLOGO ---
        productos = data.get('productos', [])
        if not isinstance(productos, list):
            return jsonify({"message": "El formato de datos es incorrecto. Se espera una lista de productos en la clave 'productos'."}), 400

        # 1. Borrar todos los documentos existentes (Sobrescritura total)
        CATALOG_COLLECTION.delete_many({})
        
        # 2. Insertar los nuevos productos
        if productos:
            productos_a_insertar = []
            for item in productos:
                if '_id' in item:
                     item.pop('_id') 
                productos_a_insertar.append(item)

            CATALOG_COLLECTION.insert_many(productos_a_insertar)
            
        print(f"INFO: Catálogo actualizado por sobrescritura. Productos insertados: {len(productos)}")

        # --- GESTIÓN DEL ANUNCIO (NUEVA LÓGICA) ---
        anuncio_data = data.get('anuncio', {})
        if anuncio_data and isinstance(anuncio_data, dict):
            # Limpiar la colección de anuncio (solo debe haber un documento)
            AD_COLLECTION.delete_many({})
            
            # Asegurar que el campo 'active' sea un booleano
            anuncio_data['active'] = bool(anuncio_data.get('active', False))
            
            # Quitar cualquier ID interno de MongoDB si se envió
            if '_id' in anuncio_data:
                anuncio_data.pop('_id')
                
            # Insertar el nuevo documento de anuncio
            AD_COLLECTION.insert_one(anuncio_data)
            print("INFO: Anuncio/Saludo actualizado con éxito.")

        # Respuesta exitosa
        return jsonify({"message": "Catálogo y Anuncio actualizados con éxito."}), 200

    except Exception as e:
        print(f"ERROR 500: Fallo interno durante la subida del catálogo/anuncio. Detalle: {e}")
        return jsonify({"message": f"ERROR 500: Fallo interno del servidor durante la operación de datos. Detalle: {e}"}), 500

# --- 5. Endpoint para Obtener el Catálogo (GET) ---
@app.route('/catalog', methods=['GET'])
def get_catalog():
    if CATALOG_COLLECTION is None:
        return jsonify({"message": "ERROR 503: Servicio de base de datos no disponible."}), 503
    
    try:
        productos_list = list(CATALOG_COLLECTION.find({}))
        
        catalog_dict = {}
        for item in productos_list:
            if '_id' in item:
                item.pop('_id')
            
            prod_id = item.get('id')
            if prod_id:
                item.pop('id') 
                catalog_dict[prod_id] = item
            else:
                 print(f"ADVERTENCIA: Producto sin clave 'id' encontrado y omitido.")

        print(f"INFO: Catálogo solicitado. Productos enviados: {len(catalog_dict)}")
        
        return jsonify(catalog_dict), 200
        
    except Exception as e:
        print(f"ERROR 500: Fallo al obtener el catálogo. Detalle: {e}")
        return jsonify({"message": "ERROR 500: Fallo al consultar la base de datos."}), 500

# --- 6. Endpoint para Obtener el Anuncio (GET) (NUEVO) ---
@app.route('/advertisement', methods=['GET'])
def get_advertisement():
    if AD_COLLECTION is None:
        # Esto podría ser un error 200 con un objeto vacío si no se quiere que la app falle
        return jsonify({"active": False, "title": "", "description": "", "image": ""}), 200
    
    try:
        # Buscar el único documento de anuncio
        ad_data = AD_COLLECTION.find_one({})
        
        if ad_data:
            # Eliminar la clave interna de MongoDB
            if '_id' in ad_data:
                ad_data.pop('_id')
            
            # Devolver los datos del anuncio
            return jsonify(ad_data), 200
        else:
            # Si no hay documento en la colección, devolver un objeto vacío/inactivo
            return jsonify({"active": False, "title": "", "description": "", "image": ""}), 200
            
    except Exception as e:
        print(f"ERROR 500: Fallo al obtener el anuncio. Detalle: {e}")
        # En caso de fallo, es mejor devolver un objeto inactivo para no bloquear la app
        return jsonify({"active": False, "title": "Error al cargar anuncio", "description": "", "image": ""}), 500


# --- 7. Punto de entrada para el servidor ---
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

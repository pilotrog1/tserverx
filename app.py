# -*- coding: utf-8 -*-
import os
import json
from flask import Flask, request, jsonify, send_from_directory
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ConfigurationError, OperationFailure
# NUEVA IMPORTACIÓN para manejar ObjectID y eliminación
from bson.objectid import ObjectId
from bson.errors import InvalidId 

# --- 1. Configuración de Flask ---
app = Flask(__name__)

# --- 2. Variables de Entorno y Configuración de DB ---
MONGO_URI = os.environ.get("MONGO_URI")

# Nombres de las colecciones
CATALOG_COLLECTION_NAME = os.environ.get('CATALOG_COLLECTION', 'Rog1') 
AD_COLLECTION_NAME = os.environ.get('AD_COLLECTION', 'Advertisement') 
DATABASE_NAME = os.environ.get('DATABASE_NAME', 'Rog') # Nombre de la DB

mongo_client = None
CATALOG_COLLECTION = None
AD_COLLECTION = None 

# Intento de conexión al iniciar el servidor
if MONGO_URI:
    try:
        mongo_client = MongoClient(
            MONGO_URI, 
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000
        )
        
        # El comando ping falla si la conexión no es válida, actuando como un chequeo de salud
        mongo_client.admin.command('ping') 
        
        db = mongo_client[DATABASE_NAME]
        CATALOG_COLLECTION = db[CATALOG_COLLECTION_NAME]
        AD_COLLECTION = db[AD_COLLECTION_NAME] 
        
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
    # Si no hay URI, asegurar que las colecciones sean None para fallar en las rutas
    CATALOG_COLLECTION = None
    AD_COLLECTION = None

# ====================================================================
# --- 3. RUTA: Servir Archivos Estáticos (Imágenes) ---
# ====================================================================
@app.route('/images/<filename>')
def serve_image(filename):
    # Esta ruta se mantiene aunque el anuncio no use imagen, es necesaria para el catálogo.
    IMAGE_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'images')
    try:
        # Nota: Asegúrate de que esta carpeta exista y contenga las imágenes.
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
        
        if not data:
             print("INFO: Recibido POST con datos nulos. Servidor activo.")
             return jsonify({"message": "Servidor activo. Operación de subida omitida (datos nulos)."}), 200

        # --- GESTIÓN DE ELIMINACIÓN ---
        productos_a_eliminar = data.get('productos_a_eliminar', [])
        if productos_a_eliminar and isinstance(productos_a_eliminar, list):
            # La clave de eliminación del cliente es el 'id' (el mismo que el _id de MongoDB en tu caso)
            delete_result = CATALOG_COLLECTION.delete_many(
                {'id': {'$in': productos_a_eliminar}}
            )
            print(f"INFO: Productos eliminados: {delete_result.deleted_count}")

        # --- GESTIÓN DEL CATÁLOGO (Inserción/Actualización) ---
        productos = data.get('productos', [])
        if not isinstance(productos, list):
            return jsonify({"message": "El formato de datos de productos es incorrecto."}), 400

        if productos:
            productos_a_insertar = []
            productos_a_actualizar = []
            
            for item in productos:
                # El gestor Kivy ya garantiza que el campo 'id' está presente
                prod_id = item.get('id') 
                
                # Quitar _id si existe para evitar problemas de inserción/actualización
                if '_id' in item:
                    item.pop('_id') 
                    
                # 1. Producto Nuevo (el gestor Kivy le asigna un ID temporal 'new_...')
                if not prod_id or not prod_id.startswith('P'):
                    # Si tiene un ID temporal, se sube sin ID para que MongoDB asigne uno (_id)
                    # El gestor Kivy ya lo envía sin 'id' en esta etapa, por lo que se inserta como nuevo.
                    # Simplemente lo agregamos a la lista de inserción sin el campo 'id'
                    if 'id' in item:
                         item.pop('id') # Quitar el ID temporal para que MongoDB use _id
                    productos_a_insertar.append(item)
                    continue

                # 2. Producto Permanente (ID comienza con 'P')
                
                # Se utiliza update_one con upsert=True para actualizar si existe o insertarlo si es nuevo 
                # (útil si el producto fue 'eliminado' y luego 're-creado' con el mismo ID)
                
                # Los campos se establecen con $set
                update_set = item.copy()
                update_set.pop('id') # No se actualiza el campo 'id' con $set
                
                CATALOG_COLLECTION.update_one(
                    {'id': prod_id}, 
                    {'$set': update_set},
                    upsert=True
                )
                
            # Insertar los productos nuevos restantes (los que tenían ID temporal o no tenían ID)
            if productos_a_insertar:
                 CATALOG_COLLECTION.insert_many(productos_a_insertar)
            
        print(f"INFO: Catálogo gestionado. Eliminados: {len(productos_a_eliminar)}, Nuevos insertados: {len(productos_a_insertar)}, Actualizados/Upsertados: {len(productos) - len(productos_a_insertar)}")

        # --- GESTIÓN DEL ANUNCIO ---
        anuncio_data = data.get('anuncio', {})
        if anuncio_data and isinstance(anuncio_data, dict):
            # Usar upsert:true para garantizar que SIEMPRE haya un documento de anuncio
            
            anuncio_data['active'] = bool(anuncio_data.get('active', False))
            
            if '_id' in anuncio_data:
                anuncio_data.pop('_id')
                
            # Buscamos un documento para actualizar, si no existe, lo insertamos
            AD_COLLECTION.update_one(
                {}, # Filtro vacío para afectar el primer documento (o el único)
                {'$set': anuncio_data},
                upsert=True
            )
            print("INFO: Anuncio/Saludo gestionado con éxito.")

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
            # Asegurar que el ID del cliente sea el campo 'id' o 'ObjectId' convertido a string
            prod_id = item.get('id')
            
            if prod_id:
                # Usar el campo 'id' (que es el ID permanente 'P...') para la clave
                key_id = prod_id
            elif '_id' in item:
                 # Si no tiene campo 'id' (productos viejos), usamos el _id de MongoDB
                 key_id = str(item['_id'])
            else:
                 print(f"ADVERTENCIA: Producto sin ID válido encontrado y omitido.")
                 continue

            # Eliminar el _id de MongoDB antes de enviar al cliente
            if '_id' in item:
                item.pop('_id')
            
            # Quitar el campo 'id' para que el cliente lo inserte de nuevo como clave
            if 'id' in item:
                item.pop('id')
            
            catalog_dict[key_id] = item
            
        print(f"INFO: Catálogo solicitado. Productos enviados: {len(catalog_dict)}")
        
        return jsonify(catalog_dict), 200
        
    except Exception as e:
        print(f"ERROR 500: Fallo al obtener el catálogo. Detalle: {e}")
        return jsonify({"message": "ERROR 500: Fallo al consultar la base de datos."}), 500

# --- 6. Endpoint para Obtener el Anuncio (GET) ---
@app.route('/advertisement', methods=['GET'])
def get_advertisement():
    if AD_COLLECTION is None:
        # Devolver un objeto inactivo por defecto si la DB no está lista
        return jsonify({"active": False, "title": "", "description": "", "image": ""}), 200
    
    try:
        # Busca el único documento de anuncio
        ad_data = AD_COLLECTION.find_one({})
        
        if ad_data:
            if '_id' in ad_data:
                ad_data.pop('_id')
            
            ad_data['active'] = bool(ad_data.get('active', False))
            
            if 'image' not in ad_data:
                ad_data['image'] = ''

            return jsonify(ad_data), 200
        else:
            # Si no hay documento, devuelve el objeto inactivo por defecto
            return jsonify({"active": False, "title": "", "description": "", "image": ""}), 200
            
    except Exception as e:
        print(f"ERROR 500: Fallo al obtener el anuncio. Detalle: {e}")
        return jsonify({"active": False, "title": "Error al cargar anuncio", "description": "", "image": ""}), 500


# --- 7. Punto de entrada para el servidor ---
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

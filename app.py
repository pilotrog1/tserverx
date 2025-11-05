# -*- coding: utf-8 -*-
import os
import sys
import json
import requests # Necesario para la Opción A: Llamada HTTP Directa
from datetime import datetime # Necesario para el registro de actividad
from flask import Flask, request, jsonify, send_from_directory
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ConfigurationError, OperationFailure
from bson.errors import InvalidId
from bson.objectid import ObjectId

# --- 1. Configuración de Flask ---
app = Flask(__name__)

# --- 2. Variables de Entorno y Configuración de DB y APIs ---
MONGO_URI = os.environ.get("MONGO_URI")

# URL BASE del Microservicio de Gestión de Catálogo para la sincronización (Opción A)
# IMPORTANTE: Cambia 'http://localhost:5001' por la URL real de tu Microservicio de Catálogo.
CATALOG_API_BASE_URL = os.environ.get("CATALOG_API_BASE_URL", "http://localhost:5001") 

# Nombres de las colecciones
CATALOG_COLLECTION_NAME = os.environ.get('CATALOG_COLLECTION', 'Rog1') 
AD_COLLECTION_NAME = os.environ.get('AD_COLLECTION', 'Advertisement') 
RATINGS_STATS_COLLECTION_NAME = os.environ.get('RATINGS_STATS_COLLECTION', 'product_stats') # Estadísticas agregadas
ACTIVITY_COLLECTION_NAME = os.environ.get('ACTIVITY_COLLECTION', 'app_activity')         # Registro de pings y MAU

# Variables de conexión
mongo_client = None
CATALOG_COLLECTION = None
AD_COLLECTION = None
RATINGS_STATS_COLLECTION = None 
ACTIVITY_COLLECTION = None      

# Intento de conexión al iniciar el servidor
if MONGO_URI:
    try:
        mongo_client = MongoClient(
            MONGO_URI, 
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000
        )
        
        mongo_client.admin.command('ping')
        
        db = mongo_client[os.environ.get('DATABASE_NAME', 'Rog')]
        
        # Colecciones existentes
        CATALOG_COLLECTION = db[CATALOG_COLLECTION_NAME]
        AD_COLLECTION = db[AD_COLLECTION_NAME] 
        
        # Colecciones nuevas (para calificaciones y analíticas)
        RATINGS_STATS_COLLECTION = db[RATINGS_STATS_COLLECTION_NAME] 
        ACTIVITY_COLLECTION = db[ACTIVITY_COLLECTION_NAME]         
        
        print(f"INFO: Conexión a MongoDB Atlas establecida con éxito en DB: {db.name}.")
        
    except OperationFailure as e:
        CATALOG_COLLECTION = None
        AD_COLLECTION = None
        RATINGS_STATS_COLLECTION = None
        ACTIVITY_COLLECTION = None
        print(f"ERROR 500: Fallo de autenticación o configuración de MongoDB. Detalle: {e.errmsg}")
    except (ConnectionFailure, ConfigurationError) as e: 
        CATALOG_COLLECTION = None
        AD_COLLECTION = None
        RATINGS_STATS_COLLECTION = None
        ACTIVITY_COLLECTION = None
        print(f"ERROR 500: Fallo de conexión o configuración de MongoDB. Detalle: {e}")
    except Exception as e:
        CATALOG_COLLECTION = None
        AD_COLLECTION = None
        RATINGS_STATS_COLLECTION = None
        ACTIVITY_COLLECTION = None
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


# ====================================================================
# --- 4. Endpoint para Subir/Actualizar (Catálogo y Anuncio) (POST) ---
# Se mantiene para la App de Gestión.
# ====================================================================
@app.route('/upload', methods=['POST'])
def upload_catalog():
    # Se verifica la disponibilidad de las colecciones necesarias para esta función
    if CATALOG_COLLECTION is None or AD_COLLECTION is None:
        return jsonify({"message": "ERROR 503: Servicio de base de datos no disponible para la subida."}), 503
    
    try:
        data = request.get_json(silent=True)
        
        if not data or (isinstance(data, dict) and 'productos' not in data and 'anuncio' not in data):
             print("INFO: Recibido POST de ping/despertar o con datos nulos. Servidor activo.")
             return jsonify({"message": "Servidor activo. Operación de subida omitida (datos nulos)."}), 200

        # --- GESTIÓN DEL CATÁLOGO ---
        productos = data.get('productos', [])
        if not isinstance(productos, list):
            return jsonify({"message": "El formato de datos de productos es incorrecto."}), 400

        # Borrar y reinsertar productos
        CATALOG_COLLECTION.delete_many({})
        if productos:
            productos_a_insertar = []
            for item in productos:
                # CORRECCIÓN: Asegurar que eliminamos el _id si viene del gestor para no causar errores en MongoDB
                if '_id' in item:
                     item.pop('_id') 
                
                productos_a_insertar.append(item)

            CATALOG_COLLECTION.insert_many(productos_a_insertar)
            
        print(f"INFO: Catálogo actualizado por sobrescritura. Productos insertados: {len(productos)}")

        # --- GESTIÓN DEL ANUNCIO ---
        anuncio_data = data.get('anuncio', {})
        if anuncio_data and isinstance(anuncio_data, dict):
            AD_COLLECTION.delete_many({})
            anuncio_data['active'] = bool(anuncio_data.get('active', False))
            
            if '_id' in anuncio_data:
                anuncio_data.pop('_id')
                
            AD_COLLECTION.insert_one(anuncio_data)
            print("INFO: Anuncio/Saludo actualizado con éxito.")

        return jsonify({"message": "Catálogo y Anuncio actualizados con éxito."}), 200

    except Exception as e:
        print(f"ERROR 500: Fallo interno durante la subida del catálogo/anuncio. Detalle: {e}")
        return jsonify({"message": f"ERROR 500: Fallo interno del servidor durante la operación de datos. Detalle: {e}"}), 500

# ====================================================================
# --- 5. Endpoint para Obtener el Catálogo (GET) ---
# ====================================================================
@app.route('/catalog', methods=['GET'])
def get_catalog():
    if CATALOG_COLLECTION is None:
        return jsonify({"message": "ERROR 503: Servicio de base de datos no disponible."}), 503
    
    try:
        productos_cursor = CATALOG_COLLECTION.find({})
        
        catalog_dict = {}
        for item in productos_cursor:
            
            # CORRECCIÓN CRÍTICA: Convertir el ObjectId a str para evitar errores de serialización JSON
            if '_id' in item:
                item['_id'] = str(item['_id'])
            
            prod_key = item.get('upc_id')
            if not prod_key:
                prod_key = item.get('name', item['_id'])
            
            catalog_dict[prod_key] = item
            

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
            # CORRECCIÓN: Quitar el _id antes de enviar
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

# ====================================================================
# --- 7. NUEVOS ENDPOINTS: CALIFICACIONES Y SINCRONIZACIÓN (Opción A) ---
# ====================================================================

@app.route('/rate', methods=['POST'])
def receive_rating():
    # El corazón del Microservicio de Calificaciones.
    if RATINGS_STATS_COLLECTION is None:
        return jsonify({"message": "ERROR 503: Servicio de calificaciones no disponible."}), 503
    
    try:
        data = request.get_json()
        product_id = data.get('id_producto')
        puntuacion = data.get('puntuacion', 0) # 1-5 estrellas o 0 (para corazón/like)
        user_id = data.get('id_usuario')
        
        # Validación de datos mínimos
        if not all([product_id, user_id]) or not isinstance(puntuacion, int) or not (0 <= puntuacion <= 5):
            return jsonify({"message": "Datos de calificación incompletos o inválidos."}), 400

        # Paso 1: Operación ATÓMICA en la colección de estadísticas
        if puntuacion > 0:
            # Lógica para Estrellas
            update_fields = {
                "$inc": {
                    "suma_puntuaciones": puntuacion, 
                    "conteo_total": 1,
                    f"distribucion_estrellas.{puntuacion}": 1,
                }
            }
        else: 
            # Lógica para Corazón (si puntuacion es 0 se asume un like/dislike simple)
            update_fields = {
                "$inc": {
                    "conteo_corazones": 1, # Se asume +1 like/corazón. La lógica UNLIKE requiere más validación.
                }
            }
        
        RATINGS_STATS_COLLECTION.update_one(
            {"id_producto": product_id},
            update_fields,
            upsert=True
        )

        # Paso 2: Leer los nuevos contadores y calcular el promedio
        updated_stats = RATINGS_STATS_COLLECTION.find_one({"id_producto": product_id})
        
        new_suma = updated_stats.get('suma_puntuaciones', 0)
        new_conteo = updated_stats.get('conteo_total', 0)
        
        new_average = round(new_suma / new_conteo, 2) if new_conteo > 0 else 0.0

        # Paso 3: Notificación SÍNCRONA al Microservicio de Catálogo (Opción A)
        catalog_url = f"{CATALOG_API_BASE_URL}/update_rating/{product_id}"
        
        print(f"INFO: Notificando al Catálogo en: {catalog_url}")
        
        response = requests.put(
            catalog_url,
            json={"calificacion_promedio": new_average}
        )

        if response.status_code != 200:
            # Si el Catálogo falla, la transacción de calificación se guardó, pero la sincronización falló.
            print(f"ADVERTENCIA: Fallo al actualizar el Catálogo. Código: {response.status_code}. Detalle: {response.text}")
            # Se devuelve 500 porque la Opción A es síncrona y la sincronización es clave.
            return jsonify({"message": "Calificación registrada, pero la sincronización con el Catálogo falló."}), 500
        
        # Respuesta exitosa al cliente
        return jsonify({"message": "Calificación y sincronización completadas."}), 201

    except requests.exceptions.ConnectionError:
        print(f"ERROR 500: No se pudo conectar al Microservicio de Catálogo. Verifique la URL: {CATALOG_API_BASE_URL}", file=sys.stderr)
        return jsonify({"message": "Fallo en la comunicación con el servicio de Catálogo."}), 500
    except Exception as e:
        print(f"ERROR 500: Fallo interno durante el proceso de calificación. Detalle: {e}", file=sys.stderr)
        return jsonify({"message": "ERROR interno del servidor."}), 500


# ====================================================================
# --- 8. NUEVO ENDPOINT: Ping de Actividad (MAU/DAU) ---
# ====================================================================
@app.route('/ping_activity', methods=['POST'])
def ping_activity():
    # Usado por la App de Catálogo al iniciar para contar usuarios activos.
    if ACTIVITY_COLLECTION is None:
        return jsonify({"message": "ERROR 503: Servicio de actividad no disponible."}), 503
    
    try:
        data = request.get_json()
        device_id = data.get('id_dispositivo')
        
        if not device_id:
            return jsonify({"message": "ID de dispositivo requerido."}), 400
            
        # Registra o actualiza la última conexión de forma atómica (upsert=True)
        ACTIVITY_COLLECTION.update_one(
            {"id_dispositivo": device_id},
            {
                "$set": {
                    "ultima_conexion": datetime.now() 
                }
            },
            upsert=True
        )
        
        return jsonify({"status": "ok", "message": "Actividad registrada."}), 200
        
    except Exception as e:
        print(f"ERROR 500: Fallo al registrar actividad. Detalle: {e}")
        return jsonify({"message": "ERROR interno al registrar actividad."}), 500


# ====================================================================
# --- 9. NUEVO ENDPOINT: Obtener Estadísticas (GET - Para App de Gestión) ---
# ====================================================================
@app.route('/stats/<string:product_id>', methods=['GET'])
def get_product_stats(product_id):
    # La App de Gestión llama a esto para ver el detalle de estrellas, corazones, etc.
    if RATINGS_STATS_COLLECTION is None:
        return jsonify({"message": "ERROR 503: Servicio de estadísticas no disponible."}), 503
    
    try:
        stats_data = RATINGS_STATS_COLLECTION.find_one({"id_producto": product_id})
        
        if stats_data:
            stats_data.pop('_id')
            
            # Calcular el promedio al vuelo para el gestor
            suma = stats_data.get('suma_puntuaciones', 0)
            conteo = stats_data.get('conteo_total', 0)
            
            promedio = suma / conteo if conteo > 0 else 0
            stats_data['calificacion_promedio'] = round(promedio, 2)
            
            return jsonify(stats_data), 200
        else:
            return jsonify({"message": "Producto no encontrado o sin estadísticas."}), 404
            
    except Exception as e:
        print(f"ERROR 500: Fallo al obtener estadísticas. Detalle: {e}")
        return jsonify({"message": "ERROR interno al consultar estadísticas."}), 500


# ====================================================================
# --- 10. Punto de entrada para el servidor ---
# ====================================================================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

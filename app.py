# -*- coding: utf-8 -*-
import os
import json
from flask import Flask, request, jsonify, send_from_directory
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ConfigurationError, OperationFailure
from bson.errors import InvalidId

# --- 1. Configuración de Flask ---
# CRÍTICO: El módulo principal DEBE llamarse 'app' para que Gunicorn lo encuentre.
app = Flask(__name__)

# --- 2. Variables de Entorno y Configuración de DB ---
# La URI debe estar configurada en las variables de entorno de Render (MONGO_URI)
MONGO_URI = os.environ.get("MONGO_URI")

# Asume que el nombre de la DB y la Colección también podrían ser variables de entorno
# Si no lo son, usa tus valores por defecto (Rog, Rog1)
DB_NAME = os.environ.get('DATABASE_NAME', 'Rog')  
COLLECTION_NAME = os.environ.get('COLLECTION_COLLECTION', 'Rog1') 

mongo_client = None
CATALOG_COLLECTION = None

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
        
    except OperationFailure as e:
        CATALOG_COLLECTION = None
        print(f"ERROR 500: Fallo de autenticación o configuración de MongoDB. Detalle: {e.errmsg}")
    except (ConnectionFailure, ConfigurationError) as e: 
        CATALOG_COLLECTION = None
        print(f"ERROR 500: Fallo de conexión o configuración de MongoDB. Detalle: {e}")
    except Exception as e:
        CATALOG_COLLECTION = None
        print(f"ERROR 500: Fallo de conexión desconocido. Detalle: {e}")
else:
    print("ADVERTENCIA: La variable MONGO_URI no está definida. El servidor funcionará sin DB.")


# ====================================================================
# --- 3. NUEVA RUTA: Servir Archivos Estáticos (Imágenes) ---
#    Soluciona el HTTP Error 404 de la aplicación móvil.
# ====================================================================
@app.route('/images/<filename>')
def serve_image(filename):
    """
    Ruta para servir archivos estáticos (imágenes) desde la carpeta local 'images'.
    Asegúrate que la app móvil solicite la URL en el formato: 
    https://tservercatalogo.onrender.com/images/nombre_imagen.jpg
    """
    # Define la ruta absoluta de la carpeta 'images' relativa al archivo del servidor
    IMAGE_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'images')
    
    # Imprimir para depuración (opcional)
    # print(f"INFO: Buscando imagen: {filename} en: {IMAGE_FOLDER}")
    
    try:
        # Envía el archivo solicitado desde la carpeta 'images'
        return send_from_directory(IMAGE_FOLDER, filename)
    except FileNotFoundError:
        # Maneja el caso en que la imagen no existe
        print(f"ADVERTENCIA: Imagen no encontrada en el servidor: {filename}")
        # Devuelve 404, lo que tu aplicación Kivy registrará correctamente como un fallo.
        return jsonify({"error": "Imagen no encontrada"}), 404
    except Exception as e:
        print(f"ERROR 500: Fallo interno al servir la imagen {filename}: {e}")
        return jsonify({"error": "Error interno del servidor al obtener la imagen"}), 500


# --- 4. Endpoint para Subir/Actualizar el Catálogo (POST) ---
@app.route('/upload', methods=['POST'])
def upload_catalog():
    if CATALOG_COLLECTION is None:
        return jsonify({"message": "ERROR 503: Servicio de base de datos no disponible."}), 503
    
    try:
        data = request.get_json(silent=True)
        
        # Manejar el ping de despertar o datos nulos
        if not data or (isinstance(data, dict) and 'productos' not in data):
             print("INFO: Recibido POST de ping/despertar o con datos nulos. Servidor activo.")
             return jsonify({"message": "Servidor activo. Operación de subida omitida (datos nulos)."}), 200

        # CRÍTICO: El gestor envía una lista de productos en la clave 'productos'.
        productos = data.get('productos', [])

        if not isinstance(productos, list):
            return jsonify({"message": "El formato de datos es incorrecto. Se espera una lista de productos en la clave 'productos'."}), 400

        # 1. Borrar todos los documentos existentes (Sobrescritura total)
        CATALOG_COLLECTION.delete_many({})
        
        # 2. Insertar los nuevos productos
        if productos:
            productos_a_insertar = []
            for item in productos:
                # Limpieza: Asegura que el cliente no envíe _id, si lo envía, se elimina
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

# --- 5. Endpoint para Obtener el Catálogo (GET) ---
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
            
            # Usamos la clave 'id' para mapear, si existe. 
            prod_id = item.get('id')
            if prod_id:
                # Quitamos la clave 'id' del cuerpo del producto para evitar redundancia en el valor
                item.pop('id') 
                catalog_dict[prod_id] = item
            else:
                 # Si el producto no tiene ID, lo omitimos o lo registramos como error
                 print(f"ADVERTENCIA: Producto sin clave 'id' encontrado y omitido.")


        print(f"INFO: Catálogo solicitado. Productos enviados: {len(catalog_dict)}")
        
        # Devolver el diccionario mapeado con la clave "catalogo"
        return jsonify(catalog_dict), 200
        
    except Exception as e:
        print(f"ERROR 500: Fallo al obtener el catálogo. Detalle: {e}")
        return jsonify({"message": "ERROR 500: Fallo al consultar la base de datos."}), 500

# --- 6. Punto de entrada para el servidor ---
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    # Usar debug=True solo localmente, no en producción
    app.run(host='0.0.0.0', port=port)
# app.py (Servidor Flask para Tiendita)

import os
import json
from datetime import datetime
# CRÍTICO: Se añade send_from_directory para servir imágenes
from flask import Flask, jsonify, request, send_from_directory 
from pymongo import MongoClient

# ----------------------------------------------------------------------
# 1. CONFIGURACIÓN DEL SERVIDOR Y BASE DE DATOS
# ----------------------------------------------------------------------

app = Flask(__name__)

# CRÍTICO: Usa la variable de entorno MONGO_URI configurada en Render.
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/tienditaDB")

# Define la ubicación de la carpeta donde están las imágenes estáticas
# ¡AJUSTA ESTO a la carpeta REAL de tu proyecto de Render!
# Si tus imágenes están en la carpeta 'images' en la raíz del proyecto:
IMAGE_FOLDER = 'images' 
# Si tus imágenes están en 'assets/images':
# IMAGE_FOLDER = 'assets/images' 


try:
    # Conexión a MongoDB
    client = MongoClient(MONGO_URI)
    db = client.get_database() 
    
    # Colecciones de la base de datos
    products_collection = db.products      # Almacena los productos
    config_collection = db.config          # Almacena anuncios y configuraciones
    
    print("Conexión a MongoDB exitosa.")
except Exception as e:
    print(f"ERROR: No se pudo conectar a MongoDB. Asegúrate de que MONGO_URI esté configurada. Error: {e}")


# ----------------------------------------------------------------------
# 2. ENDPOINT: /images/<filename> (SERVIR ARCHIVOS ESTÁTICOS)
# ----------------------------------------------------------------------

@app.route('/images/<filename>', methods=['GET'])
def serve_image(filename):
    """
    Sirve archivos de imagen estáticos desde la carpeta definida por IMAGE_FOLDER.
    Esto resuelve el error 404 que ocurría al intentar cargar imágenes remotas.
    """
    try:
        # Usa Flask para enviar el archivo desde el directorio especificado.
        # as_attachment=False indica que debe mostrar el contenido, no descargarlo.
        return send_from_directory(
            IMAGE_FOLDER, 
            filename, 
            as_attachment=False
        )
    except FileNotFoundError:
        # Si el archivo no existe, retorna un 404
        return jsonify({"error": "Imagen no encontrada"}), 404
    except Exception as e:
        # Error interno del servidor
        print(f"Error al servir imagen: {e}")
        return jsonify({"error": "Error interno del servidor"}), 500


# ----------------------------------------------------------------------
# 3. ENDPOINT: /catalog (CATÁLOGO)
# ----------------------------------------------------------------------

@app.route('/catalog', methods=['GET'])
def get_catalog():
    """Devuelve todo el catálogo de productos."""
    try:
        # Consulta todos los productos.
        all_products = list(products_collection.find({}))
        
        if not all_products:
            # Retorna 500 para forzar el reintento si la colección está vacía.
            return jsonify({"error": "Catálogo vacío"}), 500

        # Formatea los datos para que el cliente Kivy los entienda (usando _id como clave).
        catalog_dict = {}
        for product in all_products:
            product_id_string = str(product.pop('_id')) # Usaremos el ID de MongoDB como clave.
            catalog_dict[product_id_string] = product
        
        return jsonify(catalog_dict)

    except Exception:
        return jsonify({"error": "Error al cargar el catálogo"}), 500


# ----------------------------------------------------------------------
# 4. ENDPOINT: /advertisement (ANUNCIO)
# ----------------------------------------------------------------------

@app.route('/advertisement', methods=['GET'])
def get_advertisement():
    """Devuelve la configuración del anuncio activo."""
    try:
        ad_data = config_collection.find_one({"type": "ad", "active": True})
        if ad_data:
            ad_data.pop('_id', None) 
            return jsonify(ad_data)
        
        # Objeto por defecto si no hay anuncio activo
        return jsonify({"active": False, "description": ""})
    except Exception:
        return jsonify({"active": False, "description": ""})


# ----------------------------------------------------------------------
# 5. ENDPOINT: /upload (PING/DESPERTAR)
# ----------------------------------------------------------------------

@app.route('/upload', methods=['POST'])
def ping_server():
    """Respuesta simple para despertar el servidor y confirmar que está activo."""
    return jsonify({"status": "OK", "message": "Server is awake"}), 200


# ----------------------------------------------------------------------
# 6. ENDPOINT CRÍTICO: /rate (ENVÍO DE ESTADÍSTICAS)
# ----------------------------------------------------------------------

@app.route('/rate', methods=['POST'])
def rate_product():
    """
    Recibe el ID del producto y el tipo de rating ('favorite' o 'star') 
    e incrementa el contador correspondiente en la base de datos.
    """
    data = request.get_json()
    product_id = data.get('id')
    rating_type = data.get('type') # 'favorite' o 'star'

    if not product_id or rating_type not in ['favorite', 'star']:
        return jsonify({"error": "Datos de calificación inválidos."}), 400

    # 1. Determinar el campo de la base de datos a actualizar
    update_field = 'favorites_count' if rating_type == 'favorite' else 'stars_count'
    
    # El ID que envía el cliente Kivy es el ID de MongoDB (convertido a string).
    # Necesitamos buscarlo por su _id (convertido de string a ObjectId si la clave es _id).
    try:
        from bson.objectid import ObjectId
        query = {"_id": ObjectId(product_id)}
    except Exception:
        return jsonify({"error": "ID de producto con formato incorrecto."}), 400

    try:
        # 2. Operación Atómica en MongoDB ($inc)
        result = products_collection.update_one(
            query,
            {
                # $inc incrementa el campo en 1 (lo crea si no existe con valor 0 antes de sumar 1)
                "$inc": {update_field: 1}, 
                # Opcional: registrar la hora de la última interacción
                "$set": {"last_rated": datetime.utcnow()} 
            }
        )
        
        if result.matched_count == 0:
            return jsonify({"status": "warning", "message": f"Producto ID {product_id} no encontrado."}), 404

        return jsonify({"status": "success", "message": f"{rating_type.capitalize()} registrado exitosamente."}), 200

    except Exception as e:
        print(f"Error al procesar la calificación: {e}")
        return jsonify({"error": "Error interno del servidor al actualizar estadísticas."}), 500


# ----------------------------------------------------------------------
# 7. INICIO DEL SERVIDOR
# ----------------------------------------------------------------------

if __name__ == '__main__':
    # Para pruebas locales. Render usará un servidor como Gunicorn.
    app.run(host='0.0.0.0', port=os.environ.get("PORT", 5000))

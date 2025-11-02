# app.py (Servidor Flask para Tiendita)

import os
import json
from datetime import datetime
from flask import Flask, jsonify, request, send_from_directory 
from pymongo import MongoClient
from bson.objectid import ObjectId

# ----------------------------------------------------------------------
# 1. CONFIGURACIÓN DEL SERVIDOR Y BASE DE DATOS
# ----------------------------------------------------------------------

app = Flask(__name__)

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/tienditaDB")

# Define la ubicación de la carpeta donde están las imágenes estáticas
# AJUSTA ESTO a la carpeta REAL de tu proyecto de Render
IMAGE_FOLDER = 'images' 

try:
    # Conexión a MongoDB
    client = MongoClient(MONGO_URI)
    db = client.get_database() 
    
    # Colecciones de la base de datos
    products_collection = db.products      
    config_collection = db.config          
    
    print("Conexión a MongoDB exitosa.")
except Exception as e:
    print(f"ERROR: No se pudo conectar a MongoDB. Error: {e}")
    # En un entorno de producción, esto debería ser un error fatal.


# ----------------------------------------------------------------------
# 2. ENDPOINT: /images/<filename> (SERVIR ARCHIVOS ESTÁTICOS)
# ----------------------------------------------------------------------

@app.route('/images/<filename>', methods=['GET'])
def serve_image(filename):
    """
    Sirve archivos de imagen estáticos desde la carpeta definida por IMAGE_FOLDER.
    """
    try:
        return send_from_directory(
            IMAGE_FOLDER, 
            filename, 
            as_attachment=False
        )
    except FileNotFoundError:
        return jsonify({"error": "Imagen no encontrada"}), 404
    except Exception as e:
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
            # Retorna 500 si está vacío para forzar a la app Kivy a usar datos locales.
            return jsonify({"error": "Catálogo vacío"}), 500

        catalog_dict = {}
        for product in all_products:
            # CORRECCIÓN: Usar el _id como clave principal, convirtiéndolo a string.
            product_id_string = str(product.pop('_id')) 
            
            # Asegurar que las stats sean números enteros si existen
            product['stars'] = int(product.get('stars_count', 0))
            product['favorites'] = int(product.get('favorites_count', 0))
            
            catalog_dict[product_id_string] = product
        
        return jsonify(catalog_dict)

    except Exception as e:
        print(f"Error al cargar el catálogo: {e}")
        return jsonify({"error": "Error al cargar el catálogo"}), 500


# ----------------------------------------------------------------------
# 4. ENDPOINT: /advertisement (ANUNCIO)
# ----------------------------------------------------------------------

@app.route('/advertisement', methods=['GET'])
def get_advertisement():
    """Devuelve la configuración del anuncio activo."""
    try:
        # Busca el anuncio fijo 'main' o el activo, si no existe, devuelve vacío.
        ad_data = config_collection.find_one({"type": "ad", "fixed_id": "main"})
        if ad_data:
            ad_data.pop('_id', None) 
            ad_data.pop('fixed_id', None) 
            ad_data.pop('type', None)
            return jsonify(ad_data)
        
        return jsonify({"active": False, "description": "", "title": "", "image": ""})
    except Exception:
        return jsonify({"active": False, "description": "", "title": "", "image": ""})


# ----------------------------------------------------------------------
# 5. ENDPOINT CRÍTICO: /upload (SUBIDA DE CATÁLOGO Y ANUNCIO)
# ----------------------------------------------------------------------

@app.route('/upload', methods=['POST'])
def upload_data():
    """
    Recibe el payload del gestor Kivy con el catálogo y el anuncio.
    Sobreescribe la base de datos de MongoDB de forma atómica.
    """
    try:
        data = request.get_json()
        productos = data.get('productos', [])
        anuncio = data.get('anuncio', {})
        
        # 1. ACTUALIZAR ANUNCIO
        if anuncio:
            anuncio['type'] = 'ad'
            anuncio['fixed_id'] = 'main' # Usar un ID fijo para fácil acceso
            anuncio['last_updated'] = datetime.utcnow()
            
            # Reemplazar/Crear el documento de configuración del anuncio
            config_collection.replace_one(
                {"type": "ad", "fixed_id": "main"}, 
                anuncio, 
                upsert=True
            )

        # 2. ACTUALIZAR CATÁLOGO
        if productos:
            productos_a_insertar = []
            
            for prod in productos:
                prod_id_str = prod.pop('id', None)
                
                # Intentar re-usar el ObjectId si el ID es un ObjectId válido (es decir, fue descargado previamente)
                # Si no es un ObjectId válido, MongoDB generará uno nuevo.
                if prod_id_str:
                    try:
                        if len(prod_id_str) == 24: # Longitud de un ObjectId típico
                             prod['_id'] = ObjectId(prod_id_str) 
                    except Exception:
                        pass
                
                # PRESENCIA DE ESTADÍSTICAS:
                # Si el producto tiene un _id existente, vamos a PRESERVAR sus estadísticas 
                # antes de la inserción, ya que el cliente Kivy NO las envía.
                
                if '_id' in prod:
                    existing_product = products_collection.find_one({'_id': prod['_id']})
                    if existing_product:
                        # Recuperar las estadísticas existentes
                        prod['stars_count'] = existing_product.get('stars_count', 0)
                        prod['favorites_count'] = existing_product.get('favorites_count', 0)
                
                # Conversión de precio/oferta (opcional)
                for key in ['price', 'offer']:
                    if key in prod and prod[key]:
                        try:
                            # Almacenar como float para consistencia en la DB (aunque Kivy las manda como string)
                            prod[key] = float(prod[key])
                        except ValueError:
                            pass
                
                productos_a_insertar.append(prod)

            # REEMPLAZAR LA COLECCIÓN DE PRODUCTOS:
            products_collection.delete_many({}) # BORRAR TODO
            if productos_a_insertar:
                products_collection.insert_many(productos_a_insertar) # INSERTAR TODO LO NUEVO

        return jsonify({"status": "success", "message": "Catálogo y anuncio actualizados."}), 200

    except Exception as e:
        print(f"Error CRÍTICO en la subida: {e}")
        return jsonify({"error": f"Error interno al procesar la subida del catálogo. Detalle: {str(e)}"}), 500


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

    # Determinar el campo de la base de datos a actualizar
    update_field = 'favorites_count' if rating_type == 'favorite' else 'stars_count'
    
    try:
        # El ID que envía el cliente es el _id (string) de MongoDB.
        query = {"_id": ObjectId(product_id)}
    except Exception:
        return jsonify({"error": "ID de producto con formato incorrecto."}), 400

    try:
        # Operación Atómica en MongoDB ($inc)
        result = products_collection.update_one(
            query,
            {
                "$inc": {update_field: 1}, 
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

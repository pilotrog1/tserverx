# app.py (Servidor Flask para Tiendita)

import os
import json
from datetime import datetime
from flask import Flask, jsonify, request, send_from_directory 
from pymongo import MongoClient, UpdateOne, InsertOne, DeleteMany
from bson.objectid import ObjectId

# ----------------------------------------------------------------------
# 1. CONFIGURACIÓN DEL SERVIDOR Y BASE DE DATOS
# ----------------------------------------------------------------------

app = Flask(__name__)

# Usar variable de entorno o fallback a localhost
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/tienditaDB")

# Define la ubicación de la carpeta donde están las imágenes estáticas
IMAGE_FOLDER = 'images' 

try:
    client = MongoClient(MONGO_URI)
    db = client.get_database() 
    
    products_collection = db.products      
    config_collection = db.config          
    
    print("Conexión a MongoDB exitosa.")
except Exception as e:
    print(f"ERROR: No se pudo conectar a MongoDB. Error: {e}")


# ----------------------------------------------------------------------
# 2. ENDPOINT: /images/<filename> (SERVIR ARCHIVOS ESTÁTICOS)
# ----------------------------------------------------------------------

@app.route('/images/<filename>', methods=['GET'])
def serve_image(filename):
    """
    Sirve archivos de imagen estáticos desde la carpeta definida por IMAGE_FOLDER.
    """
    try:
        # Importante: Asegurar que el filename se sirva en minúsculas si fue guardado así
        return send_from_directory(
            IMAGE_FOLDER, 
            filename.lower(), 
            as_attachment=False
        )
    except FileNotFoundError:
        return jsonify({"error": "Imagen no encontrada"}), 404
    except Exception as e:
        print(f"Error al servir imagen: {e}")
        return jsonify({"error": "Error interno del servidor"}), 500


# ----------------------------------------------------------------------
# 3. ENDPOINT: /catalog (CATÁLOGO - REVISADO)
# ----------------------------------------------------------------------

@app.route('/catalog', methods=['GET'])
def get_catalog():
    """Devuelve todo el catálogo de productos, mapeando los nombres de campos para Kivy."""
    try:
        all_products = list(products_collection.find({}))
        
        if not all_products:
            # Retorna 500 si está vacío para forzar a la app Kivy a usar datos locales.
            return jsonify({"error": "Catálogo vacío"}), 500

        catalog_dict = {}
        for product in all_products:
            
            product_id_string = str(product.pop('_id')) 
            
            # Mapeo de estadísticas de DB a campos esperados por Kivy (solo para referencia)
            stars_count = product.pop('stars_count', 0)
            favorites_count = product.pop('favorites_count', 0)

            try:
                # Kivy espera strings o números, aquí usamos str() para consistencia con el lado Kivy
                product['rating'] = str(float(stars_count))
            except ValueError:
                product['rating'] = "0"

            try:
                product['rating_count'] = int(favorites_count)
            except ValueError:
                product['rating_count'] = 0
            
            # CORRECCIÓN: Conversión de precio/oferta de vuelta a string para Kivy
            for key in ['price', 'offer']:
                 if key in product:
                      # Asegurar que los números de la DB se conviertan a string
                      product[key] = str(product[key])
            
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
# 5. ENDPOINT CRÍTICO: /upload (SUBIDA DE CATÁLOGO Y ANUNCIO - REVISADO)
# ----------------------------------------------------------------------

@app.route('/upload', methods=['POST'])
def upload_data():
    """
    Recibe el payload del gestor Kivy con el catálogo y el anuncio.
    Utiliza bulk_write para inserciones/actualizaciones/borrados eficientes y atómicos.
    """
    try:
        data = request.get_json()
        productos = data.get('productos', [])
        anuncio = data.get('anuncio', {})
        productos_a_eliminar = data.get('productos_a_eliminar', [])
        
        # 1. ACTUALIZAR ANUNCIO
        if anuncio:
            anuncio['type'] = 'ad'
            anuncio['fixed_id'] = 'main' 
            anuncio['last_updated'] = datetime.utcnow()
            
            config_collection.replace_one(
                {"type": "ad", "fixed_id": "main"}, 
                anuncio, 
                upsert=True
            )

        # 2. PROCESAR OPERACIONES BULK (Actualizar/Insertar/Borrar)
        bulk_operations = []

        # 2.1. BORRADO
        if productos_a_eliminar:
             valid_delete_ids = []
             for prod_id_str in productos_a_eliminar:
                  try:
                       valid_delete_ids.append(ObjectId(prod_id_str))
                  except Exception:
                       print(f"Advertencia: ID de borrado inválido/no permanente ignorado: {prod_id_str}")

             if valid_delete_ids:
                 bulk_operations.append(DeleteMany({'_id': {'$in': valid_delete_ids}}))

        # 2.2. INSERCIÓN/ACTUALIZACIÓN
        for prod in productos:
            prod_id_str = prod.pop('id', None)
            
            # Limpiar campos que no deben guardarse en la DB
            prod.pop('rating', None) 
            prod.pop('rating_count', None)

            # Conversión de precio/oferta a float para DB (si es posible)
            for key in ['price', 'offer']:
                if key in prod and prod[key]:
                    try:
                        # Convertir a float para almacenamiento numérico en la DB
                        prod[key] = float(prod[key])
                    except ValueError:
                        pass # Si no se puede, se mantiene como string
            
            
            mongo_id = None
            if prod_id_str:
                try:
                    # Intentar convertir el ID de Kivy a ObjectId
                    mongo_id = ObjectId(prod_id_str)
                except Exception:
                    pass 

            
            if mongo_id:
                # ❗ CRÍTICO: Usar $set para ACTUALIZAR solo campos editables. 
                # Esto PRESERVA 'stars_count' y 'favorites_count'.
                update_doc = {k: v for k, v in prod.items() if v is not None} 
                
                bulk_operations.append(
                    UpdateOne(
                        {'_id': mongo_id},
                        {'$set': update_doc},
                        upsert=False
                    )
                )
            else:
                # ❗ INSERCIÓN DE NUEVO PRODUCTO
                prod['stars_count'] = 0
                prod['favorites_count'] = 0
                prod.pop('_id', None) 
                
                bulk_operations.append(
                    InsertOne(prod)
                )

        # 2.3. EJECUCIÓN DEL BULK WRITE
        if bulk_operations:
             products_collection.bulk_write(bulk_operations, ordered=False)

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

    update_field = 'favorites_count' if rating_type == 'favorite' else 'stars_count'
    
    try:
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
    app.run(host='0.0.0.0', port=os.environ.get("PORT", 5000))

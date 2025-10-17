# -*- coding: utf-8 -*-
import json
import uuid
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
# HABILITAR CORS para evitar problemas de peticiones desde el cliente
CORS(app) 

# SIMULACION DE BASE DE DATOS EN MEMORIA
CATALOGO_DB = {}

# FUNCIÓN PARA INICIALIZAR LA DB CON DATOS DE PRUEBA SI ESTA VACIA
def inicializar_db():
    if not CATALOGO_DB:
        print("inicializando base de datos con datos de ejemplo.")
        id1 = str(uuid.uuid4()).split('-')[0].upper()
        id2 = str(uuid.uuid4()).split('-')[0].upper()
        
        # --- CORRECCION CLAVE: USAR NOMBRES DE ARCHIVO EN MINUSCULAS ---
        CATALOGO_DB[id1] = {
            "name": "aceite",
            "price": "35",
            "offer": "29",
            "image": "aceite.jpg", # MINUSCULAS
            "description": "aceite vegetal de 1 litro."
        }
        CATALOGO_DB[id2] = {
            "name": "lechita",
            "price": "25",
            "offer": "22",
            "image": "leche.jpg", # MINUSCULAS
            "description": "leche entera de 1 litro."
        }
    return CATALOGO_DB

# =======================================================================
# RUTAS REST
# =======================================================================

@app.route('/catalogo', methods=['GET'])
def get_catalogo():
    """OBTIENE EL CATALOGO COMPLETO. TAMBIEN INICIALIZA SI ES NECESARIO."""
    if not CATALOGO_DB:
        inicializar_db() 
        
    print(f"devolviendo catalogo con {len(CATALOGO_DB)} productos.")
    return jsonify(CATALOGO_DB)

@app.route('/catalogo', methods=['POST'])
def add_product():
    """ANADE UN NUEVO PRODUCTO AL CATALOGO."""
    try:
        data = request.json
        if not data or 'name' not in data:
            return jsonify({"error": "datos de producto incompletos"}), 400

        new_id = str(uuid.uuid4()).split('-')[0].upper()
        
        # GUARDAR LA IMAGEN EN MINUSCULAS PARA ASEGURAR COMPATIBILIDAD
        image_name = data.get("image", "").lower()

        new_product = {
            "name": data.get("name", "sin nombre"),
            "price": data.get("price", ""),
            "offer": data.get("offer", ""),
            "image": image_name,
            "description": data.get("description", "")
        }
        
        CATALOGO_DB[new_id] = new_product
        print(f"añadido nuevo producto: {new_product['name']} con id {new_id}. imagen: {new_product['image']}")
        return jsonify({"message": "producto añadido", "id": new_id}), 201
    
    except Exception as e:
        print(f"error en post /catalogo: {e}")
        return jsonify({"error": "error interno del servidor"}), 500

@app.route('/catalogo/<product_id>', methods=['PUT'])
def update_product(product_id):
    """ACTUALIZA UN PRODUCTO EXISTENTE POR ID."""
    try:
        data = request.json
        if not data:
            return jsonify({"error": "datos de actualizacion faltantes"}), 400

        if product_id not in CATALOGO_DB:
            return jsonify({"error": "producto no encontrado"}), 404

        # ACTUALIZAR solo los campos enviados
        product = CATALOGO_DB[product_id]
        
        # GUARDAR LA IMAGEN EN MINUSCULAS PARA ASEGURAR COMPATIBILIDAD
        image_name = data.get("image", product.get("image")).lower()
        
        product.update({
            "name": data.get("name", product["name"]),
            "price": data.get("price", product["price"]),
            "offer": data.get("offer", product["offer"]),
            "image": image_name,
            "description": data.get("description", product["description"])
        })
        
        CATALOGO_DB[product_id] = product
        print(f"producto actualizado: {product_id}. nueva imagen: {product['image']}")
        return jsonify({"message": "producto actualizado"}), 200
    
    except Exception as e:
        print(f"error en put /catalogo/{product_id}: {e}")
        return jsonify({"error": "error interno del servidor"}), 500

@app.route('/catalogo/<product_id>', methods=['DELETE'])
def delete_product(product_id):
    """ELIMINA UN PRODUCTO EXISTENTE POR ID."""
    try:
        if product_id in CATALOGO_DB:
            del CATALOGO_DB[product_id]
            print(f"producto eliminado: {product_id}")
            return '', 204 
        else:
            return jsonify({"error": "producto no encontrado"}), 404
    
    except Exception as e:
        print(f"error en delete /catalogo/{product_id}: {e}")
        return jsonify({"error": "error interno del servidor"}), 500

# RUTA PARA SERVIR IMAGENES - ESTO ES SOLO DE REFERENCIA, EL ERROR 404 VIENE DE UN SERVIDOR ESTATICO EXTERNO
# SI TU SERVIDOR ESTÁTICO PERMITE SUBIR IMÁGENES, ASEGÚRATE DE NOMBRARLAS EN MINÚSCULAS.
# SI FUERAS A SERVIRLAS DIRECTAMENTE CON FLASK (NO RECOMENDADO PARA RENDER), DEBERÍAS TENER UNA RUTA ASÍ:
# @app.route('/images/<filename>')
# def serve_image(filename):
#     print(f"solicitud de imagen: {filename}")
#     return send_from_directory('images', filename.lower())


if __name__ == '__main__':
    inicializar_db()
    app.run(host='0.0.0.0', port=8080, debug=True)
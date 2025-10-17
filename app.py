# -*- coding: utf-8 -*-
import json
import uuid
from flask import Flask, jsonify, request

app = Flask(__name__)

# SIMULACION DE BASE DE DATOS EN MEMORIA
# ESTO SE REINICIA CADA VEZ QUE SE DESPLIEGA O REINICIA EL SERVIDOR
# LA ESTRUCTURA ES: { "ID_PRODUCTO": { datos } }
CATALOGO_DB = {}

# FUNCIÓN PARA INICIALIZAR LA DB CON DATOS DE PRUEBA SI ESTA VACIA
def inicializar_db():
    if not CATALOGO_DB:
        print("INICIALIZANDO BASE DE DATOS CON DATOS DE EJEMPLO.")
        # GENERAR IDS UNICOS
        id1 = str(uuid.uuid4()).split('-')[0].upper()
        id2 = str(uuid.uuid4()).split('-')[0].upper()
        
        CATALOGO_DB[id1] = {
            "name": "ACEITE",
            "price": "35",
            "offer": "29",
            "image": "ACEITE.JPG",
            "description": "ACEITE VEGETAL DE 1 LITRO."
        }
        CATALOGO_DB[id2] = {
            "name": "LECHITA",
            "price": "25",
            "offer": "22",
            "image": "LECHE.JPG",
            "description": "LECHE ENTERA DE 1 LITRO."
        }
    return CATALOGO_DB

# =======================================================================
# RUTAS REST
# =======================================================================

@app.route('/catalogo', methods=['GET'])
def get_catalogo():
    """OBTIENE EL CATALOGO COMPLETO. TAMBIEN INICIALIZA SI ES NECESARIO."""
    # ASEGURAR QUE LA DB ESTE INICIALIZADA SI ESTA VACIA
    if not CATALOGO_DB:
        inicializar_db() 
        
    print(f"DEVOLVIENDO CATALOGO CON {len(CATALOGO_DB)} PRODUCTOS.")
    return jsonify(CATALOGO_DB)

@app.route('/catalogo', methods=['POST'])
def add_product():
    """ANADE UN NUEVO PRODUCTO AL CATALOGO."""
    try:
        data = request.json
        if not data or 'name' not in data:
            return jsonify({"error": "DATOS DE PRODUCTO INCOMPLETOS"}), 400

        new_id = str(uuid.uuid4()).split('-')[0].upper()
        
        # ASEGURAR QUE SOLO GUARDAMOS LOS CAMPOS PERMITIDOS
        new_product = {
            "name": data.get("name", "SIN NOMBRE"),
            "price": data.get("price", ""),
            "offer": data.get("offer", ""),
            "image": data.get("image", ""),
            "description": data.get("description", "")
        }
        
        CATALOGO_DB[new_id] = new_product
        print(f"ANADIDO NUEVO PRODUCTO: {new_product['name']} CON ID {new_id}")
        # RESPUESTA CORRECTA PARA CREACION (201) DEBE INCLUIR EL ID
        return jsonify({"message": "PRODUCTO ANADIDO", "id": new_id}), 201
    
    except Exception as e:
        print(f"ERROR EN POST /catalogo: {e}")
        return jsonify({"error": "ERROR INTERNO DEL SERVIDOR"}), 500

@app.route('/catalogo/<product_id>', methods=['PUT'])
def update_product(product_id):
    """ACTUALIZA UN PRODUCTO EXISTENTE POR ID."""
    try:
        data = request.json
        if not data:
            return jsonify({"error": "DATOS DE ACTUALIZACION FALTANTES"}), 400

        if product_id not in CATALOGO_DB:
            return jsonify({"error": "PRODUCTO NO ENCONTRADO"}), 404

        # ACTUALIZAR SOLO LOS CAMPOS ENVIADOS, SI EXISTEN
        product = CATALOGO_DB[product_id]
        product.update({
            "name": data.get("name", product["name"]),
            "price": data.get("price", product["price"]),
            "offer": data.get("offer", product["offer"]),
            "image": data.get("image", product["image"]),
            "description": data.get("description", product["description"])
        })
        
        CATALOGO_DB[product_id] = product
        print(f"PRODUCTO ACTUALIZADO: {product_id}")
        return jsonify({"message": "PRODUCTO ACTUALIZADO"}), 200
    
    except Exception as e:
        print(f"ERROR EN PUT /catalogo/{product_id}: {e}")
        return jsonify({"error": "ERROR INTERNO DEL SERVIDOR"}), 500

@app.route('/catalogo/<product_id>', methods=['DELETE'])
def delete_product(product_id):
    """ELIMINA UN PRODUCTO EXISTENTE POR ID."""
    try:
        if product_id in CATALOGO_DB:
            del CATALOGO_DB[product_id]
            print(f"PRODUCTO ELIMINADO: {product_id}")
            # RESPUESTA CORRECTA PARA ELIMINACION (204)
            return '', 204 
        else:
            return jsonify({"error": "PRODUCTO NO ENCONTRADO"}), 404
    
    except Exception as e:
        print(f"ERROR EN DELETE /catalogo/{product_id}: {e}")
        return jsonify({"error": "ERROR INTERNO DEL SERVIDOR"}), 500

if __name__ == '__main__':
    # INICIALIZAR LA BASE DE DATOS AL INICIAR EL SERVIDOR
    inicializar_db()
    # USAR 0.0.0.0 Y PUERTO 8080 PARA COMPATIBILIDAD CON RENDER Y ENTORNOS DE DESPLIEGUE
    app.run(host='0.0.0.0', port=8080, debug=True)
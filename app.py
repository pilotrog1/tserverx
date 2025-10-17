# -*- coding: utf-8 -*-
import json
import os
import time
from flask import Flask, jsonify, request, send_from_directory
from threading import Lock

app = Flask(__name__)

# NOMBRE DEL ARCHIVO DONDE PERSISTEN LOS DATOS DEL CATÁLOGO
CATALOG_FILE = 'catalogo_data.json'
# OBJETO LOCK PARA EVITAR ESCRITURAS SIMULTÁNEAS (SEGURIDAD EN CONCURRENCIA)
data_lock = Lock()

# ======================================================================
# LÓGICA DE PERSISTENCIA (LECTURA/ESCRITURA SEGURA)
# ======================================================================

def load_catalog_data():
    """LEE LOS DATOS DEL CATÁLOGO DESDE EL ARCHIVO JSON."""
    if not os.path.exists(CATALOG_FILE):
        return {}
    
    with data_lock:
        try:
            with open(CATALOG_FILE, 'r', encoding='utf-8') as f:
                # INTENTA CARGAR EL JSON. SI FALLA, RETORNA VACÍO.
                data = json.load(f)
                print(f"[{time.strftime('%H:%M:%S')}] DATOS DE CATÁLOGO CARGADOS CORRECTAMENTE.")
                return data
        except json.JSONDecodeError:
            print(f"[{time.strftime('%H:%M:%S')}] ERROR: EL ARCHIVO JSON ESTÁ CORRUPTO. INICIANDO CATÁLOGO VACÍO.")
            return {}
        except Exception as e:
            print(f"[{time.strftime('%H:%M:%S')}] ERROR AL LEER EL ARCHIVO: {e}")
            return {}

def save_catalog_data(data):
    """ESCRIBE LOS DATOS DEL CATÁLOGO AL ARCHIVO JSON DE MANERA SEGURA."""
    with data_lock:
        try:
            # USA UN ARCHIVO TEMPORAL PARA ESCRITURA ATÓMICA
            temp_file = CATALOG_FILE + '.tmp'
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            
            # REEMPLAZA EL ARCHIVO ORIGINAL SÓLO SI LA ESCRITURA FUE EXITOSA
            os.replace(temp_file, CATALOG_FILE)
            print(f"[{time.strftime('%H:%M:%S')}] DATOS DE CATÁLOGO GUARDADOS CORRECTAMENTE.")
            return True
        except Exception as e:
            print(f"[{time.strftime('%H:%M:%S')}] ERROR AL GUARDAR EL ARCHIVO: {e}")
            return False

# CARGA INICIAL DEL CATÁLOGO AL INICIAR EL SERVIDOR
catalog_data = load_catalog_data()

# ======================================================================
# ENDPOINTS API
# ======================================================================

@app.route('/ping', methods=['GET'])
def ping():
    """ENDPOINT PARA MANTENER ACTIVO EL SERVIDOR DE RENDER (PERSISTENCIA)."""
    # NO HACE NADA, SÓLO DEVUELVE UNA RESPUESTA RÁPIDA
    print(f"[{time.strftime('%H:%M:%S')}] RECIBIDO PING DE PERSISTENCIA. MANTENIENDO ACTIVO.")
    return jsonify({"status": "OK", "message": "SERVER ACTIVO"}), 200

@app.route('/catalogo', methods=['GET'])
def get_catalogo():
    """OBTIENE EL CATÁLOGO COMPLETO."""
    print(f"[{time.strftime('%H:%M:%S')}] SOLICITUD DE CATÁLOGO. ENVIANDO {len(catalog_data)} PRODUCTOS.")
    return jsonify(catalog_data)

@app.route('/catalogo/add', methods=['POST'])
def add_product():
    """AÑADE UN NUEVO PRODUCTO AL CATÁLOGO."""
    try:
        product = request.get_json()
        if not product or 'name' not in product:
            return jsonify({"error": "DATOS DE PRODUCTO INVÁLIDOS"}), 400

        # GENERAR ID SIMPLE (USANDO TIMESTAMP)
        new_id = str(int(time.time() * 1000))
        catalog_data[new_id] = product
        
        # GUARDAR LOS DATOS ACTUALIZADOS DE FORMA SEGURA
        if save_catalog_data(catalog_data):
            print(f"[{time.strftime('%H:%M:%S')}] PRODUCTO AÑADIDO: {product['name']}")
            return jsonify({"status": "OK", "id": new_id, "product": product}), 201
        else:
            return jsonify({"error": "ERROR AL PERSISTIR LOS DATOS"}), 500

    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] ERROR EN ADD_PRODUCT: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/catalogo/edit/<product_id>', methods=['PUT'])
def edit_product(product_id):
    """EDITA UN PRODUCTO EXISTENTE."""
    try:
        if product_id not in catalog_data:
            return jsonify({"error": "PRODUCTO NO ENCONTRADO"}), 404

        updates = request.get_json()
        if not updates:
            return jsonify({"error": "DATOS DE ACTUALIZACIÓN INVÁLIDOS"}), 400

        catalog_data[product_id].update(updates)

        if save_catalog_data(catalog_data):
            print(f"[{time.strftime('%H:%M:%S')}] PRODUCTO EDITADO: ID {product_id}")
            return jsonify({"status": "OK", "product": catalog_data[product_id]}), 200
        else:
            return jsonify({"error": "ERROR AL PERSISTIR LOS DATOS"}), 500

    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] ERROR EN EDIT_PRODUCT: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/catalogo/delete/<product_id>', methods=['DELETE'])
def delete_product(product_id):
    """ELIMINA UN PRODUCTO DEL CATÁLOGO."""
    try:
        if product_id not in catalog_data:
            return jsonify({"error": "PRODUCTO NO ENCONTRADO"}), 404

        del catalog_data[product_id]

        if save_catalog_data(catalog_data):
            print(f"[{time.strftime('%H:%M:%S')}] PRODUCTO ELIMINADO: ID {product_id}")
            return jsonify({"status": "OK", "message": f"PRODUCTO {product_id} ELIMINADO"}), 200
        else:
            return jsonify({"error": "ERROR AL PERSISTIR LOS DATOS"}), 500

    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] ERROR EN DELETE_PRODUCT: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/images/<filename>')
def serve_image(filename):
    """SIRVE ARCHIVOS DE IMAGEN DESDE EL DIRECTORIO LOCAL DE IMÁGENES."""
    # ASEGÚRATE DE QUE LA CARPETA 'images' EXISTA Y CONTENGA TUS IMÁGENES
    return send_from_directory('images', filename)

if __name__ == '__main__':
    # INTENTA CREAR EL ARCHIVO SI NO EXISTE
    if not os.path.exists(CATALOG_FILE):
        save_catalog_data({})
        
    # ESTO ES NECESARIO PARA LA EJECUCIÓN EN RENDER
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
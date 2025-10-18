# -*- coding: utf-8 -*-
import os
import json
from flask import Flask, jsonify, request, send_from_directory, abort
from flask_cors import CORS

# ======================================================================
# CONFIGURACIÓN DE PERSISTENCIA
# ======================================================================

CATALOG_FILE = 'catalogo_data.json' 
CATALOGO_DB = {}
IMAGE_FOLDER = 'images'

# ======================================================================
# FUNCIONES DE PERSISTENCIA
# ======================================================================

def load_catalogo_from_file():
    global CATALOGO_DB
    if os.path.exists(CATALOG_FILE):
        try:
            with open(CATALOG_FILE, 'r', encoding='utf-8') as f:
                CATALOGO_DB = json.load(f)
            print(f"INFO: Catálogo cargado desde {CATALOG_FILE}. Productos: {len(CATALOGO_DB)}")
        except Exception as e:
            print(f"ERROR: Fallo al cargar el catálogo desde el archivo: {e}")
            CATALOGO_DB = {}
    else:
        print(f"INFO: Archivo {CATALOG_FILE} no encontrado. Inicializando con catálogo vacío.")
        # Datos de ejemplo iniciales
        CATALOGO_DB = {
            'P1': {'name': 'LECHITA', 'price': '25', 'offer': '22', 'image': 'leche.jpg', 'description': 'LECHE FRESCA ENTERA.'},
            'P2': {'name': 'ACEITE', 'price': '35', 'offer': '29', 'image': 'aceite.jpg', 'description': 'ACEITE DE COCINA VEGETAL.'},
            'P3': {'name': 'MARUCHAN', 'price': '20', 'offer': '17', 'image': 'maruchan.jpg', 'description': 'SOPA INSTANTÁNEA SABOR POLLO.'},
        }
        save_catalogo_to_file()

def save_catalogo_to_file():
    try:
        with open(CATALOG_FILE, 'w', encoding='utf-8') as f:
            json.dump(CATALOGO_DB, f, indent=2, ensure_ascii=False)
        print(f"INFO: Catálogo guardado exitosamente en {CATALOG_FILE}.")
    except Exception as e:
        print(f"ERROR: Fallo al guardar el catálogo en el archivo: {e}")

# ======================================================================
# CONFIGURACIÓN DE FLASK
# ======================================================================

if not os.path.exists(IMAGE_FOLDER):
    os.makedirs(IMAGE_FOLDER)

app = Flask(__name__)
CORS(app)  # Habilita CORS para todas las rutas

# ======================================================================
# RUTAS DE LA API
# ======================================================================

@app.route('/')
def home():
    return "SERVIDOR DE CATÁLOGO ACTIVO. USE /CATALOGO PARA DATOS.", 200

@app.route('/catalogo', methods=['GET'])
def get_catalogo():
    return jsonify(CATALOGO_DB)

@app.route('/update_catalogo', methods=['POST'])
def update_catalogo():
    global CATALOGO_DB
    
    if not request.json:
        return jsonify({"message": "FALTA CUERPO JSON EN LA PETICIÓN"}), 400

    new_catalogo = request.json
    
    if not isinstance(new_catalogo, dict):
        return jsonify({"message": "EL CATÁLOGO DEBE SER UN DICCIONARIO DE PRODUCTOS"}), 400

    CATALOGO_DB = new_catalogo
    save_catalogo_to_file()
    
    print("--- CATÁLOGO ACTUALIZADO ---")
    print(f"Total productos: {len(CATALOGO_DB)}")
    
    return jsonify({"message": "CATÁLOGO ACTUALIZADO CON ÉXITO", "count": len(CATALOGO_DB)}), 200

@app.route('/images/<path:filename>')
def serve_image(filename):
    try:
        safe_filename = filename.lower().strip()
        return send_from_directory(IMAGE_FOLDER, safe_filename)
    except FileNotFoundError:
        print(f"ERROR: Imagen no encontrada - {filename}")
        abort(404)

# ======================================================================
# INICIO DE LA APLICACIÓN
# ======================================================================
if __name__ == '__main__':
    load_catalogo_from_file()
    app.run(debug=True, host='0.0.0.0', port=5000)
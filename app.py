# -*- coding: utf-8 -*-
import os
import json
from flask import Flask, jsonify, request, send_from_directory, abort

# ======================================================================
# CONFIGURACIÓN DE PERSISTENCIA
# ======================================================================

# Nombre del archivo donde se guardará el catálogo (persistencia)
CATALOG_FILE = 'catalogo_data.json' 
CATALOGO_DB = {} # Ahora es solo el caché en memoria
IMAGE_FOLDER = 'images'

# ======================================================================
# FUNCIONES DE PERSISTENCIA
# ======================================================================

def load_catalogo_from_file():
    """Carga el catálogo desde el archivo si existe al iniciar el servidor."""
    global CATALOGO_DB
    if os.path.exists(CATALOG_FILE):
        try:
            # Usar encoding='utf-8' es importante para caracteres especiales
            with open(CATALOG_FILE, 'r', encoding='utf-8') as f:
                CATALOGO_DB = json.load(f)
            print(f"INFO: Catálogo cargado desde {CATALOG_FILE}. Productos: {len(CATALOGO_DB)}")
        except Exception as e:
            print(f"ERROR: Fallo al cargar el catálogo desde el archivo: {e}")
            CATALOGO_DB = {} # Si falla, inicializa vacío
    else:
        print(f"INFO: Archivo {CATALOG_FILE} no encontrado. Inicializando con catálogo vacío.")

def save_catalogo_to_file():
    """Guarda el catálogo actual a un archivo (persistencia)."""
    try:
        # Usar indent=2 hace el JSON legible; ensure_ascii=False para caracteres
        with open(CATALOG_FILE, 'w', encoding='utf-8') as f:
            json.dump(CATALOGO_DB, f, indent=2, ensure_ascii=False)
        print(f"INFO: Catálogo guardado exitosamente en {CATALOG_FILE}.")
    except Exception as e:
        print(f"ERROR: Fallo al guardar el catálogo en el archivo: {e}")

# ======================================================================
# CONFIGURACIÓN DE FLASK
# ======================================================================

# CREAR CARPETA PARA IMÁGENES SI NO EXISTE
if not os.path.exists(IMAGE_FOLDER):
    os.makedirs(IMAGE_FOLDER)

app = Flask(__name__)

# ======================================================================
# RUTAS DE LA API
# ======================================================================

@app.route('/')
def home():
    """RUTA INICIAL PARA VERIFICACIÓN DEL SERVIDOR."""
    return "SERVIDOR DE CATÁLOGO ACTIVO. USE /CATALOGO PARA DATOS.", 200

@app.route('/catalogo', methods=['GET'])
def get_catalogo():
    """OBTIENE EL CATÁLOGO COMPLETO."""
    return jsonify(CATALOGO_DB)

@app.route('/update_catalogo', methods=['POST'])
def update_catalogo():
    """ACTUALIZA Y PERSISTE el catálogo completo desde el cliente gestor."""
    global CATALOGO_DB
    
    if not request.json:
        return jsonify({"message": "FALTA CUERPO JSON EN LA PETICIÓN"}), 400

    new_catalogo = request.json
    
    if not isinstance(new_catalogo, dict):
        return jsonify({"message": "EL CATÁLOGO DEBE SER UN DICCIONARIO DE PRODUCTOS"}), 400

    # 1. ACTUALIZAR LA BASE DE DATOS EN MEMORIA
    CATALOGO_DB = new_catalogo
    
    # 2. PERSISTENCIA: GUARDAR EL CATÁLOGO ACTUALIZADO EN EL ARCHIVO
    save_catalogo_to_file()
    
    print("--- CATÁLOGO ACTUALIZADO ---")
    
    return jsonify({"message": "CATÁLOGO ACTUALIZADO CON ÉXITO", "count": len(CATALOGO_DB)}), 200


@app.route('/images/<filename>')
def serve_image(filename):
    """SIRVE IMÁGENES ESTÁTICAS DESDE LA CARPETA 'IMAGES'."""
    try:
        # Flask buscará el archivo en la carpeta 'images'
        return send_from_directory(IMAGE_FOLDER, filename)
    except FileNotFoundError:
        # Si la imagen no se encuentra, abortar con error 404
        abort(404) 

# ======================================================================
# INICIO DE LA APLICACIÓN
# ======================================================================
if __name__ == '__main__':
    # PASO CLAVE: CARGAR EL CATÁLOGO GUARDADO AL INICIAR EL SERVIDOR
    load_catalogo_from_file()
    
    # EJECUTAR FLASK
    app.run(debug=True, host='0.0.0.0', port=5000)

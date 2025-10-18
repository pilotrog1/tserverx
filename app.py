# -*- coding: utf-8 -*-
import os
import json
from flask import Flask, jsonify, request, send_from_directory, abort

# ======================================================================
# CONFIGURACIÓN INICIAL DEL CATÁLOGO
# ======================================================================

# Base de datos inicial (Catálogo)
# EN UN ENTORNO REAL, ESTO SERÍA UNA BASE DE DATOS COMO SQLITE O POSTGRES
CATALOGO_DB = {}


# ======================================================================
# CONFIGURACIÓN DE FLASK
# ======================================================================

# CREAR CARPETA PARA IMÁGENES SI NO EXISTE
IMAGE_FOLDER = 'images'
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
    """ACTUALIZA EL CATÁLOGO COMPLETO DESDE EL CLIENTE GESTOR."""
    global CATALOGO_DB
    
    # 1. VERIFICAR QUE EL CUERPO DE LA PETICIÓN ES JSON
    if not request.json:
        return jsonify({"message": "FALTA CUERPO JSON EN LA PETICIÓN"}), 400

    new_catalogo = request.json
    
    # 2. VALIDACIÓN BÁSICA DE LA ESTRUCTURA (OPCIONAL PERO RECOMENDADA)
    if not isinstance(new_catalogo, dict):
        return jsonify({"message": "EL CATÁLOGO DEBE SER UN DICCIONARIO DE PRODUCTOS"}), 400

    # 3. ACTUALIZAR LA BASE DE DATOS EN MEMORIA
    # EN UN ENTORNO REAL, AQUÍ SE ESCRIBIRÍA A LA BASE DE DATOS
    CATALOGO_DB = new_catalogo
    
    # OPCIONAL: IMPRIMIR EL NUEVO CATÁLOGO PARA VERIFICACIÓN EN LA CONSOLA DEL SERVIDOR
    print("--- CATÁLOGO ACTUALIZADO ---")
    print(json.dumps(CATALOGO_DB, indent=2))
    
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
    # EJECUTAR FLASK EN MODO DEBUG
    app.run(debug=True, host='0.0.0.0', port=5000)

# -*- coding: utf-8 -*-
import os
import json
from flask import Flask, jsonify, request, send_from_directory, abort

# ======================================================================
# CONFIGURACIÓN INICIAL DEL CATÁLOGO
# ======================================================================

# Base de datos inicial (Catálogo)
# EN UN ENTORNO REAL, ESTO SERÍA UNA BASE DE DATOS COMO SQLITE O POSTGRES
CATALOGO_DB = {
    'P1': {'name': 'LECHITA', 'price': '25', 'offer': '22', 'image': 'leche.jpg', 'description': 'LECHE FRESCA ENTERA.'},
    'P2': {'name': 'ACEITE', 'price': '35', 'offer': '29', 'image': 'aceite.jpg', 'description': 'ACEITE DE COCINA VEGETAL.'},
    'P3': {'name': 'MARUCHAN', 'price': '20', 'offer': '17', 'image': 'maruchan.jpg', 'description': 'SOPA INSTANTÁNEA SABOR POLLO.'},
    'P4': {'name': 'HUEVO', 'price': '38', 'offer': '', 'image': 'huevo.jpg', 'description': 'DOCENA DE HUEVOS FRESCOS.'},
    'P5': {'name': 'JARRITOS 2 LTS', 'price': '30', 'offer': '28', 'image': 'jarritos2l.jpg', 'description': 'REFRESCO DE SABORES DE 2 LITROS.'},
    'P6': {'name': 'ATÚN', 'price': '27', 'offer': '', 'image': 'atun.jpg', 'description': 'LATA DE ATÚN EN AGUA.'},
    'P7': {'name': 'MUÑECO', 'price': '250', 'offer': '200', 'image': 'muñeco.jpg', 'description': 'MUÑECO DE PLÁSTICO PARA NIÑOS.'},
    'P8': {'name': 'CÁNÍCAS', 'price': '22', 'offer': '20', 'image': 'canicas.jpg', 'description': 'BOLSA DE 10 CÁNÍCAS DE COLORES.'},
    'P9': {'name': 'JARRITOS', 'price': '22', 'offer': '20', 'image': 'jarritos.jpg', 'description': 'REFRESCO INDIVIDUAL DE SABORES.'},
    'P10': {'name': 'AZÚCAR', 'price': '17', 'offer': '14', 'image': 'azucar.jpg', 'description': 'KILO DE AZÚCAR ESTÁNDAR.'},
    'P11': {'name': 'GOMAS', 'price': '10', 'offer': '7', 'image': 'gomas.jpg', 'description': 'PAQUETE DE 5 GOMAS DE MASCAR.'},
    'P12': {'name': 'AGUA EMBOTELLADA', 'price': '15', 'offer': '', 'image': 'agua.jpg', 'description': 'BOTELLA DE AGUA PURIFICADA.'},
    'P13': {'name': 'COCA-COLA LATA', 'price': '23', 'offer': '21', 'image': 'cocalata.jpg', 'description': 'LATA DE REFRESCO COCA-COLA.'},
    'P14': {'name': 'COCA-COLA EN BOTELLA', 'price': '25', 'offer': '20', 'image': 'cocabotella.jpg', 'description': 'BOTELLA PERSONAL DE COCA-COLA.'},
    'P15': {'name': 'SACAPUNTAS', 'price': '8', 'offer': '5', 'image': 'sacapuntas.jpg', 'description': 'SACAPUNTAS CON DEPÓSITO.'},
    'P16': {'name': 'JAMÓN', 'price': '25', 'offer': '22', 'image': 'jamon.jpg', 'description': '200 GRAMOS DE JAMÓN DE PAVO.'}
}


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

import json
import os
from flask import Flask, jsonify, request, send_from_directory
from werkzeug.utils import secure_filename # PARA GESTIONAR SUBIDA DE ARCHIVOS

# CONFIGURACION BASE
app = Flask(__name__)
catalogo_file = 'catalogo.json'
images_dir = 'images'
UPLOAD_FOLDER = 'images'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# ASEGURARSE DE QUE EL DIRECTORIO DE IMAGENES EXISTE
if not os.path.exists(images_dir):
    os.makedirs(images_dir)

# -------------------------------------------------------------------
# 1. ENDPOINT DE LECTURA (PARA LA APP DE PROMOCION)
# -------------------------------------------------------------------

@app.route('/catalogo', methods=['GET'])
def get_catalogo():
    """DEVUELVE EL CATALOGO JSON."""
    try:
        with open(catalogo_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return jsonify(data)
    except FileNotFoundError:
        # DEVUELVE UN CATALOGO VACIO SI NO SE ENCUENTRA EL ARCHIVO
        return jsonify({}), 200 
    except Exception as e:
        return jsonify({"error": f"ERROR AL CARGAR EL CATALOGO: {str(e)}"}), 500

@app.route('/images/<filename>', methods=['GET'])
def serve_image(filename):
    """SIRVE LAS IMAGENES ESTATICAS DESDE LA CARPETA /images."""
    return send_from_directory(images_dir, filename)

# -------------------------------------------------------------------
# 2. ENDPOINT DE ESCRITURA (PARA LA APP DE GESTION)
# -------------------------------------------------------------------

@app.route('/update_catalogo', methods=['POST'])
def update_catalogo():
    """RECIBE Y GUARDA EL CATALOGO JSON COMPLETO ACTUALIZADO."""
    try:
        new_catalogo = request.json
        if not isinstance(new_catalogo, dict):
            return jsonify({"error": "FORMATO JSON INVALIDO"}), 400

        with open(catalogo_file, 'w', encoding='utf-8') as f:
            # ALMACENAR CON INDENTACION PARA MEJOR LECTURA
            json.dump(new_catalogo, f, indent=4, ensure_ascii=False)

        return jsonify({"message": "CATALOGO ACTUALIZADO CORRECTAMENTE"}), 200

    except Exception as e:
        return jsonify({"error": f"ERROR AL GUARDAR: {e}"}), 500

@app.route('/upload_image', methods=['POST'])
def upload_image():
    """RECIBE UNA IMAGEN Y LA GUARDA EN LA CARPETA /images."""
    if 'file' not in request.files:
        return jsonify({"error": "NO SE ENCONTRO LA PARTE 'file' EN LA PETICION"}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({"error": "NO SE SELECCIONO NINGUN ARCHIVO"}), 400

    if file:
        # ASEGURAR NOMBRE SEGURO Y GUARDAR
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        return jsonify({"message": "IMAGEN SUBIDA CORRECTAMENTE", "filename": filename}), 200
        
    return jsonify({"error": "ERROR AL PROCESAR LA IMAGEN"}), 500

# -------------------------------------------------------------------
# 3. PUNTO DE INICIO
# -------------------------------------------------------------------

# SOLO PARA PRUEBAS LOCALES, RENDER USARA GUNICORN
if __name__ == '__main__':
    print("EJECUTANDO SERVIDOR EN MODO DE PRUEBA LOCAL...")
    app.run(host='0.0.0.0', debug=True, port=5000)

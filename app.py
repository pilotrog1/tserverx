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
        
        # Usamos un prefijo simple para los IDs de ejemplo para que siempre aparezcan primero
        # al ordenar por ID simple, pero se recomienda UUIDs para producción.
        id1 = "p01" 
        id2 = "p02"
        id3 = "p03"
        
        # --- CORRECCION CLAVE: USAR NOMBRES DE ARCHIVO EN MINUSCULAS ---
        CATALOGO_DB[id1] = {
            "name": "aceite comestible 1l",
            "price": "35",
            "offer": "29",
            "image": "aceite.jpg", # MINUSCULAS
            "description": "aceite vegetal de 1 litro, perfecto para freír y cocinar."
        }
        CATALOGO_DB[id2] = {
            "name": "maruchan pollo",
            "price": "20",
            "offer": "17",
            "image": "maruchan.jpg", # MINUSCULAS
            "description": "sopa instantánea sabor pollo. lista en 3 minutos."
        }
        CATALOGO_DB[id3] = {
            "name": "leche entera",
            "price": "30",
            "offer": "27",
            "image": "leche.jpg", # MINUSCULAS
            "description": "leche entera de 1 litro. fresca y nutritiva."
        }
    return CATALOGO_DB

# =======================================================================
# RUTAS REST
# =======================================================================

@app.route('/ping', methods=['GET'])
def ping():
    """RUTA SIMPLE PARA MANTENER EL SERVIDOR ACTIVO."""
    return jsonify({"status": "activo"}), 200

@app.route('/catalogo', methods=['GET'])
def get_catalogo():
    """OBTIENE EL CATALOGO COMPLETO. TAMBIEN INICIALIZA SI ES NECESARIO."""
    if not CATALOGO_DB:
        inicializar_db() 
        
    print(f"devolviendo catalogo con {len(CATALOGO_DB)} productos.")
    return jsonify(CATALOGO_DB)

@app.route('/update_catalogo', methods=['POST'])
def update_catalogo():
    """REEMPLAZA EL CATALOGO COMPLETO CON LOS NUEVOS DATOS DEL GESTOR."""
    try:
        data = request.json
        if not isinstance(data, dict):
            return jsonify({"error": "formato de catalogo invalido"}), 400

        # REEMPLAZAR LA DB EN MEMORIA
        CATALOGO_DB.clear()
        
        # Asegurarse de que las imágenes se guarden en minúsculas en la "db"
        for prod_id, product_data in data.items():
            if "image" in product_data:
                product_data["image"] = product_data["image"].lower()
            CATALOGO_DB[prod_id] = product_data
            
        print(f"catalogo actualizado. total de productos: {len(CATALOGO_DB)}")
        return jsonify({"message": "catalogo actualizado exitosamente", "count": len(CATALOGO_DB)}), 200
    
    except Exception as e:
        print(f"error en post /update_catalogo: {e}")
        return jsonify({"error": "error interno del servidor durante la actualización"}), 500


if __name__ == '__main__':
    inicializar_db()
    # Usar el puerto 8080 o el puerto por defecto de render para el despliegue
    app.run(host='0.0.0.0', port=8080)

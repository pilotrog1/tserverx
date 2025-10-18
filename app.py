# -*- coding: utf-8 -*-
import os
import json
import atexit
from datetime import datetime
from flask import Flask, jsonify, request, send_from_directory, abort
from flask_cors import CORS
import threading
import time

# ======================================================================
# CONFIGURACIÓN DE PERSISTENCIA
# ======================================================================

CATALOG_FILE = 'catalogo_data.json' 
CATALOGO_DB = {} # Contiene los datos del catálogo en memoria
IMAGE_FOLDER = 'images'
AUTO_SAVE_INTERVAL = 600  # 10 minutos en segundos

# ======================================================================
# FUNCIONES DE PERSISTENCIA MEJORADAS
# ======================================================================

def load_catalogo_from_file():
    """Carga el catálogo desde el archivo con manejo robusto de errores"""
    global CATALOGO_DB
    max_retries = 3
    retry_delay = 1
    
    for attempt in range(max_retries):
        try:
            if os.path.exists(CATALOG_FILE):
                print(f"INFO: Intentando cargar catálogo desde {CATALOG_FILE} (intento {attempt + 1})")
                with open(CATALOG_FILE, 'r', encoding='utf-8') as f:
                    CATALOGO_DB = json.load(f)
                print(f"INFO: Catálogo cargado exitosamente. Productos: {len(CATALOGO_DB)}")
                return True
            else:
                print(f"INFO: Archivo {CATALOG_FILE} no encontrado. Inicializando con datos de ejemplo.")
                initialize_sample_data()
                return True
                
        except json.JSONDecodeError as e:
            print(f"ERROR: Archivo JSON corrupto (intento {attempt + 1}): {e}")
            if attempt == max_retries - 1:
                print("ERROR: No se pudo cargar el archivo JSON. Inicializando con datos de ejemplo.")
                initialize_sample_data()
                return False
            time.sleep(retry_delay)
            
        except Exception as e:
            print(f"ERROR inesperado al cargar catálogo (intento {attempt + 1}): {e}")
            if attempt == max_retries - 1:
                print("ERROR: No se pudo cargar el archivo. Inicializando con datos de ejemplo.")
                initialize_sample_data()
                return False
            time.sleep(retry_delay)
    
    return False

def save_catalogo_to_file():
    """Guarda el catálogo actual a un archivo con manejo robusto de errores"""
    max_retries = 3
    retry_delay = 1
    
    for attempt in range(max_retries):
        try:
            # Crear copia de seguridad del archivo actual si existe
            if os.path.exists(CATALOG_FILE):
                backup_file = f"{CATALOG_FILE}.backup"
                try:
                    import shutil
                    shutil.copy2(CATALOG_FILE, backup_file)
                except Exception as e:
                    print(f"ADVERTENCIA: No se pudo crear copia de seguridad: {e}")
            
            # Guardar el archivo nuevo
            with open(CATALOG_FILE, 'w', encoding='utf-8') as f:
                json.dump(CATALOGO_DB, f, indent=2, ensure_ascii=False)
            
            print(f"INFO: Catálogo guardado exitosamente en {CATALOG_FILE} - {len(CATALOGO_DB)} productos")
            return True
            
        except Exception as e:
            print(f"ERROR al guardar catálogo (intento {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                print("ERROR: No se pudo guardar el catálogo después de varios intentos")
                return False
    
    return False

def initialize_sample_data():
    """Inicializa con datos de ejemplo si no hay archivo"""
    global CATALOGO_DB
    sample_data = {
        'P1': {
            'name': 'LECHITA', 
            'price': '25', 
            'offer': '22', 
            'image': 'leche.jpg', 
            'description': 'LECHE FRESCA ENTERA.'
        },
        'P2': {
            'name': 'ACEITE', 
            'price': '35', 
            'offer': '29', 
            'image': 'aceite.jpg', 
            'description': 'ACEITE DE COCINA VEGETAL.'
        },
        'P3': {
            'name': 'MARUCHAN', 
            'price': '20', 
            'offer': '17', 
            'image': 'maruchan.jpg', 
            'description': 'SOPA INSTANTÁNEA SABOR POLLO.'
        },
    }
    CATALOGO_DB = sample_data
    print("INFO: Datos de ejemplo inicializados")
    save_catalogo_to_file()

def auto_save_worker():
    """Trabajador para guardado automático periódico"""
    while True:
        time.sleep(AUTO_SAVE_INTERVAL)
        if CATALOGO_DB:  # Solo guardar si hay datos
            # print(f"INFO: Auto-guardado iniciado - {len(CATALOGO_DB)} productos")
            success = save_catalogo_to_file()
            if success:
                # print("INFO: Auto-guardado completado")
                pass
            else:
                print("ERROR: Auto-guardado falló")

def start_auto_save():
    """Inicia el hilo de guardado automático"""
    auto_save_thread = threading.Thread(target=auto_save_worker, daemon=True)
    auto_save_thread.start()
    print("INFO: Sistema de auto-guardado iniciado")

def cleanup_on_exit():
    """Función de limpieza al salir"""
    print("INFO: Cerrando servidor - guardando datos finales...")
    save_catalogo_to_file()
    print("INFO: Servidor cerrado correctamente")

# ======================================================================
# CONFIGURACIÓN DE FLASK
# ======================================================================

if not os.path.exists(IMAGE_FOLDER):
    os.makedirs(IMAGE_FOLDER)

app = Flask(__name__)
CORS(app)  # Habilita CORS para todas las rutas

# ======================================================================
# RUTAS DE LA API MEJORADAS
# ======================================================================

@app.route('/')
def home():
    """RUTA INICIAL PARA VERIFICACIÓN DEL SERVIDOR"""
    server_info = {
        "status": "SERVIDOR DE CATÁLOGO ACTIVO",
        "endpoints": {
            "/catalogo": "GET - Obtener catálogo completo",
            "/update_catalogo": "POST - Actualizar catálogo",
            "/images/<filename>": "GET - Servir imágenes"
        },
        "stats": {
            "productos": len(CATALOGO_DB),
            "ultima_actualizacion": datetime.now().isoformat()
        }
    }
    return jsonify(server_info)

@app.route('/catalogo', methods=['GET'])
def get_catalogo():
    """OBTIENE EL CATÁLOGO COMPLETO con el formato esperado por el cliente"""
    try:
        response_data = {
            "catalogo": CATALOGO_DB, # ⬅️ Campo clave para la app cliente
            "metadata": {
                "total_productos": len(CATALOGO_DB),
                "ultima_actualizacion": datetime.now().isoformat(),
                "estado": "ok"
            }
        }
        return jsonify(response_data)
    except Exception as e:
        error_response = {
            "error": "Error interno del servidor",
            "detalles": str(e),
            "estado": "error"
        }
        return jsonify(error_response), 500

@app.route('/update_catalogo', methods=['POST'])
def update_catalogo():
    """ACTUALIZA Y PERSISTE el catálogo completo desde el cliente gestor"""
    global CATALOGO_DB
    
    if not request.json:
        error_response = {
            "message": "FALTA CUERPO JSON EN LA PETICIÓN",
            "estado": "error"
        }
        return jsonify(error_response), 400

    new_catalogo = request.json
    
    if not isinstance(new_catalogo, dict):
        error_response = {
            "message": "EL CATÁLOGO DEBE SER UN DICCIONARIO DE PRODUCTOS",
            "estado": "error"
        }
        return jsonify(error_response), 400

    try:
        # 1. ACTUALIZAR LA BASE DE DATOS EN MEMORIA
        old_count = len(CATALOGO_DB)
        CATALOGO_DB = new_catalogo
        new_count = len(CATALOGO_DB)
        
        # 2. PERSISTENCIA INMEDIATA: GUARDAR EL CATÁLOGO ACTUALIZADO
        save_success = save_catalogo_to_file()
        
        print("=== CATÁLOGO ACTUALIZADO ===")
        print(f"Productos anteriores: {old_count}")
        print(f"Productos nuevos: {new_count}")
        print(f"Guardado en archivo: {'Éxito' if save_success else 'Falló'}")
        
        success_response = {
            "message": "CATÁLOGO ACTUALIZADO CON ÉXITO",
            "count": new_count,
            "previous_count": old_count,
            "file_saved": save_success,
            "estado": "ok"
        }
        return jsonify(success_response), 200

    except Exception as e:
        error_response = {
            "message": f"ERROR INTERNO AL ACTUALIZAR CATÁLOGO: {str(e)}",
            "estado": "error"
        }
        return jsonify(error_response), 500

@app.route('/images/<path:filename>')
def serve_image(filename):
    """SIRVE IMÁGENES ESTÁTICAS DESDE LA CARPETA 'IMAGES'."""
    try:
        # Normalizar el nombre del archivo
        safe_filename = filename.lower().strip()
        # print(f"INFO: Solicitando imagen: {safe_filename}")
        return send_from_directory(IMAGE_FOLDER, safe_filename)
    except FileNotFoundError:
        print(f"ERROR: Imagen no encontrada - {filename}")
        # La app cliente maneja el fallback, solo necesitamos devolver 404
        abort(404) 
    except Exception as e:
        print(f"ERROR inesperado sirviendo imagen {filename}: {e}")
        error_response = {
            "error": "Error interno del servidor",
            "detalles": str(e),
            "estado": "error"
        }
        return jsonify(error_response), 500

@app.route('/status', methods=['GET'])
def get_status():
    """Endpoint para verificar el estado del servidor"""
    status_info = {
        "servidor": "activo",
        "productos_en_memoria": len(CATALOGO_DB),
        "archivo_persistente": os.path.exists(CATALOG_FILE),
        "ultima_actualizacion": datetime.now().isoformat(),
        "auto_guardado_activo": True,
        "estado": "ok"
    }
    return jsonify(status_info)

# ======================================================================
# MANEJO DE ERRORES GLOBALES
# ======================================================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint no encontrado", "estado": "error"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Error interno del servidor", "estado": "error"}), 500

# ======================================================================
# INICIO DE LA APLICACIÓN
# ======================================================================
if __name__ == '__main__':
    # PASO CLAVE: CARGAR EL CATÁLOGO GUARDADO AL INICIAR EL SERVIDOR
    print("=== INICIANDO SERVIDOR DE CATÁLOGO ===")
    
    load_success = load_catalogo_from_file()
    if not load_success:
        print("ADVERTENCIA: El servidor inició con datos de ejemplo debido a errores de carga")
    
    # INICIAR GUARDADO AUTOMÁTICO
    start_auto_save()
    
    # REGISTRAR FUNCIÓN DE LIMPIEZA
    atexit.register(cleanup_on_exit)
    
    print("=== SERVIDOR INICIADO CORRECTAMENTE ===")
    print(f"URL: http://0.0.0.0:5000")
    print(f"Productos cargados: {len(CATALOGO_DB)}")
    print(f"Auto-guardado cada: {AUTO_SAVE_INTERVAL} segundos")
    
    # EJECUTAR FLASK
    app.run(debug=True, host='0.0.0.0', port=5000)

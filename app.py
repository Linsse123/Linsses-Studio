import os
import uuid
import base64
import io
import logging
import tempfile
from flask import Flask, request, jsonify, render_template
from pdf2image import convert_from_bytes
from PIL import Image
import requests

# CONFIGURACIÓN OPTIMIZADA PARA RENDER (512MB RAM)
ROBOFLOW_API_KEY = "hKrCyLFvEqmxmyVGuMfF"
WORKFLOW_URL = "https://serverless.roboflow.com/detector-de-puertas/workflows/detect-count-and-visualize-4"

# DPI bajo (150) es vital para que el servidor no se colapse
PDF_DPI = 150 
Image.MAX_IMAGE_PIXELS = None
TEMP_DIR = tempfile.gettempdir()

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
IMAGES = {}

def encode_image_to_base64(image):
    buffered = io.BytesIO()
    # Calidad 70 para ahorrar ancho de banda
    image.save(buffered, format="JPEG", quality=70)
    return base64.b64encode(buffered.getvalue()).decode("utf-8")

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/upload_pdf', methods=['POST'])
def upload_pdf():
    if 'file' not in request.files: return jsonify({"error": "No file"}), 400
    file = request.files['file']
    try:
        # Convertimos PDF con DPI controlado para no saturar RAM
        images = convert_from_bytes(file.read(), dpi=PDF_DPI)
        if not images: return jsonify({"error": "PDF error"}), 500
        
        img = images[0].convert("RGB")
        file_id = str(uuid.uuid4())
        path = os.path.join(TEMP_DIR, f"{file_id}.jpg")
        
        # Guardamos en disco y liberamos objeto original
        img.save(path, "JPEG", quality=80)
        IMAGES[file_id] = path
        
        # Generamos miniatura ligera (1000px de referencia)
        display_w = 1000
        w_percent = (display_w / float(img.size[0]))
        h_size = int((float(img.size[1]) * float(w_percent)))
        thumb = img.resize((display_w, h_size), Image.Resampling.LANCZOS)
        
        return jsonify({
            "file_id": file_id,
            "filename": file.filename,
            "image_base64": encode_image_to_base64(thumb),
            "width": display_w,
            "height": h_size
        })
    except Exception as e:
        logging.error(f"Upload Error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/analyze_zone', methods=['POST'])
def analyze_zone():
    data = request.json
    file_id = data.get('file_id')
    coords = data.get('coords')
    conf = float(data.get('min_confidence', 75)) / 100.0
    
    if file_id not in IMAGES: return jsonify({"error": "Expired"}), 404
        
    try:
        with Image.open(IMAGES[file_id]) as full_img:
            # Calculamos escala respecto al ancho de referencia del frontend
            scale = full_img.size[0] / float(data.get('ref_width', 1000))
            zx, zy = int(coords['x']*scale), int(coords['y']*scale)
            zw, zh = int(coords['w']*scale), int(coords['h']*scale)
            
            # Recorte de zona
            zone = full_img.crop((zx, zy, zx+zw, zy+zh))
            
            # Slicer de 6 sectores (3x2) con poco empalme (6%)
            all_dets = []
            h_cuts = [(0, int(zh*0.53)), (int(zh*0.47), zh)]
            w_cuts = [(0, int(zw*0.36)), (int(zw*0.32), int(zw*0.68)), (int(zw*0.64), zw)]
            
            for y1, y2 in h_cuts:
                for x1, x2 in w_cuts:
                    tile = zone.crop((x1, y1, x2, y2))
                    b64 = encode_image_to_base64(tile)
                    
                    res = requests.post(WORKFLOW_URL, json={
                        "api_key": ROBOFLOW_API_KEY,
                        "inputs": {"image": {"type": "base64", "value": b64}}
                    }, timeout=30).json()
                    
                    # Manejo flexible de respuesta Roboflow
                    preds = res.get('predictions', res.get('outputs', []))
                    if isinstance(preds, dict): preds = preds.get('predictions', [])
                    
                    if isinstance(preds, list):
                        for p in preds:
                            if p.get('confidence', 0) >= conf:
                                all_dets.append({
                                    "x": (x1 + p['x']) - (p['width']/2),
                                    "y": (y1 + p['y']) - (p['height']/2),
                                    "width": p['width'], "height": p['height'],
                                    "confidence": p['confidence']
                                })
                            
        # Limpieza de duplicados (IoU)
        all_dets.sort(key=lambda d: d['confidence'], reverse=True)
        final = []
        while all_dets:
            curr = all_dets.pop(0)
            final.append(curr)
            # Filtro de solapamiento
            all_dets = [d for d in all_dets if not (max(curr['x'], d['x']) < min(curr['x']+curr['width'], d['x']+d['width']) and max(curr['y'], d['y']) < min(curr['y']+curr['height'], d['y']+d['height']))]
                            
        return jsonify({"detections": [{ "x": d['x']/scale, "y": d['y']/scale, "width": d['width']/scale, "height": d['height']/scale, "confidence": d['confidence'] } for d in final]})
    except Exception as e:
        logging.error(f"Analysis Error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Usar puerto de variable de entorno para Render
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
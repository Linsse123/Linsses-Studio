import os
import platform
import uuid
import base64
import io
import logging
import tempfile
from flask import Flask, request, jsonify, render_template
from pdf2image import convert_from_bytes
from PIL import Image
import requests

# --- CONFIGURACIÓN ---
ROBOFLOW_API_KEY = "hKrCyLFvEqmxmyVGuMfF"
WORKFLOW_URL = "https://serverless.roboflow.com/detector-de-puertas/workflows/detect-count-and-visualize-4"

PDF_DPI = 300 
Image.MAX_IMAGE_PIXELS = None

POPPLER_PATH = None
if platform.system() == "Windows":
    possible_path = r"E:\Programas\planos\poppler\Library\bin"
    if os.path.exists(possible_path):
        POPPLER_PATH = possible_path

TEMP_DIR = tempfile.mkdtemp()
app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

IMAGES = {}

def encode_image_to_base64(image):
    buffered = io.BytesIO()
    if image.mode != "RGB":
        image = image.convert("RGB")
    image.save(buffered, format="JPEG", quality=85)
    return base64.b64encode(buffered.getvalue()).decode("utf-8")

def run_workflow(image_tile):
    image_base64 = encode_image_to_base64(image_tile)
    payload = {
        "api_key": ROBOFLOW_API_KEY,
        "inputs": {
            "image": {"type": "base64", "value": image_base64}
        }
    }
    try:
        res = requests.post(WORKFLOW_URL, json=payload)
        return res.json() if res.status_code == 200 else {}
    except Exception as e:
        logging.error(f"Error conexión: {e}")
        return {}

def find_predictions(data):
    if isinstance(data, list): return data
    if isinstance(data, dict):
        if 'predictions' in data: return find_predictions(data['predictions'])
        if 'outputs' in data:
            if isinstance(data['outputs'], list):
                for out in data['outputs']:
                    val = out.get('value', out)
                    if isinstance(val, dict) and 'predictions' in val:
                        return find_predictions(val['predictions'])
            return find_predictions(data['outputs'])
        for key in ['results', 'output']:
            if key in data: return find_predictions(data[key])
    return []

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/upload_pdf', methods=['POST'])
def upload_pdf():
    if 'file' not in request.files: return jsonify({"error": "No hay archivo"}), 400
    file = request.files['file']
    try:
        images = convert_from_bytes(file.read(), dpi=PDF_DPI, poppler_path=POPPLER_PATH)
        if not images: return jsonify({"error": "Error al leer PDF"}), 500
        
        original_img = images[0].convert("RGB")
        file_id = str(uuid.uuid4())
        
        file_path = os.path.join(TEMP_DIR, f"{file_id}.jpg")
        original_img.save(file_path, "JPEG", quality=95)
        IMAGES[file_id] = file_path
        
        target_width = 1200 # Aumentado un poco para mejor visualización
        w_percent = (target_width / float(original_img.size[0]))
        h_size = int((float(original_img.size[1]) * float(w_percent)))
        thumbnail = original_img.resize((target_width, h_size), Image.Resampling.LANCZOS)
        
        return jsonify({
            "file_id": file_id,
            "filename": file.filename,
            "image_base64": encode_image_to_base64(thumbnail),
            "width": target_width,
            "height": h_size
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/analyze_zone', methods=['POST'])
def analyze_zone():
    data = request.json
    file_id = data.get('file_id')
    coords = data.get('coords')
    req_confidence = float(data.get('min_confidence', 75)) / 100.0 # Default fallback
    
    if not file_id or file_id not in IMAGES:
        return jsonify({"error": "Imagen expirada"}), 404
        
    img_path = IMAGES[file_id]
    if not os.path.exists(img_path):
        return jsonify({"error": "Archivo no encontrado"}), 404
        
    try:
        original = Image.open(img_path)
        frontend_width = data.get('ref_width', 1200)
        
        orig_w, orig_h = original.size
        scale_factor = orig_w / float(frontend_width)
        
        zx = int(coords['x'] * scale_factor)
        zy = int(coords['y'] * scale_factor)
        zw = int(coords['w'] * scale_factor)
        zh = int(coords['h'] * scale_factor)
        
        zx = max(0, zx); zy = max(0, zy)
        
        zone_img = original.crop((zx, zy, zx + zw, zy + zh))
        
        # --- ESTRATEGIA DE 6 SECTORES (CORTE FINO) ---
        h_cuts = [(0, int(zh * 0.53)), (int(zh * 0.47), zh)]
        w_cuts = [(0, int(zw * 0.36)), (int(zw * 0.32), int(zw * 0.68)), (int(zw * 0.64), zw)]
        
        tiles_coords = []
        for (y1, y2) in h_cuts:
            for (x1, x2) in w_cuts:
                tiles_coords.append((x1, y1, x2, y2))
        
        all_detections = []
        
        for (tx1, ty1, tx2, ty2) in tiles_coords:
            tile = zone_img.crop((tx1, ty1, tx2, ty2))
            preds = find_predictions(run_workflow(tile))
            
            if preds:
                for p in preds:
                    if not isinstance(p, dict) or 'x' not in p: continue
                    if p.get('confidence', 0) < req_confidence: continue

                    center_x_in_tile = p['x']
                    center_y_in_tile = p['y']
                    
                    abs_x = (tx1 + center_x_in_tile) - (p['width'] / 2)
                    abs_y = (ty1 + center_y_in_tile) - (p['height'] / 2)

                    all_detections.append({
                        "x": abs_x,
                        "y": abs_y,
                        "width": p['width'],
                        "height": p['height'],
                        "confidence": p['confidence'],
                        "class": p['class']
                    })

        all_detections.sort(key=lambda d: d.get('confidence', 0), reverse=True)
        final_detections = []
        
        def get_iou(boxA, boxB):
            xA = max(boxA['x'], boxB['x']); yA = max(boxA['y'], boxB['y'])
            xB = min(boxA['x']+boxA['width'], boxB['x']+boxB['width'])
            yB = min(boxA['y']+boxA['height'], boxB['y']+boxB['height'])
            inter = max(0, xB - xA) * max(0, yB - yA)
            areaA = boxA['width']*boxA['height']; areaB = boxB['width']*boxB['height']
            return inter / float(areaA + areaB - inter) if (areaA + areaB - inter) > 0 else 0

        while all_detections:
            curr = all_detections.pop(0)
            final_detections.append(curr)
            all_detections = [d for d in all_detections if get_iou(curr, d) <= 0.20]

        inv_scale = 1.0 / scale_factor
        frontend_dets = [{
            "x": d['x'] * inv_scale,
            "y": d['y'] * inv_scale,
            "width": d['width'] * inv_scale,
            "height": d['height'] * inv_scale,
            "confidence": d['confidence']
        } for d in final_detections]

        return jsonify({"detections": frontend_dets})
        
    except Exception as e:
        logging.error(f"Error analizando zona: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
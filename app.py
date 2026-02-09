import os
import uuid
import base64
import io
import requests
from flask import Flask, request, jsonify, render_template, send_from_directory

app = Flask(__name__)

# Configuración Roboflow
ROBOFLOW_API_KEY = "hKrCyLFvEqmxmyVGuMfF"
WORKFLOW_URL = "https://serverless.roboflow.com/detector-de-puertas/workflows/detect-count-and-visualize-10"

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/list_pdfs')
def list_pdfs():
    files = [f for f in os.listdir('.') if f.lower().endswith('.pdf')]
    return jsonify(files)

@app.route('/pdfs/<path:filename>')
def serve_pdf(filename):
    return send_from_directory('.', filename)

def find_predictions(data):
    if isinstance(data, dict):
        if "predictions" in data and isinstance(data["predictions"], list):
            return data["predictions"]
        for key, value in data.items():
            result = find_predictions(value)
            if result: return result
    elif isinstance(data, list):
        for item in data:
            result = find_predictions(item)
            if result: return result
    return None

@app.route('/analyze_zone_fast', methods=['POST'])
def analyze_zone_fast():
    data = request.json
    # Recibimos el base64 directamente del recorte del frontend
    b64_image = data['image_b64']
    
    try:
        response = requests.post(WORKFLOW_URL, json={
            "api_key": ROBOFLOW_API_KEY,
            "inputs": {"image": {"type": "base64", "value": b64_image}}
        })
        res = response.json()
        preds = find_predictions(res)
        
        detections = []
        if preds:
            for p in preds:
                if p.get('confidence', 0) >= (float(data['min_confidence'])/100):
                    # No dividimos por scale aquí porque el recorte ya viene escalado
                    detections.append({
                        "x": p['x'] - p['width']/2,
                        "y": p['y'] - p['height']/2,
                        "width": p['width'],
                        "height": p['height']
                    })
                    
        return jsonify({"detections": detections, "count": len(detections)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
import streamlit as st
import requests
import base64
from pdf2image import convert_from_bytes
from PIL import Image, ImageDraw, ImageFont
import io
import pandas as pd
import zipfile
import gc
import os
import platform
from streamlit_drawable_canvas import st_canvas

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Detector Francotirador Pro (Lista)", layout="wide")
Image.MAX_IMAGE_PIXELS = None 

# ------------------------------------------------------------------
# 🔑 CREDENCIALES
# ------------------------------------------------------------------
API_KEY = "hKrCyLFvEqmxmyVGuMfF"
WORKSPACE_NAME = "detector-de-puertas"
WORKFLOW_ID = "detect-count-and-visualize-4" 

# --- 1. CONEXIÓN ---
def analyze_image_base64(img_base64):
    try:
        url = f"https://detect.roboflow.com/infer/workflows/{WORKSPACE_NAME}/{WORKFLOW_ID}"
        payload = {
            "api_key": API_KEY,
            "inputs": {"image": {"type": "base64", "value": img_base64}}
        }
        response = requests.post(url, json=payload)
        return response.json() if response.status_code == 200 else {}
    except:
        return {}

def find_predictions(data):
    if isinstance(data, list):
        if not data: return []
        if isinstance(data[0], dict) and ('x' in data[0] or 'predictions' in data[0]):
            if 'predictions' in data[0]: return find_predictions(data[0]['predictions'])
            return data
    elif isinstance(data, dict):
        if 'predictions' in data: return find_predictions(data['predictions'])
        for k in ['outputs', 'results', 'output']:
            if k in data: return find_predictions(data[k])
    return []

# --- 2. SISTEMA ANTI-DUPLICADOS (MATEMÁTICO) ---
def calculate_iou(boxA, boxB):
    """Calcula si dos cajas se enciman"""
    ax1, ay1 = boxA['x'] - boxA['width']/2, boxA['y'] - boxA['height']/2
    ax2, ay2 = boxA['x'] + boxA['width']/2, boxA['y'] + boxA['height']/2
    
    bx1, by1 = boxB['x'] - boxB['width']/2, boxB['y'] - boxB['height']/2
    bx2, by2 = boxB['x'] + boxB['width']/2, boxB['y'] + boxB['height']/2

    x_inter1 = max(ax1, bx1)
    y_inter1 = max(ay1, by1)
    x_inter2 = min(ax2, bx2)
    y_inter2 = min(ay2, by2)

    if x_inter2 < x_inter1 or y_inter2 < y_inter1: return 0.0

    area_inter = (x_inter2 - x_inter1) * (y_inter2 - y_inter1)
    area_a = boxA['width'] * boxA['height']
    area_b = boxB['width'] * boxB['height']
    
    union = area_a + area_b - area_inter
    return area_inter / union if union > 0 else 0

def clean_duplicates_aggressive(detections):
    """Elimina puertas repetidas en los bordes de los recortes"""
    if not detections: return []
    detections.sort(key=lambda x: x.get('confidence', 0), reverse=True)
    
    keep = []
    while detections:
        curr = detections.pop(0)
        keep.append(curr)
        remaining = []
        for other in detections:
            iou = calculate_iou(curr, other)
            # Si se tocan más del 15% (0.15), asumimos que es la misma puerta duplicada
            if iou < 0.15: 
                remaining.append(other)
        detections = remaining
    return keep

# --- 3. ORQUESTADOR ---
def analyze_region(region_crop, region_name, conf_thresh, tile_size=1500):
    w, h = region_crop.size
    overlap = 300 
    
    coordinates = []
    y = 0
    while y < h:
        x = 0
        while x < w:
            x2 = min(x + tile_size, w)
            y2 = min(y + tile_size, h)
            coordinates.append((max(0, x2 - tile_size), max(0, y2 - tile_size), x2, y2))
            if x2 == w: break
            x += tile_size - overlap
        if y2 == h: break
        y += tile_size - overlap

    all_dets_raw = []
    
    # Nota: Quitamos la barra de progreso interna para no saturar la vista global
    for i, (x1, y1, x2, y2) in enumerate(coordinates):
        tile = region_crop.crop((x1, y1, x2, y2))
        buf = io.BytesIO()
        tile.convert("RGB").save(buf, format="JPEG", quality=90)
        b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        
        resp = analyze_image_base64(b64)
        preds = find_predictions(resp)
        
        if preds:
            for p in preds:
                if not isinstance(p, dict): continue
                conf = p.get('confidence', 0)
                if conf > 1: conf /= 100.0
                
                if conf < conf_thresh: continue
                
                p_adj = p.copy()
                p_adj['confidence'] = conf 
                p_adj['x'] += x1
                p_adj['y'] += y1
                all_dets_raw.append(p_adj)
    
    # Limpieza final
    return clean_duplicates_aggressive(all_dets_raw)

# --- INTERFAZ ---
st.title("DETECTOR DE PUERTAS")

with st.sidebar:
    st.header("1. Cargar Planos")
    uploaded_files = st.file_uploader("Sube PDFs", type=["pdf"], accept_multiple_files=True)
    st.divider()
    st.header("2. Configuración")
    dpi = st.select_slider("Calidad Visual", [100, 150], value=100)
    conf = st.slider("Confianza Mínima", 0.05, 0.9, 0.50)
    st.info(f"Modelo: {WORKFLOW_ID}")
    
    with st.expander("ℹ️ Info del Sistema"):
        st.caption(f"Python: {platform.python_version()}")
        st.caption(f"Streamlit: {st.__version__}")

# Inicializamos el estado para guardar las imágenes cargadas
if "pdf_images" not in st.session_state:
    st.session_state.pdf_images = {}

if uploaded_files:
# Cargar solo lo nuevo
    new_files = [f for f in uploaded_files if f.name not in st.session_state.pdf_images]
    if new_files:
        with st.spinner(f"Procesando {len(new_files)} planos nuevos..."):
            # Configuración de Poppler dinámica
            poppler_path = None
            if platform.system() == "Windows":
                # Ruta local específica del usuario
                local_poppler = r"E:\Programas\planos\poppler\Library\bin"
                if os.path.exists(local_poppler):
                    poppler_path = local_poppler

            for f in new_files:
                # Si poppler_path es None, pdf2image buscará en el PATH del sistema (ideal para Cloud)
                try:
                    images = convert_from_bytes(f.getvalue(), dpi=dpi, fmt="jpeg", poppler_path=poppler_path)
                    if images:
                        st.session_state.pdf_images[f.name] = images[0]
                        st.success(f"✅ Convertido: {f.name} ({images[0].size})")
                    else:
                        st.error(f"⚠️ El archivo {f.name} no generó imágenes.")
                except Exception as e:
                    st.error(f"❌ Error procesando {f.name}: {str(e)}")
                    # Mostrar ayuda si es error de Poppler
                    if "poppler" in str(e).lower():
                        st.warning("Parece un error de Poppler. Verifica que 'packages.txt' incluya 'poppler-utils'.")
    
    st.success(f"📂 {len(st.session_state.pdf_images)} planos cargados. Dibuja las zonas en la lista de abajo.")

    # --- AQUÍ ESTÁ EL CAMBIO CLAVE: LISTA COLAPSABLE ---
    
    # Diccionario para guardar los resultados de dibujo de CADA plano
    canvas_results = {}

    for filename, img in st.session_state.pdf_images.items():
        # Usamos st.expander para crear la lista colapsable
        with st.expander(f"📄 Plano: {filename}", expanded=True):
            custom_width = st.slider("Ajustar ancho de imagen", 600, 1200, 800, 50, key=f"width_{filename}")
            
            # 1. Crear una copia RE-ESCALADA para visualización (Display Image)
            # Esto corrige el problema de que la imagen original sea muy grande y no se vea
            bg_img = img.copy()
            w_original, h_original = bg_img.size
            new_height = int(h_original * (custom_width / w_original))
            
            # 1. Redimensionamos PRIMERO (Crucial para que no sea gigante)
            bg_img = bg_img.resize((custom_width, new_height), Image.LANCZOS)
            
            # 2. ASEGURAR RGB
            bg_img = bg_img.convert("RGB")
            
            # 3. CONVERTIR A BASE64 STRING (Bypass total del procesamiento de streamlit)
            buffered = io.BytesIO()
            bg_img.save(buffered, format="JPEG", quality=85)
            img_str = base64.b64encode(buffered.getvalue()).decode()
            bg_image_url = f"data:image/jpeg;base64,{img_str}"
            
            # Canvas: Le pasamos la URL (string)
            canvas_results[filename] = st_canvas(
                fill_color="rgba(255, 0, 0, 0.3)",
                stroke_color="#FF0000",
                background_image=None, # Ponemos None aquí para evitar conflictos si la librería espera algo
                background_color="#EEE", # Color de fondo por si acaso
                # Pasamos la imagen usando el argumento especial para URLs si existe, o background_image
                # La librería usa 'background_image' para todo.
                background_image=bg_image_url, 
                update_streamlit=True,
                height=new_height,
                width=custom_width,
                drawing_mode="rect",
                key=f"canvas_{filename}",
            )

    st.divider()
    
    # Botón único para procesar TODO lo marcado
    if st.button("🔍 Analizar Zonas Marcadas (En todos los planos)", type="primary"):
        
        # Filtramos solo los planos donde el usuario dibujó algo
        items_to_process = []
        for fname, res in canvas_results.items():
            if res.json_data and len(res.json_data["objects"]) > 0:
                items_to_process.append((fname, res))
        
        if not items_to_process:
            st.warning("⚠️ No has dibujado ningún recuadro. Dibuja sobre los planos arriba.")
        else:
            # Barra de progreso global
            prog_bar = st.progress(0)
            status_text = st.empty()
            
            for i, (fname, res) in enumerate(items_to_process):
                status_text.write(f"⚙️ Analizando **{fname}**...")
                
                orig_img = st.session_state.pdf_images[fname]
                final_img = orig_img.copy()
                draw = ImageDraw.Draw(final_img)
                
                # Fuente
                try: font = ImageFont.truetype("arial.ttf", 24)
                except: font = ImageFont.load_default()
                
                objects = res.json_data["objects"]
                w_orig, h_orig = orig_img.size
                scale_factor = w_orig / 800 # 800 es el ancho del canvas
                
                file_total_doors = 0
                
                for idx, obj in enumerate(objects):
                    l = int(obj["left"] * scale_factor)
                    t = int(obj["top"] * scale_factor)
                    w = int(obj["width"] * scale_factor)
                    h = int(obj["height"] * scale_factor)
                    
                    zone_name = f"Zona {idx + 1}"
                    region = orig_img.crop((l, t, l+w, t+h))
                    
                    # Analizar (con tu lógica anti-duplicados)
                    dets = analyze_region(region, zone_name, conf)
                    count = len(dets)
                    file_total_doors += count
                    
                    # Dibujar
                    for d in dets:
                        xg = d['x'] + l
                        yg = d['y'] + t
                        wd = d['width']
                        hd = d['height']
                        
                        # Caja Roja
                        draw.rectangle([xg-wd/2, yg-hd/2, xg+wd/2, yg+hd/2], outline="red", width=4)
                        
                        # Etiqueta de Confianza
                        conf_text = f"{int(d['confidence']*100)}%"
                        text_x = xg - wd/2
                        text_y = yg - hd/2 - 25
                        bbox = draw.textbbox((text_x, text_y), conf_text, font=font)
                        draw.rectangle(bbox, fill="red")
                        draw.text((text_x, text_y), conf_text, fill="white", font=font)
                
                # Mostrar resultado debajo del plano correspondiente
                st.success(f"✅ {fname}: **{file_total_doors}** puertas encontradas.")
                st.image(final_img, caption=f"Resultados: {fname}", use_column_width=True)
                
                prog_bar.progress((i + 1) / len(items_to_process))
            
            status_text.success("¡Análisis completado!")
            prog_bar.empty()

else:
    st.info("Sube tus archivos en la barra lateral.")
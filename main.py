import streamlit as st
import requests
import json
from PIL import Image
import pandas as pd
import re
import io  # Para el buffer de Excel
import google.generativeai as genai  # Gemini

st.set_page_config(page_title="Lector Inteligente de Facturas", layout="wide")

# 🔑 API Keys desde secrets.toml
OCR_API_KEY = st.secrets["OCR_SPACE_KEY"]
GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]

# 📡 Configurar Gemini
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel("models/gemini-1.5-flash-001")

st.title("📄 Lector Inteligente de Facturas usando OCR.space + Gemini")

uploaded_file = st.file_uploader("Subir factura (imagen)", type=["jpg", "jpeg", "png"])

def ocr_space_api(image_bytes):
    url_api = "https://api.ocr.space/parse/image"
    payload = {
        'apikey': OCR_API_KEY,
        'language': 'spa',
        'isOverlayRequired': False
    }
    files = {
        'file': ('factura.png', image_bytes)
    }
    response = requests.post(url_api, data=payload, files=files)
    result = response.json()
    if result.get("IsErroredOnProcessing"):
        st.error("Error en OCR.space: " + result.get("ErrorMessage", ["Error desconocido"])[0])
        return ""
    return result["ParsedResults"][0]["ParsedText"]

def extract_json_from_text(text):
    try:
        # Extrae el primer bloque JSON encontrado en el texto (entre llaves)
        json_str = re.search(r"\{.*\}", text, re.DOTALL).group(0)
        return json_str
    except Exception:
        return None

if uploaded_file:
    image = Image.open(uploaded_file)
    st.image(image, caption="Factura subida", use_container_width=True)

    uploaded_file_bytes = uploaded_file.getvalue()

    with st.spinner("Extrayendo texto con OCR.space..."):
        text = ocr_space_api(uploaded_file_bytes)

    if text:
        st.text_area("Texto extraído por OCR.space", text, height=300)

        with st.spinner("Interpretando datos con Gemini..."):
            prompt = f"""Sos un asistente que analiza texto OCR de facturas. A partir del siguiente texto extraído:
{text}

Extraé los siguientes datos clave en formato JSON válido, sin ningún texto adicional ni explicación, exactamente así:
- Proveedor
- Monto total
- Fecha de compra (dd/mm/aaaa)
- Fecha de vencimiento (si existe)
- Sucursal (si aparece)
- Días restantes hasta el vencimiento (si hay fecha)

Responde solo con el JSON válido correspondiente."""

            try:
                response = model.generate_content(
                    contents=[{"role": "user", "parts": [prompt]}]
                )
                output = response.text
            except Exception as e:
                st.error(f"Error al procesar con Gemini: {e}")
                output = ""

        if output:
            st.subheader("📌 Datos extraídos por Gemini")
            st.code(output, language="json")

            json_text = extract_json_from_text(output)
            if json_text:
                try:
                    data_json = json.loads(json_text)
                    df = pd.DataFrame([data_json])
                    st.dataframe(df)

                    # Generar Excel en memoria
                    output_stream = io.BytesIO()
                    df.to_excel(output_stream, index=False, engine='openpyxl')
                    output_stream.seek(0)

                    st.download_button(
                        label="💾 Descargar Excel",
                        data=output_stream,
                        file_name="factura_extraida.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                except Exception as e:
                    st.error(f"No se pudo procesar el JSON: {e}")
            else:
                st.error("No se encontró un JSON válido en la respuesta.")



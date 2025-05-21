import streamlit as st
import requests
import json
from PIL import Image
import pandas as pd
import re
import google.generativeai as genai  # Gemini
from io import BytesIO

st.set_page_config(page_title="Lector Inteligente de Facturas", layout="wide")

# 🔑 API Keys desde secrets.toml
MINDEE_API_KEY = st.secrets["MINDEE_API_KEY"]
GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]

# 📡 Configurar Gemini
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel("models/gemini-1.5-flash-001")

st.title("📄 Lector Inteligente de Facturas usando Mindee + Gemini")

uploaded_file = st.file_uploader("Subir factura (imagen)", type=["jpg", "jpeg", "png"])

# 🧠 Función para usar Mindee OCR
def mindee_ocr_api(image_bytes):
    url = "https://api.mindee.net/v1/products/mindee/invoices/v4/predict"
    headers = {
        "Authorization": f"Token {MINDEE_API_KEY}"
    }
    files = {
        "document": ("factura.jpg", image_bytes)
    }

    response = requests.post(url, headers=headers, files=files)
    
    try:
        result = response.json()  # ⬅️ ya es un dict
    except Exception:
        st.error("❌ No se pudo interpretar la respuesta de Mindee.")
        return None

    if response.status_code != 201:
        mensaje_error = result.get('api_request', {}).get('error', {}).get('message', 'Error desconocido')
        st.error(f"❌ Error en Mindee OCR: {mensaje_error}")
        return None
    
    return result  # ⬅️ devolvemos dict

# ✅ Función para extraer texto de la respuesta
def extract_text_from_mindee_response(data):
    try:
        prediction = data.get("document", {}).get("inference", {}).get("prediction")

        if isinstance(prediction, list):
            texto = "\n".join(
                [f"{item.get('name', 'Campo desconocido')}: {item.get('value', '')}" for item in prediction]
            )
        elif isinstance(prediction, dict):
            texto = "\n".join(
                [f"{key}: {value.get('value', '')}" for key, value in prediction.items()]
            )
        else:
            texto = "❌ No se encontraron predicciones válidas."

        return texto
    except Exception as e:
        st.error(f"Error extrayendo texto: {e}")
        return ""

# Extraer JSON desde respuesta de Gemini
def extract_json_from_text(text):
    try:
        json_str = re.search(r"\{.*\}", text, re.DOTALL).group(0)
        return json_str
    except Exception:
        return None

# 🚀 FLUJO PRINCIPAL
if uploaded_file:
    image = Image.open(uploaded_file)
    st.image(image, caption="Factura subida", use_container_width=True)

    uploaded_file_bytes = uploaded_file.getvalue()

    with st.spinner("🧠 Extrayendo texto con Mindee..."):
        ocr_result = mindee_ocr_api(uploaded_file_bytes)

    if ocr_result:
        # ✅ Mostrar JSON crudo
        st.subheader("🔍 Respuesta JSON completa de Mindee")
        st.json(ocr_result)

        text = extract_text_from_mindee_response(ocr_result)
        st.text_area("🧾 Texto estructurado por Mindee", text, height=300)

        with st.spinner("🤖 Interpretando datos con Gemini..."):
            prompt = f"""Sos un asistente que analiza texto OCR de facturas. A partir del siguiente texto extraído:
{text}

Extraé los siguientes datos clave en formato JSON válido:
- Proveedor
- Monto total
- Fecha de compra (dd/mm/aaaa)
- Fecha de vencimiento (si existe)
- Sucursal (si aparece)
- Días restantes hasta el vencimiento (si hay fecha)

Solo devolvé el JSON válido, sin explicaciones."""

            try:
                response = model.generate_content(
                    contents=[{"role": "user", "parts": [prompt]}]
                )
                output = response.text
            except Exception as e:
                st.error(f"❌ Error al procesar con Gemini: {e}")
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

                    # Descargar como Excel
                    output_xlsx = BytesIO()
                    with pd.ExcelWriter(output_xlsx, engine="xlsxwriter") as writer:
                        df.to_excel(writer, index=False, sheet_name="Factura")
                    st.download_button(
                        label="💾 Descargar XLSX",
                        data=output_xlsx.getvalue(),
                        file_name="factura_extraida.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                except Exception as e:
                    st.error(f"⚠️ No se pudo procesar el JSON: {e}")
            else:
                st.error("⚠️ No se encontró un JSON válido en la respuesta.")



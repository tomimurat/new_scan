import streamlit as st
import requests
import json
from PIL import Image
import io
from openai import OpenAI
import os
import pandas as pd

st.set_page_config(page_title="Lector Inteligente de Facturas", layout="wide")

OCR_API_KEY = st.secrets["OCR_SPACE_KEY"]
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
client = OpenAI(api_key=OPENAI_API_KEY)

st.title("📄 Lector Inteligente de Facturas usando OCR.space")

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


if uploaded_file:
    image = Image.open(uploaded_file)
    st.image(image, caption="Factura subida", use_container_width=True)

    uploaded_file_bytes = uploaded_file.getvalue()  # <-- Aquí está la clave

    with st.spinner("Extrayendo texto con OCR.space..."):
        text = ocr_space_api(uploaded_file_bytes)


    if text:
        st.text_area("Texto extraído por OCR.space", text, height=300)

        with st.spinner("Interpretando datos con GPT..."):
            prompt = f"""Sos un asistente que analiza texto OCR de facturas. A partir del siguiente texto extraído:
{text}

Extraé los siguientes datos clave en formato JSON:
- Proveedor
- Monto total
- Fecha de compra (dd/mm/aaaa)
- Fecha de vencimiento (si existe)
- Sucursal (si aparece)
- Días restantes hasta el vencimiento (si hay fecha)

Solo devolvé un JSON válido con los datos."""

            response = client.chat.completions.create(
                model="gpt-3.5",
                messages=[
                    {"role": "system", "content": "Sos un lector experto de facturas."},
                    {"role": "user", "content": prompt}
                ]
            )
            output = response.choices[0].message.content

        st.subheader("📌 Datos extraídos por GPT")
        st.code(output, language="json")

        try:
            data_json = json.loads(output)
            df = pd.DataFrame([data_json])
            st.dataframe(df)

            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button("💾 Descargar CSV", data=csv, file_name="factura_extraida.csv", mime="text/csv")
        except Exception as e:
            st.error(f"No se pudo procesar el JSON: {e}")


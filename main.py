import streamlit as st
import requests
import openai
import os

st.set_page_config(page_title="Lector de Facturas con GPT", layout="wide")
st.title("📄 Lector de Facturas con GPT (sin OCR local)")
st.write("Subí una imagen de una factura y extraé los datos automáticamente usando GPT.")

# OCR.Space API Key (gratuita)
OCR_API_KEY = st.secrets["OCR_SPACE_KEY"]
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
openai.api_key = OPENAI_API_KEY

# Subida de archivo
uploaded_file = st.file_uploader("Subí una imagen de la factura", type=["jpg", "jpeg", "png"])

def ocr_space_image(image_file):
    url_api = "https://api.ocr.space/parse/image"
    result = requests.post(
        url_api,
        files={"filename": image_file},
        data={"apikey": OCR_API_KEY, "language": "spa"},
    )
    return result.json()

if uploaded_file:
    st.image(uploaded_file, caption="Factura subida", use_container_width=True)
    with st.spinner("Extrayendo texto con OCR.Space..."):
        ocr_result = ocr_space_image(uploaded_file)
        try:
            text = ocr_result["ParsedResults"][0]["ParsedText"]
        except Exception as e:
            st.error("Error al extraer texto de la imagen.")
            st.stop()

    if st.checkbox("📄 Mostrar texto OCR"):
        st.text_area("Texto extraído:", text, height=300)

    # Llamado a OpenAI para interpretar texto
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

Solo devolvé un JSON válido con los datos.\""\""

        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Sos un lector experto de facturas."},
                {"role": "user", "content": prompt}
            ]
        )
        output = response.choices[0].message.content

    st.subheader("📌 Datos extraídos por GPT")
    st.code(output, language="json")

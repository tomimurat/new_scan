import streamlit as st
from PIL import Image
from datetime import datetime
import pandas as pd
import os
from openai import OpenAI

# Configuración de la página
st.set_page_config(page_title="Lector Inteligente de Facturas", layout="wide")

# Clave API de OpenAI desde secretos
os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]

# Instancia cliente OpenAI
client = OpenAI()

st.title("📄 Lector Inteligente de Facturas")
st.write("Subí una imagen de una factura para extraer los datos automáticamente.")

uploaded_file = st.file_uploader("Subir factura (imagen)", type=["jpg", "jpeg", "png"])

if uploaded_file:
    image = Image.open(uploaded_file)
    st.image(image, caption="Factura subida", use_container_width=True)

    # Usamos pytesseract para OCR si lo querés seguir usando:
    import pytesseract
    pytesseract.pytesseract.tesseract_cmd = r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe"

    with st.spinner("Procesando imagen con OCR..."):
        text = pytesseract.image_to_string(image)

    # Mostrar texto extraído (debug)
    if st.checkbox("Mostrar texto completo extraído (OCR)"):
        st.text_area("Texto extraído:", text, height=300)

    # Preparar prompt para OpenAI GPT
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

    with st.spinner("Interpretando datos con GPT..."):
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Sos un lector experto de facturas."},
                {"role": "user", "content": prompt}
            ]
        )

        output = response.choices[0].message.content

    st.subheader("📌 Datos extraídos por GPT")
    st.code(output, language="json")

    # Convertir JSON a DataFrame para mostrar y descargar
    try:
        import json
        data_json = json.loads(output)

        df = pd.DataFrame([data_json])
        st.dataframe(df)

        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("💾 Descargar CSV", data=csv, file_name="factura_extraida.csv", mime="text/csv")
    except Exception as e:
        st.error(f"No se pudo procesar el JSON: {e}")


    st.subheader("📌 Datos extraídos por GPT")
    st.code(output, language="json")

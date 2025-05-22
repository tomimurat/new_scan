import streamlit as st
import requests
import json
from PIL import Image
import pandas as pd
import re
import io
from datetime import datetime  # Para calcular días de vencimiento
import google.generativeai as genai  # Gemini

st.set_page_config(page_title="Lector Inteligente de Facturas", layout="wide")

# secrets.toml
OCR_API_KEY = st.secrets["OCR_SPACE_KEY"]
GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]

# Configurar Gemini
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel("models/gemini-1.5-flash-001")

st.title("📄 Lector Inteligente de Facturas usando OCR.space + Gemini")

uploaded_file = st.file_uploader("Subir factura (imagen)", type=["jpg", "jpeg", "png"])

#  OCR
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

# JSON del texto
def extract_json_from_text(text):
    try:
        json_str = re.search(r"\{.*\}", text, re.DOTALL).group(0)
        return json_str
    except Exception:
        return None

#imagen
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
- Número de factura (suele aparecer debajo de la misma en caso de no estar al lado)
- Fecha de compra (dd/mm/aaaa)
- Fecha de vencimiento (si existe)
- Sucursal (si aparece)

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

                    # días restantes hasta el vencimiento
                    fecha_vencimiento_str = data_json.get("Fecha de vencimiento")
                    if fecha_vencimiento_str:
                        try:
                            vencimiento = datetime.strptime(fecha_vencimiento_str, "%d/%m/%Y")
                            hoy = datetime.now()
                            dias_restantes = (vencimiento - hoy).days
                            data_json["Días restantes hasta el vencimiento"] = dias_restantes
                        except Exception as e:
                            st.warning(f"No se pudo calcular la diferencia de días: {e}")
                            data_json["Días restantes hasta el vencimiento"] = "Error"
                    else:
                        data_json["Días restantes hasta el vencimiento"] = "No especificado"

                    # Mostrar en tabla
                    df = pd.DataFrame([data_json])

                    def resaltar_dias(val):
                        if isinstance(val, int):
                            if val < 0:
                                return "background-color: #ffcccc; color: red;"  # vencido
                            elif val <= 3:
                                return "background-color: #fff3cd; color: #856404;"  # cerca de vencer
                            else:
                                return "background-color: #d4edda; color: #155724;"  # todo ok
                        return ""

                    st.subheader("📋 Datos estructurados")
                    st.dataframe(df.style.applymap(resaltar_dias, subset=["Días restantes hasta el vencimiento"]))

                    #  Exportar Excel
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


# app/payment.py
import mercadopago

from database import SessionLocal, Order
from dotenv import load_dotenv
import streamlit as st
import logging
import traceback


# Obtener la ruta absoluta al directorio raíz del proyecto
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


MP_ACCESS_TOKEN = st.secrets[mercadopago][TK]
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# Inicializar el cliente de MercadoPago

sdk = mercadopago.SDK("MP_ACCESS_TOKEN")

def crear_preferencia(order_id, total):

    preference_data = {
        "items": [
            {
                "title": f"Pedido #{order_id}",
                "quantity": 1,
                "currency_id": "CLP",  # Asegúrate de usar la moneda correcta
                "unit_price": float(total)
            }
        ],
        "external_reference": str(order_id),  # Asociar la preferencia con la orden
        "back_urls": {
            "success": "https://tu_sitio.com/exito",     # URL donde redirigir al éxito
            "failure": "https://tu_sitio.com/fallo",     # URL donde redirigir al fallo
            "pending": "https://tu_sitio.com/pendiente"  # URL donde redirigir si está pendiente
        },
        "auto_return": "approved",
        "notification_url": WEBHOOK_URL  # URL de tu webhook
    }
    try:
        preference_response = sdk.preference().create(preference_data)
        preference = preference_response["response"]
        
        if preference_response["status"] >= 400:
            # Manejar errores basados en el status_code
            st.error(f"Error al crear preferencia: {preference_response['status']}")
            st.error(preference)
            return None
        else:
            # Preferencia creada exitosamente
            return preference["init_point"]
    except Exception as e:
        st.error(f"Ocurrió un error inesperado: {e}")
        return None

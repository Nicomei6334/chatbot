# app/payment.py
import mercadopago
import os
from database import SessionLocal, Order
from dotenv import load_dotenv
import streamlit as st
import logging
import traceback


# Obtener la ruta absoluta al directorio raíz del proyecto
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Cargar las variables de entorno
load_dotenv(os.path.join(BASE_DIR, '.env'))

MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# Inicializar el cliente de MercadoPago



def crear_preferencia(order_id, total):
    sdk = mercadopago.SDK("MP_ACCESS_TOKEN")
    
    preference_data = {
        "items": [
            {
                "title": f"Pedido #{order_id}",
                "quantity": 1,
                "currency_id": "ARS",
                "unit_price": float(total)
            }
        ],
        "back_urls": {
            "success": "https://tu_sitio.com/exito",
            "failure": "https://tu_sitio.com/fallo",
            "pending": "https://tu_sitio.com/pendiente"
        },
        "auto_return": "approved"
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
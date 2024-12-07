# app/payment.py
import mercadopago

from database import SessionLocal, Order

import streamlit as st
import logging
import traceback

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


MP_ACCESS_TOKEN = st.secrets["mercadopago"]["TK"]
WEBHOOK_URL = st.secrets["WEBHOOK"]["WH"]

# Inicializar el cliente de MercadoPago

sdk = mercadopago.SDK(MP_ACCESS_TOKEN)

if not WEBHOOK_URL:
    logger.error("WEBHOOK_URL no está configurada.")
    st.error("Configuración de Webhook no encontrada. Por favor, revisa las variables de entorno.")

def crear_preferencia(order_id, total):
    """
    Crea una preferencia de pago en MercadoPago.

    Args:
        order_id (int): ID del pedido.
        total (float): Total del pedido en CLP.

    Returns:
        str: URL de inicio de pago de MercadoPago o None si falla.
    """    
     # Convertir el total a entero para cumplir con los requisitos de MercadoPago
    total_int = int(total)
    preference_data = {
        "items": [
            {
                "title": f"Pedido #{order_id}",
                "quantity": 1,
                "currency_id": "CLP",  # Asegúrate de usar la moneda correcta
                "unit_price": total_int
            }
        ],
        "external_reference": str(order_id),  # Asociar la preferencia con la orden
        "back_urls": {
            "success": f"https://chatbotverduras.streamlit.app?payment_status=approved&order_id={order_id}",
            "failure": f"https://chatbotverduras.streamlit.app?payment_status=rejected&order_id={order_id}",
            "pending": f"https://chatbotverduras.streamlit.app?payment_status=pending&order_id={order_id}"
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
            # Preferencia creada exitosamente, guardar la URL de preferencia en la base de datos
            db = SessionLocal()
            order = db.query(Order).filter(Order.idorders == order_id).first()
            if order:
                order.preference_url = preference["init_point"]
                db.commit()
                logger.info(f"Preferencia URL guardada para el pedido ID {order_id}.")
            db.close()
            return preference["init_point"]
    except Exception as e:
        st.error(f"Ocurrió un error inesperado: {e}")
        logger.error(f"Error al crear preferencia: {e}")
        return None

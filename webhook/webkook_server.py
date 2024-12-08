# webhook.py
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
import os
import mercadopago
from app.database import SessionLocal, Order
from dotenv import load_dotenv
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



MP_ACCESS_TOKEN = st.secrets["mercadopago"]["TK"]
SUPABASE_URL = st.secrets["SUPABASE"]["URL"]
SUPABASE_KEY = st.secrets["SUPABASE"]["KEY"]
BUCKET_NAME = "productos-imagenes"  # Asegúrate de que coincida con tu configuración

# Inicializar el cliente de MercadoPago
sdk = mercadopago.SDK(MP_ACCESS_TOKEN)

app = FastAPI()


@app.post("/webhook")
async def mercadopago_webhook(request: Request):
    try:
        data = await request.json()
        logger.info(f"Webhook recibido: {data}")

        if data.get("type") == "payment":
            payment_id = data["data"]["id"]
            logger.info(f"Procesando pago con ID: {payment_id}")

            # Consultar el pago a MercadoPago
            payment_info = sdk.payment().get(payment_id)
            payment = payment_info["response"]

            # Obtener el estado del pago
            status = payment.get("status")
            external_reference = payment.get("external_reference")  # order_id

            if not external_reference:
                logger.error("No se encontró 'external_reference' en el pago.")
                raise HTTPException(status_code=400, detail="Missing external_reference")

            order_id = int(external_reference)
            logger.info(f"Actualizando estado del pedido ID: {order_id} a {status}")

            # Actualizar el estado en la base de datos
            db = SessionLocal()
            try:
                order = db.query(Order).filter(Order.idorders == order_id).first()
                if not order:
                    logger.error(f"Orden ID {order_id} no encontrada.")
                    raise HTTPException(status_code=404, detail="Order not found")

                if status == "approved":
                    order.status = "aprobado"
                elif status == "pending":
                    order.status = "pendiente"
                elif status == "rejected":
                    order.status = "rechazado"
                else:
                    order.status = "desconocido"

                db.commit()
                logger.info(f"Orden ID {order_id} actualizada a {order.status}")
            except Exception as e:
                db.rollback()
                logger.error(f"Error al actualizar la orden: {e}")
                raise HTTPException(status_code=500, detail="Error updating order")
            finally:
                db.close()

        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Error en webhook: {e}")
        raise HTTPException(status_code=400, detail="Invalid request")

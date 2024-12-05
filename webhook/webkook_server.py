# webhook/webhook_server.py
from fastapi import FastAPI, Request
import os
import json
from app.database import SessionLocal, Order, Producto
from dotenv import load_dotenv
from sqlalchemy.exc import SQLAlchemyError
import uvicorn
import logging

# Obtener la ruta absoluta al directorio raíz del proyecto
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, '.env'))

DATABASE_URL = os.getenv("DATABASE_URL")
# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

@app.post("/webhook")
async def webhook(request: Request):
    payload = await request.json()

    # Verificar que el evento sea de tipo 'payment'
    if payload.get("type") == "payment":
        payment = payload.get("data")
        payment_id = str(payment.get("id"))
        status = payment.get("status")

        db = SessionLocal()
        try:
            # Buscar la orden por payment_id
            order = db.query(Order).filter(Order.payment_id == payment_id).first()
            if order:
                if status == "approved":
                    order.status = "aprobado"
                elif status == "in_process":
                    order.status = "pendiente"
                elif status in ["rejected", "cancelled"]:
                    order.status = "rechazado"
                db.commit()
                print(f"Orden {order.idorders} actualizada a {order.status}")
            else:
                print(f"No se encontró la orden con payment_id: {payment_id}")
        except SQLAlchemyError as e:
            db.rollback()
            print(f"Error al actualizar la orden: {e}")
        finally:
            db.close()

    return {"status": "received"}

if __name__ == "__main__":
    # Ejecutar el servidor de webhook
    uvicorn.run(app, host="0.0.0.0", port=8000)

# admin.py

import streamlit as st
from app.database import SessionLocal, Order, User  # Asegúrate de que estos modelos están definidos en database.py
import pandas as pd
from sqlalchemy import func
import os
from dotenv import load_dotenv

# Cargar las variables de entorno
load_dotenv()

# Obtener las credenciales de administrador desde el archivo .env
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

def authenticate_admin(username, password):
    """
    Verifica si las credenciales de administrador son correctas.
    """
    return username == ADMIN_USERNAME and password == ADMIN_PASSWORD

def mostrar_pedidos():
    """
    Muestra todos los pedidos en una tabla.
    """
    db = SessionLocal()
    try:
        # Suponiendo que el modelo Order tiene una relación con User
        pedidos = db.query(Order).join(User).all()
        if not pedidos:
            st.info("No hay pedidos para mostrar.")
            return
        
        data = []
        for pedido in pedidos:
            data.append({
                "ID": pedido.id,
                "Usuario": pedido.user.email,  # Asegúrate de que hay una relación user en Order
                "Producto": pedido.product,
                "Cantidad": pedido.quantity,
                "Precio": pedido.price,
                "Fecha": pedido.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            })
        
        df = pd.DataFrame(data)
        st.dataframe(df)
    except Exception as e:
        st.error("Error al obtener los pedidos.")
    finally:
        db.close()

def mostrar_estadisticas():
    """
    Muestra estadísticas como el total de pedidos y los ingresos totales.
    """
    db = SessionLocal()
    try:
        total_pedidos = db.query(func.count(Order.id)).scalar()
        total_ingresos = db.query(func.sum(Order.price)).scalar()
        
        if total_ingresos is None:
            total_ingresos = 0
        
        st.metric("Total de Pedidos", total_pedidos)
        st.metric("Total de Ingresos", f"${total_ingresos:,.0f} CLP")
    except Exception as e:
        st.error("Error al obtener las estadísticas.")
    finally:
        db.close()

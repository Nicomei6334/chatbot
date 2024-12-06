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

def gestionar_productos():
    """
    Permite al administrador gestionar los productos (editar, añadir, eliminar).
    """
    st.subheader("Gestionar Productos")
    db = SessionLocal()
    
    try:
        # Obtener productos actuales
        productos = db.query(Producto).all()

        # Mostrar tabla editable
        if productos:
            st.write("Productos Actuales:")
            data = []
            for producto in productos:
                data.append({
                    "ID": producto.idproductos,
                    "Nombre": producto.nombre,
                    "Unidad": producto.unidad,
                    "Precio": producto.precio,
                    "Stock": producto.stock,
                    "Imagen URL": producto.imagen
                })
            
            df = pd.DataFrame(data)
            edited_df = st.experimental_data_editor(df, num_rows="dynamic", key="product_editor")

            # Guardar cambios realizados por el administrador
            if st.button("Guardar Cambios"):
                for index, row in edited_df.iterrows():
                    producto = db.query(Producto).filter(Producto.idproductos == row["ID"]).first()
                    if producto:
                        producto.nombre = row["Nombre"]
                        producto.unidad = row["Unidad"]
                        producto.precio = row["Precio"]
                        producto.stock = row["Stock"]
                        producto.imagen = row["Imagen URL"]
                        db.commit()
                st.success("Cambios guardados exitosamente.")
        else:
            st.info("No hay productos registrados.")

        # Añadir nuevos productos
        st.write("---")
        st.subheader("Añadir Nuevo Producto")
        with st.form("add_product_form"):
            nuevo_nombre = st.text_input("Nombre del Producto")
            nueva_unidad = st.text_input("Unidad (ejemplo: kg, unidad)")
            nuevo_precio = st.number_input("Precio", min_value=0.0, step=1.0)
            nuevo_stock = st.number_input("Stock", min_value=0, step=1)
            nueva_imagen = st.text_input("URL de la Imagen")
            submit = st.form_submit_button("Añadir Producto")

            if submit:
                if nuevo_nombre and nueva_unidad and nuevo_precio > 0:
                    nuevo_producto = Producto(
                        nombre=nuevo_nombre,
                        unidad=nueva_unidad,
                        precio=nuevo_precio,
                        stock=nuevo_stock,
                        imagen=nueva_imagen
                    )
                    db.add(nuevo_producto)
                    db.commit()
                    st.success(f"Producto '{nuevo_nombre}' añadido exitosamente.")
                else:
                    st.error("Por favor, completa todos los campos obligatorios.")
    
    except Exception as e:
        st.error(f"Error al gestionar productos: {e}")
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

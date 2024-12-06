# admin.py

import streamlit as st
from app.database import SessionLocal, Order, User  # Asegúrate de que estos modelos están definidos en database.py
import pandas as pd
from sqlalchemy import func
import os
from dotenv import load_dotenv


# Obtener las credenciales de administrador desde el archivo .env
ADMIN_USERNAME = st.secrets["admin"]["user"]
ADMIN_PASSWORD = st.secrets["admin"]["pass"]

def authenticate_admin(username, password):
    """
    Verifica si las credenciales de administrador son correctas.
    """
    return username == ADMIN_USERNAME and password == ADMIN_PASSWORD

def mostrar_pedidos():
    """
    Muestra todos los pedidos en un menú interactivo. Al seleccionar un pedido, se muestran los detalles.
    """
    db = SessionLocal()
    try:
        # Obtener todos los pedidos junto con la información del usuario
        pedidos = db.query(Order).join(User).all()

        if not pedidos:
            st.info("No hay pedidos para mostrar.")
            return

        # Crear opciones para el selectbox
        opciones_pedidos = [
            f"Pedido ID: {pedido.id} - Usuario: {pedido.user.email}" for pedido in pedidos
        ]
        
        # Mostrar el selectbox para seleccionar un pedido
        seleccionado = st.selectbox(
            "Selecciona un pedido para ver sus detalles:",
            opciones_pedidos,
            key="pedido_selectbox"
        )

        # Encontrar el pedido correspondiente
        pedido = next(pedido for pedido in pedidos if f"Pedido ID: {pedido.id}" in seleccionado)

        # Mostrar detalles del pedido
        st.subheader(f"Detalles del Pedido ID: {pedido.id}")
        st.write(f"**Usuario:** {pedido.user.email}")
        st.write(f"**Estado:** {pedido.status}")
        st.write(f"**Fecha:** {pedido.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        st.write(f"**Total:** ${pedido.total:,.0f} CLP")

        # Mostrar los productos del pedido
        if pedido.order_items:
            st.write("### Productos:")
            for item in pedido.order_items:
                producto = item.producto.nombre if item.producto else "Desconocido"
                cantidad = item.quantity
                precio_unitario = item.unit_price
                subtotal = cantidad * precio_unitario
                imagen_url = item.producto.imagen if item.producto and item.producto.imagen else None

                # Mostrar detalles del producto
                with st.container():
                    st.write(f"**Producto:** {producto}")
                    st.write(f"**Cantidad:** {cantidad}")
                    st.write(f"**Precio Unitario:** ${precio_unitario:,.0f} CLP")
                    st.write(f"**Subtotal:** ${subtotal:,.0f} CLP")
                    if imagen_url:
                        st.image(imagen_url, caption=producto, width=100)
                    st.write("---")
        else:
            st.warning("Este pedido no tiene productos asociados.")
    
    except Exception as e:
        st.error(f"Error al obtener los pedidos: {e}")
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

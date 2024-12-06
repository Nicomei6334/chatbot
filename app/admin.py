# admin.py

import streamlit as st
from database import SessionLocal, Order, User, Producto  # Asegúrate de que estos modelos están definidos en database.py
import pandas as pd
from sqlalchemy import func
from sqlalchemy.orm import joinedload
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
    Muestra todos los pedidos en una lista interactiva. Al seleccionar un pedido, se muestran los detalles.
    """
    
    # Ajustar el estilo si es necesario (Opcional)
    st.markdown("""
    <style>
    /* Aplica estilos a la tabla */
    table {
        background-color: #ffffff !important;
        color: #000000 !important;
    }
    
    /* Estilos para el encabezado de la tabla */
    thead tr th {
        background-color: #f0f0f0 !important;
        color: #000000 !important;
    }
    
    /* Estilos para las celdas del cuerpo de la tabla */
    tbody tr td {
        background-color: #ffffff !important;
        color: #000000 !important;
    }
    
    /* Si hay alguna clase específica que causa conflicto, prueba esto: */
    /* Cambia .css-1cypcdb por la clase que veas en tu HTML si difiere */
    .css-1cypcdb th, .css-1cypcdb td {
        background-color: #ffffff !important;
        color: #000000 !important;
        border: 1px solid #ccc !important;
    }
    
    /* Ajusta el color del texto en otras áreas, como selectboxes o encabezados si es necesario */
    .css-1cypcdb p, .css-1cypcdb label {
        color: #000 !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    db = SessionLocal()
    try:
        # Obtener todos los pedidos con información del usuario
        pedidos = db.query(Order).join(User).all()

        if not pedidos:
            st.info("No hay pedidos para mostrar.")
            return

        # Crear opciones para el selectbox
        opciones_pedidos = [f"Pedido ID: {pedido.idorders} - Usuario: {pedido.user.email}" for pedido in pedidos]

        # Seleccionar un pedido
        selected_pedido = st.selectbox("Selecciona un pedido para ver los detalles:", opciones_pedidos)

        # Extraer el ID del pedido seleccionado
        pedido_id = int(selected_pedido.split(":")[1].split("-")[0].strip())

        # Buscar el pedido seleccionado
        pedido_seleccionado = db.query(Order).filter(Order.idorders == pedido_id).first()

        if pedido_seleccionado:
            # Mostrar detalles del pedido seleccionado
            st.subheader(f"Detalles del Pedido ID: {pedido_seleccionado.idorders}")
            st.write(f"**Usuario:** {pedido_seleccionado.user.email}")
            st.write(f"**Estado:** {pedido_seleccionado.status.capitalize()}")
            st.write(f"**Fecha:** {pedido_seleccionado.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")

            # Lógica para el total:
            # Si el pedido está pendiente, mostramos el total original.
            # Si el pedido está rechazado (equivalente a cancelado), mostramos 0.
            # Si quieres incluir más condiciones, puedes hacerlo.
            if pedido_seleccionado.status.lower() == "pendiente":
                total_mostrar = pedido_seleccionado.total or 0
            elif pedido_seleccionado.status.lower() == "rechazado":
                total_mostrar = 0
            else:
                # Para otros estados (por ejemplo, aprobado), puedes decidir qué mostrar
                # Aquí lo dejamos igual al total original o 0 si no existe
                total_mostrar = pedido_seleccionado.total or 0

            st.write(f"**Total:** ${total_mostrar:,.0f} CLP")

            # Mostrar los productos del pedido en una tabla
            if pedido_seleccionado.order_items:
                st.write("### Productos del Pedido:")
                productos_data = []
                for item in pedido_seleccionado.order_items:
                    producto_nombre = item.producto.nombre if item.producto else "Desconocido"
                    subtotal = item.quantity * item.unit_price
                    productos_data.append({
                        "Producto": producto_nombre,
                        "Cantidad": item.quantity,
                        "Precio Unitario": f"${item.unit_price:,.0f}",
                        "Subtotal": f"${subtotal:,.0f}",
                    })

                # Mostrar los productos como tabla
                st.table(productos_data)
            else:
                st.warning("Este pedido no tiene productos asociados.")
        else:
            st.error("Pedido no encontrado.")
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
        # Obtener productos actuales desde la base de datos
        lista_productos = db.query(Producto).all()

        if lista_productos:
            st.write("Productos Actuales:")
            for producto in lista_productos:
                with st.expander(f"Producto ID: {producto.idproductos} - {producto.nombre}"):
                    nuevo_nombre = st.text_input("Nombre", value=producto.nombre, key=f"nombre_{producto.idproductos}")
                    nueva_unidad = st.text_input("Unidad", value=producto.unidad, key=f"unidad_{producto.idproductos}")
                    nuevo_precio = st.number_input("Precio", value=producto.precio, step=1.0, key=f"precio_{producto.idproductos}")
                    nuevo_stock = st.number_input("Stock", value=producto.stock, step=1, key=f"stock_{producto.idproductos}")
                    nueva_imagen = st.text_input("URL de la Imagen", value=producto.imagen, key=f"imagen_{producto.idproductos}")
                    
                    if st.button(f"Guardar Cambios para ID {producto.idproductos}", key=f"guardar_{producto.idproductos}"):
                        producto.nombre = nuevo_nombre
                        producto.unidad = nueva_unidad
                        producto.precio = nuevo_precio
                        producto.stock = nuevo_stock
                        producto.imagen = nueva_imagen
                        db.commit()
                        st.success(f"Producto ID {producto.idproductos} actualizado correctamente.")

        else:
            st.info("No hay productos registrados.")

        # Añadir nuevos productos
        st.write("---")
        st.subheader("Añadir Nuevo Producto")
        with st.form("add_product_form"):
            nuevo_id = st.number_input("ID del Producto (único)", min_value=1, step=1, key="nuevo_id")
            nuevo_nombre = st.text_input("Nombre del Producto", key="nuevo_nombre")
            nueva_unidad = st.text_input("Unidad (ejemplo: kg, unidad)", key="nueva_unidad")
            nuevo_precio = st.number_input("Precio", min_value=0.0, step=1.0, key="nuevo_precio")
            nuevo_stock = st.number_input("Stock", min_value=0, step=1, key="nuevo_stock")
            nueva_imagen = st.text_input("URL de la Imagen", key="nueva_imagen")
            submit = st.form_submit_button("Añadir Producto")

            if submit:
                # Validar que el ID no esté ocupado
                producto_existente = db.query(Producto).filter(Producto.idproductos == nuevo_id).first()
                if producto_existente:
                    st.error(f"El ID {nuevo_id} ya está ocupado. Por favor, elige otro.")
                elif nuevo_nombre and nueva_unidad and nuevo_precio > 0:
                    nuevo_producto = Producto(
                        idproductos=nuevo_id,
                        nombre=nuevo_nombre,
                        unidad=nueva_unidad,
                        precio=nuevo_precio,
                        stock=nuevo_stock,
                        imagen=nueva_imagen
                    )
                    db.add(nuevo_producto)
                    db.commit()
                    st.success(f"Producto '{nuevo_nombre}' añadido exitosamente con ID {nuevo_id}.")
                else:
                    st.error("Por favor, completa todos los campos obligatorios.")
    
    except Exception as e:
        st.error(f"Error al gestionar productos: {e}")
    finally:
        db.close()
        
def mostrar_estadisticas():
    """
    Muestra estadísticas clave para que el dueño pueda analizar su negocio.
    """
    db = SessionLocal()
    try:
        # Estadísticas básicas
        total_pedidos = db.query(func.count(Order.idorders)).scalar()
        total_ingresos = db.query(func.sum(Order.total)).scalar()
        
        # Asegurarse de que no haya valores nulos
        if total_ingresos is None:
            total_ingresos = 0
        
        # Producto más vendido
        producto_mas_vendido = (
            db.query(Producto.nombre, func.sum(OrderItem.quantity).label("total_vendido"))
            .join(OrderItem, Producto.idproductos == OrderItem.product_id)
            .group_by(Producto.nombre)
            .order_by(func.sum(OrderItem.quantity).desc())
            .first()
        )
        
        # Total de productos vendidos
        total_productos_vendidos = db.query(func.sum(OrderItem.quantity)).scalar()
        if total_productos_vendidos is None:
            total_productos_vendidos = 0

        # Usuario con más pedidos
        usuario_mas_pedidos = (
            db.query(User.email, func.count(Order.idorders).label("total_pedidos"))
            .join(Order, User.idusers == Order.user_id)
            .group_by(User.email)
            .order_by(func.count(Order.idorders).desc())
            .first()
        )
        
        # Mostrar estadísticas en la página
        st.subheader("📊 Estadísticas del Negocio")
        st.metric("Total de Pedidos", total_pedidos)
        st.metric("Total de Ingresos", f"${total_ingresos:,.0f} CLP")
        st.metric("Cantidad Total de Productos Vendidos", total_productos_vendidos)
        
        if producto_mas_vendido:
            st.metric("Producto Más Vendido", f"{producto_mas_vendido[0]} ({producto_mas_vendido[1]} unidades)")
        else:
            st.metric("Producto Más Vendido", "N/A")
        
        if usuario_mas_pedidos:
            st.metric("Usuario con Más Pedidos", f"{usuario_mas_pedidos[0]} ({usuario_mas_pedidos[1]} pedidos)")
        else:
            st.metric("Usuario con Más Pedidos", "N/A")

    except Exception as e:
        st.error(f"Error al obtener las estadísticas: {e}")
    finally:
        db.close()

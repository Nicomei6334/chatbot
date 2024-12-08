# admin.py

import streamlit as st
from database import SessionLocal, Order, User, Producto, OrderItem, Feedback  # Asegúrate de que estos modelos están definidos en database.py
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
     /* Seleccionar los encabezados de fila (índices) */
    table th[scope="row"] {
        background-color: #ffffff !important;
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
            st.write(f"**Usuario:** {pedido_seleccionado.user.first_name} {pedido_seleccionado.user.last_name}")
            st.write(f"**Correo:** {pedido_seleccionado.user.email}")
            st.write(f"**Numero telefónico** {pedido_seleccionado.user.phone}")
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
    db = SessionLocal()

    # Bandera para saber si el último envío fue exitoso
    if "last_submission_success" not in st.session_state:
        st.session_state["last_submission_success"] = False

    # Si el último envío fue exitoso, reiniciar campos antes de mostrar el formulario
    if st.session_state["last_submission_success"]:
        st.session_state["nuevo_id"] = 1
        st.session_state["nuevo_nombre"] = ""
        st.session_state["nueva_unidad"] = ""
        st.session_state["nuevo_precio"] = 0.0
        st.session_state["nuevo_stock"] = 0
        st.session_state["nueva_imagen"] = ""
        st.session_state["last_submission_success"] = False

    # Asegurar llaves en session_state
    if "nuevo_id" not in st.session_state:
        st.session_state["nuevo_id"] = 1
    if "nuevo_nombre" not in st.session_state:
        st.session_state["nuevo_nombre"] = ""
    if "nueva_unidad" not in st.session_state:
        st.session_state["nueva_unidad"] = ""
    if "nuevo_precio" not in st.session_state:
        st.session_state["nuevo_precio"] = 0.0
    if "nuevo_stock" not in st.session_state:
        st.session_state["nuevo_stock"] = 0
    if "nueva_imagen" not in st.session_state:
        st.session_state["nueva_imagen"] = ""

    st.subheader("Gestionar Productos")

    try:
        lista_productos = db.query(Producto).all()

        if lista_productos:
            # Crear un diccionario para mapear la opción seleccionada con el producto
            opciones = ["Ninguno"] + [f"SKU: {p.idproductos} - {p.nombre}" for p in lista_productos]
            producto_map = {f"SKU: {p.idproductos} - {p.nombre}": p for p in lista_productos}

            seleccion = st.selectbox("Selecciona un producto para editar:", opciones)
            
            if seleccion != "Ninguno":
                producto = producto_map[seleccion]
                # Mostrar formulario para editar producto seleccionado
                with st.form(f"edit_form_{producto.idproductos}", clear_on_submit=False):
                    nuevo_nombre = st.text_input("Nombre", value=producto.nombre)
                    nueva_unidad = st.text_input("Unidad", value=producto.unidad)
                    nuevo_precio = st.number_input("Precio", value=producto.precio, step=1.0)
                    nuevo_stock = st.number_input("Stock", value=producto.stock, step=1)
                    nueva_imagen = st.text_input("URL de la Imagen", value=producto.imagen if producto.imagen else "")

                    col1, col2 = st.columns(2)
                    with col1:
                        guardar_cambios = st.form_submit_button("Guardar Cambios")
                    with col2:
                        eliminar = st.form_submit_button("Eliminar Producto")

                    if guardar_cambios:
                        # Validar si el nombre ya existe en otro producto distinto del actual
                        producto_mismo_nombre = db.query(Producto).filter(
                            Producto.nombre == nuevo_nombre,
                            Producto.idproductos != producto.idproductos
                        ).first()
                        if producto_mismo_nombre:
                            st.error("Ya existe otro producto con el mismo nombre. Por favor, elige otro nombre.")
                        else:
                            producto.nombre = nuevo_nombre
                            producto.unidad = nueva_unidad
                            producto.precio = nuevo_precio
                            producto.stock = nuevo_stock
                            producto.imagen = nueva_imagen
                            db.commit()
                            st.success(f"Producto ID {producto.idproductos} actualizado correctamente.")
                            st.session_state["last_submission_success"] = True
                            st.stop()

                    if eliminar:
                        db.delete(producto)
                        db.commit()
                        st.success(f"Producto ID {producto.idproductos} eliminado correctamente.")
                        st.session_state["last_submission_success"] = True
                        st.stop()

        else:
            st.info("No hay productos registrados.")

        st.write("---")
        st.subheader("Añadir Nuevo Producto")

        with st.form("add_product_form", clear_on_submit=False):
            nuevo_id = st.number_input("SKU del Producto (único)", min_value=1, step=1, key="nuevo_id")
            nuevo_nombre = st.text_input("Nombre del Producto", key="nuevo_nombre")
            nueva_unidad = st.text_input("Unidad (ejemplo: kg, unidad)", key="nueva_unidad")
            nuevo_precio = st.number_input("Precio", min_value=0.0, step=1.0, key="nuevo_precio")
            nuevo_stock = st.number_input("Stock", min_value=0, step=1, key="nuevo_stock")
            nueva_imagen = st.text_input("URL de la Imagen", key="nueva_imagen")

            submit = st.form_submit_button("Añadir Producto")

            if submit:
                # Verificar ID único
                producto_existente_id = db.query(Producto).filter(Producto.idproductos == nuevo_id).first()
                # Verificar nombre único
                producto_existente_nombre = db.query(Producto).filter(Producto.nombre == nuevo_nombre).first()

                if producto_existente_id:
                    st.error(f"El ID {nuevo_id} ya está ocupado. Por favor, elige otro.")
                elif producto_existente_nombre:
                    st.error("Ya existe otro producto con el mismo nombre. Por favor, elige otro nombre.")
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
                    st.session_state["last_submission_success"] = True
                    st.stop()
                else:
                    st.error("Por favor, completa todos los campos obligatorios.")

    except Exception as e:
        st.error(f"Error al gestionar productos: {e}")
    finally:
        db.close()
        
opciones_satisfaccion = ["Muy Satisfecho", "Satisfecho", "Neutral", "Insatisfecho", "Muy Insatisfecho"]
satisfaccion_map = {op: i+1 for i, op in enumerate(opciones_satisfaccion)}

def admin_ver_feedback():
    st.header("Historial de Feedback")
    db = SessionLocal()
    feedbacks = db.query(Feedback).order_by(Feedback.idfeedback.desc()).all()
    db.close()

    if not feedbacks:
        st.info("No hay feedback registrado.")
        return

    # Mostrar un selectbox con los IDs de feedback
    feedback_ids = [f.idfeedback for f in feedbacks]
    selected_id = st.selectbox("Selecciona el número de feedback", feedback_ids)

    # Mostrar la información del feedback seleccionado
    selected_feedback = next((f for f in feedbacks if f.idfeedback == selected_id), None)
    if selected_feedback:
        # Convertir la escala numérica a texto (opcional)
        invert_map = {v: k for k, v in satisfaccion_map.items()}
        amigable_text = invert_map.get(selected_feedback.rating_amigable, "N/A")
        rapidez_text = invert_map.get(selected_feedback.rating_rapidez, "N/A")

        st.write(f"**Amigable:** {amigable_text}")
        st.write(f"**Rapidez:** {rapidez_text}")
        st.write(f"**¿Utilizaría en el futuro?:** {selected_feedback.future_use}")
        st.write(f"**Comentario:** {selected_feedback.comment}")
        st.write(f"**Fecha:** {selected_feedback.created_at}")

        
def mostrar_estadisticas():
    """
    Muestra estadísticas clave para que el dueño pueda analizar su negocio,
    incluyendo top 3 productos más vendidos y top 3 pedidos con mayor valor total.
    """
    db = SessionLocal()
    try:
        # Estadísticas básicas
        total_pedidos = db.query(func.count(Order.idorders)).scalar()
        total_ingresos = db.query(func.sum(Order.total)).scalar()

        # Asegurar que no haya valores nulos
        if total_ingresos is None:
            total_ingresos = 0

        # Producto más vendido (anterior)
        producto_mas_vendido = (
            db.query(Producto.nombre, func.sum(OrderItem.quantity).label("total_vendido"))
            .join(OrderItem, Producto.idproductos == OrderItem.product_id)
            .group_by(Producto.nombre)
            .order_by(func.sum(OrderItem.quantity).desc())
            .first()
        )

        # Top 3 productos más vendidos
        top_3_productos = (
            db.query(Producto.nombre, func.sum(OrderItem.quantity).label("total_vendido"))
            .join(OrderItem, Producto.idproductos == OrderItem.product_id)
            .group_by(Producto.nombre)
            .order_by(func.sum(OrderItem.quantity).desc())
            .limit(3)
            .all()
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

        # Total de ventas desde items
        total_ventas = db.query(func.sum(OrderItem.quantity * OrderItem.unit_price)).scalar()
        if total_ventas is None:
            total_ventas = 0

        # Top 3 pedidos con mayor valor total
        top_3_pedidos = (
            db.query(Order.idorders, Order.total)
            .order_by(Order.total.desc())
            .limit(3)
            .all()
        )

        st.subheader("📊 Estadísticas del Negocio")
        st.metric("Total de Pedidos", total_pedidos)
        st.metric("Total de Ingresos (desde orders.total)", f"${total_ingresos:,.0f} CLP")
        st.metric("Cantidad Total de Productos Vendidos", total_productos_vendidos)
        st.metric("Total de Ventas (calculado desde items)", f"${total_ventas:,.0f} CLP")

        # Producto Más Vendido (anterior)
        if producto_mas_vendido:
            st.metric("Producto Más Vendido", f"{producto_mas_vendido[0]} ({producto_mas_vendido[1]} unidades)")
        else:
            st.metric("Producto Más Vendido", "N/A")

        # Usuario con Más Pedidos
        if usuario_mas_pedidos:
            st.metric("Usuario con Más Pedidos", f"{usuario_mas_pedidos[0]} ({usuario_mas_pedidos[1]} pedidos)")
        else:
            st.metric("Usuario con Más Pedidos", "N/A")

        # Mostrar Top 3 Productos Más Vendidos
        st.subheader("Top 3 Productos Más Vendidos")
        if top_3_productos:
            for i in range(3):
                if i < len(top_3_productos):
                    nombre, vendidos = top_3_productos[i]
                    st.write(f"{i+1}. {nombre} - {vendidos} unidades")
                else:
                    st.write(f"{i+1}. N/A")
        else:
            # Si no hay productos
            for i in range(3):
                st.write(f"{i+1}. N/A")

        # Mostrar Top 3 Pedidos (por valor total)
        st.subheader("Top 3 Pedidos con Mayor Valor Total")
        if top_3_pedidos:
            for i in range(3):
                if i < len(top_3_pedidos):
                    pid, ptotal = top_3_pedidos[i]
                    st.write(f"{i+1}. Pedido #{pid} - Total: ${ptotal:,.0f} CLP")
                else:
                    st.write(f"{i+1}. N/A")
        else:
            for i in range(3):
                st.write(f"{i+1}. N/A")

    except Exception as e:
        st.error(f"Error al obtener las estadísticas: {e}")
    finally:
        db.close()


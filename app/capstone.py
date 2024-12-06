# app/capstone.py
import sys
import os
import logging
# Obtener la ruta absoluta al directorio raíz del proyecto
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)
import streamlit as st
from chatbot import predict_class, get_response, intents
from streamlit_option_menu import option_menu
import json
import bcrypt
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload
from database import SessionLocal, User, Order, init_db, Producto, OrderItem
import os
import re
import time
from dotenv import load_dotenv
from datetime import datetime, timezone
import pandas as pd
from admin import authenticate_admin, mostrar_pedidos, mostrar_estadisticas, gestionar_productos
from payment import crear_preferencia
# Cargar las variables de entorno

load_dotenv()

# Inicializar la base de datos

init_db()

from app.database import Message  # Asegúrate de importar la clase Message

def almacenar_mensaje(user_id, content, sender):
    db = SessionLocal()
    try:
        new_message = Message(
            user_id=user_id,
            content=content,
            sender=sender
        )
        db.add(new_message)
        db.commit()
    except Exception as e:
        db.rollback()
        st.error("Ocurrió un error al almacenar el mensaje.")
    finally:
        db.close()

# Función para inyectar CSS personalizado
def local_css(file_name):
    css_path = os.path.join(BASE_DIR, 'styles', file_name)
    if os.path.exists(css_path):
        with open(css_path) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    else:
        st.warning(f"El archivo CSS {file_name} no se encontró.")

# Cargar el archivo CSS al inicio

# Obtener las credenciales de administrador desde el archivo .env
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")


# Función para cargar el historial de mensajes

def cargar_historial_mensajes(user_id):
    db = SessionLocal()
    try:
        mensajes = db.query(Message).filter(Message.user_id == user_id).order_by(Message.timestamp).all()
        st.session_state.messages = [
            {"role": "user" if msg.sender == "user" else "assistant", "content": msg.content}
            for msg in mensajes
        ]
    except Exception:
        st.error("Ocurrió un error al cargar el historial de mensajes.")
    finally:
        db.close()

def validar_dominio(email):
    dominios_permitidos = ['gmail.com', 'outlook.com', 'hotmail.com']
    dominio = email.split('@')[-1]
    if dominio in dominios_permitidos or re.match(r".+\.(edu|org|gov)$", dominio):
        return True
    return False
def historial_mensajes_page():
    st.header("Historial de Mensajes")
    
    db = SessionLocal()
    try:
        # Obtener todos los mensajes del usuario
        mensajes = db.query(Message).filter(Message.user_id == st.session_state.user_id).order_by(Message.timestamp.desc()).all()
        
        if not mensajes:
            st.info("No tienes mensajes en tu historial.")
            return
        
        # Agrupar mensajes por fecha
        mensajes_por_fecha = {}
        for msg in mensajes:
            fecha = msg.timestamp.date()
            if fecha not in mensajes_por_fecha:
                mensajes_por_fecha[fecha] = []
            mensajes_por_fecha[fecha].append(msg)
        
        # Listar las fechas disponibles
        fechas_disponibles = sorted(mensajes_por_fecha.keys(), reverse=True)
        
        # Seleccionar una fecha para ver los mensajes
        selected_date = st.selectbox("Selecciona una fecha para ver los mensajes:", fechas_disponibles, format_func=lambda x: x.strftime("%d/%m/%Y"))
        
        st.markdown(f"### Conversaciones del **{selected_date.strftime('%d/%m/%Y')}**")
        
        # Mostrar los mensajes de la fecha seleccionada
        for msg in mensajes_por_fecha[selected_date]:
            with st.chat_message("user" if msg.sender == "user" else "assistant"):
                st.markdown(msg.content, unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Ocurrió un error al cargar el historial de mensajes: {e}")
    finally:
        db.close()
        
def initialize_session():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "admin_authenticated" not in st.session_state:
        st.session_state.admin_authenticated = False
    if "user_id" not in st.session_state:
        st.session_state.user_id = None
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "carrito" not in st.session_state:
        st.session_state.carrito = {}
    if "boleta_generada" not in st.session_state:
        st.session_state.boleta_generada = False
    if "menu_mostrado" not in st.session_state:
        st.session_state.menu_mostrado = False
    if "first_message" not in st.session_state:
        st.session_state.first_message = True
    if "login_attempts" not in st.session_state:
        st.session_state.login_attempts = {}

def sidebar_menu():
    # Generar una clave única basada en el estado de la sesión para forzar la actualización del menú
    if st.session_state.admin_authenticated:
        menu_key = "menu_admin"
        options = ["Ver Pedidos", "Estadísticas", "Cerrar Sesión Admin"]
        icons = ["cart", "bar-chart", "box-arrow-right"]
        menu_title = "Administrador"
    elif st.session_state.logged_in:
        menu_key = "menu_user"
        options = ["Chatbot", "Historial Mensajes", "Mis Pedidos", "Cerrar Sesión"]
        icons = ["chat", "clock-history", "list-task", "box-arrow-right"]
        menu_title = "Usuario"
    else:
        menu_key = "menu_not_logged_in"
        options = ["Iniciar Sesión", "Registrarse", "Acceder como Admin"]
        icons = ["box-arrow-in-right", "person-plus", "shield-lock"]
        menu_title = "Bienvenido"
    
    with st.sidebar:
        selected = option_menu(
            menu_title=menu_title,
            options=options,
            icons=icons,
            menu_icon="cast" if st.session_state.admin_authenticated else "person-circle" if st.session_state.logged_in else "door-open",
            default_index=0,
            orientation="vertical",
            styles={
                "container": {
                    "padding": "10px",
                    "background-color": "#f0f2f6",
                    "width": "220px"  # Reducir el ancho para hacerlo más compacto
                },
                "icon": {
                    "color": "#4B5563",
                    "font-size": "18px"  # Reducir el tamaño de los íconos
                },
                "nav-link": {
                    "font-size": "14px",
                    "text-align": "left",
                    "margin": "5px",
                    "--hover-color": "#e0e0e0"
                },
                "nav-link-selected": {
                    "background-color": "#4B5563",
                    "color": "white"
                },
            },
            key=menu_key  # Clave dinámica para forzar la actualización
        )
    return selected

# Función para registrar un nuevo usuario
def register_page():
    st.header("Registro de Usuario")
    with st.form("register_form"):
        email = st.text_input("Correo Electrónico", key="register_user_email")
        password = st.text_input("Contraseña", type="password", key="register_password")
        confirm_password = st.text_input("Confirmar Contraseña", type="password", key="register_confirm_password")
        submit = st.form_submit_button("Registrarse")
        
        if submit:
            # Validar los campos del formulario
            if not email or not password or not confirm_password:
                st.error("Por favor, completa todos los campos.")
            elif not validar_dominio(email):
                st.error("Dominio de correo no permitido. Usa gmail.com, outlook.com, hotmail.com o un dominio institucional.")
            elif password != confirm_password:
                st.error("Las contraseñas no coinciden.")
            else:
                # Registrar usuario en la base de datos
                db = SessionLocal()
                try:
                    existing_user = db.query(User).filter(User.email == email).first()
                    if existing_user:
                        st.error("El correo electrónico ya está registrado.")
                    else:
                        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
                        nombre_usuario = email.split('@')[0]
                        new_user = User(nameusers=nombre_usuario, email=email, password=hashed_password.decode('utf-8'))
                        db.add(new_user)
                        db.commit()
                        
                        # Actualizar el estado de la sesión
                        st.session_state.logged_in = True
                        st.session_state.user_id = new_user.idusers
                        st.session_state.messages = []
                        st.session_state.carrito = {}
                        st.session_state.boleta_generada = False
                        st.session_state.menu_mostrado = False
                        st.session_state.first_message = True
                        cargar_historial_mensajes(new_user.idusers)
                        
                        st.success("Registro exitoso. Ahora puedes acceder al chatbot.")
                        # Reiniciar el menú para forzar la actualización
                        st.session_state.menu_key = f"menu_user_{st.session_state.user_id}"
                        
                        # No usar st.experimental_rerun(), simplemente continúa
                except IntegrityError:
                    db.rollback()
                    st.error("El correo electrónico ya está registrado.")
                except Exception:
                    db.rollback()
                    st.error("Ocurrió un error durante el registro.")
                finally:
                    db.close()

# Función para autenticar usuario
def login_page():
    st.header("Inicio de Sesión")
    with st.form("login_form"):
        email = st.text_input("Correo Electrónico", key="login_user_email")
        password = st.text_input("Contraseña", type="password", key="login_password")
        submit = st.form_submit_button("Iniciar Sesión")
        
        if submit:
            if not email or not password:
                st.error("Por favor, completa todos los campos.")
            elif not validar_dominio(email):
                st.error("Dominio de correo no permitido.")
            else:
                db = SessionLocal()
                try:
                    user = db.query(User).filter(User.email == email).first()
                    if user and bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8')):
                        # Actualizar el estado de la sesión
                        st.session_state.logged_in = True
                        st.session_state.user_id = user.idusers
                        st.session_state.messages = []
                        st.session_state.carrito = {}
                        st.session_state.boleta_generada = False
                        st.session_state.menu_mostrado = False
                        
                        st.session_state.first_message = True
                        cargar_historial_mensajes(user.idusers)
                        
                        st.success("Has iniciado sesión exitosamente.")
                        
                        # Reiniciar el menú para forzar la actualización
                        st.session_state.menu_key = f"menu_user_{st.session_state.user_id}"
                        
                        # No usar st.experimental_rerun(), simplemente continúa
                    else:
                        st.error("Correo electrónico o contraseña incorrectos.")
                except Exception:
                    st.error("Ocurrió un error durante el inicio de sesión.")
                finally:
                    db.close()


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
def ver_historial_pedidos():
    db = SessionLocal()
    try:
        pedidos = db.query(Order).options(
            joinedload(Order.order_items).joinedload(OrderItem.producto)
        ).filter(Order.user_id == st.session_state.user_id).order_by(Order.timestamp.desc()).all()
        
        if not pedidos:
            st.info("No tienes pedidos registrados.")
            return
        
        st.header("📄 Historial de Pedidos")
        
        for pedido in pedidos:
            with st.expander(f"Pedido #{pedido.idorders} - {pedido.timestamp.strftime('%Y-%m-%d %H:%M:%S')}", expanded=False):
                # Mostrar el estado del pedido con clase CSS
                status = pedido.status.lower()
                if status == "pendiente":
                    status_class = "status-pendiente"
                elif status == "aprobado":
                    status_class = "status-aprobado"
                elif status == "rechazado":
                    status_class = "status-rechazado"
                elif status == "cancelado":
                    status_class = "status-cancelado"
                else:
                    status_class = "status-unknown"
                
                st.markdown(f"**Estado:** <span class='{status_class}'>{pedido.status.capitalize()}</span>", unsafe_allow_html=True)
                st.markdown(f"**Total:** <div class='order-total'>${pedido.total:,.0f} CLP</div>", unsafe_allow_html=True)
                
                # Crear una tabla para los items del pedido
                contenido = "| Imagen | Producto | Cantidad | Precio Unitario (CLP) | Subtotal (CLP) |\n"
                contenido += "|---|---|---|---|---|\n"
                
                for item in pedido.order_items:
                    producto = item.producto.nombre if item.producto else "Desconocido"
                    cantidad = item.quantity
                    precio = item.unit_price
                    subtotal = cantidad * precio
                    imagen_url = item.producto.imagen if item.producto and item.producto.imagen else ""
                    if imagen_url:
                        imagen_html = f"<img src='{imagen_url}' alt='{producto}'>"
                    else:
                        imagen_html = "Sin imagen"
                    contenido += f"| {imagen_html} | {producto} | {cantidad} | ${precio:,.0f} | ${subtotal:,.0f} |\n"
                
                st.markdown(contenido, unsafe_allow_html=True)
                
                # Mostrar enlace a MercadoPago si el estado es pendiente
                if status == "pendiente" and pedido.preference_url:
                    st.markdown(f"**[Completar Pago en MercadoPago]({pedido.preference_url})**", unsafe_allow_html=True)
                
                # Botón para cancelar el pedido si está pendiente
                if status == "pendiente":
                    if st.button("Cancelar Pedido", key=f"cancelar_pedido_{pedido.idorders}"):
                        cancelar_pedido(pedido.idorders)
    except Exception as e:
        st.error(f"Ocurrió un error al cargar el historial de pedidos: {e}")
    finally:
        db.close()



def cancelar_pedido(order_id):
    db = SessionLocal()
    try:
        pedido = db.query(Order).filter(Order.idorders == order_id).first()
        if pedido:
            pedido.status = "cancelado"
            db.commit()
            st.success("Compra cancelada exitosamente. Gracias por utilizar nuestro sistema de ventas.")
            
            # Opcional: Manejar el reembolso si ya se procesó el pago
            # Aquí podrías integrar la lógica de reembolso con MercadoPago
        else:
            st.error("Pedido no encontrado.")
    except Exception as e:
        db.rollback()
        st.error(f"Error al cancelar el pedido: {e}")
    finally:
        db.close()

def generar_boleta(carrito, productos, order_id):
    if carrito:
        db = SessionLocal()
        contenido = "### 🧾 Boleta de Compra #{order_id}\n\n"
        contenido += "| Producto | Cantidad | Subtotal (CLP) | IVA (19%) (CLP) | Total (CLP) |\n"
        contenido += "|---|---|---|---|---|\n"
        subtotal_sin_iva = 0
        iva_total = 0
        total_con_iva = 0

        for nombre, detalle in carrito.items():
            producto = next((p for p in productos if p.nombre == nombre), None)
            if producto:
                cantidad = detalle['cantidad']
                precio_unitario = detalle['precio']
                subtotal_producto = (precio_unitario / 1.19) * cantidad
                iva_producto = subtotal_producto * 0.19
                total_producto = subtotal_producto + iva_producto
                subtotal_sin_iva += subtotal_producto
                iva_total += iva_producto
                total_con_iva += total_producto
                contenido += f"| {nombre} | {cantidad} | ${subtotal_producto:,.0f} | ${iva_producto:,.0f} | ${total_producto:,.0f} |\n"

        contenido += "\n"
        contenido += f"**Subtotal (sin IVA):** ${subtotal_sin_iva:,.0f} CLP\n\n"
        contenido += f"**IVA (19%)**: ${iva_total:,.0f} CLP\n\n"
        contenido += f"**Total:** ${total_con_iva:,.0f} CLP\n\n"

        db.close()
        return contenido, total_con_iva
    else:
        return "Tu carrito está vacío.", 0

def finalizar_pedido(productos):
    carrito = st.session_state.get('carrito', {})
    total = st.session_state.get('total_pedido', 0.0)
    if carrito:
        order_id = registrar_pedido(
            user_id=st.session_state.user_id,
            carrito=carrito,
            total=total
        )
        if order_id:
            # Crear preferencia de pago y obtener el enlace de MercadoPago
            init_point = crear_preferencia(order_id, total)
            
            # Generar la boleta
            boleta = generar_boleta(carrito, productos, order_id)
            st.session_state['boleta_generada'] = True
            st.session_state['boleta'] = boleta
            st.session_state['total_pedido'] = total
            st.session_state['mostrar_boton_pago'] = True
            
            # Mostrar la boleta
            st.markdown(boleta, unsafe_allow_html=True)
            
            # Botón para pagar con MercadoPago
            st.markdown(f"**[Pagar con MercadoPago]({init_point})**", unsafe_allow_html=True)
            
            # Botón para cancelar la compra
            if st.button("Cancelar Compra", key=f"cancelar_compra_{order_id}"):
                cancelar_pedido(order_id)
    else:
        st.warning("No hay productos en el carrito para finalizar el pedido.")

def mostrar_menu_interactivo(productos):
    with st.expander("🛒 Menú de Productos", expanded=True):
        # Agregar un campo de búsqueda para filtrar productos
        search_query = st.text_input("Buscar Producto", "")
        productos_filtrados = [p for p in productos if search_query.lower() in p.nombre.lower()]
        
        # Crear un encabezado para la tabla de productos
        header_cols = st.columns([2, 1, 2])  # Reducir columnas: Producto, Precio, Cantidad
        with header_cols[0]:
            st.markdown("**Producto**")
        with header_cols[1]:
            st.markdown("**Precio (CLP)**")
        with header_cols[2]:
            st.markdown("**Cantidad**")
        
        # Crear una tabla para mostrar los productos con la nueva estructura
        for producto in productos_filtrados:
            nombre = producto.nombre  # Cambiado de producto['nombre'] a producto.nombre
            precio = producto.precio  # Cambiado de producto['precio'] a producto.precio
            unidad = producto.unidad    # Cambiado de producto['unidad'] a producto.unidad
            stock = producto.stock      # Cambiado de producto['stock'] a producto.stock
            imagen = producto.imagen if producto.imagen else 'https://via.placeholder.com/100'
            key_cantidad = f"cantidad_{nombre}"

            # Crear una fila con 3 columnas: Producto, Precio, Input de Cantidad
            col1, col2, col3 = st.columns([2, 1, 2])
            
            with col1:
                st.markdown(f"### {nombre} ({unidad})")
                st.markdown(f"**** ${precio:,.0f} CLP")
                st.markdown(f"**Stock:** {stock} {unidad}(s)")
            
            with col2:
                st.image(imagen, width=80, use_container_width=True, clamp=True, channels="RGB", output_format="auto")
            
            with col3:
                # Input numérico para la cantidad
                cantidad = st.number_input(
                    label="",
                    min_value=0,
                    max_value=stock,
                    value=st.session_state.get(key_cantidad, 0),
                    step=1,
                    key=f"input_{nombre}"
                )
                st.session_state[key_cantidad] = cantidad  # Actualizar el estado
                # Actualizar el carrito automáticamente
                if cantidad > 0:
                    st.session_state.carrito[nombre] = {
                        'unidad': unidad,
                        'precio': precio,
                        'cantidad': cantidad
                    }
                else:
                    st.session_state.carrito.pop(nombre, None)
    
    # Calcular subtotal sin IVA
    subtotal = sum(
        (producto.precio / 1.19) * st.session_state.get(f"cantidad_{producto.nombre}", 0) 
        for producto in productos_filtrados
    )
    
    # Calcular IVA
    iva_total = subtotal * 0.19
    
    # Calcular total con IVA
    total_con_iva = subtotal + iva_total
    
    # Mostrar el subtotal y total
    st.markdown("---")
    st.write(f"**Subtotal** (sin IVA): ${subtotal:,.0f} CLP")
    st.write(f"**IVA (19%)**: ${iva_total:,.0f} CLP")
    st.write(f"**Total**: ${total_con_iva:,.0f} CLP")
    
    # Botón para generar boleta
    if st.button("Mostrar carrito"):
        if st.session_state.carrito:
            finalizar_pedido(productos)
        else:
            st.warning("No tienes productos en el carrito para generar una boleta.")


# Función para autenticar administrador y mostrar interfaz admin
def admin_login_page():
    st.header("Inicio de Sesión - Administrador")
    with st.form("admin_login_form"):
        admin_username = st.text_input("Nombre de Usuario", key="admin_username")
        admin_password = st.text_input("Contraseña", type="password", key="admin_password")
        submit_admin = st.form_submit_button("Iniciar Sesión Admin")
    
    if submit_admin:
        if not admin_username or not admin_password:
            st.error("Por favor, completa todos los campos.")
        else:
            # Autenticación de administrador
            if authenticate_admin(admin_username, admin_password):
                # Actualizar el estado de la sesión
                st.session_state.admin_authenticated = True
                
                st.success("Has iniciado sesión como administrador.")
                
                # Reiniciar el menú para forzar la actualización
                st.session_state.menu_key = f"menu_admin_{admin_username}"
            else:
                st.error("Credenciales incorrectas.")


def mostrar_pedidos():
    db = SessionLocal()
    pedidos = db.query(Order).order_by(Order.timestamp.desc()).all()
    
    if not pedidos:
        st.info("No hay pedidos registrados.")
        db.close()
        return
    
    contenido = "### 📄 Historial de Pedidos de Todos los Usuarios\n\n"
    contenido += "| ID Pedido | Usuario | Producto | Cantidad | Precio Unitario (CLP) | Fecha | Estado |\n"
    contenido += "|---|---|---|---|---|---|---|\n"
    
    for pedido in pedidos:
        usuario = db.query(User).filter(User.idusers == pedido.user_id).first()
        nombre_usuario = usuario.nameusers if usuario else "Desconocido"
        
        # Iterar sobre los OrderItems para obtener cada producto en el pedido
        for item in pedido.order_items:
            producto = item.producto.nombre if item.producto else "Desconocido"
            cantidad = item.cantidad
            precio = item.precio
            fecha = pedido.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            status = pedido.status.lower()
            
            # Asignar color basado en el estado
            if status == "pendiente":
                color = "orange"
            elif status == "aprobado":
                color = "green"
            elif status == "rechazado":
                color = "red"
            else:
                color = "black"
            
            # Formatear el estado con color
            estado_formateado = f"<span style='color:{color}'>{pedido.status.capitalize()}</span>"
            
            contenido += f"| {pedido.idorders} | {nombre_usuario} | {producto} | {cantidad} | ${precio:,.0f} | {fecha} | {estado_formateado} |\n"
    
    contenido += "\n<style>table {width: 100%;} th, td {padding: 8px 12px;}</style>"
    
    st.markdown(contenido, unsafe_allow_html=True)
    db.close()
# capstone.py

def registrar_pedido(user_id, carrito, total, payment_id=None):
    db = SessionLocal()
    try:
        # Crear una nueva orden con estado 'pendiente'
        new_order = Order(
            user_id=user_id,
            payment_id=payment_id,  # Inicialmente None o el ID proporcionado
            status="pendiente",
            total=total,
            timestamp=datetime.now(timezone.utc)
        )
        db.add(new_order)
        db.commit()
        db.refresh(new_order)
        order_id = new_order.idorders

        # Registrar cada ítem del carrito
        for nombre, detalle in carrito.items():
            producto = db.query(Producto).filter(Producto.nombre == nombre).first()
            if producto:
                # Verificar stock
                if producto.stock >= detalle['cantidad']:
                    producto.stock -= detalle['cantidad']
                    order_item = OrderItem(
                        order_id=order_id,
                        product_id=producto.idproductos,
                        quantity=detalle['cantidad'],
                        unit_price=detalle['precio']
                    )
                    db.add(order_item)
                else:
                    st.error(f"No hay suficiente stock para {nombre}.")
                    db.rollback()
                    return None
            else:
                st.error(f"Producto {nombre} no encontrado.")
                db.rollback()
                return None
        db.commit()
        return order_id
    except Exception as e:
        db.rollback()
        st.error(f"Error al registrar el pedido: {e}")
        return None
    finally:
        db.close()

    
def mostrar_estadisticas():
    db = SessionLocal()
    pedidos = db.query(Order).all()
    db.close()
    
    if not pedidos:
        st.info("No hay pedidos para generar estadísticas.")
        return
    
    total_ventas = sum(pedido.quantity * pedido.price for pedido in pedidos)
    productos = {}
    for pedido in pedidos:
        if pedido.product in productos:
            productos[pedido.product] += pedido.quantity
        else:
            productos[pedido.product] = pedido.quantity
    
    productos_df = pd.DataFrame(list(productos.items()), columns=['Producto', 'Cantidad Vendida'])
    productos_df = productos_df.sort_values(by='Cantidad Vendida', ascending=False)
    
    st.subheader("Estadísticas de Ventas")
    st.write(f"**Ventas Totales:** ${total_ventas:,.0f} CLP")
    st.write("**Productos Más Vendidos:**")
    st.dataframe(productos_df)

def cargar_productos():
    db = SessionLocal()
    try:
        productos = db.query(Producto).all()
        return productos
    except Exception as e:
        st.error(f"Error al cargar los productos desde la base de datos: {e}")
        return []
    finally:
        db.close()
        
def actualizar_stock(producto_nombre, cantidad_comprada):
    db = SessionLocal()
    try:
        producto = db.query(Producto).filter(Producto.nombre == producto_nombre).first()
        if producto:
            if producto.stock >= cantidad_comprada:
                producto.stock -= cantidad_comprada
                db.commit()
            else:
                st.error(f"No hay suficiente stock para {producto_nombre}.")
        else:
            st.error(f"Producto {producto_nombre} no encontrado.")
    except Exception as e:
        db.rollback()
        st.error(f"Error al actualizar el stock: {e}")
    finally:
        db.close()

def chatbot_page():
    productos = cargar_productos()
    st.header("Bienvenido a tu chatbot de venta de verduras")

    # Mensaje de bienvenida si es la primera vez
    if st.session_state.first_message:
        with st.chat_message("assistant"):
            welcome_message = "Hola, ¿Cómo puedo ayudarte hoy? Empieza escribiendo 'abrir menu'"
            st.markdown(welcome_message)
        st.session_state.messages.append({"role": "assistant", "content": welcome_message})
        st.session_state.first_message = False
    # Input del usuario
    if prompt := st.chat_input("Escribe tu mensaje aquí..."):
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Predicción de la intención
        intents_pred = predict_class(prompt)
        response = get_response(intents_pred, intents, prompt)
        
        # Manejar la respuesta
        if response == 'mostrar_menu':
            st.session_state.menu_mostrado = True
        elif response == 'consultar_historial':
            contenido = ver_historial_pedidos()
            with st.chat_message("assistant"):
                st.markdown(contenido, unsafe_allow_html=True)
            st.session_state.messages.append({"role": "assistant", "content": contenido})
        else:
            # Mostrar la respuesta normal
            with st.chat_message("assistant"):
                st.markdown(response, unsafe_allow_html=True)
            st.session_state.messages.append({"role": "assistant", "content": response})
    
    # Mostrar el menú si corresponde
    if st.session_state.get('menu_mostrado', False):
        mostrar_menu_interactivo(productos)
    
    # Mostrar el botón de "Pagar" si se ha generado una boleta
    if st.session_state.get('mostrar_boton_pago', False):
        if st.button("Pagar con MercadoPago"):
            # Crear la orden en la base de datos con estado 'pendiente'
            db = SessionLocal()
            try:
                new_order = Order(
                    user_id=st.session_state.user_id,
                    status="pendiente",
                    total=st.session_state.total_pedido
                )
                db.add(new_order)
                db.commit()
                db.refresh(new_order)
                order_id = new_order.idorders
            except Exception as e:
                db.rollback()
                st.error(f"Error al crear la orden: {e}")
                return
            finally:
                db.close()
            
            # Crear los items para MercadoPago
            items = []
            for nombre, detalle in st.session_state.carrito.items():
                items.append({
                    "title": nombre,
                    "quantity": detalle['cantidad'],
                    "currency_id": "CLP",
                    "unit_price": detalle['precio']
                })
            
            # Crear preferencia de pago
            init_point = crear_preferencia(order_id, st.session_state.user_id, items, st.session_state.total_pedido)
            
            # Redirigir al usuario al checkout
            st.success("Redirigiendo a MercadoPago...")
            st.markdown(f"[Pagar Ahora]({init_point})", unsafe_allow_html=True)
            
            # Limpiar el carrito y otras variables
            st.session_state.carrito = {}
            st.session_state.boleta_generada = False
            st.session_state.mostrar_boton_pago = False

def admin_page():
    st.header("Panel de Administración")
    selected = option_menu(
        menu_title="Administrar",
        options=["Ver Pedidos", "Estadísticas"],
        icons=["cart", "bar-chart"],
        menu_icon="tools",
        default_index=0,
        orientation="horizontal",
        styles={
            "container": {"padding": "5!important", "background-color": "#fafafa"},
            "icon": {"color": "#2C3E50", "font-size": "18px"}, 
            "nav-link": {"font-size": "16px", "text-align": "left", "margin":"0px", "--hover-color": "#eee"},
            "nav-link-selected": {"background-color": "#2C3E50"},
        },
        key="admin_inner_menu"  # Clave única para el menú interno del admin
    )
    
    if selected == "Ver Pedidos":
        mostrar_pedidos()
    elif selected == "Estadísticas":
        mostrar_estadisticas()

def main():
    local_css("styles.css")

    st.title("Asistente Virtual - Venta de Verduras 🥦🥕")
    
    # Inicializar las variables de sesión
    initialize_session()
    
    # Definir el menú en la sidebar
    selected = sidebar_menu()
    
    # Manejar las opciones seleccionadas del menú
    if st.session_state.admin_authenticated:
        if selected == "Ver Pedidos":
            st.session_state.page = 'admin_ver_pedidos'
        elif selected == "Estadísticas":
            st.session_state.page = 'admin_estadisticas'
        elif selected == "Cerrar Sesión Admin":
            st.session_state.admin_authenticated = False
            st.session_state.page = 'login'
    elif st.session_state.logged_in:
        
        if selected == "Chatbot":
            st.session_state.page = 'chatbot'
        elif selected == "Mis Pedidos":
            st.session_state.page = 'mis_pedidos'
        elif selected == "Cerrar Sesión":
            st.session_state.logged_in = False
            st.session_state.user_id = None
            st.session_state.messages = []
            st.session_state.carrito = {}
            st.session_state.boleta_generada = False
            st.session_state.menu_mostrado = False
            st.session_state.first_message = True
            st.session_state.page = 'login'
    else:
        if selected == "Iniciar Sesión":
            st.session_state.page = 'login'
        elif selected == "Registrarse":
            st.session_state.page = 'register'
        elif selected == "Acceder como Admin":
            st.session_state.page = 'admin_login'
    
    # Mostrar la página correspondiente
    if st.session_state.page == 'login':
        login_page()
    elif st.session_state.page == 'register':
        register_page()
    elif st.session_state.page == 'admin_login':
        admin_login_page()
    elif st.session_state.page == 'chatbot':
        
        if st.session_state.logged_in and not st.session_state.admin_authenticated:
            chatbot_page()
        else:
            st.warning("Por favor, inicia sesión para acceder al chatbot.")
    elif st.session_state.page == 'mis_pedidos':
        if st.session_state.logged_in and not st.session_state.admin_authenticated:
            contenido = ver_historial_pedidos()
            st.markdown(contenido, unsafe_allow_html=True)
        else:
            st.warning("Por favor, inicia sesión para ver tus pedidos.")
    elif st.session_state.page == 'admin_ver_pedidos':
        if st.session_state.admin_authenticated:
            mostrar_pedidos()
        else:
            st.warning("Acceso denegado.")
    elif st.session_state.page == 'admin_estadisticas':
        if st.session_state.admin_authenticated:
            mostrar_estadisticas()
        else:
            st.warning("Acceso denegado.")
    elif st.session_state.page == 'admin':
        admin_page()
    else:
        st.warning("Página no encontrada.")
def historial_mensajes_page():
    st.header("Historial de Mensajes")
    
    db = SessionLocal()
    try:
        # Obtener todos los mensajes del usuario
        mensajes = db.query(Message).filter(Message.user_id == st.session_state.user_id).order_by(Message.timestamp.desc()).all()
        
        if not mensajes:
            st.info("No tienes mensajes en tu historial.")
            return
        
        # Agrupar mensajes por fecha
        mensajes_por_fecha = {}
        for msg in mensajes:
            fecha = msg.timestamp.date()
            if fecha not in mensajes_por_fecha:
                mensajes_por_fecha[fecha] = []
            mensajes_por_fecha[fecha].append(msg)
        
        # Listar las fechas disponibles
        fechas_disponibles = sorted(mensajes_por_fecha.keys(), reverse=True)
        
        # Seleccionar una fecha para ver los mensajes
        selected_date = st.selectbox("Selecciona una fecha para ver los mensajes:", fechas_disponibles, format_func=lambda x: x.strftime("%d/%m/%Y"))
        
        st.markdown(f"### Conversaciones del **{selected_date.strftime('%d/%m/%Y')}**")
        
        # Mostrar los mensajes de la fecha seleccionada
        for msg in mensajes_por_fecha[selected_date]:
            with st.chat_message("user" if msg.sender == "user" else "assistant"):
                st.markdown(msg.content, unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Ocurrió un error al cargar el historial de mensajes: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    main()

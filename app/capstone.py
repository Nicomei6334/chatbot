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
from database import SessionLocal, User, Order, init_db, Producto, OrderItem,Feedback
import os
import re
import time
from dotenv import load_dotenv
from datetime import datetime, timezone
import pandas as pd
from admin import authenticate_admin, mostrar_pedidos, mostrar_estadisticas, gestionar_productos, admin_ver_feedback
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
ADMIN_USERNAME = st.secrets["admin"]["user"]
ADMIN_PASSWORD = st.secrets["admin"]["pass"]

def validar_dominio(email):
    dominios_permitidos = ['gmail.com', 'outlook.com', 'hotmail.com']
    dominio = email.split('@')[-1]
    if dominio in dominios_permitidos or re.match(r".+\.(edu|org|gov)$", dominio):
        return True
    return False
        
def initialize_session():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "admin_authenticated" not in st.session_state:
        st.session_state.admin_authenticated = False
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
    if 'total_pedido' not in st.session_state:
        st.session_state.total_pedido = 0
    if 'mostrar_boton_pago' not in st.session_state:
        st.session_state.mostrar_boton_pago = False
    if 'user_id' not in st.session_state:
        st.session_state.user_id = obtener_user_id()  # Inicializa a None si no está logueado
    if 'ultimo_pedido_aprobado' not in st.session_state:
        st.session_state.ultimo_pedido_aprobado = False

    if "login_attempts" not in st.session_state:
        st.session_state.login_attempts = {}

def sidebar_menu():
    # Generar una clave única basada en el estado de la sesión para forzar la actualización del menú
    if st.session_state.admin_authenticated:
        menu_key = "menu_admin"
        options = ["Ver Pedidos", "Estadísticas", "Gestionar Productos","Ver feedbacks", "Cerrar Sesión Admin"]
        icons = ["cart", "bar-chart", "box-arrow-right"]
        menu_title = "Administrador"
    elif st.session_state.logged_in:
        menu_key = "menu_user"
        options = ["Chatbot", "Historial Mensajes(PROXIMAMENTE)", "Mis Pedidos","Danos tu feedback", "Cerrar Sesión"]
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

def register_page():
    st.header("Registro de Usuario")
    with st.form("register_form"):
        first_name = st.text_input("Nombre", key="register_first_name")
        last_name = st.text_input("Apellido", key="register_last_name")
        phone = st.text_input("Teléfono", key="register_phone")
        email = st.text_input("Correo Electrónico", key="register_user_email")
        password = st.text_input("Contraseña", type="password", key="register_password")
        confirm_password = st.text_input("Confirmar Contraseña", type="password", key="register_confirm_password")
        submit = st.form_submit_button("Registrarse")
     
        if submit:
            # Validar los campos del formulario
            if not first_name or not last_name or not email or not password or not confirm_password:
                st.error("Por favor, completa todos los campos requeridos.")
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
                        new_user = User(
                            first_name=first_name,
                            last_name=last_name,
                            phone=phone,
                            email=email,
                            password=hashed_password.decode('utf-8')
                        )
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
                  
                        
                        st.success("Registro exitoso. Ahora puedes acceder al chatbot.")
                        # Reiniciar el menú para forzar la actualización
                        st.session_state.menu_key = f"menu_user_{st.session_state.user_id}"
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
                    producto = item.producto
                    if producto:
                        nombre_producto = producto.nombre
                        cantidad = item.quantity
                        precio = item.unit_price
                        subtotal = cantidad * precio
                        imagen_url = producto.imagen if producto.imagen else 'https://via.placeholder.com/100'
                        imagen_html = f"<img src='{imagen_url}' alt='{nombre_producto}' width='50'>"
                        contenido += f"| {imagen_html} | {nombre_producto} | {cantidad} | ${precio:,.0f} | ${subtotal:,.0f} |\n"
                    else:
                        contenido += f"| Sin imagen | Desconocido | {item.quantity} | ${item.unit_price:,.0f} | ${item.quantity * item.unit_price:,.0f} |\n"
                
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
def verificar_estado_pedidos():
    db = SessionLocal()
    try:
        # Obtener los pedidos del usuario con estado 'aprobado' recientes
        pedido_aprobado = db.query(Order).filter(
            Order.user_id == st.session_state.user_id,
            Order.status == "aprobado"
        ).order_by(Order.timestamp.desc()).first()

        if pedido_aprobado and not st.session_state.get('ultimo_pedido_aprobado', False):
            st.session_state['ultimo_pedido_aprobado'] = True
    except Exception as e:
        st.error(f"Error al verificar el estado de los pedidos: {e}")
    finally:
        db.close()
def obtener_user_id():
  return 1
    
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
        contenido = f"### 🧾 Boleta de Compra #{order_id}\n\n"
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

        contenido += f"\n**Subtotal (sin IVA):** ${subtotal_sin_iva:,.0f} CLP\n\n"
        contenido += f"**IVA (19%):** ${iva_total:,.0f} CLP\n\n"
        contenido += f"**Total:** ${total_con_iva:,.0f} CLP\n\n"
        return contenido, total_con_iva
    else:
        return "Tu carrito está vacío.", 0

def finalizar_pedido(productos):
    carrito = st.session_state.get('carrito', {})
    total_cents = int(st.session_state.get('total_pedido', 0))  # Asegurarse de que es entero

    if carrito:
        db = SessionLocal()
        try:
            # Crear la orden en la base de datos con estado 'pendiente'
            new_order = Order(
                user_id=st.session_state.user_id,
                status="pendiente",
                total=total_cents  # Almacenado en centavos
            )
            db.add(new_order)
            db.commit()
            db.refresh(new_order)
            order_id = new_order.idorders

            # Almacenar el order_id en la sesión para poder cancelarlo desde el chatbot
            st.session_state['current_order_id'] = order_id

            # Crear los items para MercadoPago y OrderItems en la base de datos
            items = []
            for nombre, detalle in st.session_state.carrito.items():
                nombre_limpio = nombre.strip()
                producto = db.query(Producto).filter(Producto.nombre == nombre_limpio).first()
                if producto:
                    # Verificar stock
                    if producto.stock >= detalle['cantidad']:
                        producto.stock -= detalle['cantidad']
                        # Crear OrderItem
                        order_item = OrderItem(
                            order_id=order_id,
                            product_id=producto.idproductos,
                            quantity=detalle['cantidad'],
                            unit_price=int(detalle['precio'])  # Asegurar que es entero
                        )
                        db.add(order_item)
                        # Preparar los items para MercadoPago
                        items.append({
                            "title": nombre_limpio,  # Usar nombre limpio
                            "quantity": detalle['cantidad'],
                            "currency_id": "CLP",
                            "unit_price": int(detalle['precio'])  # Convertir a entero (CLP)
                        })
                    else:
                        st.error(f"No hay suficiente stock para '{nombre_limpio}'.")
                        db.rollback()
                        return
                else:
                    st.error(f"Producto '{nombre_limpio}' no encontrado.")
                    db.rollback()
                    return

            db.commit()  # Confirmar cambios de stock y OrderItems

            # Crear preferencia de pago en MercadoPago
            init_point = crear_preferencia(order_id, items)

            if not init_point:
                st.error("No se pudo crear la preferencia de pago.")
                return

            # Generar la boleta
            boleta, _ = generar_boleta(carrito, productos, order_id)
            st.session_state['boleta_generada'] = True
            st.session_state['boleta'] = boleta
            st.session_state['mostrar_boton_pago'] = True

            # Mostrar la boleta
            st.markdown(boleta, unsafe_allow_html=True)

            # Mostrar el enlace de pago directamente en la boleta
            st.markdown(f"[**Pagar Ahora en MercadoPago**]({init_point})", unsafe_allow_html=True)

            # Opcional: Botón para Modificar Pedido
            st.markdown("---")
            st.write("### Opciones:")
            
            if st.button("Modificar Pedido"):
                st.session_state.carrito = {}
                st.session_state.total_pedido = 0
                st.session_state.menu_mostrado = True
                st.success("Puedes modificar tu pedido seleccionando los productos nuevamente.")

            # Mensaje para cancelar via chatbot
            st.write("Si deseas cancelar tu pedido, por favor escribe 'salir' al chatbot.")

        except Exception as e:
            db.rollback()
            st.error(f"Error al finalizar el pedido: {e}")
            logger.error(f"Error al finalizar el pedido: {e}")
            return
        finally:
            db.close()
    else:
        st.warning("No hay productos en el carrito para finalizar el pedido.")
            
def mostrar_menu_interactivo(productos):
    productos = sorted(productos, key=lambda p: p.idproductos)
    # CSS para permitir scroll vertical dentro del expander (opcional)
    st.markdown("""
        <style>
        .menu-expander > div:nth-child(1) {
            max-height: 600px;
            overflow-y: auto;
        }
        </style>
    """, unsafe_allow_html=True)

    with st.expander("🛒 Menú de Productos", expanded=True):
        # Añadir una clase al contenedor del expander para el CSS
        st.markdown('<div class="menu-expander">', unsafe_allow_html=True)

        # Campo de búsqueda
        search_query = st.text_input("Buscar Producto", "")
        productos_filtrados = [p for p in productos if search_query.lower() in p.nombre.lower()]

        # Definir el número de columnas (ejemplo: 4 columnas por fila)
        num_columnas = 4

        # Dividir la lista de productos en filas de num_columnas
        for i in range(0, len(productos_filtrados), num_columnas):
            fila_productos = productos_filtrados[i:i+num_columnas]
            cols = st.columns(num_columnas)

            for col, producto in zip(cols, fila_productos):
                nombre = producto.nombre
                precio = producto.precio
                unidad = producto.unidad
                stock = producto.stock
                # URL de imagen por defecto si no hay imagen
                imagen = producto.imagen if producto.imagen else 'https://via.placeholder.com/100'

                key_cantidad = f"cantidad_{nombre}"

                with col:
                    # Mostrar imagen con un ancho fijo para evitar tamaños inconsistentes
                    st.image(imagen, width=150, use_container_width=False)
                    st.markdown(f"**{nombre}**")
                    st.markdown(f"Precio: ${precio:,.0f} CLP")
                    st.markdown(f"Stock: {stock} {unidad}(s)")

                    # Input para la cantidad
                    cantidad = st.number_input(
                        label="Cantidad",
                        min_value=0,
                        max_value=stock,
                        value=st.session_state.get(key_cantidad, 0),
                        step=1,
                        key=f"input_{nombre}"
                    )
                    st.session_state[key_cantidad] = cantidad

                    # Actualizar el carrito
                    if cantidad > 0:
                        st.session_state.carrito[nombre] = {
                            'unidad': unidad,
                            'precio': precio,
                            'cantidad': cantidad
                        }
                    else:
                        st.session_state.carrito.pop(nombre, None)

        st.markdown('</div>', unsafe_allow_html=True)

    # Calcular subtotal sin IVA, IVA y total con IVA
    subtotal = sum(
        (producto.precio / 1.19) * st.session_state.get(f"cantidad_{producto.nombre}", 0)
        for producto in productos_filtrados
    )

    iva_total = subtotal * 0.19
    total_con_iva = subtotal + iva_total

    # Guardar el total en el estado de la sesión
    st.session_state['total_pedido'] = total_con_iva

    # Mostrar el subtotal, IVA y total
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
    
def mostrar_feedback():
    st.header("Tu opinión es importante para nosotros") 

    opciones_satisfaccion = ["Muy Satisfecho", "Satisfecho", "Neutral", "Insatisfecho", "Muy Insatisfecho"]
    satisfaccion_map = {op: i+1 for i, op in enumerate(opciones_satisfaccion)}
    st.subheader("Sección 1: Satisfacción general del servicio")
    rating_amigable_resp = st.radio("¿El sistema lo considera amigable a su uso?", opciones_satisfaccion)
    rating_rapidez_resp = st.radio("¿Considera el sistema rapido?", opciones_satisfaccion)
    st.subheader("Sección 2: ¿Utilizarías nuestro servicio al cliente en el futuro?")
    future_use_resp = st.radio("Seleccione una de las 3 opciones", ["Sí", "No", "Tal vez"])
    st.subheader("Sección 3: ¿Cómo podemos mejorar nuestro servicio?")
    comment_resp = st.text_area("Escribe tu opinión")
        
    if st.button("Enviar"):
            db = SessionLocal()
            try:
                new_feedback = Feedback(
                    rating_amigable=satisfaccion_map[rating_amigable_resp],
                    rating_rapidez=satisfaccion_map[rating_rapidez_resp],
                    future_use=future_use_resp,
                    comment=comment_resp
                    )
                db.add(new_feedback)
                db.commit()
                st.success("¡Gracias por tu retroalimentación!")
            except Exception as e:
                db.rollback()
                st.error(f"Ocurrió un error: {e}")
            finally:
                db.close()

def admin_page():
    st.header("🛡️Panel de Administración🛠️")
    selected = option_menu(
        menu_title="Administrar",
        options=["Ver Pedidos", "Estadísticas","Gestionar Pedidos"],
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
    elif selected == "Gestionar Productos":
        gestionar_productos()

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
        elif selected== "Gestionar Productos":
            st.session_state.page= 'gestionar_productos'
        elif selected == "Ver feedbacks":
            st.session_state.page= 'adm_feedbacks'
        elif selected == "Cerrar Sesión Admin":
            st.session_state.admin_authenticated = False
            st.session_state.page = 'login'
  
    elif st.session_state.logged_in:
        if selected == "Chatbot":
            st.session_state.page = 'chatbot'
        elif selected == "Mis Pedidos":
            st.session_state.page = 'mis_pedidos'
        elif selected == "Danos tu feedback":
            st.session_state.page = 'feedback'
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
            
    elif st.session_state.page== 'feedback':
        if st.session_state.logged_in and not st.session_state.admin_authenticated:
            contenido = mostrar_feedback()
            st.markdown(contenido, unsafe_allow_html=True)
        else:
            st.warning("Por favor, inicia sesión poder ingresar tu feedback.")
        
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
    elif st.session_state.page == 'gestionar_productos':  
        if st.session_state.admin_authenticated:
            gestionar_productos()
        else:
            st.warning("Acceso denegado.")
            
    elif st.session_state.page == 'admin':
        if st.session_state.admin_authenticated:
            admin_page()
        else:
            st.warning("Acceso denegado.")
        
    elif st.session_state.page == 'adm_feedbacks':
        if st.session_state.admin_authenticated:
            admin_ver_feedback()
        else:
            st.warning("Acceso denegado.")
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

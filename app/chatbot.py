# chatbot.py
import random
import json
import pickle
import numpy as np
import nltk
from nltk.stem import WordNetLemmatizer
from tensorflow.keras.models import load_model
from fuzzywuzzy import process
import re
import streamlit as st
from database import SessionLocal, Order
from dotenv import load_dotenv
import os


# Obtener la ruta absoluta al directorio 'data'
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # Directorio raíz del proyecto
DATA_DIR = os.path.join(BASE_DIR, 'data')

# Obtener la ruta absoluta al archivo intents_capstone.json
script_dir = os.path.dirname(__file__)  # Directorio actual del script
intents_path = os.path.join(script_dir, '..', 'data', 'intents_capstone.json')

with open(intents_path, 'r', encoding='utf-8') as f:
    intents = json.load(f)

# Cargar las variables de entorno
load_dotenv(os.path.join(BASE_DIR, '.env'))


def local_css(file_name):
    css_path = os.path.join(BASE_DIR, 'styles', file_name)
    if os.path.exists(css_path):
        with open(css_path) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    else:
        st.warning(f"El archivo CSS {file_name} no se encontró.")

# Cargar el archivo CSS al inicio
local_css("styles.css")

# Cargar recursos
lemmatizer = WordNetLemmatizer()

words_path = os.path.join(DATA_DIR, 'words.pkl')
classes_path = os.path.join(DATA_DIR, 'classes.pkl')
model_path = os.path.join(DATA_DIR, 'chatbot_model.h5')

with open(words_path, 'rb') as f:
    words = pickle.load(f)

with open(classes_path, 'rb') as f:
    classes = pickle.load(f)

model = load_model(model_path)

# Cargar la lista de productos desde la base de datos
def cargar_productos_db():
    db = SessionLocal()
    try:
        productos = db.query(Producto).all()
        productos_dict = {p.nombre: p for p in productos}
        return productos_dict
    except Exception as e:
        st.error(f"Error al cargar los productos desde la base de datos: {e}")
        return {}
    finally:
        db.close()


def inicializar_carrito():
    if 'carrito' not in st.session_state:
        st.session_state.carrito = {}

def encontrar_producto(nombre_producto):
    nombres_productos = [producto['nombre'] for producto in productos]
    nombre_producto = nombre_producto.lower()
    nombres_productos_lower = [p.lower() for p in nombres_productos]
    coincidencia, puntuacion = process.extractOne(nombre_producto, nombres_productos_lower)
    if puntuacion >= 80:
        # Retornar el producto completo
        indice = nombres_productos_lower.index(coincidencia)
        return productos[indice]
    else:
        return None

def agregar_producto_carrito(nombre_producto, cantidad):
    producto = encontrar_producto(nombre_producto)
    if producto:
        nombre = producto['nombre']
        unidad = producto['unidad']
        if nombre in st.session_state.carrito:
            st.session_state.carrito[nombre]['cantidad'] += cantidad
        else:
            st.session_state.carrito[nombre] = {
                'unidad': unidad,
                'precio': producto['precio'],
                'cantidad': cantidad
            }
        key_cantidad = f"cantidad_{nombre}"
        st.session_state[key_cantidad] = st.session_state.carrito[nombre]['cantidad']
        return f"He añadido {cantidad} {unidad} de {nombre} a tu carrito."
    else:
        return "Producto no reconocido. Por favor, intenta de nuevo."

def eliminar_producto_carrito(nombre_producto):
    producto = encontrar_producto(nombre_producto)
    if producto:
        nombre = producto['nombre']
        if nombre in st.session_state.carrito:
            del st.session_state.carrito[nombre]
            return f"He eliminado {nombre} de tu carrito."
        else:
            return f"{nombre} no está en tu carrito."
    else:
        return "Producto no reconocido. Por favor, intenta de nuevo."

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
        
def ver_carrito():
    if st.session_state.carrito:
        contenido = ""
        contenido += "| Producto | Cantidad | Unidad | Subtotal (CLP) | IVA (19%) (CLP) | Total (CLP) |\n"
        contenido += "|---|---|---|---|---|---|\n"
        subtotal_sin_iva = 0
        iva_total = 0
        total_con_iva = 0
        for nombre, detalle in st.session_state.carrito.items():
            cantidad = detalle['cantidad']
            unidad = detalle['unidad']
            precio_unitario = detalle['precio']
            # Calcular subtotal sin IVA por producto
            subtotal_producto = (precio_unitario / 1.19) * cantidad
            # Calcular IVA del producto
            iva_producto = subtotal_producto * 0.19
            # Calcular total del producto
            total_producto = subtotal_producto + iva_producto
            subtotal_sin_iva += subtotal_producto
            iva_total += iva_producto
            total_con_iva += total_producto
            # Agregar la fila a la tabla
            contenido += f"| {nombre} | {cantidad} | {unidad} | ${subtotal_producto:,.0f} | ${iva_producto:,.0f} | ${total_producto:,.0f} |\n"
        
        # Agregar los totales al carrito
        contenido += "\n"
        contenido += f"**Subtotal (sin IVA):** ${subtotal_sin_iva:,.0f} CLP\n\n"
        contenido += f"**IVA (19%):** ${iva_total:,.0f} CLP\n\n"
        contenido += f"**Total:** ${total_con_iva:,.0f} CLP\n"
        return contenido
    else:
        return "Tu carrito está vacío."


def calcular_total():
    total = 0
    for detalle in st.session_state.carrito.values():
        total += detalle['cantidad'] * detalle['precio']
    iva = total * 0.19
    total_con_iva = total + iva
    return total_con_iva

def clean_up_sentence(sentence):
    sentence_words = nltk.word_tokenize(sentence)
    sentence_words = [lemmatizer.lemmatize(word.lower()) for word in sentence_words]
    return sentence_words

def bag_of_words(sentence):
    sentence_words = clean_up_sentence(sentence)
    bag = [0] * len(words)
    for w in sentence_words:
        for i, word in enumerate(words):
            if word == w:
                bag[i] = 1
    return np.array(bag)

def predict_class(sentence):
    bow = bag_of_words(sentence)
    res = model.predict(np.array([bow]))[0]
    ERROR_THRESHOLD = 0.25
    results = [[i, r] for i, r in enumerate(res) if r > ERROR_THRESHOLD]
    results.sort(key=lambda x: x[1], reverse=True)
    return_list = []
    for r in results:
        return_list.append({'intent': classes[r[0]], 'probability': str(r[1])})
    return return_list

def get_response(intents_list, intents_json, message):
    inicializar_carrito()
    if not intents_list:
        # No se detectó ninguna intención con suficiente confianza
        for intent in intents_json['intents']:
            if intent['tag'] == 'error':
                return random.choice(intent['responses'])
        # Si no existe una intención 'error', devuelve un mensaje genérico
        return "Lo siento, no entendí tu solicitud. ¿Podrías reformularla?"
    
    tag = intents_list[0]['intent']
    list_of_intents = intents_json['intents']
    
    for i in list_of_intents:
        if i['tag'] == tag:
            if tag == 'ver_productos':
                # Mostrar lista de productos
                lista_productos = ', '.join([p['nombre'] for p in productos])
                result = i['responses'][0].replace('[lista_productos]', lista_productos)
            elif tag == 'mostrar_menu':
                # Indicar que se debe mostrar el menú interactivo
                result = 'mostrar_menu'
            elif tag == 'agregar_carrito':
                # Extraer el producto y cantidad del mensaje usando regex
                pattern = r"(?i)(?:comprar|añadir|agregar|necesito|quiero)\s*(?:(\d+)\s*)?(kg|unidad|paquete)?\s*(?:de\s*)?(.*)"
                matches = re.findall(pattern, message)
                if matches:
                    cantidad_str, unidad, nombre_producto = matches[0]
                    cantidad = int(cantidad_str) if cantidad_str else 1
                    if not unidad:
                        # Determinar la unidad según el producto
                        producto = encontrar_producto(nombre_producto)
                        if producto:
                            unidad = producto['unidad']
                        else:
                            unidad = ''
                    nombre_producto = nombre_producto.strip()
                    respuesta = agregar_producto_carrito(nombre_producto, cantidad)
                    result = respuesta
                else:
                    result = "Por favor, especifica el producto y la cantidad que deseas agregar."
            elif tag == 'eliminar_carrito':
                # Extraer el nombre del producto
                pattern = r"(?i)(?:eliminar|quitar|remover|sacar|elimina|puedes eliminar)\s*(?:del\s*carrito\s*)?(.*)"
                matches = re.findall(pattern, message)
                if matches:
                    nombre_producto = matches[0].strip()
                    respuesta = eliminar_producto_carrito(nombre_producto)
                    result = respuesta
                else:
                    result = "Por favor, indica el producto que deseas eliminar."
            elif tag == 'consultar_carrito':
                contenido = ver_carrito()
                result = contenido
            elif tag == 'realizar_compra':
                if st.session_state.logged_in:
                    total = calcular_total()
                    result = i['responses'][0].replace('{total}', f"{total:,.0f}")
                else:
                    result = "Por favor, inicia sesión para realizar una compra."
            elif tag == 'confirmar_pago':
                if st.session_state.logged_in:
                    # Generar boleta y preparar botón de Finalizar Compra
                    boleta = generar_boleta()
                    result = boleta
                    st.session_state.carrito = {}  # Vaciar el carrito después de confirmar pago
                    st.session_state.boleta_generada = True  # Indicador para mostrar el botón
                else:
                    result = "Por favor, inicia sesión para confirmar el pago."
            elif tag == 'consultar_historial':
                if st.session_state.logged_in:
                    contenido = ver_historial_pedidos()
                    result = contenido
                else:
                    result = "Por favor, inicia sesión para consultar tu historial de pedidos."
            elif tag == 'cancelar':
                result = random.choice(i['responses'])
                # Ocultar el menú al cancelar
                st.session_state.menu_mostrado = False
            else:
                result = random.choice(i['responses'])
            break
    else:
        # Si no se encuentra la intención, usar 'error'
        for intent in list_of_intents:
            if intent['tag'] == 'error':
                result = random.choice(intent['responses'])
                break
        else:
            result = "Lo siento, no entendí tu solicitud. ¿Podrías reformularla?"
    
    return result 

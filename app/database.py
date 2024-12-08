# app/database.py
from sqlalchemy import Column, Integer, String, ForeignKey, Float, DateTime, Text
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv
from datetime import datetime
import streamlit as st

# Cargar variables de entorno
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, '.env'))
DATABASE_URL = st.secrets["connections.supabase"]["SUPABASE_URL"]

try:
    # Crear motor de base de datos
    engine = create_engine(DATABASE_URL, echo=True)
    connection = engine.connect()
    print("Conexión exitosa a la base de datos.")
    connection.close()
except Exception as e:
    print(f"Error al conectar a la base de datos: {e}")

# Crear una fábrica de sesiones
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Declarative base
Base = declarative_base()

## Tabla Users
class User(Base):
    __tablename__ = "users"
    idusers = Column(Integer, primary_key=True, index=True)
    first_name = Column(String, nullable=False)    # Nuevo campo
    last_name = Column(String, nullable=False)     # Nuevo campo
    phone = Column(String, nullable=True) 
    email = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


    ## relationships
    orders = relationship("Order", back_populates="user")
    messages = relationship("Message", back_populates="user")
    context = relationship("Context", back_populates="user")



## Tabla Orders
class Order(Base):
    __tablename__ = "orders"
    idorders = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.idusers"), nullable=False)
    payment_id = Column(String, unique=True, index=True, nullable=True)  # ID de pago de MercadoPago
    status = Column(String, default="pendiente")  # pendiente, aprobado, rechazado
    total = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    preference_url = Column(String, nullable=True)  # Nueva columna para almacenar el enlace de pago

    
    ## relationships
    user = relationship("User", back_populates="orders")
    order_items = relationship("OrderItem", back_populates="order")


## Tabla OrderItems
class OrderItem(Base):
    __tablename__ = "order_items"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.idorders"), nullable=False)
    product_id = Column(Integer, ForeignKey("productos.idproductos"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)

    ## relationships
    order = relationship("Order", back_populates="order_items")
    producto = relationship("Producto", back_populates="order_items")


## Tabla Producto
class Producto(Base):
    __tablename__ = "productos"
    idproductos = Column(Integer, primary_key=True, index=True,autoincrement=True)
    nombre = Column(String(255), unique=True, nullable=False)
    unidad = Column(String(50), nullable=False)
    precio = Column(Float, nullable=False)
    stock = Column(Integer, nullable=False)
    imagen = Column(String, nullable=True)

    ## relationships
    order_items = relationship("OrderItem", back_populates="producto")


## Tabla Messages
class Message(Base):
    __tablename__ = "messages"
    idmessages = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.idusers"), nullable=False)
    content = Column(Text, nullable=False)
    sender = Column(String(50), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    ## relationships
    user = relationship("User", back_populates="messages")


## Tabla Intent
class Intent(Base):
    __tablename__ = "intents"
    idintents = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False)
    description = Column(Text)

    ## relationships
    responses = relationship("Response", back_populates="intent")
    contexts = relationship("Context", back_populates="intent")


## Tabla Responses
class Response(Base):
    __tablename__ = "responses"
    idresponses = Column(Integer, primary_key=True, index=True)
    intent_id = Column(Integer, ForeignKey("intents.idintents"), nullable=False)
    response = Column(Text, nullable=False)

    ## relationships
    intent = relationship("Intent", back_populates="responses")


## Tabla Feedback
class Feedback(Base):
    __tablename__ = "feedback"
    idfeedback = Column(Integer, primary_key=True, index=True)
    rating_amigable = Column(Integer, nullable=True)
    rating_rapidez = Column(Integer, nullable=True)
    future_use = Column(String(50), nullable=True)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

## Tabla Context
class Context(Base):
    __tablename__ = "context"
    idcontext = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.idusers"), nullable=False)
    current_intent_id = Column(Integer, ForeignKey("intents.idintents"), nullable=False)
    update_at = Column(DateTime, default=datetime.utcnow)

    ## relationships
    user = relationship("User", back_populates="context")
    intent = relationship("Intent", back_populates="contexts")


## Crear Tablas
def init_db():
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    init_db()
    print("Base de datos inicializada con éxito.")

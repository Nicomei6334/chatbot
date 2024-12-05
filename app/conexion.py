
from dotenv import load_dotenv
import os
# Cargar variables de entorno
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
print(f"URL: {DATABASE_URL}")

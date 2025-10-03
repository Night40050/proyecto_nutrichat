import os
import sys
from dotenv import load_dotenv

# Agregar el directorio actual al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Cargar variables de entorno
load_dotenv()

# Importar y ejecutar el bot
from app.bot.telegram_bot import run_bot

if __name__ == "__main__":
    print("Iniciando NutriChat Bot...")
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if token:
        print(f"Token configurado: {token[:10]}...")
        run_bot()
    else:
        print("ERROR: No se encontró el token TELEGRAM_BOT_TOKEN en el archivo .env")
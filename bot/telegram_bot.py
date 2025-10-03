import os
import re
import logging
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ConversationHandler, ContextTypes, filters
import httpx
import json

# Configurar logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Cargar variables de entorno
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:5000/api")
API_KEY = os.getenv("API_KEY", "")

# Estados para conversaciones
REGISTER_EMAIL, REGISTER_PASSWORD, REGISTER_NAME = range(3)

class APIClient:
    """Cliente para comunicarse con la API Flask"""
    
    def __init__(self, base_url: str, api_key: str = ""):
        self.base_url = base_url
        self.api_key = api_key
        self.headers = {"Content-Type": "application/json"}
        if api_key:
            self.headers["X-API-Key"] = api_key
    
    async def create_user(self, user_data: dict):
        """Crear usuario via API"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}/users/register",
                    json=user_data,
                    headers=self.headers,
                    timeout=10.0
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"Error API create_user: {e}")
                return None
    
    async def get_user_by_telegram_id(self, telegram_id: int):
        """Obtener usuario por Telegram ID"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/users/telegram/{telegram_id}",
                    headers=self.headers,
                    timeout=10.0
                )
                if response.status_code == 404:
                    return None
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"Error API get_user: {e}")
                return None
    
    async def update_user_profile(self, user_id: str, data: dict):
        """Actualizar perfil de usuario"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.put(
                    f"{self.base_url}/users/{user_id}/profile",
                    json=data,
                    headers=self.headers,
                    timeout=10.0
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"Error API update_profile: {e}")
                return None

# Inicializar cliente API
api_client = APIClient(API_BASE_URL, API_KEY)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando de inicio"""
    user_id = update.effective_user.id
    
    # Verificar si el usuario ya existe
    existing_user = await api_client.get_user_by_telegram_id(user_id)
    
    if existing_user:
        await update.message.reply_text(
            f"Hola de nuevo {existing_user.get('nombre') or existing_user.get('email')}!\n\n"
            "Comandos disponibles:\n"
            "/profile - Ver mi perfil\n"
            "/help - Ver todos los comandos"
        )
    else:
        await update.message.reply_text(
            "Hola! Soy NutriChat\n\n"
            "Parece que es tu primera vez aquí.\n"
            "Comandos disponibles:\n"
            "/register - Crear cuenta\n"
            "/help - Ver ayuda completa"
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostrar ayuda"""
    await update.message.reply_text(
        "NutriChat Bot - Comandos disponibles:\n\n"
        "Cuenta:\n"
        "/start - Inicio\n"
        "/register - Crear cuenta\n"
        "/profile - Ver mi perfil\n\n"
        "Otros:\n"
        "/help - Esta ayuda\n"
        "/cancel - Cancelar operación actual"
    )

# === REGISTRO DE USUARIO ===
async def register_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Iniciar registro"""
    user_id = update.effective_user.id
    
    # Verificar si ya está registrado
    existing_user = await api_client.get_user_by_telegram_id(user_id)
    if existing_user:
        await update.message.reply_text(
            "Ya tienes una cuenta registrada. Usa /profile para ver tus datos."
        )
        return ConversationHandler.END
    
    await update.message.reply_text(
        "Vamos a crear tu cuenta en NutriChat.\n\n"
        "Paso 1/3: Por favor, escribe tu email:"
    )
    return REGISTER_EMAIL

async def register_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Capturar email"""
    email = update.message.text.strip().lower()
    
    # Validar formato de email
    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
        await update.message.reply_text(
            "Email inválido. Por favor, ingresa un email válido:"
        )
        return REGISTER_EMAIL
    
    context.user_data['email'] = email
    await update.message.reply_text(
        "Email válido.\n\n"
        "Paso 2/3: Ahora escribe una contraseña (mínimo 6 caracteres):"
    )
    return REGISTER_PASSWORD

async def register_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Capturar contraseña"""
    password = update.message.text.strip()
    
    if len(password) < 6:
        await update.message.reply_text(
            "La contraseña debe tener al menos 6 caracteres. Intenta de nuevo:"
        )
        return REGISTER_PASSWORD
    
    context.user_data['password'] = password
    await update.message.reply_text(
        "Contraseña aceptada.\n\n"
        "Paso 3/3: Como te llamas? (opcional, escribe 'saltar'):"
    )
    return REGISTER_NAME

async def register_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Capturar nombre y crear usuario"""
    nombre = update.message.text.strip()
    
    if nombre.lower() in ['saltar', 'skip']:
        nombre = None
    
    # Preparar datos para la API
    user_data = {
        "email": context.user_data['email'],
        "password": context.user_data['password'],
        "nombre": nombre,
        "telegram_id": update.effective_user.id
    }
    
    # Crear usuario via API
    result = await api_client.create_user(user_data)
    
    if result and result.get('success'):
        user = result.get('user', {})
        await update.message.reply_text(
            f"Cuenta creada exitosamente!\n\n"
            f"Email: {user.get('email')}\n"
            f"Nombre: {user.get('nombre') or 'No especificado'}\n\n"
            "Ya puedes usar todos los servicios de NutriChat.\n"
            "Usa /profile para ver tu perfil completo."
        )
    else:
        error_msg = result.get('message', 'Error desconocido') if result else 'Error de conexión'
        await update.message.reply_text(
            f"Error al crear la cuenta: {error_msg}\n"
            "Intenta más tarde."
        )
    
    # Limpiar datos temporales
    context.user_data.clear()
    return ConversationHandler.END

async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostrar perfil del usuario"""
    user_id = update.effective_user.id
    user = await api_client.get_user_by_telegram_id(user_id)
    
    if not user:
        await update.message.reply_text(
            "No tienes una cuenta registrada.\n"
            "Usa /register para crear una cuenta."
        )
        return
    
    # Construir mensaje de perfil
    profile_text = f"Mi Perfil NutriChat:\n\n"
    profile_text += f"Email: {user.get('email')}\n"
    profile_text += f"Nombre: {user.get('nombre') or 'No especificado'}\n"
    profile_text += f"Teléfono: {user.get('telefono') or 'No especificado'}\n"
    
    if user.get('fecha_registro'):
        profile_text += f"Miembro desde: {user['fecha_registro'][:10]}\n"
    
    await update.message.reply_text(profile_text)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancelar operación"""
    await update.message.reply_text("Operación cancelada.")
    return ConversationHandler.END

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Manejar errores del bot"""
    logger.error(msg="Exception while handling an update:", exc_info=context.error)

def main():
    """Función principal del bot"""
    if not TELEGRAM_TOKEN:
        print("ERROR: Token de Telegram no configurado")
        return
    
    print(f"Iniciando NutriChat Bot...")
    print(f"API Base URL: {API_BASE_URL}")
    
    # Crear aplicación
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Conversación de registro
    register_handler = ConversationHandler(
        entry_points=[CommandHandler('register', register_start)],
        states={
            REGISTER_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_email)],
            REGISTER_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_password)],
            REGISTER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_name)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    
    # Handlers básicos
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("profile", show_profile))
    application.add_handler(register_handler)
    
    # Error handler
    application.add_error_handler(error_handler)
    
    # Iniciar bot
    print("Bot iniciado. Presiona Ctrl+C para detener.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
"""
Bot de Telegram para NutriChat - Integrado con Sistema de Recomendaciones y Neon
VERSIÓN CORREGIDA - EL BOT PIDE NOMBRE Y EMAIL CORRECTAMENTE
"""

import os
import logging
import json
import requests
from datetime import datetime
from typing import Dict, Any, Optional
import asyncio

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler, 
    CallbackQueryHandler, 
    ContextTypes,
    filters,
    ConversationHandler
)
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Importar motor de recomendaciones
try:
    from app.recommender.recommender_engine import RecommenderEngine
except ImportError:
    # Si no existe, crear una clase dummy
    class RecommenderEngine:
        def get_recommendations(self, user_id, n_recommendations=10):
            return []
        def get_nutritional_recommendations(self, user_id):
            return {'message': '', 'recommendations': [], 'stats': {'total_products': 0}}

# Configurar logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Estados para conversación - DEFINIR CORRECTAMENTE
NOMBRE, EMAIL = range(2)

# Token del bot
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
API_BASE_URL = 'http://127.0.0.1:5000/api/v1'
FRONTEND_URL = 'http://127.0.0.1:5000'

class NutriChatBot:
    """Bot de Telegram con Sistema de Recomendaciones - Conectado a Neon"""
    
    def __init__(self):
        self.recommender = RecommenderEngine()
        self.user_cache = {}
        self.categories = {
            1: 'Frutas y Verduras',
            2: 'Lácteos y Huevos',
            3: 'Carnes y Pescados',
            4: 'Despensa',
            5: 'Aseo y Hogar',
            6: 'Bebidas',
            7: 'Panadería y Pastelería'
        }
    
    # ==================== COMANDOS PRINCIPALES ====================
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /start"""
        user = update.effective_user
        telegram_id = user.id
        
        logger.info(f"🔍 /start recibido de user {user.first_name} (ID: {telegram_id})")
        
        # Verificar usuario en Neon
        user_data = await self._check_user(telegram_id)
        
        if user_data:
            context.user_data['user_id'] = user_data['user_id']
            context.user_data['nombre'] = user_data['nombre']
            
            welcome_text = (
                f"👋 ¡Bienvenido de nuevo, {user_data['nombre']}!\n\n"
                f"📊 **Tu resumen:**\n"
                f"• Productos: {user_data.get('total_products', 0)}\n"
                f"• Sesiones: {user_data.get('total_sessions', 0)}\n\n"
                f"¿Qué deseas hacer?"
            )
            
            keyboard = [
                [InlineKeyboardButton("🎯 Ver Recomendaciones", callback_data='recomendaciones')],
                [InlineKeyboardButton("🥗 Consejos Nutricionales", callback_data='nutricion')],
                [InlineKeyboardButton("📊 Mis Estadísticas", callback_data='estadisticas')],
                [InlineKeyboardButton("⚡ Scraping Rápido", callback_data='scraping')],
                [InlineKeyboardButton("📱 Abrir Web", url=f"{FRONTEND_URL}/dashboard")],
            ]
        else:
            welcome_text = (
                f"👋 ¡Hola {user.first_name}! Bienvenido a NutriChat Bot.\n\n"
                "🤖 **Tu asistente nutricional con IA**\n\n"
                "Para comenzar, necesitas registrarte:"
            )
            keyboard = [
                [InlineKeyboardButton("📝 Registrarme", callback_data='registro')],
                [InlineKeyboardButton("ℹ️ Cómo funciona", callback_data='info')],
            ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def recomendaciones(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Mostrar recomendaciones personalizadas"""
        query = update.callback_query
        await query.answer()
        
        user_id = context.user_data.get('user_id')
        if not user_id:
            await query.edit_message_text(
                "❌ Debes iniciar sesión primero.\nUsa /start para comenzar."
            )
            return
        
        # Obtener recomendaciones
        try:
            recommendations = self.recommender.get_recommendations(user_id, n_recommendations=5)
        except:
            recommendations = []
        
        if not recommendations:
            await query.edit_message_text(
                "📭 No hay suficientes productos para generar recomendaciones.\n\n"
                "¡Haz scraping o agrega productos manualmente!",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🛒 Ir a Productos", url=f"{FRONTEND_URL}/products")
                ]])
            )
            return
        
        text = "🎯 **Tus recomendaciones personalizadas:**\n\n"
        
        for i, rec in enumerate(recommendations[:5], 1):
            text += f"{i}. *{rec['name']}*\n"
            text += f"   💰 ${rec['price']:,.0f} | 📂 {rec['category']}\n"
            text += f"   📌 {rec['reason']}\n\n"
        
        keyboard = [
            [InlineKeyboardButton("🔄 Actualizar", callback_data='recomendaciones')],
            [InlineKeyboardButton("🥗 Consejos Nutricionales", callback_data='nutricion')],
            [InlineKeyboardButton("📊 Ver Dashboard", url=f"{FRONTEND_URL}/dashboard")],
            [InlineKeyboardButton("⬅️ Volver", callback_data='volver')],
        ]
        
        await query.edit_message_text(
            text, 
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    async def nutricion(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Recomendaciones nutricionales"""
        query = update.callback_query
        await query.answer()
        
        user_id = context.user_data.get('user_id')
        if not user_id:
            await query.edit_message_text("❌ Debes iniciar sesión primero.")
            return
        
        try:
            nutrition = self.recommender.get_nutritional_recommendations(user_id)
        except:
            nutrition = {'stats': {'total_products': 0}, 'recommendations': []}
        
        text = f"🥗 **Consejos Nutricionales Personalizados**\n\n"
        text += f"📊 Basado en tus {nutrition['stats']['total_products']} productos:\n\n"
        
        if nutrition.get('recommendations'):
            for rec in nutrition['recommendations']:
                text += f"**{rec['title']}**\n"
                text += f"{rec['description']}\n"
                text += f"👉 {rec['action']}\n\n"
        else:
            text += "✨ Agrega más productos para recibir consejos personalizados.\n\n"
        
        keyboard = [
            [InlineKeyboardButton("🎯 Ver Productos", callback_data='recomendaciones')],
            [InlineKeyboardButton("📊 Estadísticas", callback_data='estadisticas')],
            [InlineKeyboardButton("⬅️ Volver", callback_data='volver')],
        ]
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    async def estadisticas(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Mostrar estadísticas del usuario desde Neon"""
        query = update.callback_query
        await query.answer()
        
        user_id = context.user_data.get('user_id')
        if not user_id:
            await query.edit_message_text("❌ Debes iniciar sesión primero.")
            return
        
        try:
            # Verificar conexión a API primero
            health = requests.get(f"{API_BASE_URL}/health", timeout=3)
            if health.status_code != 200:
                raise Exception("API no disponible")
            
            # Obtener productos de Neon
            products_res = requests.get(f"{API_BASE_URL}/products/items", timeout=5)
            products_data = products_res.json() if products_res.status_code == 200 else {'count': 0, 'products': []}
            
            # Obtener historial de scraping de Neon
            history_res = requests.get(f"{API_BASE_URL}/scraping/history", timeout=5)
            history_data = history_res.json() if history_res.status_code == 200 else {'count': 0}
            
            total_products = products_data.get('count', 0)
            total_value = sum(p.get('price', 0) for p in products_data.get('products', []))
            total_sessions = history_data.get('count', 0)
            
            text = (
                f"📊 **Tus Estadísticas**\n\n"
                f"📦 **Productos:** {total_products}\n"
                f"💰 **Valor total:** ${total_value:,.0f}\n"
                f"🔄 **Sesiones:** {total_sessions}\n"
            )
            
        except requests.exceptions.ConnectionError:
            logger.error("❌ No se pudo conectar a la API")
            text = "❌ No se pudo conectar al servidor.\n¿Está corriendo `python run.py`?"
        except Exception as e:
            logger.error(f"Error obteniendo stats: {e}")
            text = "❌ Error obteniendo estadísticas."
        
        keyboard = [
            [InlineKeyboardButton("🎯 Recomendaciones", callback_data='recomendaciones')],
            [InlineKeyboardButton("🥗 Nutrición", callback_data='nutricion')],
            [InlineKeyboardButton("⬅️ Volver", callback_data='volver')],
        ]
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    async def scraping(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Menú de scraping"""
        query = update.callback_query
        await query.answer()
        
        keyboard = []
        for cat_id, cat_name in self.categories.items():
            keyboard.append([InlineKeyboardButton(
                f"{self._get_category_emoji(cat_name)} {cat_name}", 
                callback_data=f'scrape_{cat_id}'
            )])
        
        keyboard.append([InlineKeyboardButton("⬅️ Volver", callback_data='volver')])
        
        await query.edit_message_text(
            "⚡ **Scraping Rápido**\n\nSelecciona una categoría para extraer productos:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    async def scrape_categoria(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Iniciar scraping para una categoría"""
        query = update.callback_query
        await query.answer()
        
        user_id = context.user_data.get('user_id')
        if not user_id:
            await query.edit_message_text("❌ Debes iniciar sesión primero.")
            return
        
        category_id = int(query.data.split('_')[1])
        category_name = self.categories.get(category_id, 'Desconocida')
        
        await query.edit_message_text(
            f"⏳ Iniciando scraping de **{category_name}**...\n\n"
            f"Esto puede tomar unos minutos. Te avisaré cuando termine.",
            parse_mode='Markdown'
        )
        
        # Llamar a la API de scraping
        try:
            response = requests.post(
                f"{API_BASE_URL}/scraping/start",
                json={'mode': 'auto', 'category': category_id},
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                await query.message.reply_text(
                    f"✅ **Scraping iniciado!**\n\n"
                    f"ID de sesión: `{data.get('session_id')}`\n"
                    f"Categoría: {category_name}\n\n"
                    f"Puedes ver el progreso en la web.",
                    parse_mode='Markdown'
                )
            else:
                await query.message.reply_text(
                    f"❌ Error iniciando scraping: {response.json().get('message', 'Error desconocido')}"
                )
        except Exception as e:
            await query.message.reply_text(f"❌ Error de conexión: {str(e)}")
        
        # Volver al menú principal
        await self.volver(update, context)
    
    async def volver(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Volver al menú principal"""
        query = update.callback_query
        
        nombre = context.user_data.get('nombre', 'Usuario')
        
        text = f"👋 ¡Hola {nombre}!\n\n¿Qué deseas hacer?"
        
        keyboard = [
            [InlineKeyboardButton("🎯 Recomendaciones", callback_data='recomendaciones')],
            [InlineKeyboardButton("🥗 Consejos Nutricionales", callback_data='nutricion')],
            [InlineKeyboardButton("📊 Estadísticas", callback_data='estadisticas')],
            [InlineKeyboardButton("⚡ Scraping", callback_data='scraping')],
            [InlineKeyboardButton("📱 Ver Dashboard", url=f"{FRONTEND_URL}/dashboard")],
        ]
        
        if query:
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
    
    # ==================== REGISTRO EN NEON (CORREGIDO) ====================
    
    async def registro(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Iniciar proceso de registro - ENTRA AL CONVERSATION HANDLER"""
        query = update.callback_query
        await query.answer()
        
        telegram_id = update.effective_user.id
        context.user_data['telegram_id'] = telegram_id
        
        logger.info(f"📝 Iniciando registro para telegram_id: {telegram_id}")
        
        await query.edit_message_text(
            "📝 **Registro en NutriChat**\n\n"
            "Por favor, ingresa tu **nombre completo**:",
            parse_mode='Markdown'
        )
        return NOMBRE  # Importante: devolver el estado NOMBRE
    
    async def recibir_nombre(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Recibir nombre del usuario - ESTADO NOMBRE"""
        nombre = update.message.text.strip()
        context.user_data['nombre'] = nombre
        
        logger.info(f"✅ Nombre recibido: {nombre}")
        
        # Preguntar email y cambiar al estado EMAIL
        await update.message.reply_text(
            f"✅ Gracias {nombre}!\n\n"
            f"Ahora ingresa tu **correo electrónico**:"
        )
        return EMAIL  # Cambiar al estado EMAIL
    
    async def recibir_email(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Recibir email - ESTADO EMAIL"""
        email = update.message.text.strip()
        context.user_data['email'] = email
        
        logger.info(f"✅ Email recibido: {email}")
        
        # Mostrar resumen y botones de confirmación
        text = (
            f"📋 **Resumen de registro:**\n\n"
            f"👤 **Nombre:** {context.user_data['nombre']}\n"
            f"📧 **Email:** {email}\n"
            f"🆔 **Telegram ID:** `{context.user_data['telegram_id']}`\n\n"
            f"¿Confirmar registro?"
        )
        
        keyboard = [
            [
                InlineKeyboardButton("✅ Confirmar", callback_data='confirmar_registro'),
                InlineKeyboardButton("❌ Cancelar", callback_data='cancelar_registro')
            ]
        ]
        
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        return ConversationHandler.END  # Terminar conversación
    
    async def confirmar_registro(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Confirmar y completar registro en Neon"""
        query = update.callback_query
        await query.answer()
        
        logger.info("✅ Confirmando registro...")
        logger.info(f"📝 Datos en context: {context.user_data}")
        
        try:
            # Verificar que tenemos todos los datos
            if 'telegram_id' not in context.user_data:
                logger.error("❌ No hay telegram_id en context")
                await query.edit_message_text(
                    "❌ Error: No se encontró tu ID de Telegram. Por favor usa /start nuevamente."
                )
                return
            
            if 'nombre' not in context.user_data:
                context.user_data['nombre'] = f"Usuario_{context.user_data['telegram_id']}"
            
            if 'email' not in context.user_data:
                context.user_data['email'] = f"user_{context.user_data['telegram_id']}@telegram.com"
            
            # Datos del usuario para registrar en Neon
            user_data = {
                'telegram_id': context.user_data['telegram_id'],
                'nombre': context.user_data['nombre'],
                'email': context.user_data['email'],
                'telefono': ''
            }
            
            logger.info(f"📝 Registrando usuario en Neon: {user_data}")
            
            # Llamar a la API de registro
            response = requests.post(
                f"{API_BASE_URL}/users/register",
                json=user_data,
                timeout=10
            )
            
            logger.info(f"📊 Respuesta de API: {response.status_code}")
            logger.info(f"📊 Contenido: {response.text}")
            
            if response.status_code in [200, 201]:
                data = response.json()
                context.user_data['user_id'] = data.get('user_id')
                
                await query.edit_message_text(
                    "✅ **¡Registro completado con éxito!**\n\n"
                    "Ya puedes usar todas las funciones de NutriChat.\n\n"
                    "¿Qué deseas hacer ahora?",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🎯 Ver Recomendaciones", callback_data='recomendaciones')
                    ]]),
                    parse_mode='Markdown'
                )
                logger.info(f"✅ Usuario registrado en Neon: {context.user_data['user_id']}")
            else:
                error_msg = "Error desconocido"
                try:
                    error_msg = response.json().get('message', 'Error desconocido')
                except:
                    error_msg = response.text
                
                # Si el error es que ya existe, igual podemos continuar
                if "ya registrado" in error_msg.lower():
                    await query.edit_message_text(
                        "ℹ️ **Ya estás registrado**\n\n"
                        "Puedes usar /start para acceder a las funciones.",
                        parse_mode='Markdown'
                    )
                else:
                    await query.edit_message_text(
                        f"❌ Error en el registro: {error_msg}",
                        parse_mode='Markdown'
                    )
                logger.error(f"❌ Error registrando usuario: {error_msg}")
            
        except requests.exceptions.ConnectionError as e:
            logger.error(f"❌ Error de conexión: {e}")
            await query.edit_message_text(
                "❌ No se pudo conectar con el servidor.\n"
                "Asegúrate de que la aplicación NutriChat esté corriendo (`python run.py`)."
            )
        except Exception as e:
            logger.error(f"❌ Error en registro: {e}")
            import traceback
            traceback.print_exc()
            await query.edit_message_text(
                f"❌ Error en el registro: {str(e)[:100]}"
            )
    
    async def cancelar_registro(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancelar registro"""
        query = update.callback_query
        await query.answer()
        
        logger.info("❌ Registro cancelado por el usuario")
        
        await query.edit_message_text(
            "❌ Registro cancelado.\n\n"
            "Usa /start cuando quieras intentarlo nuevamente."
        )
    
    async def info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Mostrar información del bot"""
        query = update.callback_query
        await query.answer()
        
        text = (
            "ℹ️ **Acerca de NutriChat Bot**\n\n"
            "🤖 **Versión:** 2.0 Professional\n"
            "🧠 **Motor:** IA\n"
            "💾 **Base de datos:** PostgreSQL (Neon)\n\n"
            "**Características:**\n"
            "• Recomendaciones personalizadas\n"
            "• Análisis nutricional\n"
            "• Scraping automático de Tiendas D1\n"
            "• Estadísticas en tiempo real\n\n"
            "**Comandos:**\n"
            "/start - Iniciar el bot"
        )
        
        keyboard = [
            [InlineKeyboardButton("📝 Registrarme", callback_data='registro')],
            [InlineKeyboardButton("⬅️ Volver", callback_data='volver')],
        ]
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    # ==================== UTILIDADES ====================
    
    async def _check_user(self, telegram_id: int) -> Optional[Dict]:
        """Verificar usuario en Neon mediante la API"""
        try:
            logger.info(f"🔍 Verificando usuario con telegram_id: {telegram_id}")
            
            # Llamar a tu endpoint para verificar usuario
            response = requests.get(
                f"{API_BASE_URL}/users/check/{telegram_id}",
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('registered'):
                    logger.info(f"✅ Usuario encontrado: {data.get('nombre')}")
                    
                    # Obtener productos del usuario
                    try:
                        products_res = requests.get(
                            f"{API_BASE_URL}/products/items",
                            timeout=3
                        )
                        products_data = products_res.json() if products_res.status_code == 200 else {'count': 0}
                    except:
                        products_data = {'count': 0}
                    
                    # Obtener sesiones
                    try:
                        sessions_res = requests.get(
                            f"{API_BASE_URL}/scraping/history",
                            timeout=3
                        )
                        sessions_data = sessions_res.json() if sessions_res.status_code == 200 else {'count': 0}
                    except:
                        sessions_data = {'count': 0}
                    
                    return {
                        'user_id': data.get('user_id'),
                        'nombre': data.get('nombre', 'Usuario'),
                        'total_products': products_data.get('count', 0),
                        'total_sessions': sessions_data.get('count', 0)
                    }
                else:
                    logger.info("ℹ️ Usuario no registrado")
                    return None
            return None
        except requests.exceptions.ConnectionError:
            logger.error(f"❌ No se pudo conectar a la API en {API_BASE_URL}")
            return None
        except Exception as e:
            logger.error(f"Error verificando usuario: {e}")
            return None
    
    def _get_category_emoji(self, category: str) -> str:
        """Obtener emoji para categoría"""
        emojis = {
            'Frutas y Verduras': '🍎',
            'Lácteos y Huevos': '🥛',
            'Carnes y Pescados': '🍗',
            'Despensa': '📦',
            'Aseo y Hogar': '🧹',
            'Bebidas': '🥤',
            'Panadería y Pastelería': '🥖'
        }
        return emojis.get(category, '📦')
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Manejar errores"""
        logger.error(f"Error: {context.error}")
        
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "❌ Ocurrió un error. Por favor intenta de nuevo más tarde."
            )

def main():
    """Función principal para iniciar el bot"""
    if not TOKEN:
        logger.error("❌ TELEGRAM_BOT_TOKEN no configurado")
        print("\n⚠️  No se encontró TELEGRAM_BOT_TOKEN en .env")
        print("📝 1. Ve a @BotFather en Telegram")
        print("🔑 2. Crea un nuevo bot con /newbot")
        print("📋 3. Copia el token y agrégalo a tu archivo .env")
        print("✅ 4. Ejecuta este script nuevamente\n")
        return
    
    # Crear bot
    bot = NutriChatBot()
    app = Application.builder().token(TOKEN).build()
    
    # Handlers de comandos
    app.add_handler(CommandHandler("start", bot.start))
    
    # Handlers de callbacks
    app.add_handler(CallbackQueryHandler(bot.recomendaciones, pattern='^recomendaciones$'))
    app.add_handler(CallbackQueryHandler(bot.nutricion, pattern='^nutricion$'))
    app.add_handler(CallbackQueryHandler(bot.estadisticas, pattern='^estadisticas$'))
    app.add_handler(CallbackQueryHandler(bot.scraping, pattern='^scraping$'))
    app.add_handler(CallbackQueryHandler(bot.info, pattern='^info$'))
    app.add_handler(CallbackQueryHandler(bot.volver, pattern='^volver$'))
    app.add_handler(CallbackQueryHandler(bot.cancelar_registro, pattern='^cancelar_registro$'))
    app.add_handler(CallbackQueryHandler(bot.confirmar_registro, pattern='^confirmar_registro$'))
    app.add_handler(CallbackQueryHandler(bot.scrape_categoria, pattern='^scrape_[1-7]$'))
    
    # ConversationHandler para registro - CORREGIDO
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(bot.registro, pattern='^registro$')],
        states={
            NOMBRE: [MessageHandler(filters.TEXT & ~filters.COMMAND, bot.recibir_nombre)],
            EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, bot.recibir_email)],
        },
        fallbacks=[CommandHandler("cancel", bot.cancelar_registro)],
    )
    app.add_handler(conv_handler)
    
    # Error handler
    app.add_error_handler(bot.error_handler)
    
    # Iniciar bot
    print("=" * 60)
    print("🤖 NUTRICHAT TELEGRAM BOT")
    print("=" * 60)
    print(f"🚀 Iniciando bot...")
    print(f"📱 Token: {TOKEN[:10]}...{TOKEN[-5:]}")
    print("✅ Bot está funcionando!")
    print("📱 Busca tu bot en Telegram y escribe /start")
    print("=" * 60)
    
    app.run_polling()

if __name__ == '__main__':
    main()
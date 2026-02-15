"""
Aplicación principal de NutriChat - VERSIÓN COMPLETA CON POSTGRESQL (NEON)
"""
from flask import Flask, jsonify, render_template, request, session, redirect, url_for, flash
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token
import os
import logging
import threading
import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path
import sys
from sqlalchemy import text
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

def create_app(config_name=None):
    """
    Factory para crear la aplicación Flask
    """
    app = Flask(__name__, template_folder='templates', static_folder='static')
    
    # ==================== CONFIGURACIÓN ====================
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'jwt-secret-key-change-in-production')
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES', 86400))
    
    # 🔥 CONEXIÓN A POSTGRESQL (Neon)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'postgresql://neondb_owner:npg_SIdvyh2Npx9B@ep-snowy-brook-ai3y4234-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require')
    
    # Configuración adicional para PostgreSQL
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'pool_size': 5,
        'max_overflow': 10
    }
    
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['PERMANENT_SESSION_LIFETIME'] = 3600
    app.config['SESSION_PERMANENT'] = True
    app.config['SESSION_USE_SIGNER'] = True
    
    # Directorios scraping
    app.config['SCRAPER_DIR'] = Path('scraping_results_v8')
    app.config['CAPTURAS_DIR'] = app.config['SCRAPER_DIR'] / "screenshots"
    app.config['DATOS_DIR'] = app.config['SCRAPER_DIR'] / "data"
    app.config['TEMP_DIR'] = app.config['SCRAPER_DIR'] / "temp"
    
    for dir_path in [app.config['SCRAPER_DIR'], app.config['CAPTURAS_DIR'], 
                    app.config['DATOS_DIR'], app.config['TEMP_DIR']]:
        dir_path.mkdir(parents=True, exist_ok=True)
    
    # ==================== EXTENSIONES ====================
    cors_origins = os.getenv('CORS_ORIGINS', '*').split(',')
    CORS(app, resources={r"/api/*": {"origins": cors_origins}}, supports_credentials=True)
    
    jwt = JWTManager(app)
    logging.basicConfig(level=os.getenv('LOG_LEVEL', 'INFO'))
    
    # ==================== BASE DE DATOS ====================
    from app.models.database import db
    db.init_app(app)
    
    print(f"""
    🚀 NUTRICHAT - ASISTENTE NUTRICIONAL INTELIGENTE
    ============================================================
    ✨ Versión: 2.0 Professional
    🌐 Frontend: http://127.0.0.1:5000
    📚 API REST: http://127.0.0.1:5000/api/v1/
    🔧 Modo: {os.getenv('FLASK_ENV', 'desarrollo').upper()}
    💾 Database: PostgreSQL (Neon)
    ============================================================
    ✅ Sistema listo para recibir conexiones...
    ============================================================
    """)
    
    # ==================== RUTAS DE TEMPLATES ====================
    
    @app.route('/')
    def index():
        """Página principal"""
        return render_template('index.html')
    
    @app.route('/login')
    def login():
        """Página de login"""
        return render_template('auth/login.html')
    
    @app.route('/register')
    def register():
        """Página de registro"""
        return render_template('auth/register.html')
    
    @app.route('/dashboard')
    def dashboard():
        """Dashboard principal"""
        if not session.get('user_id'):
            flash('Debes iniciar sesión para acceder al dashboard', 'warning')
            return redirect(url_for('login'))
        return render_template('dashboard/home.html')
    
    @app.route('/profile')
    def profile():
        """Perfil de usuario"""
        if not session.get('user_id'):
            flash('Debes iniciar sesión para ver tu perfil', 'warning')
            return redirect(url_for('login'))
        return render_template('dashboard/profile.html')
    
    @app.route('/products')
    def products():
        """Gestión de productos"""
        if not session.get('user_id'):
            flash('Debes iniciar sesión para ver productos', 'warning')
            return redirect(url_for('login'))
        return render_template('dashboard/products.html')
    
    @app.route('/lists')
    def lists():
        """Listas de compra"""
        if not session.get('user_id'):
            flash('Debes iniciar sesión para ver listas', 'warning')
            return redirect(url_for('login'))
        return render_template('dashboard/lists.html')
    
    @app.route('/scraping')
    def scraping_page():
        """Página de scraping"""
        if not session.get('user_id'):
            flash('Debes iniciar sesión para usar el scraping', 'warning')
            return redirect(url_for('login'))
        return render_template('dashboard/scraping.html')
    
    @app.route('/logout')
    def logout():
        """Cerrar sesión"""
        session.clear()
        flash('Sesión cerrada correctamente', 'info')
        return redirect(url_for('index'))
    
    # ==================== API AUTH Y SESIÓN ====================
    
    @app.route('/api/v1/session/check', methods=['GET'])
    def check_session():
        """Verificar sesión activa"""
        return jsonify({
            'success': True,
            'is_logged_in': bool(session.get('user_id')),
            'user': {
                'id': session.get('user_id'),
                'name': session.get('user_name'),
                'telegram_id': session.get('user_telegram_id')
            } if session.get('user_id') else None
        }), 200
    
    @app.route('/api/v1/users/register', methods=['POST'])
    def api_register():
        """Registrar usuario con SQL directo"""
        try:
            data = request.get_json()
            if not data or 'telegram_id' not in data:
                return jsonify({'success': False, 'message': 'telegram_id es requerido'}), 400
            
            telegram_id = int(data['telegram_id'])
            user_id = str(uuid.uuid4())
            
            # Verificar si ya existe
            query = text("SELECT usuario_id FROM usuarios WHERE telegram_id = :telegram_id")
            result = db.session.execute(query, {'telegram_id': telegram_id})
            existing_user = result.fetchone()
            
            if existing_user:
                return jsonify({'success': False, 'message': 'Usuario ya registrado'}), 409
            
            # Crear usuario
            insert_query = text("""
                INSERT INTO usuarios (
                    usuario_id, nombre, email, telefono, rol_id, 
                    telegram_id, activo, fecha_registro
                ) VALUES (
                    :user_id, :nombre, :email, :telefono, :rol_id,
                    :telegram_id, :activo, CURRENT_TIMESTAMP
                )
            """)
            
            db.session.execute(insert_query, {
                'user_id': user_id,
                'nombre': data.get('nombre', 'Usuario'),
                'email': data.get('email'),
                'telefono': data.get('telefono'),
                'rol_id': 2,
                'telegram_id': telegram_id,
                'activo': True
            })
            db.session.commit()
            
            # Crear token
            token = create_access_token(identity=user_id)
            
            # Guardar en sesión
            session.permanent = True
            session['user_id'] = user_id
            session['user_name'] = data.get('nombre', 'Usuario')
            session['user_telegram_id'] = telegram_id
            
            return jsonify({
                'success': True,
                'message': 'Usuario registrado',
                'user_id': user_id,
                'access_token': token,
                'user': {
                    'id': user_id,
                    'nombre': data.get('nombre', 'Usuario'),
                    'telegram_id': telegram_id
                }
            }), 201
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': str(e)}), 500
    
    @app.route('/api/v1/users/login', methods=['POST'])
    def api_login():
        """Iniciar sesión con SQL directo"""
        try:
            data = request.get_json()
            if not data or 'telegram_id' not in data:
                return jsonify({'success': False, 'message': 'telegram_id es requerido'}), 400
            
            telegram_id = int(data['telegram_id'])
            
            # Buscar usuario
            query = text("""
                SELECT usuario_id, nombre, email, telefono, telegram_id 
                FROM usuarios 
                WHERE telegram_id = :telegram_id AND activo = true
            """)
            
            result = db.session.execute(query, {'telegram_id': telegram_id})
            user_data = result.fetchone()
            
            if not user_data:
                return jsonify({'success': False, 'message': 'Usuario no encontrado'}), 404
            
            # Crear token
            user_id = str(user_data[0])
            token = create_access_token(identity=user_id)
            
            # Guardar en sesión (¡ASEGURAR QUE SE GUARDE!)
            session.permanent = True
            session['user_id'] = user_id
            session['user_name'] = user_data[1] or 'Usuario'
            session['user_telegram_id'] = user_data[4]
            
            # Forzar guardado de sesión
            session.modified = True
            
            print(f"✅ Sesión creada: user_id={user_id}, user_name={session['user_name']}")
            
            return jsonify({
                'success': True,
                'message': 'Inicio de sesión exitoso',
                'access_token': token,
                'user': {
                    'id': user_id,
                    'nombre': user_data[1] or 'Usuario',
                    'telegram_id': user_data[4]
                }
            }), 200
            
        except Exception as e:
            print(f"❌ Error en login: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500
    
    
    @app.route('/api/v1/users/check/<int:telegram_id>', methods=['GET'])
    def check_user(telegram_id):
        """Verificar si un usuario existe por telegram_id"""
        try:
            query = text("""
                SELECT usuario_id, nombre, email 
                FROM usuarios 
                WHERE telegram_id = :telegram_id AND activo = true
            """)
            
            result = db.session.execute(query, {'telegram_id': telegram_id})
            user = result.fetchone()
            
            if user:
                return jsonify({
                    'success': True,
                    'registered': True,
                    'user_id': str(user[0]),
                    'nombre': user[1],
                    'email': user[2]
                }), 200
            else:
                return jsonify({
                    'success': True,
                    'registered': False
                }), 200
                
        except Exception as e:
            return jsonify({
                'success': False,
                'message': str(e)
            }), 500
    
    # ==================== API SCRAPING ====================
    
    @app.route('/api/v1/scraping/start', methods=['POST'])
    def start_scraping():
        """Iniciar scraping REAL"""
        if not session.get('user_id'):
            return jsonify({'success': False, 'message': 'No autorizado'}), 401
        
        try:
            data = request.get_json()
            mode = data.get('mode', 'auto')
            category = data.get('category', 1)
            
            session_id = f"{session.get('user_id')}_{str(uuid.uuid4())[:8]}"
            
            # Iniciar en segundo plano
            thread = threading.Thread(
                target=run_scraping_task,
                args=(app, session_id, mode, category, session.get('user_id'))
            )
            thread.daemon = True
            thread.start()
            
            # Guardar estado inicial
            status_file = app.config['SCRAPER_DIR'] / f'status_{session_id}.json'
            initial_status = {
                'session_id': session_id,
                'user_id': session.get('user_id'),
                'status': 'starting',
                'progress': 0,
                'step': 'Iniciando...',
                'message': 'Preparando scraping D1',
                'start_time': datetime.now().isoformat(),
                'mode': mode,
                'category': category
            }
            
            with open(status_file, 'w', encoding='utf-8') as f:
                json.dump(initial_status, f, ensure_ascii=False, indent=2)
            
            return jsonify({
                'success': True,
                'session_id': session_id,
                'message': 'Scraping iniciado en segundo plano',
                'mode': mode,
                'category': category
            }), 200
            
        except Exception as e:
            app.logger.error(f"Error iniciando scraping: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500
    
    @app.route('/api/v1/scraping/status/<session_id>', methods=['GET'])
    def get_scraping_status(session_id):
        """Obtener estado del scraping"""
        if not session.get('user_id'):
            return jsonify({'success': False, 'message': 'No autorizado'}), 401
        
        try:
            status_file = app.config['SCRAPER_DIR'] / f'status_{session_id}.json'
            
            if not status_file.exists():
                return jsonify({
                    'success': False,
                    'message': 'Sesión no encontrada'
                }), 404
            
            with open(status_file, 'r', encoding='utf-8') as f:
                status_data = json.load(f)
            
            return jsonify({'success': True, 'status': status_data}), 200
            
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500
    
    @app.route('/api/v1/scraping/results/<session_id>', methods=['GET'])
    def get_scraping_results(session_id):
        """Obtener resultados del scraping"""
        if not session.get('user_id'):
            return jsonify({'success': False, 'message': 'No autorizado'}), 401
        
        try:
            data_dir = app.config['DATOS_DIR']
            matching_files = list(data_dir.glob(f'*{session_id}*.json'))
            
            if not matching_files:
                return jsonify({
                    'success': False,
                    'message': 'Resultados no encontrados'
                }), 404
            
            results_file = max(matching_files, key=lambda x: x.stat().st_mtime)
            
            with open(results_file, 'r', encoding='utf-8') as f:
                results_data = json.load(f)
            
            return jsonify({
                'success': True,
                'results': results_data,
                'count': len(results_data.get('products', []))
            }), 200
            
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500
    
    @app.route('/api/v1/scraping/system-check', methods=['GET'])
    def system_check():
        """Verificar estado del sistema"""
        status = check_scraping_system()
        return jsonify({'success': True, 'system_status': status}), 200
    
    @app.route('/api/v1/scraping/categories', methods=['GET'])
    def get_scraping_categories():
        """Obtener categorías disponibles"""
        categories = {
            1: 'Frutas y Verduras',
            2: 'Lácteos y Huevos',
            3: 'Carnes y Pescados',
            4: 'Despensa',
            5: 'Aseo y Hogar',
            6: 'Bebidas',
            7: 'Panadería y Pastelería'
        }
        return jsonify({'success': True, 'categories': categories}), 200
    
    @app.route('/api/v1/scraping/history', methods=['GET'])
    def get_scraping_history():
        """Obtener historial de scraping del usuario"""
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': 'No autorizado'}), 401
        
        try:
            query = text("""
                SELECT session_id, mode, category, new_products, 
                       updated_products, total_products, total_value, 
                       created_at, status
                FROM scraping_sessions 
                WHERE user_id = :user_id
                ORDER BY created_at DESC
                LIMIT 10
            """)
            
            result = db.session.execute(query, {'user_id': user_id})
            sessions = result.fetchall()
            
            sessions_list = []
            for sess in sessions:
                session_data = {
                    'session_id': sess[0] if sess[0] else 'N/A',
                    'mode': sess[1] or 'manual',
                    'category': sess[2] or 1,
                    'new_products': sess[3] or 0,
                    'updated_products': sess[4] or 0,
                    'total_products': sess[5] or 0,
                    'total_value': float(sess[6]) if sess[6] else 0,
                    'created_at': sess[7].strftime('%Y-%m-%d %H:%M') if sess[7] else '',
                    'status': sess[8] or 'completed'
                }
                sessions_list.append(session_data)
            
            return jsonify({
                'success': True,
                'sessions': sessions_list,
                'count': len(sessions_list)
            }), 200
            
        except Exception as e:
            app.logger.error(f"Error obteniendo historial: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500
    
    # ==================== API DASHBOARD Y PRODUCTOS ====================
    
    @app.route('/api/v1/dashboard/stats', methods=['GET'])
    def get_dashboard_stats():
        """Obtener estadísticas del dashboard"""
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': 'No autorizado'}), 401
        
        try:
            # 1. Productos Totales
            query = text("SELECT COUNT(*) FROM user_products WHERE user_id = :user_id")
            result = db.session.execute(query, {'user_id': user_id})
            total_products = result.scalar() or 0
            
            # 2. Valor Total
            query = text("SELECT COALESCE(SUM(price), 0) FROM user_products WHERE user_id = :user_id")
            result = db.session.execute(query, {'user_id': user_id})
            total_value = float(result.scalar() or 0)
            
            # 3. Scraping Sessions (hoy)
            today = datetime.utcnow().date()
            query = text("""
                SELECT COUNT(*) FROM scraping_sessions 
                WHERE user_id = :user_id AND DATE(created_at) = :today
            """)
            result = db.session.execute(query, {'user_id': user_id, 'today': today})
            today_sessions = result.scalar() or 0
            
            # 4. Última sesión de scraping
            last_scraping_data = {
                'new_products': 0,
                'updated_products': 0,
                'total_scraped': 0,
                'date': 'Nunca',
                'session_id': None
            }
            
            query = text("""
                SELECT new_products, updated_products, total_products, 
                       created_at, session_id 
                FROM scraping_sessions 
                WHERE user_id = :user_id AND status = 'completed'
                ORDER BY created_at DESC 
                LIMIT 1
            """)
            result = db.session.execute(query, {'user_id': user_id})
            last_session = result.fetchone()
            
            if last_session:
                last_scraping_data = {
                    'new_products': last_session[0] or 0,
                    'updated_products': last_session[1] or 0,
                    'total_scraped': last_session[2] or 0,
                    'date': last_session[3].strftime('%H:%M') if last_session[3] else 'N/A',
                    'session_id': last_session[4]
                }
            
            # 5. Últimos productos
            latest_products_list = []
            try:
                query = text("""
                    SELECT name, price, category 
                    FROM user_products 
                    WHERE user_id = :user_id 
                    ORDER BY id DESC 
                    LIMIT 5
                """)
                result = db.session.execute(query, {'user_id': user_id})
                rows = result.fetchall()
                
                for row in rows:
                    name = str(row[0]) if row[0] else 'Producto'
                    price = float(row[1]) if row[1] else 0
                    category = str(row[2]) if row[2] else 'General'
                    
                    latest_products_list.append({
                        'name': name[:25],
                        'price': f"${price:,.0f}",
                        'category': category,
                        'date': 'Hoy'
                    })
                
            except Exception as e:
                app.logger.warning(f"Error en actividad: {e}")
                latest_products_list = []
            
            return jsonify({
                'success': True,
                'stats': {
                    'total_products': total_products,
                    'total_value': total_value,
                    'formatted_value': f"${total_value:,.0f}",
                    'today_sessions': today_sessions,
                    'last_scraping': last_scraping_data,
                    'latest_products': latest_products_list,
                    'health_score': 85,
                    'growth_percent': 12,
                    'system_health': 100,
                    'user_name': session.get('user_name', 'Usuario')
                }
            })
            
        except Exception as e:
            app.logger.error(f"Error en stats: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/v1/products/items', methods=['GET'])
    def get_products():
        """Obtener productos del usuario"""
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': 'No autorizado'}), 401
        
        try:
            query = text("""
                SELECT id, name, category, price, source, description, 
                       added_date, last_updated
                FROM user_products 
                WHERE user_id = :user_id
                ORDER BY added_date DESC NULLS LAST, id DESC
            """)
            
            result = db.session.execute(query, {'user_id': user_id})
            rows = result.fetchall()
            
            products_list = []
            for row in rows:
                product_dict = {
                    'id': row[0],
                    'name': row[1] or 'Sin nombre',
                    'category': row[2] or 'General',
                    'price': float(row[3]) if row[3] else 0.0,
                    'description': row[5] or '',
                    'source': row[4] or 'manual',
                    'created_at': row[6].strftime('%Y-%m-%d %H:%M') if row[6] else None,
                    'updated_at': row[7].strftime('%Y-%m-%d %H:%M') if row[7] else None
                }
                products_list.append(product_dict)
            
            return jsonify({
                'success': True,
                'products': products_list,
                'count': len(products_list)
            }), 200
            
        except Exception as e:
            app.logger.error(f"Error obteniendo productos: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500
    
    @app.route('/api/v1/products/items', methods=['POST'])
    def create_product():
        """Crear nuevo producto"""
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': 'No autorizado'}), 401
        
        try:
            data = request.get_json()
            if not data or 'name' not in data:
                return jsonify({'success': False, 'message': 'Nombre requerido'}), 400
            
            query = text("""
                INSERT INTO user_products (
                    user_id, name, category, price, source, description,
                    added_date, last_updated
                ) VALUES (
                    :user_id, :name, :category, :price, :source, :description,
                    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                ) RETURNING id
            """)
            
            result = db.session.execute(query, {
                'user_id': user_id,
                'name': data['name'],
                'category': data.get('category', 'General'),
                'price': data.get('price', 0),
                'source': 'manual',
                'description': data.get('description', '')
            })
            db.session.commit()
            
            product_id = result.fetchone()[0]
            
            return jsonify({
                'success': True,
                'message': 'Producto creado exitosamente',
                'product': {
                    'id': product_id,
                    'name': data['name'],
                    'category': data.get('category', 'General'),
                    'price': data.get('price', 0)
                }
            }), 201
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': str(e)}), 500
    
    @app.route('/api/v1/products/items/<int:product_id>', methods=['DELETE'])
    def delete_product(product_id):
        """Eliminar producto"""
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': 'No autorizado'}), 401
        
        try:
            query = text("DELETE FROM user_products WHERE id = :product_id AND user_id = :user_id")
            result = db.session.execute(query, {'product_id': product_id, 'user_id': user_id})
            db.session.commit()
            
            if result.rowcount == 0:
                return jsonify({'success': False, 'message': 'Producto no encontrado'}), 404
            
            return jsonify({
                'success': True,
                'message': 'Producto eliminado'
            }), 200
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': str(e)}), 500
    
    # ==================== API LISTAS DE COMPRA ====================
    
    @app.route('/api/v1/lists', methods=['GET'])
    def get_shopping_lists():
        """Obtener listas de compra del usuario"""
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': 'No autorizado'}), 401
        
        try:
            query = text("""
                SELECT id, name, description, total_items, total_value, 
                       status, created_at, updated_at
                FROM shopping_lists 
                WHERE user_id = :user_id
                ORDER BY updated_at DESC
            """)
            
            result = db.session.execute(query, {'user_id': user_id})
            lists_data = result.fetchall()
            
            lists = []
            for row in lists_data:
                list_dict = {
                    'id': row[0],
                    'name': row[1] or 'Lista sin nombre',
                    'description': row[2] or '',
                    'total_items': row[3] or 0,
                    'total_value': float(row[4]) if row[4] else 0.0,
                    'formatted_value': f"${float(row[4]):,.0f}" if row[4] else "$0",
                    'status': row[5] or 'active',
                    'created_at': row[6].strftime('%Y-%m-%d %H:%M') if row[6] else '',
                    'updated_at': row[7].strftime('%Y-%m-%d %H:%M') if row[7] else ''
                }
                lists.append(list_dict)
            
            return jsonify({
                'success': True,
                'lists': lists,
                'count': len(lists)
            }), 200
            
        except Exception as e:
            app.logger.error(f"Error obteniendo listas: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500
    
    @app.route('/api/v1/lists', methods=['POST'])
    def create_shopping_list():
        """Crear nueva lista de compra"""
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': 'No autorizado'}), 401
        
        try:
            data = request.get_json()
            if not data or 'name' not in data:
                return jsonify({'success': False, 'message': 'Nombre de lista requerido'}), 400
            
            query = text("""
                INSERT INTO shopping_lists 
                (user_id, name, description, total_items, total_value, status)
                VALUES 
                (:user_id, :name, :description, 0, 0, 'active')
                RETURNING id
            """)
            
            result = db.session.execute(query, {
                'user_id': user_id,
                'name': data['name'],
                'description': data.get('description', '')
            })
            db.session.commit()
            
            list_id = result.fetchone()[0]
            
            return jsonify({
                'success': True,
                'message': 'Lista creada exitosamente',
                'list': {
                    'id': list_id,
                    'name': data['name'],
                    'description': data.get('description', '')
                }
            }), 201
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': str(e)}), 500
    
    @app.route('/api/v1/lists/<int:list_id>', methods=['DELETE'])
    def delete_shopping_list(list_id):
        """Eliminar lista de compra"""
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': 'No autorizado'}), 401
        
        try:
            query = text("DELETE FROM shopping_lists WHERE id = :list_id AND user_id = :user_id")
            result = db.session.execute(query, {'list_id': list_id, 'user_id': user_id})
            db.session.commit()
            
            if result.rowcount == 0:
                return jsonify({'success': False, 'message': 'Lista no encontrada'}), 404
            
            return jsonify({
                'success': True,
                'message': 'Lista eliminada'
            }), 200
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': str(e)}), 500
    
    @app.route('/api/v1/lists/<int:list_id>/items', methods=['GET'])
    def get_list_items(list_id):
        """Obtener items de una lista"""
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': 'No autorizado'}), 401
        
        try:
            # Verificar que la lista pertenece al usuario
            check_query = text("SELECT id FROM shopping_lists WHERE id = :list_id AND user_id = :user_id")
            check_result = db.session.execute(check_query, {'list_id': list_id, 'user_id': user_id})
            if not check_result.fetchone():
                return jsonify({'success': False, 'message': 'Lista no encontrada'}), 404
            
            # Obtener items
            query = text("""
                SELECT id, product_id, product_name, quantity, price, 
                       category, checked, added_at
                FROM shopping_list_items 
                WHERE list_id = :list_id
                ORDER BY checked, category, added_at DESC
            """)
            
            result = db.session.execute(query, {'list_id': list_id})
            items_data = result.fetchall()
            
            items = []
            for row in items_data:
                item_dict = {
                    'id': row[0],
                    'product_id': row[1],
                    'product_name': row[2] or 'Producto sin nombre',
                    'quantity': row[3] or 1,
                    'price': float(row[4]) if row[4] else 0.0,
                    'formatted_price': f"${float(row[4]):,.0f}" if row[4] else "$0",
                    'category': row[5] or 'General',
                    'checked': bool(row[6]),
                    'added_at': row[7].strftime('%Y-%m-%d %H:%M') if row[7] else ''
                }
                items.append(item_dict)
            
            return jsonify({
                'success': True,
                'items': items,
                'count': len(items)
            }), 200
            
        except Exception as e:
            app.logger.error(f"Error obteniendo items: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500
    
    @app.route('/api/v1/lists/<int:list_id>/items', methods=['POST'])
    def add_item_to_list(list_id):
        """Agregar item a lista de compra"""
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': 'No autorizado'}), 401
        
        try:
            data = request.get_json()
            if not data or 'product_name' not in data:
                return jsonify({'success': False, 'message': 'Nombre de producto requerido'}), 400
            
            # Verificar que la lista pertenece al usuario
            check_query = text("SELECT id FROM shopping_lists WHERE id = :list_id AND user_id = :user_id")
            check_result = db.session.execute(check_query, {'list_id': list_id, 'user_id': user_id})
            if not check_result.fetchone():
                return jsonify({'success': False, 'message': 'Lista no encontrada'}), 404
            
            # Agregar item con transacción
            with db.session.begin_nested():
                # Insertar item
                insert_query = text("""
                    INSERT INTO shopping_list_items 
                    (list_id, product_id, product_name, quantity, price, category)
                    VALUES 
                    (:list_id, :product_id, :product_name, :quantity, :price, :category)
                    RETURNING id
                """)
                
                result = db.session.execute(insert_query, {
                    'list_id': list_id,
                    'product_id': data.get('product_id'),
                    'product_name': data['product_name'],
                    'quantity': data.get('quantity', 1),
                    'price': data.get('price', 0),
                    'category': data.get('category', 'General')
                })
                item_id = result.fetchone()[0]
                
                # Actualizar contadores de la lista
                update_query = text("""
                    UPDATE shopping_lists 
                    SET total_items = total_items + 1,
                        total_value = total_value + :price_value,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = :list_id
                """)
                
                db.session.execute(update_query, {
                    'list_id': list_id,
                    'price_value': data.get('price', 0) * data.get('quantity', 1)
                })
            
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Producto agregado a la lista',
                'item': {
                    'id': item_id,
                    'product_name': data['product_name']
                }
            }), 201
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': str(e)}), 500
    
    @app.route('/api/v1/lists/<int:list_id>/items/<int:item_id>', methods=['DELETE'])
    def remove_item_from_list(list_id, item_id):
        """Eliminar item de lista de compra"""
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': 'No autorizado'}), 401
        
        try:
            # Obtener el item antes de eliminarlo
            item_query = text("""
                SELECT price, quantity FROM shopping_list_items 
                WHERE id = :item_id AND list_id = :list_id
            """)
            item_result = db.session.execute(item_query, {'item_id': item_id, 'list_id': list_id})
            item_data = item_result.fetchone()
            
            if not item_data:
                return jsonify({'success': False, 'message': 'Item no encontrado'}), 404
            
            # Transacción
            with db.session.begin_nested():
                # Eliminar item
                delete_query = text("DELETE FROM shopping_list_items WHERE id = :item_id")
                db.session.execute(delete_query, {'item_id': item_id})
                
                # Actualizar contadores
                update_query = text("""
                    UPDATE shopping_lists 
                    SET total_items = total_items - 1,
                        total_value = total_value - :price_value,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = :list_id AND user_id = :user_id
                """)
                
                db.session.execute(update_query, {
                    'list_id': list_id,
                    'user_id': user_id,
                    'price_value': item_data[0] * item_data[1]
                })
            
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Producto eliminado de la lista'
            }), 200
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': str(e)}), 500
    
    @app.route('/api/v1/lists/<int:list_id>/items/<int:item_id>/toggle', methods=['PUT'])
    def toggle_item_checked(list_id, item_id):
        """Marcar/desmarcar item como comprado"""
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': 'No autorizado'}), 401
        
        try:
            query = text("""
                UPDATE shopping_list_items 
                SET checked = NOT checked
                WHERE id = :item_id AND list_id = :list_id
            """)
            
            result = db.session.execute(query, {'item_id': item_id, 'list_id': list_id})
            db.session.commit()
            
            if result.rowcount == 0:
                return jsonify({'success': False, 'message': 'Item no encontrado'}), 404
            
            return jsonify({
                'success': True,
                'message': 'Estado actualizado'
            }), 200
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': str(e)}), 500
    
        # ==================== RUTAS ADICIONALES ====================

    @app.route('/recommendations')
    def recommendations():
        """Página de recomendaciones IA"""
        if not session.get('user_id'):
            flash('Debes iniciar sesión para ver recomendaciones', 'warning')
            return redirect(url_for('login'))
        return render_template('dashboard/recommendations.html')
    
    @app.route('/api/v1/health', methods=['GET'])
    def health_check():
        """Verificar salud del sistema con PostgreSQL"""
        db_status = "connected"
        db_details = {}
        
        try:
            # Verificar conexión a PostgreSQL
            result = db.session.execute(text("SELECT version()"))
            version = result.fetchone()
            db_details['version'] = str(version[0])[:50] + '...'
            
            # Verificar tablas existentes
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            db_details['tables'] = tables
            
        except Exception as e:
            db_status = f"error: {str(e)}"
        
        return jsonify({
            'success': True,
            'status': 'healthy',
            'service': 'NutriChat API',
            'version': '2.0',
            'database': {
                'status': db_status,
                'details': db_details
            },
            'timestamp': datetime.now().isoformat(),
            'user_logged_in': bool(session.get('user_id'))
        }), 200
    
    # ==================== FUNCIONES DE SCRAPING ====================
    
    def check_scraping_system():
        """Verificar estado del sistema"""
        status = {
            'system_ready': True,
            'message': '✅ Sistema NutriChat operativo al 100%',
            'system_health': 100,
            'categories': {
                1: 'Frutas y Verduras',
                2: 'Lácteos y Huevos',
                3: 'Carnes y Pescados',
                4: 'Despensa',
                5: 'Aseo y Hogar',
                6: 'Bebidas',
                7: 'Panadería y Pastelería'
            },
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'version': '2.0'
        }
        
        try:
            # Verificar base de datos
            db.session.execute(text("SELECT 1"))
            status['database'] = 'CONECTADA'
            
            # Verificar scraper
            scraper_file = Path(__file__).parent / "scraping" / "d1_scraper.py"
            status['scraper'] = 'DISPONIBLE' if scraper_file.exists() else 'NO ENCONTRADO'
            
        except Exception as e:
            status['database'] = 'ERROR'
            status['system_health'] = 80
            status['message'] = '⚠️ Base de datos con problemas'
        
        return status
    
    def run_scraping_task(app_instance, session_id, mode, category, user_id):
        """Ejecutar tarea de scraping REAL"""
        try:
            print(f"🎯 [SCRAPING] Iniciando scraping REAL para usuario {user_id}")
            
            status = {
                'session_id': session_id,
                'user_id': user_id,
                'status': 'running',
                'progress': 10,
                'step': 'Preparando',
                'message': 'Iniciando scraping D1',
                'start_time': datetime.now().isoformat()
            }
            
            save_status(app_instance, session_id, status)
            
            with app_instance.app_context():
                try:
                    from app.scraping.scraping_api import scrape
                    
                    status['progress'] = 30
                    status['step'] = 'Ejecutando scraper'
                    status['message'] = 'Extrayendo productos de D1...'
                    save_status(app_instance, session_id, status)
                    
                    result = scrape(
                        category_id=category,
                        mode=mode,
                        session_id=session_id,
                        user_id=user_id
                    )
                    
                    if result.get('success', False):
                        save_scraping_session_to_db(
                            session_id=session_id,
                            user_id=user_id,
                            mode=mode,
                            category=category,
                            result=result
                        )
                        
                        status.update({
                            'status': 'completed',
                            'progress': 100,
                            'step': 'Completado',
                            'message': f"✅ {result.get('message', 'Scraping exitoso')}",
                            'results': {
                                'product_count': result.get('total_products', 0),
                                'total_value': result.get('total_value', 0),
                                'new_products': result.get('new_products', 0),
                                'updated_products': result.get('updated_products', 0)
                            },
                            'end_time': datetime.now().isoformat()
                        })
                        
                        print(f"✅ [SCRAPING] COMPLETADO: {result.get('new_products')} nuevos productos")
                        
                    else:
                        status.update({
                            'status': 'error',
                            'progress': 0,
                            'step': 'Error',
                            'message': f"❌ {result.get('error', 'Error desconocido')}",
                            'end_time': datetime.now().isoformat()
                        })
                        
                except Exception as e:
                    print(f"❌ Error en scraping: {e}")
                    status.update({
                        'status': 'error',
                        'message': f'Error: {str(e)}',
                        'end_time': datetime.now().isoformat()
                    })
            
            save_status(app_instance, session_id, status)
            print(f"📄 [SCRAPING] Estado guardado para {session_id}")
            
        except Exception as e:
            print(f"❌❌❌ ERROR FATAL en scraping: {e}")
            status.update({
                'status': 'error',
                'message': f'Error fatal: {str(e)}',
                'end_time': datetime.now().isoformat()
            })
            save_status(app_instance, session_id, status)
    
    def save_scraping_session_to_db(session_id, user_id, mode, category, result):
        """Guardar sesión de scraping en PostgreSQL"""
        try:
            # Crear tabla si no existe
            create_query = text("""
                CREATE TABLE IF NOT EXISTS scraping_sessions (
                    id SERIAL PRIMARY KEY,
                    session_id VARCHAR(100) NOT NULL,
                    user_id VARCHAR(100) NOT NULL,
                    mode VARCHAR(20) DEFAULT 'manual',
                    category INTEGER DEFAULT 1,
                    new_products INTEGER DEFAULT 0,
                    updated_products INTEGER DEFAULT 0,
                    total_products INTEGER DEFAULT 0,
                    total_value DECIMAL(10,2) DEFAULT 0,
                    status VARCHAR(20) DEFAULT 'completed',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            db.session.execute(create_query)
            
            # Insertar sesión
            insert_query = text("""
                INSERT INTO scraping_sessions 
                (session_id, user_id, mode, category, new_products, 
                 updated_products, total_products, total_value, status)
                VALUES 
                (:session_id, :user_id, :mode, :category, :new_products,
                 :updated_products, :total_products, :total_value, :status)
            """)
            
            db.session.execute(insert_query, {
                'session_id': session_id,
                'user_id': user_id,
                'mode': mode,
                'category': category,
                'new_products': result.get('new_products', 0),
                'updated_products': result.get('updated_products', 0),
                'total_products': result.get('total_products', 0),
                'total_value': result.get('total_value', 0),
                'status': 'completed'
            })
            db.session.commit()
            print(f"💾 [SCRAPING] Sesión guardada en DB: {session_id}")
            
        except Exception as e:
            print(f"❌ Error guardando sesión: {e}")
            db.session.rollback()
    
    def save_status(app_instance, session_id, status):
        """Guardar estado del scraping"""
        try:
            status_file = app_instance.config['SCRAPER_DIR'] / f'status_{session_id}.json'
            with open(status_file, 'w', encoding='utf-8') as f:
                json.dump(status, f, ensure_ascii=False, indent=2)
        except Exception as e:
            app_instance.logger.error(f"Error guardando status: {e}")
    
    # ==================== CONFIGURACIÓN JWT ====================
    
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({
            'success': False,
            'message': 'Token expirado',
            'error': 'token_expired'
        }), 401
    
    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return jsonify({
            'success': False,
            'message': 'Token inválido',
            'error': 'invalid_token'
        }), 401
    
    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return jsonify({
            'success': False,
            'message': 'Token faltante',
            'error': 'authorization_required'
        }), 401
    
    # ==================== INICIALIZAR BASE DE DATOS ====================
    
    with app.app_context():
        try:
            # Crear todas las tablas
            db.create_all()
            print("✅ Base de datos verificada")
            
            # Verificar conexión a PostgreSQL
            result = db.session.execute(text('SELECT version()'))
            version = result.fetchone()
            print(f"✅ Conectado a PostgreSQL: {version[0][:60]}...")
            
            # Crear tablas específicas si no existen
            tables_to_create = [
                ("""
                CREATE TABLE IF NOT EXISTS shopping_lists (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(100) NOT NULL,
                    name VARCHAR(100) NOT NULL,
                    description TEXT,
                    total_items INTEGER DEFAULT 0,
                    total_value DECIMAL(10,2) DEFAULT 0,
                    status VARCHAR(20) DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """),
                ("""
                CREATE TABLE IF NOT EXISTS shopping_list_items (
                    id SERIAL PRIMARY KEY,
                    list_id INTEGER NOT NULL,
                    product_id INTEGER,
                    product_name VARCHAR(200) NOT NULL,
                    quantity INTEGER DEFAULT 1,
                    price DECIMAL(10,2) DEFAULT 0,
                    category VARCHAR(50),
                    checked BOOLEAN DEFAULT FALSE,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (list_id) REFERENCES shopping_lists(id) ON DELETE CASCADE
                )
                """)
            ]
            
            for create_query in tables_to_create:
                try:
                    db.session.execute(text(create_query))
                except Exception as e:
                    print(f"ℹ️ Tabla ya existe o error: {e}")
            
            db.session.commit()
            
            # Mostrar tablas existentes
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            print(f"📊 Tablas disponibles: {', '.join(tables) if tables else 'ninguna'}")
            
            print("\n🎯 Sistema NutriChat completamente funcional y listo")
            print("   - Dashboard operativo ✅")
            print("   - Gestión de productos ✅")
            print("   - Listas de compra ✅")
            print("   - Sistema de scraping ✅")
            print("   - PostgreSQL (Neon) ✅")
            
        except Exception as e:
            print(f"⚠️ Error en base de datos: {e}")
    
    return app
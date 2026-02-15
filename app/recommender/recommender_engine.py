"""
Motor de Recomendaciones Avanzado - Versión Light (Funciona en Windows)
"""
import os
import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from collections import Counter, defaultdict
import logging

# Machine Learning básico
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans

# Importaciones de la app
from app.models.database import db
from sqlalchemy import text

logger = logging.getLogger(__name__)

class RecommenderEngine:
    """
    Motor de Recomendaciones - Versión Estable para Windows
    """
    
    def __init__(self):
        self.user_vectors = {}
        self.product_vectors = {}
        self.similarity_matrix = None
        self.product_features = None
        self.user_clusters = {}
        
        # Modelos
        self.tfidf = TfidfVectorizer(max_features=100, stop_words='spanish')
        self.scaler = StandardScaler()
    
    # ==================== ENTRENAMIENTO ====================
    
    def train_models(self, user_id: Optional[str] = None):
        """Entrena modelos con datos actuales"""
        logger.info("🚀 Entrenando modelos de recomendación...")
        
        products = self._get_all_products(user_id)
        user_history = self._get_user_history(user_id)
        
        if not products:
            logger.warning("⚠️ No hay suficientes productos para entrenar")
            return
        
        self._create_product_vectors(products)
        self._create_similarity_matrix()
        
        if len(products) >= 10:
            self._cluster_products(products)
        
        if user_id:
            self._create_user_profile(user_id, user_history)
        
        logger.info(f"✅ Modelos entrenados: {len(products)} productos")
    
    def _get_all_products(self, user_id: Optional[str] = None) -> List[Dict]:
        """Obtiene productos del sistema"""
        try:
            if user_id:
                query = text("""
                    SELECT id, name, category, price, source, description 
                    FROM user_products 
                    WHERE user_id = :user_id
                """)
                result = db.session.execute(query, {'user_id': user_id})
            else:
                query = text("""
                    SELECT id, name, category, price, source, description 
                    FROM user_products 
                    LIMIT 1000
                """)
                result = db.session.execute(query)
            
            products = []
            for row in result:
                products.append({
                    'id': row[0],
                    'name': row[1] or '',
                    'category': row[2] or 'General',
                    'price': float(row[3]) if row[3] else 0,
                    'source': row[4] or 'manual',
                    'description': row[5] or ''
                })
            return products
        except Exception as e:
            logger.error(f"Error obteniendo productos: {e}")
            return []
    
    def _get_user_history(self, user_id: str) -> Dict:
        """Obtiene historial del usuario"""
        try:
            query = text("""
                SELECT id, name, category, price, added_date
                FROM user_products 
                WHERE user_id = :user_id
                ORDER BY added_date DESC
            """)
            result = db.session.execute(query, {'user_id': user_id})
            
            history = []
            for row in result:
                history.append({
                    'id': row[0],
                    'name': row[1],
                    'category': row[2],
                    'price': float(row[3]) if row[3] else 0,
                    'date': row[4]
                })
            
            return {
                'products': history,
                'total_products': len(history)
            }
        except Exception as e:
            logger.error(f"Error obteniendo historial: {e}")
            return {'products': [], 'total_products': 0}
    
    def _create_product_vectors(self, products: List[Dict]):
        """Crea vectores para productos"""
        texts = [f"{p['name']} {p['category']} {p['description']}" for p in products]
        
        if texts:
            self.product_features = self.tfidf.fit_transform(texts)
        
        numeric_features = []
        for p in products:
            numeric_features.append([
                p['price'] / 100000,
                self._category_to_idx(p['category'])
            ])
        
        if numeric_features:
            self.numeric_features = self.scaler.fit_transform(numeric_features)
        
        for i, p in enumerate(products):
            vector = {
                'tfidf': self.product_features[i].toarray()[0] if self.product_features is not None else None,
                'numeric': self.numeric_features[i] if self.numeric_features is not None else None,
                'category_idx': self._category_to_idx(p['category'])
            }
            self.product_vectors[p['id']] = vector
    
    def _create_similarity_matrix(self):
        """Crea matriz de similitud"""
        n_products = len(self.product_vectors)
        if n_products == 0:
            return
        
        combined_features = []
        self.product_ids = list(self.product_vectors.keys())
        
        for pid in self.product_ids:
            vec = self.product_vectors[pid]
            feat = []
            if vec['tfidf'] is not None:
                feat.extend(vec['tfidf'])
            if vec['numeric'] is not None:
                feat.extend(vec['numeric'])
            combined_features.append(feat)
        
        if combined_features:
            self.similarity_matrix = cosine_similarity(combined_features)
    
    def _cluster_products(self, products: List[Dict], n_clusters: int = 5):
        """Agrupa productos en clusters"""
        if len(products) < n_clusters:
            return
        
        features = []
        for p in products:
            vec = self.product_vectors.get(p['id'], {})
            feat = []
            if vec.get('tfidf') is not None:
                feat.extend(vec['tfidf'][:20])
            if vec.get('numeric') is not None:
                feat.extend(vec['numeric'])
            features.append(feat)
        
        if features:
            kmeans = KMeans(n_clusters=min(n_clusters, len(products)), random_state=42, n_init=10)
            clusters = kmeans.fit_predict(features)
            
            for i, p in enumerate(products):
                if p['id'] in self.product_vectors:
                    self.product_vectors[p['id']]['cluster'] = int(clusters[i])
    
    def _create_user_profile(self, user_id: str, history: Dict):
        """Crea perfil del usuario"""
        if not history['products']:
            return
        
        user_vector = []
        weights = []
        
        for product in history['products']:
            vec = self.product_vectors.get(product['id'])
            if vec:
                days_ago = 0
                if product.get('date'):
                    days_ago = (datetime.now() - product['date']).days
                weight = np.exp(-days_ago / 30)
                
                feat = []
                if vec['tfidf'] is not None:
                    feat.extend(vec['tfidf'])
                if vec['numeric'] is not None:
                    feat.extend(vec['numeric'])
                
                if feat:
                    user_vector.append(np.array(feat) * weight)
                    weights.append(weight)
        
        if user_vector:
            self.user_vectors[user_id] = np.average(user_vector, axis=0, weights=weights)
    
    # ==================== RECOMENDACIONES ====================
    
    def get_recommendations(self, user_id: str, n_recommendations: int = 10) -> List[Dict]:
        """Obtiene recomendaciones personalizadas"""
        recommendations = []
        history = self._get_user_history(user_id)
        
        if not history['products']:
            return self._get_popular_products(n_recommendations)
        
        if not self.product_vectors:
            self.train_models(user_id)
        
        # Estrategias de recomendación
        content_based = self._content_based_filtering(user_id, history, n_recommendations)
        category_based = self._category_based_recommendations(user_id, history, n_recommendations)
        trending = self._trending_products(n_recommendations)
        
        all_recs = content_based + category_based + trending
        
        seen = {p['id'] for p in history['products']}
        unique_recs = []
        seen_ids = set()
        
        for rec in all_recs:
            if rec['id'] not in seen and rec['id'] not in seen_ids:
                seen_ids.add(rec['id'])
                unique_recs.append(rec)
        
        unique_recs.sort(key=lambda x: x.get('score', 0), reverse=True)
        return unique_recs[:n_recommendations]
    
    def _content_based_filtering(self, user_id: str, history: Dict, n: int) -> List[Dict]:
        """Recomendaciones basadas en contenido similar"""
        if not history['products'] or not self.similarity_matrix:
            return []
        
        recommendations = []
        
        for product in history['products'][:3]:
            try:
                if product['id'] not in self.product_ids:
                    continue
                    
                idx = self.product_ids.index(product['id'])
                similarities = self.similarity_matrix[idx]
                
                top_indices = np.argsort(similarities)[-4:-1][::-1]
                
                for sim_idx in top_indices:
                    similar_id = self.product_ids[sim_idx]
                    if similar_id != product['id']:
                        for p in history['products']:
                            if p['id'] == similar_id:
                                recommendations.append({
                                    'id': similar_id,
                                    'name': p['name'],
                                    'category': p['category'],
                                    'price': p['price'],
                                    'reason': f'Similar a {product["name"][:20]}...',
                                    'score': float(similarities[sim_idx]),
                                    'source': 'content_based'
                                })
                                break
            except Exception as e:
                continue
        
        return recommendations
    
    def _category_based_recommendations(self, user_id: str, history: Dict, n: int) -> List[Dict]:
        """Recomendaciones basadas en categorías favoritas"""
        if not history['products']:
            return []
        
        categories = Counter([p['category'] for p in history['products']])
        top_categories = [cat for cat, _ in categories.most_common(3)]
        
        recommendations = []
        
        for category in top_categories:
            try:
                query = text("""
                    SELECT id, name, category, price
                    FROM user_products 
                    WHERE user_id != :user_id AND category = :category
                    LIMIT 3
                """)
                
                result = db.session.execute(query, {
                    'user_id': user_id,
                    'category': category
                }).fetchall()
                
                for row in result:
                    recommendations.append({
                        'id': row[0],
                        'name': row[1],
                        'category': row[2],
                        'price': float(row[3]),
                        'reason': f'Basado en tu interés en {category}',
                        'score': 0.7,
                        'source': 'category_based'
                    })
            except:
                continue
        
        return recommendations
    
    def _trending_products(self, n: int) -> List[Dict]:
        """Productos populares/tendencias"""
        try:
            query = text("""
                SELECT id, name, category, price
                FROM user_products 
                ORDER BY id DESC
                LIMIT 10
            """)
            
            result = db.session.execute(query).fetchall()
            
            recommendations = []
            for row in result:
                recommendations.append({
                    'id': row[0],
                    'name': row[1],
                    'category': row[2],
                    'price': float(row[3]),
                    'reason': 'Producto popular',
                    'score': 0.5,
                    'source': 'trending'
                })
            
            return recommendations
        except:
            return []
    
    def _get_popular_products(self, n: int) -> List[Dict]:
        """Productos populares para usuarios nuevos"""
        try:
            query = text("""
                SELECT id, name, category, price
                FROM user_products 
                LIMIT :limit
            """)
            
            result = db.session.execute(query, {'limit': n}).fetchall()
            
            recommendations = []
            for row in result:
                recommendations.append({
                    'id': row[0],
                    'name': row[1],
                    'category': row[2],
                    'price': float(row[3]),
                    'reason': 'Producto recomendado',
                    'score': 0.5,
                    'source': 'popular'
                })
            
            return recommendations
        except:
            return []
    
    # ==================== NUTRICIÓN ====================
    
    def get_nutritional_recommendations(self, user_id: str) -> Dict:
        """Recomendaciones nutricionales básicas"""
        history = self._get_user_history(user_id)
        
        if not history['products']:
            return {
                'message': 'Agrega productos para recibir recomendaciones',
                'recommendations': []
            }
        
        categories = Counter([p['category'] for p in history['products']])
        total = len(history['products'])
        
        recommendations = []
        
        if categories.get('Frutas y Verduras', 0) < total * 0.3:
            recommendations.append({
                'type': 'balance',
                'title': '🍎 Más frutas y verduras',
                'description': 'Incrementa tu consumo de frutas y verduras',
                'action': 'Revisa nuestra sección de productos frescos'
            })
        
        if categories.get('Carnes y Pescados', 0) > total * 0.5:
            recommendations.append({
                'type': 'balance',
                'title': '🥩 Balancea tus proteínas',
                'description': 'Alterna con proteínas vegetales',
                'action': 'Prueba legumbres y frutos secos'
            })
        
        if len(categories) < 3:
            recommendations.append({
                'type': 'variety',
                'title': '🔄 Aumenta tu variedad',
                'description': 'Explora nuevas categorías',
                'action': 'Descubre productos de diferentes secciones'
            })
        
        return {
            'message': 'Recomendaciones para tu salud',
            'recommendations': recommendations,
            'stats': {
                'total_products': total,
                'categories': len(categories)
            }
        }
    
    # ==================== UTILIDADES ====================
    
    def _category_to_idx(self, category: str) -> int:
        """Convierte categoría a índice"""
        categories = {
            'Frutas y Verduras': 1,
            'Lácteos y Huevos': 2,
            'Carnes y Pescados': 3,
            'Despensa': 4,
            'Aseo y Hogar': 5,
            'Bebidas': 6,
            'Panadería y Pastelería': 7
        }
        return categories.get(category, 0)
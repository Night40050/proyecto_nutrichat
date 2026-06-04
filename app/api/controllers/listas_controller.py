"""
Controlador para gestión de listas de mercado en NutriChat
"""
from flask import request, jsonify
from flask_jwt_extended import get_jwt_identity
from sqlalchemy.exc import IntegrityError
from decimal import Decimal, InvalidOperation
import uuid
from app.models.database import db
from app.models.listas import ListaMercado, ProductosEnLista
from app.models.productos import Producto
import logging

logger = logging.getLogger(__name__)


class ListasController:
    # ==================== LISTAS DE MERCADO ====================
    
    @staticmethod
    def create_lista():
        """
        Crear una nueva lista de mercado
        
        Body JSON:
        {
            "nombre": "Lista Semanal",     // OPCIONAL
            "descripcion": "..."          // OPCIONAL
        }
        
        Response:
        {
            "success": true,
            "message": "Lista creada exitosamente",
            "data": {...}
        }
        """
        try:
            user_id = get_jwt_identity()
            data = request.get_json() or {}
            
            # Convertir user_id string a UUID
            try:
                usuario_id = uuid.UUID(user_id)
            except (ValueError, TypeError):
                return jsonify({
                    'success': False,
                    'message': 'ID de usuario inválido'
                }), 400
            
            # Crear lista usando método del modelo
            lista = ListaMercado.create_lista(
                usuario_id=usuario_id,
                nombre=data.get('nombre'),
                descripcion=data.get('descripcion')
            )
            
            # Guardar en base de datos
            db.session.add(lista)
            db.session.commit()
            
            logger.info(f"Lista creada exitosamente - Usuario ID: {usuario_id}, Nombre: {data.get('nombre')}")
            
            return jsonify({
                'success': True,
                'message': 'Lista creada exitosamente',
                'data': lista.to_json_safe()
            }), 201
            
        except ValueError as e:
            db.session.rollback()
            return jsonify({
                'success': False,
                'message': str(e)
            }), 400
            
        except IntegrityError as e:
            db.session.rollback()
            logger.error(f"Error de integridad: {str(e)}")
            return jsonify({
                'success': False,
                'message': 'Error de integridad al crear lista'
            }), 409
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error al crear lista: {str(e)}")
            return jsonify({
                'success': False,
                'message': f'Error interno del servidor: {str(e)}'
            }), 500

    @staticmethod
    def create_lista_completa():
        """
        Crear una lista de mercado y sus productos asociados en una sola petición
        """
        try:
            user_id = get_jwt_identity()
            data = request.get_json() or {}
            
            usuario_id = uuid.UUID(user_id)
            
            # 1. Capturar campos principales que vienen de n8n
            nombre_lista = data.get('nombre_lista', 'Lista de Mercado')
            descripcion = data.get('descripcion', '')
            
            # Capturar el total que calculó Gemini por si acaso
            total_raw = data.get('total_estimado', 0)
            try:
                total_inicial = Decimal(str(total_raw))
            except (ValueError, TypeError, InvalidOperation):
                total_inicial = Decimal('0.00')
            
            # Crear la cabecera pasando el total inicial
            lista = ListaMercado(
                usuario_id=usuario_id,
                nombre=nombre_lista,
                descripcion=descripcion,
                total_estimado=total_inicial # ─── GUARDADO CORRECTO DEL TOTAL ───
            )
            
            db.session.add(lista)
            db.session.flush() # Mantiene el ID de la lista en memoria antes del commit
            
            # 2. Procesar y asociar los productos si vienen en la petición
            productos_data = data.get('productos', [])
            total_calculado = Decimal('0.00') # Para verificar sumatorias reales
            
            for p in productos_data:
                producto_id = p.get('producto_id')
                if not producto_id:
                    continue
                
                # Convertir los valores al formato correcto
                cantidad = Decimal(str(p.get('cantidad', 1)))
                precio_unitario = Decimal(str(p.get('precio_unitario', 0)))
                notas = p.get('notas', p.get('justificacion', ''))
                
                # Sumar al acumulador real
                total_calculado += cantidad * precio_unitario
                
                # Crear la relación usando el modelo existente
                item = ProductosEnLista.create_item_lista(
                    lista_id=lista.id,
                    producto_id=uuid.UUID(producto_id),
                    cantidad=cantidad,
                    precio_unitario=precio_unitario,
                    notas=notas
                )
                db.session.add(item)
            
            # Opcional: Si el total calculado difiere del enviado por fallos de redondeo de la IA, 
            # aseguramos la consistencia guardando la suma exacta de los productos reales.
            if total_calculado > 0:
                lista.total_estimado = total_calculado
            
            # Confirmar toda la transacción en la base de datos (Cabecera + Productos)
            db.session.commit()
            
            logger.info(f"Lista completa creada exitosamente - ID: {lista.id} con Total: {lista.total_estimado}")
            return jsonify({
                'success': True,
                'message': 'Lista y productos guardados correctamente',
                'lista_id': str(lista.id),
                'total_guardado': float(lista.total_estimado)
            }), 201
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error al crear lista completa: {str(e)}")
            return jsonify({
                'success': False,
                'message': f'Error interno: {str(e)}'
            }), 500

    @staticmethod
    def get_listas_by_usuario():
        """
        Obtener listas del usuario autenticado
        
        Response:
        {
            "success": true,
            "data": [...]
        }
        """
        try:
            user_id = get_jwt_identity()
            
            # Convertir user_id string a UUID
            try:
                usuario_id = uuid.UUID(user_id)
            except (ValueError, TypeError):
                return jsonify({
                    'success': False,
                    'message': 'ID de usuario inválido'
                }), 400
            
            listas = ListaMercado.get_by_usuario(usuario_id)
            
            return jsonify({
                'success': True,
                'data': [lista.to_json_safe() for lista in listas],
                'count': len(listas)
            }), 200
            
        except Exception as e:
            logger.error(f"Error al obtener listas por usuario: {str(e)}")
            return jsonify({
                'success': False,
                'message': 'Error interno del servidor'
            }), 500
    
    @staticmethod
    def get_lista_by_id(lista_id):
        """
        Obtener lista por ID (solo si pertenece al usuario autenticado)
        
        Parámetros:
        - lista_id: ID de la lista (UUID)
        
        Response:
        {
            "success": true,
            "data": {...}
        }
        """
        try:
            user_id = get_jwt_identity()
            
            # Convertir IDs string a UUID
            try:
                usuario_id = uuid.UUID(user_id)
                lista_uuid = uuid.UUID(lista_id)
            except (ValueError, TypeError):
                return jsonify({
                    'success': False,
                    'message': 'ID inválido'
                }), 400
            
            lista = ListaMercado.query.get(lista_uuid)
            
            if not lista:
                return jsonify({
                    'success': False,
                    'message': 'Lista no encontrada'
                }), 404
            
            # Verificar que la lista pertenece al usuario autenticado
            if lista.usuario_id != usuario_id:
                return jsonify({
                    'success': False,
                    'message': 'No tienes permiso para acceder a esta lista'
                }), 403
            
            return jsonify({
                'success': True,
                'data': lista.to_json_safe()
            }), 200
            
        except Exception as e:
            logger.error(f"Error al buscar lista por ID: {str(e)}")
            return jsonify({
                'success': False,
                'message': 'Error interno del servidor'
            }), 500
    
    @staticmethod
    def update_lista(lista_id):
        """
        Actualizar lista de mercado
        
        Parámetros:
        - lista_id: ID de la lista (UUID)
        
        Body JSON (todos opcionales):
        {
            "nombre": "...",
            "descripcion": "..."
        }
        
        Response:
        {
            "success": true,
            "message": "Lista actualizada exitosamente",
            "data": {...}
        }
        """
        try:
            user_id = get_jwt_identity()
            
            # Convertir IDs string a UUID
            try:
                usuario_id = uuid.UUID(user_id)
                lista_uuid = uuid.UUID(lista_id)
            except (ValueError, TypeError):
                return jsonify({
                    'success': False,
                    'message': 'ID inválido'
                }), 400
            
            lista = ListaMercado.query.get(lista_uuid)
            
            if not lista:
                return jsonify({
                    'success': False,
                    'message': 'Lista no encontrada'
                }), 404
            
            # Verificar que la lista pertenece al usuario autenticado
            if lista.usuario_id != usuario_id:
                return jsonify({
                    'success': False,
                    'message': 'No tienes permiso para modificar esta lista'
                }), 403
            
            data = request.get_json()
            if not data:
                return jsonify({
                    'success': False,
                    'message': 'No se enviaron datos'
                }), 400
            
            # Campos actualizables
            if 'nombre' in data:
                lista.nombre = data['nombre'].strip() if data['nombre'] else None
            if 'descripcion' in data:
                lista.descripcion = data['descripcion'].strip() if data['descripcion'] else None
            
            # Actualizar timestamp
            lista.update_timestamp()
            
            db.session.commit()
            
            logger.info(f"Lista actualizada exitosamente - ID: {lista_id}")
            
            return jsonify({
                'success': True,
                'message': 'Lista actualizada exitosamente',
                'data': lista.to_json_safe()
            }), 200
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error al actualizar lista: {str(e)}")
            return jsonify({
                'success': False,
                'message': 'Error interno del servidor'
            }), 500
    
    @staticmethod
    def delete_lista(lista_id):
        """
        Eliminar lista de mercado
        
        Parámetros:
        - lista_id: ID de la lista (UUID)
        
        Response:
        {
            "success": true,
            "message": "Lista eliminada exitosamente"
        }
        """
        try:
            user_id = get_jwt_identity()
            
            # Convertir IDs string a UUID
            try:
                usuario_id = uuid.UUID(user_id)
                lista_uuid = uuid.UUID(lista_id)
            except (ValueError, TypeError):
                return jsonify({
                    'success': False,
                    'message': 'ID inválido'
                }), 400
            
            lista = ListaMercado.query.get(lista_uuid)
            
            if not lista:
                return jsonify({
                    'success': False,
                    'message': 'Lista no encontrada'
                }), 404
            
            # Verificar que la lista pertenece al usuario autenticado
            if lista.usuario_id != usuario_id:
                return jsonify({
                    'success': False,
                    'message': 'No tienes permiso para eliminar esta lista'
                }), 403
            
            db.session.delete(lista)
            db.session.commit()
            
            logger.info(f"Lista eliminada exitosamente - ID: {lista_id}")
            
            return jsonify({
                'success': True,
                'message': 'Lista eliminada exitosamente'
            }), 200
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error al eliminar lista: {str(e)}")
            return jsonify({
                'success': False,
                'message': 'Error interno del servidor'
            }), 500
    
    @staticmethod
    def search_listas_by_nombre():
        """
        Buscar listas por nombre (búsqueda parcial)
        
        Query params:
        - nombre: Nombre a buscar (requerido)
        
        Response:
        {
            "success": true,
            "data": [...]
        }
        """
        try:
            user_id = get_jwt_identity()
            nombre = request.args.get('nombre')
            
            if not nombre:
                return jsonify({
                    'success': False,
                    'message': 'nombre es requerido como query parameter'
                }), 400
            
            # Convertir user_id string a UUID
            try:
                usuario_id = uuid.UUID(user_id)
            except (ValueError, TypeError):
                return jsonify({
                    'success': False,
                    'message': 'ID de usuario inválido'
                }), 400
            
            listas = ListaMercado.get_by_nombre(usuario_id, nombre)
            
            return jsonify({
                'success': True,
                'data': [lista.to_json_safe() for lista in listas],
                'count': len(listas)
            }), 200
            
        except Exception as e:
            logger.error(f"Error al buscar listas por nombre: {str(e)}")
            return jsonify({
                'success': False,
                'message': 'Error interno del servidor'
            }), 500
    
    # ==================== PRODUCTOS EN LISTA ====================
    
    @staticmethod
    def add_producto_to_lista(lista_id):
        """
        Agregar producto a una lista
        
        Parámetros:
        - lista_id: ID de la lista (UUID)
        
        Body JSON:
        {
            "producto_id": "uuid",        // REQUERIDO
            "cantidad": 2.5,              // OPCIONAL (default: 1)
            "unidad_medida": "kg",        // OPCIONAL
            "precio_unitario": 25.50,     // OPCIONAL
            "notas": "..."               // OPCIONAL
        }
        
        Response:
        {
            "success": true,
            "message": "Producto agregado a la lista exitosamente",
            "data": {...}
        }
        """
        try:
            user_id = get_jwt_identity()
            data = request.get_json()
            
            if not data:
                return jsonify({
                    'success': False,
                    'message': 'No se enviaron datos'
                }), 400
            
            producto_id = data.get('producto_id')
            
            if not producto_id:
                return jsonify({
                    'success': False,
                    'message': 'producto_id es requerido'
                }), 400
            
            # Convertir IDs string a UUID
            try:
                usuario_id = uuid.UUID(user_id)
                lista_uuid = uuid.UUID(lista_id)
                producto_uuid = uuid.UUID(producto_id)
            except (ValueError, TypeError):
                return jsonify({
                    'success': False,
                    'message': 'ID inválido: debe ser un UUID válido'
                }), 400
            
            # Verificar que la lista existe y pertenece al usuario
            lista = ListaMercado.query.get(lista_uuid)
            if not lista:
                return jsonify({
                    'success': False,
                    'message': 'Lista no encontrada'
                }), 404
            
            if lista.usuario_id != usuario_id:
                return jsonify({
                    'success': False,
                    'message': 'No tienes permiso para modificar esta lista'
                }), 403
            
            # Verificar que el producto existe
            producto = Producto.query.get(producto_uuid)
            if not producto:
                return jsonify({
                    'success': False,
                    'message': 'Producto no encontrado'
                }), 404
            
            # Verificar si el producto ya está en la lista
            item_existente = ProductosEnLista.get_item(lista_uuid, producto_uuid)
            if item_existente:
                return jsonify({
                    'success': False,
                    'message': 'Este producto ya está en la lista'
                }), 409
            
            # Convertir cantidad a Decimal si se proporciona
            cantidad = None
            if 'cantidad' in data and data['cantidad'] is not None:
                try:
                    cantidad = Decimal(str(data['cantidad']))
                    if cantidad <= 0:
                        return jsonify({
                            'success': False,
                            'message': 'La cantidad debe ser mayor a cero'
                        }), 400
                except (InvalidOperation, ValueError, TypeError):
                    return jsonify({
                        'success': False,
                        'message': 'cantidad debe ser un número válido'
                    }), 400
            
            # Convertir precio_unitario a Decimal si se proporciona
            precio_unitario = None
            if 'precio_unitario' in data and data['precio_unitario'] is not None:
                try:
                    precio_unitario = Decimal(str(data['precio_unitario']))
                    if precio_unitario < 0:
                        return jsonify({
                            'success': False,
                            'message': 'El precio no puede ser negativo'
                        }), 400
                except (InvalidOperation, ValueError, TypeError):
                    return jsonify({
                        'success': False,
                        'message': 'precio_unitario debe ser un número válido'
                    }), 400
            
            # Crear item usando método del modelo
            item = ProductosEnLista.create_item_lista(
                lista_id=lista_uuid,
                producto_id=producto_uuid,
                cantidad=cantidad,
                unidad_medida=data.get('unidad_medida'),
                precio_unitario=precio_unitario,
                notas=data.get('notas')
            )
            
            # Guardar en base de datos
            db.session.add(item)
            
            # Actualizar timestamp de la lista
            lista.update_timestamp()
            
            db.session.commit()
            
            logger.info(f"Producto agregado a lista exitosamente - Lista ID: {lista_id}, Producto ID: {producto_id}")
            
            return jsonify({
                'success': True,
                'message': 'Producto agregado a la lista exitosamente',
                'data': item.to_json_safe()
            }), 201
            
        except ValueError as e:
            db.session.rollback()
            return jsonify({
                'success': False,
                'message': str(e)
            }), 400
            
        except IntegrityError as e:
            db.session.rollback()
            logger.error(f"Error de integridad: {str(e)}")
            return jsonify({
                'success': False,
                'message': 'Error de integridad al agregar producto'
            }), 409
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error al agregar producto a lista: {str(e)}")
            return jsonify({
                'success': False,
                'message': f'Error interno del servidor: {str(e)}'
            }), 500
    
    @staticmethod
    def get_productos_by_lista(lista_id):
        """
        Obtener productos de una lista
        
        Parámetros:
        - lista_id: ID de la lista (UUID)
        
        Response:
        {
            "success": true,
            "data": [...]
        }
        """
        try:
            user_id = get_jwt_identity()
            
            # Convertir IDs string a UUID
            try:
                usuario_id = uuid.UUID(user_id)
                lista_uuid = uuid.UUID(lista_id)
            except (ValueError, TypeError):
                return jsonify({
                    'success': False,
                    'message': 'ID inválido'
                }), 400
            
            # Verificar que la lista existe y pertenece al usuario
            lista = ListaMercado.query.get(lista_uuid)
            if not lista:
                return jsonify({
                    'success': False,
                    'message': 'Lista no encontrada'
                }), 404
            
            if lista.usuario_id != usuario_id:
                return jsonify({
                    'success': False,
                    'message': 'No tienes permiso para acceder a esta lista'
                }), 403
            
            productos = ProductosEnLista.get_by_lista(lista_uuid)
            
            return jsonify({
                'success': True,
                'data': [item.to_json_safe() for item in productos],
                'count': len(productos)
            }), 200
            
        except Exception as e:
            logger.error(f"Error al obtener productos de lista: {str(e)}")
            return jsonify({
                'success': False,
                'message': 'Error interno del servidor'
            }), 500
    
    @staticmethod
    def update_producto_in_lista(lista_id, producto_id):
        """
        Actualizar producto en lista
        
        Parámetros:
        - lista_id: ID de la lista (UUID)
        - producto_id: ID del producto (UUID)
        
        Body JSON (todos opcionales):
        {
            "cantidad": 3.0,
            "unidad_medida": "kg",
            "precio_unitario": 30.00,
            "notas": "..."
        }
        
        Response:
        {
            "success": true,
            "message": "Producto actualizado exitosamente",
            "data": {...}
        }
        """
        try:
            user_id = get_jwt_identity()
            data = request.get_json()
            
            if not data:
                return jsonify({
                    'success': False,
                    'message': 'No se enviaron datos'
                }), 400
            
            # Convertir IDs string a UUID
            try:
                usuario_id = uuid.UUID(user_id)
                lista_uuid = uuid.UUID(lista_id)
                producto_uuid = uuid.UUID(producto_id)
            except (ValueError, TypeError):
                return jsonify({
                    'success': False,
                    'message': 'ID inválido'
                }), 400
            
            # Verificar que la lista existe y pertenece al usuario
            lista = ListaMercado.query.get(lista_uuid)
            if not lista:
                return jsonify({
                    'success': False,
                    'message': 'Lista no encontrada'
                }), 404
            
            if lista.usuario_id != usuario_id:
                return jsonify({
                    'success': False,
                    'message': 'No tienes permiso para modificar esta lista'
                }), 403
            
            # Buscar el item
            item = ProductosEnLista.get_item(lista_uuid, producto_uuid)
            if not item:
                return jsonify({
                    'success': False,
                    'message': 'Producto no encontrado en la lista'
                }), 404
            
            # Actualizar campos
            if 'cantidad' in data and data['cantidad'] is not None:
                try:
                    cantidad = Decimal(str(data['cantidad']))
                    if cantidad <= 0:
                        return jsonify({
                            'success': False,
                            'message': 'La cantidad debe ser mayor a cero'
                        }), 400
                    item.actualizar_cantidad(cantidad)
                except (InvalidOperation, ValueError, TypeError) as e:
                    return jsonify({
                        'success': False,
                        'message': f'cantidad inválida: {str(e)}'
                    }), 400
            
            if 'unidad_medida' in data:
                item.unidad_medida = data['unidad_medida'].strip() if data['unidad_medida'] else None
            
            if 'precio_unitario' in data and data['precio_unitario'] is not None:
                try:
                    precio = Decimal(str(data['precio_unitario']))
                    if precio < 0:
                        return jsonify({
                            'success': False,
                            'message': 'El precio no puede ser negativo'
                        }), 400
                    item.establecer_precio(precio)
                except (InvalidOperation, ValueError, TypeError) as e:
                    return jsonify({
                        'success': False,
                        'message': f'precio_unitario inválido: {str(e)}'
                    }), 400
            
            if 'notas' in data:
                item.notas = data['notas'].strip() if data['notas'] else None
            
            # Actualizar timestamp de la lista
            lista.update_timestamp()
            
            db.session.commit()
            
            logger.info(f"Producto actualizado en lista exitosamente - Lista ID: {lista_id}, Producto ID: {producto_id}")
            
            return jsonify({
                'success': True,
                'message': 'Producto actualizado exitosamente',
                'data': item.to_json_safe()
            }), 200
            
        except ValueError as e:
            db.session.rollback()
            return jsonify({
                'success': False,
                'message': str(e)
            }), 400
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error al actualizar producto en lista: {str(e)}")
            return jsonify({
                'success': False,
                'message': 'Error interno del servidor'
            }), 500
    
    @staticmethod
    def remove_producto_from_lista(lista_id, producto_id):
        """
        Eliminar producto de una lista
        
        Parámetros:
        - lista_id: ID de la lista (UUID)
        - producto_id: ID del producto (UUID)
        
        Response:
        {
            "success": true,
            "message": "Producto eliminado de la lista exitosamente"
        }
        """
        try:
            user_id = get_jwt_identity()
            
            # Convertir IDs string a UUID
            try:
                usuario_id = uuid.UUID(user_id)
                lista_uuid = uuid.UUID(lista_id)
                producto_uuid = uuid.UUID(producto_id)
            except (ValueError, TypeError):
                return jsonify({
                    'success': False,
                    'message': 'ID inválido'
                }), 400
            
            # Verificar que la lista existe y pertenece al usuario
            lista = ListaMercado.query.get(lista_uuid)
            if not lista:
                return jsonify({
                    'success': False,
                    'message': 'Lista no encontrada'
                }), 404
            
            if lista.usuario_id != usuario_id:
                return jsonify({
                    'success': False,
                    'message': 'No tienes permiso para modificar esta lista'
                }), 403
            
            # Buscar el item
            item = ProductosEnLista.get_item(lista_uuid, producto_uuid)
            if not item:
                return jsonify({
                    'success': False,
                    'message': 'Producto no encontrado en la lista'
                }), 404
            
            db.session.delete(item)
            
            # Actualizar timestamp de la lista
            lista.update_timestamp()
            
            db.session.commit()
            
            logger.info(f"Producto eliminado de lista exitosamente - Lista ID: {lista_id}, Producto ID: {producto_id}")
            
            return jsonify({
                'success': True,
                'message': 'Producto eliminado de la lista exitosamente'
            }), 200
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error al eliminar producto de lista: {str(e)}")
            return jsonify({
                'success': False,
                'message': 'Error interno del servidor'
            }), 500


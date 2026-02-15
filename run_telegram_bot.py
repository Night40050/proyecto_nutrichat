"""
Script para ejecutar el bot de Telegram
"""
import os
import sys
from pathlib import Path

# Agregar directorio raíz al path
sys.path.append(str(Path(__file__).parent))

from app.telegram_bot import main

if __name__ == '__main__':
    main()
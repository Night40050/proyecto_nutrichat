"""
Configurar Tesseract para Windows
"""
import os
import sys
import subprocess
from pathlib import Path

def setup_tesseract():
    """Configurar Tesseract para la aplicación"""
    
    print("🔧 Configurando Tesseract para NutriChat...")
    print("=" * 50)
    
    # RUTAS COMUNES DE TESSERACT EN WINDOWS
    tesseract_paths = [
        # Ruta por defecto instalación nueva
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files\Tesseract-OCR",
        # Ruta alternativa
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR",
        # Ruta instalación manual
        r"C:\tesseract\tesseract.exe",
        r"C:\tesseract",
        # Ruta AppData
        str(Path.home() / "AppData" / "Local" / "Programs" / "Tesseract-OCR"),
    ]
    
    found_path = None
    tesseract_exe = None
    
    # Buscar Tesseract
    for path in tesseract_paths:
        if os.path.exists(path):
            if path.endswith('.exe'):
                tesseract_exe = path
                found_path = str(Path(path).parent)
                print(f"✅ Tesseract encontrado en: {path}")
                break
            else:
                exe_path = Path(path) / "tesseract.exe"
                if exe_path.exists():
                    tesseract_exe = str(exe_path)
                    found_path = path
                    print(f"✅ Tesseract encontrado en: {exe_path}")
                    break
    
    if not found_path:
        print("❌ TESSERACT NO ENCONTRADO")
        print("\n📥 POR FAVOR INSTALA TESSERACT:")
        print("1. Ve a: https://github.com/UB-Mannheim/tesseract/wiki")
        print("2. Descarga: tesseract-ocr-w64-setup-5.3.3.20231005.exe")
        print("3. Ejecuta COMO ADMINISTRADOR")
        print("4. Durante instalación MARCA: 'Add to PATH'")
        print("5. Instala en: C:\\Program Files\\Tesseract-OCR")
        print("6. REINICIA tu computadora")
        return False
    
    # Configurar variable de entorno
    os.environ['TESSERACT_PATH'] = found_path
    os.environ['PATH'] = found_path + ';' + os.environ['PATH']
    
    # Verificar que funciona
    try:
        result = subprocess.run([tesseract_exe, "--version"], 
                              capture_output=True, 
                              text=True,
                              shell=True,
                              timeout=5)
        
        if result.returncode == 0:
            version = result.stdout.strip().split('\n')[0]
            print(f"✅ Tesseract funciona correctamente")
            print(f"📦 Versión: {version}")
            print(f"📍 Ruta configurada: {found_path}")
            
            # Guardar configuración en archivo
            config_file = Path(__file__).parent / 'tesseract_config.py'
            with open(config_file, 'w', encoding='utf-8') as f:
                f.write(f'TESSERACT_PATH = r"{found_path}"\n')
                f.write(f'TESSERACT_EXE = r"{tesseract_exe}"\n')
            
            print(f"\n💾 Configuración guardada en: {config_file}")
            return True
        else:
            print("❌ Tesseract no responde correctamente")
            return False
            
    except Exception as e:
        print(f"❌ Error verificando Tesseract: {e}")
        return False

if __name__ == "__main__":
    setup_tesseract()
    
    print("\n" + "=" * 50)
    print("🎯 Para usar en Flask, importa así:")
    print("""
import pytesseract

# Configurar ruta específica
pytesseract.pytesseract.tesseract_cmd = r'C:\\Program Files\\Tesseract-OCR\\tesseract.exe'
    """)
    
    input("\nPresiona Enter para continuar...")
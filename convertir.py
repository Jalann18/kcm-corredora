import os
from PIL import Image

# Esta es la ruta que nos dio tu comando find/grep
ruta_imagenes = './static/core/img/' 

if not os.path.exists(ruta_imagenes):
    print(f"❌ No encontré la carpeta en: {ruta_imagenes}")
else:
    print(f"🚀 Iniciando conversión en: {ruta_imagenes}")
    archivos = os.listdir(ruta_imagenes)
    contador = 0
    
    for archivo in archivos:
        if archivo.lower().endswith((".png", ".jpg", ".jpeg")):
            try:
                nombre_sin_ext = os.path.splitext(archivo)[0]
                img = Image.open(os.path.join(ruta_imagenes, archivo))
                
                # Convertimos a RGB para evitar problemas con canales alfa
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                
                img.save(os.path.join(ruta_imagenes, f"{nombre_sin_ext}.webp"), "WEBP", quality=80)
                print(f"✅ {archivo} -> .webp")
                contador += 1
            except Exception as e:
                print(f"⚠️ Error con {archivo}: {e}")
    
    print(f"\n✨ ¡Terminado! Se convirtieron {contador} imágenes.")

from PIL import Image

def convert_to_white_transparent(input_path, output_path):
    img = Image.open(input_path).convert("RGBA")
    data = img.getdata()
    
    new_data = []
    for item in data:
        r, g, b, a = item
        # Usamos el brillo maximo del pixel original como el canal alfa
        # para preservar los bordes suavizados (anti-aliasing)
        intensity = max(r, g, b)
        
        # Opcional: si hay un poco de ruido de compresión en el fondo negro,
        # lo podemos forzar a 0 si es muy oscuro.
        if intensity < 15:
            intensity = 0
            
        # El color siempre será blanco puro (255, 255, 255), 
        # la transparencia dependerá de qué tan brillante era originalmente.
        new_data.append((255, 255, 255, intensity))
        
    img.putdata(new_data)
    img.save(output_path, "WEBP")
    print(f"Logo convertido y guardado en {output_path}")

if __name__ == "__main__":
    convert_to_white_transparent("static/core/img/logo.webp", "static/core/img/logo-blanco.webp")

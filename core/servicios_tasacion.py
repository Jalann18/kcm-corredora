# core/servicios_tasacion.py
from datetime import datetime
from decimal import Decimal

# Valores referenciales estimados (UF por m2 construido) para comunas de la RM
VALORES_COMUNA_UF_M2 = {
    # Sector Oriente
    "Vitacura": 110,
    "Lo Barnechea": 105,
    "Las Condes": 100,
    "Providencia": 90,
    "La Reina": 85,
    "Ñuñoa": 80,
    
    # Centro y emergentes
    "Santiago": 65,
    "San Miguel": 65,
    "Macul": 62,
    "Independencia": 58,
    "Estación Central": 55,
    
    # Periferia urbana principal
    "La Florida": 55,
    "Maipú": 50,
    "Peñalolén": 60,
    "Quilicura": 48,
    "Puente Alto": 45,
    "San Bernardo": 45,
    "Pudahuel": 48,
    "Cerrillos": 50,
    
    # Otras
    "Conchalí": 45,
    "Cerro Navia": 40,
    "El Bosque": 42,
    "Huechuraba": 60,
    "La Cisterna": 52,
    "La Granja": 40,
    "La Pintana": 38,
    "Lo Espejo": 38,
    "Lo Prado": 42,
    "Pedro Aguirre Cerda": 45,
    "Quinta Normal": 48,
    "Recoleta": 52,
    "Renca": 42,
    "San Joaquín": 50,
    "San Ramón": 40,
}

# Promedio si la comuna no está en la lista principal
PROMEDIO_DEFAULT = 45

def estimar_precio_propiedad(datos):
    """
    Calcula un rango de precio estimado en UF basado en los datos de la propiedad.
    'datos' es un diccionario con:
    - comuna (str)
    - tipo_propiedad (str: 'casa', 'departamento')
    - sup_construida (float)
    - sup_terreno (float) - opcional
    - dormitorios (int)
    - banos (int)
    - estacionamientos (int)
    - bodegas (int)
    - ano_construccion (int)
    
    Retorna un tuple: (precio_minimo_uf, precio_maximo_uf)
    """
    comuna = datos.get('comuna', '')
    tipo = datos.get('tipo_propiedad', 'casa').lower()
    sup_construida = float(datos.get('sup_construida', 0) or 0)
    sup_terreno = float(datos.get('sup_terreno', 0) or 0)
    
    dormitorios = int(datos.get('dormitorios', 0) or 0)
    banos = int(datos.get('banos', 0) or 0)
    estacionamientos = int(datos.get('estacionamientos', 0) or 0)
    bodegas = int(datos.get('bodegas', 0) or 0)
    ano_construccion = datos.get('ano_construccion')
    
    # Obtener valor base de la comuna
    valor_base_m2 = VALORES_COMUNA_UF_M2.get(comuna, PROMEDIO_DEFAULT)
    
    # Calcular valor base por m2 construido
    precio_estimado = sup_construida * valor_base_m2
    
    # Ajuste por terreno extra (sólo para casas)
    if tipo == 'casa' and sup_terreno > sup_construida:
        terreno_libre = sup_terreno - sup_construida
        # El m2 de terreno sin construir se valora aprox al 35% del m2 construido
        precio_estimado += (terreno_libre * valor_base_m2 * 0.35)
        
    # Adicionales
    precio_estimado += (banos * 150)
    precio_estimado += (bodegas * 100)
    
    if tipo == 'departamento':
        precio_estimado += (estacionamientos * 350) # Más caros en deptos
    else:
        precio_estimado += (estacionamientos * 200)
        
    # Ajuste por antigüedad (Depreciación)
    if ano_construccion:
        ano_actual = datetime.now().year
        antiguedad = max(0, ano_actual - int(ano_construccion))
        
        if antiguedad <= 2:
            # Propiedad nueva o casi nueva (+5%)
            precio_estimado *= 1.05
        else:
            # -0.8% por cada año de antigüedad, tope de -35%
            depreciacion = min(0.35, antiguedad * 0.008)
            precio_estimado *= (1 - depreciacion)
            
    # Redondeo final y márgenes (rango de +/- 8% por estado de conservación, terminaciones, etc)
    precio_base = round(precio_estimado / 10) * 10  # Redondear a la decena más cercana
    
    precio_min = round((precio_base * 0.92) / 10) * 10
    precio_max = round((precio_base * 1.08) / 10) * 10
    
    return int(precio_min), int(precio_max)

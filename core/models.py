# core/models.py
from django.db import models
from django.utils import timezone
from django.utils.text import slugify
from django.core.validators import MinValueValidator
from decimal import Decimal

# Solo Región Metropolitana
REGIONES_CHOICES = [
    ("Metropolitana de Santiago", "Metropolitana de Santiago"),
]

# Comunas de la RM
COMUNAS_RM = [
    "Cerrillos", "Cerro Navia", "Conchalí", "El Bosque", "Estación Central", "Huechuraba",
    "Independencia", "La Cisterna", "La Florida", "La Granja", "La Pintana", "La Reina",
    "Las Condes", "Lo Barnechea", "Lo Espejo", "Lo Prado", "Macul", "Maipú", "Ñuñoa",
    "Pedro Aguirre Cerda", "Peñalolén", "Providencia", "Pudahuel", "Puente Alto",
    "Quilicura", "Quinta Normal", "Recoleta", "Renca", "San Joaquín", "San Miguel",
    "San Ramón", "Santiago", "Vitacura", "San Bernardo", "El Monte", "Isla de Maipo",
    "Padre Hurtado", "Peñaflor", "Talagante"
]

TIPO_OPERACION = [
    ("venta", "Venta"),
    ("arriendo", "Arriendo"),
]

TIPO_PROPIEDAD = [
    ("casa", "Casa"),
    ("departamento", "Departamento"),
    ("parcela", "Parcela/Terreno"),
    ("oficina", "Oficina"),
    ("comercial", "Local/Bodega"),
]

class Agente(models.Model):
    nombre = models.CharField(max_length=120)
    email = models.EmailField()
    telefono = models.CharField(max_length=30, blank=True)
    foto = models.ImageField(upload_to='agentes/', blank=True, null=True)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre

class Propiedad(models.Model):
    titulo = models.CharField(max_length=180)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    descripcion = models.TextField()

    tipo_operacion = models.CharField(max_length=20, choices=TIPO_OPERACION)
    tipo_propiedad = models.CharField(max_length=30, choices=TIPO_PROPIEDAD)

    # Siempre RM
    region = models.CharField(
        max_length=40,
        choices=REGIONES_CHOICES,
        default="Metropolitana de Santiago"
    )
    # Solo comunas RM
    comuna = models.CharField(
        max_length=60,
        choices=[(c, c) for c in COMUNAS_RM]
    )
    direccion = models.CharField(max_length=200, blank=True)

    # Moneda principal: UF
    precio_uf = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    # Campo legado (CLP) mantenido solo para compatibilidad con datos antiguos
    precio_clp = models.PositiveBigIntegerField(validators=[MinValueValidator(1)])
    dormitorios = models.PositiveSmallIntegerField(default=0)
    banos = models.PositiveSmallIntegerField(default=0)
    estacionamientos = models.PositiveSmallIntegerField(default=0)

    sup_construida_m2 = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    sup_terreno_m2 = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    ano_construccion = models.PositiveSmallIntegerField(blank=True, null=True)

    agente = models.ForeignKey(Agente, on_delete=models.SET_NULL, null=True, blank=True)

    destacada = models.BooleanField(default=False)
    publicada = models.BooleanField(default=True)
    portada = models.ImageField(upload_to='propiedades/', blank=True, null=True)

    creado = models.DateTimeField(default=timezone.now)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-destacada', '-creado']

    def __str__(self):
        return self.titulo

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.titulo)[:180] or f"propiedad-{int(timezone.now().timestamp())}"
            slug = base
            i = 2
            from django.db.models import Q
            while Propiedad.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{i}"
                i += 1
            self.slug = slug
        super().save(*args, **kwargs)


class ImagenPropiedad(models.Model):
    propiedad = models.ForeignKey(Propiedad, on_delete=models.CASCADE, related_name='imagenes')
    imagen = models.ImageField(upload_to='propiedades/galeria/')
    orden = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['orden', 'id']

    def __str__(self):
        return f"Imagen {self.orden} de {self.propiedad.titulo}"

class Lead(models.Model):
    propiedad = models.ForeignKey(
        Propiedad, on_delete=models.CASCADE,
        related_name='leads', null=True, blank=True   # 👈 cambio clave
    )
    nombre = models.CharField(max_length=120)
    email = models.EmailField()
    telefono = models.CharField(max_length=30, blank=True)
    mensaje = models.TextField(blank=True)
    creado = models.DateTimeField(default=timezone.now)
    comuna = models.CharField(max_length=60, blank=True)
    origen = models.CharField(max_length=50, default='web')

class CarouselSlide(models.Model):
    imagen = models.ImageField(upload_to='banners/')
    titulo = models.CharField(max_length=120, blank=True)
    subtitulo = models.CharField(max_length=200, blank=True)
    cta_text = models.CharField("Texto botón", max_length=40, blank=True)
    cta_url = models.URLField("URL botón", blank=True)
    activo = models.BooleanField(default=True)
    orden = models.PositiveSmallIntegerField(default=0, help_text="Menor número = aparece antes")
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["orden", "id"]  # orden estable
        verbose_name = "Slide de carrusel"
        verbose_name_plural = "Slides de carrusel"

    def __str__(self):
        return self.titulo or f"Slide #{self.pk}"

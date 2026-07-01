from django import forms
from django.contrib import admin
from adminsortable2.admin import SortableInlineAdminMixin, SortableAdminBase
from django.utils.safestring import mark_safe
from .models import Propiedad, ImagenPropiedad, Agente, Lead, CarouselSlide


# ─────────────────────────────────────────────────────────────────────────────
# WIDGET Y CAMPO PERSONALIZADOS PARA SUBIDA MÚLTIPLE
# Fix del bug de ClearableFileInput + allow_multiple_selected en Django
# ─────────────────────────────────────────────────────────────────────────────

class MultipleFileInput(forms.FileInput):
    """Widget que permite selección múltiple de archivos."""
    allow_multiple_selected = True  # Requerido por Django para permitir múltiples archivos

    def __init__(self, attrs=None):
        default_attrs = {'multiple': True, 'accept': 'image/*'}
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)

    def value_from_datadict(self, data, files, name):
        if hasattr(files, 'getlist'):
            return files.getlist(name)
        if files:
            val = files.get(name)
            return [val] if val else []
        return []


class MultipleFileField(forms.FileField):
    """
    Campo que acepta correctamente múltiples archivos.
    El widget nativo de Django solo toma el primer archivo; este campo
    sobreescribe clean() para iterar sobre la lista completa.
    """
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('widget', MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        # data es una lista de archivos (gracias a MultipleFileInput)
        # Si no se subió nada y el campo no es obligatorio, retornamos lista vacía
        if not data:
            if self.required:
                raise forms.ValidationError(self.error_messages['required'])
            return []
        # Validar cada archivo individualmente con el clean del padre
        result = []
        for f in data:
            cleaned = super().clean(f, initial)
            result.append(cleaned)
        return result


# ─────────────────────────────────────────────────────────────────────────────
# INLINE PARA IMÁGENES
# ─────────────────────────────────────────────────────────────────────────────

class ImagenPropiedadInline(admin.TabularInline):
    model = ImagenPropiedad
    extra = 0
    verbose_name = "Foto de Galería"
    verbose_name_plural = "📸 Galería de Fotos — Arrastra las filas para cambiar el orden"
    fields = ("imagen", "preview", "orden")
    readonly_fields = ("preview",)

    def preview(self, obj):
        if obj.imagen:
            return mark_safe(
                f'<img src="{obj.imagen.url}" '
                f'style="height:90px;width:120px;object-fit:cover;'
                f'border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,0.2);" />'
            )
        return "—"
    preview.short_description = "Vista Previa"


# ─────────────────────────────────────────────────────────────────────────────
# FORMULARIO DE PROPIEDAD (con campo múltiple corregido)
# ─────────────────────────────────────────────────────────────────────────────

class PropiedadAdminForm(forms.ModelForm):
    fotos_multiples = MultipleFileField(
        required=False,
        label="Fotos múltiples",
        help_text=(
            "Selecciona varias imágenes a la vez (Ctrl+clic o Cmd+clic). "
            "Las fotos subidas aquí aparecerán ordenadas visualmente en la galería de abajo."
        ),
    )

    class Meta:
        model = Propiedad
        fields = '__all__'


# ─────────────────────────────────────────────────────────────────────────────
# ADMIN DE PROPIEDADES
# ─────────────────────────────────────────────────────────────────────────────

@admin.register(Propiedad)
class PropiedadAdmin(SortableAdminBase, admin.ModelAdmin):
    form = PropiedadAdminForm
    list_display = (
        "titulo", "tipo_operacion", "tipo_propiedad",
        "comuna", "precio_uf", "publicada", "destacada", "fotos_count"
    )
    list_filter  = ("tipo_operacion", "tipo_propiedad", "comuna", "publicada", "destacada")
    search_fields = ("titulo", "descripcion", "comuna", "direccion")
    prepopulated_fields = {"slug": ("titulo",)}
    inlines = [ImagenPropiedadInline]
    list_editable = ("publicada", "destacada")

    fieldsets = (
        ("Datos Principales", {
            "fields": ("titulo", "descripcion", ("tipo_operacion", "tipo_propiedad")),
            "description": "Ingresa el título y descripción de la propiedad.",
        }),
        ("Precio", {
            "fields": (("precio_uf", "precio_clp"),),
            "description": "Ingresa el valor en UF. El campo CLP es solo para compatibilidad con registros antiguos.",
        }),
        ("Ubicación", {
            "fields": ("region", "comuna", "direccion"),
        }),
        ("Características", {
            "fields": (
                ("dormitorios", "banos", "estacionamientos"),
                ("sup_construida_m2", "sup_terreno_m2"),
                "ano_construccion",
            ),
        }),
        ("Portada y Galería de Fotos", {
            "fields": ("portada", "fotos_multiples"),
            "description": (
                "La Portada es la imagen principal que aparece en las tarjetas de listado. "
                "Usa el campo de Fotos Múltiples para subir varias imágenes a la vez "
                "(mantén Ctrl o Cmd presionado para seleccionar varias). "
                "Luego ordénalas arrastrando las filas de la galería."
            ),
        }),
        ("Configuración Interna", {
            "fields": ("agente", "destacada", "publicada", "slug"),
            "classes": ("collapse",),
            "description": "Opciones de visibilidad y metadatos técnicos.",
        }),
    )

    def fotos_count(self, obj):
        count = obj.imagenes.count()
        if count == 0:
            color = "#dc3545"
            texto = "Sin fotos"
        elif count < 3:
            color = "#fd7e14"
            texto = f"{count} foto{'s' if count != 1 else ''}"
        else:
            color = "#198754"
            texto = f"{count} fotos"
        return mark_safe(
            f'<span style="color:{color};font-weight:600;">{texto}</span>'
        )
    fotos_count.short_description = "Galería"

    class Media:
        js = ('core/js/drag_drop.js',)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # Procesar la lista de archivos del campo múltiple
        archivos = form.cleaned_data.get('fotos_multiples') or []
        for f in archivos:
            if f:
                ImagenPropiedad.objects.create(propiedad=obj, imagen=f)


# ─────────────────────────────────────────────────────────────────────────────
# ADMIN DE AGENTE
# ─────────────────────────────────────────────────────────────────────────────

@admin.register(Agente)
class AgenteAdmin(admin.ModelAdmin):
    list_display  = ("nombre", "email", "telefono", "activo")
    search_fields = ("nombre", "email")
    list_editable = ("activo",)


# ─────────────────────────────────────────────────────────────────────────────
# ADMIN DE LEADS
# ─────────────────────────────────────────────────────────────────────────────

@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display  = ("nombre", "email", "telefono", "origen_badge", "propiedad_link", "creado")
    list_filter   = ("creado", "origen", "comuna")
    search_fields = ("nombre", "email", "telefono", "mensaje")
    readonly_fields = ("creado",)
    date_hierarchy = "creado"

    def origen_badge(self, obj):
        colores = {
            "web":              ("#0d6efd", "Web"),
            "publicacion":      ("#6f42c1", "Publicación"),
            "tasador_virtual":  ("#198754", "Tasador Virtual"),
            "contacto":         ("#fd7e14", "Contacto"),
        }
        color, label = colores.get(obj.origen, ("#6c757d", obj.origen))
        return mark_safe(
            f'<span style="background:{color};color:#fff;padding:2px 10px;'
            f'border-radius:20px;font-size:0.78rem;font-weight:600;">{label}</span>'
        )
    origen_badge.short_description = "Origen"

    def propiedad_link(self, obj):
        if obj.propiedad:
            url = f"/admin/core/propiedad/{obj.propiedad.pk}/change/"
            return mark_safe(f'<a href="{url}" style="color:#0d6efd;">{obj.propiedad.titulo[:40]}</a>')
        return mark_safe('<span style="color:#adb5bd;">General</span>')
    propiedad_link.short_description = "Propiedad"


# ─────────────────────────────────────────────────────────────────────────────
# ADMIN DE CAROUSEL
# ─────────────────────────────────────────────────────────────────────────────

@admin.register(CarouselSlide)
class CarouselSlideAdmin(admin.ModelAdmin):
    list_display  = ("preview", "titulo", "activo", "orden")
    list_editable = ("activo", "orden")
    search_fields = ("titulo", "subtitulo")
    list_filter   = ("activo",)
    ordering      = ("orden", "id")

    def preview(self, obj):
        if obj.imagen:
            return mark_safe(
                f'<img src="{obj.imagen.url}" '
                f'style="height:50px;width:90px;object-fit:cover;border-radius:6px;" />'
            )
        return "—"
    preview.short_description = "Preview"
    preview.admin_order_field = "imagen"

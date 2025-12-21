# core/admin.py
from django.contrib import admin
from .models import Propiedad, ImagenPropiedad, Agente, Lead, CarouselSlide
from django.utils.safestring import mark_safe


class ImagenPropiedadInline(admin.TabularInline):
    model = ImagenPropiedad
    extra = 1


@admin.register(Propiedad)
class PropiedadAdmin(admin.ModelAdmin):
    list_display = ("titulo", "tipo_operacion", "tipo_propiedad", "region", "comuna", "precio_uf", "publicada", "destacada")
    list_filter = ("tipo_operacion", "tipo_propiedad", "region", "publicada", "destacada")
    search_fields = ("titulo", "descripcion", "comuna", "direccion")
    prepopulated_fields = {"slug": ("titulo",)}
    inlines = [ImagenPropiedadInline]


@admin.register(Agente)
class AgenteAdmin(admin.ModelAdmin):
    list_display = ("nombre", "email", "telefono", "activo")
    search_fields = ("nombre", "email")


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ("propiedad", "nombre", "email", "telefono", "creado", "origen")
    list_filter = ("creado", "origen")
    search_fields = ("nombre", "email", "telefono")


@admin.register(CarouselSlide)
class CarouselSlideAdmin(admin.ModelAdmin):
    list_display = ("preview", "titulo", "activo", "orden")
    list_editable = ("activo", "orden")
    search_fields = ("titulo", "subtitulo")
    list_filter = ("activo",)
    ordering = ("orden", "id")

    def preview(self, obj):
        if obj.imagen:
            return mark_safe(
                f'<img src="{obj.imagen.url}" style="height:50px;object-fit:cover;border-radius:6px" />'
            )
        return "—"

    preview.short_description = "Preview"
    # opcional: permite ordenar por el campo imagen (si te sirve)
    preview.admin_order_field = "imagen"

from django import forms
from django.contrib import admin
from adminsortable2.admin import SortableInlineAdminMixin, SortableAdminBase
from django.utils.safestring import mark_safe
from django.utils.safestring import mark_safe
from .models import Propiedad, ImagenPropiedad, Agente, Lead, CarouselSlide

# --- INLINE PARA IMÁGENES CON DRAG & DROP ---
class ImagenPropiedadInline(SortableInlineAdminMixin, admin.TabularInline):
    model = ImagenPropiedad
    extra = 0
    readonly_fields = ("preview",)

    def preview(self, obj):
        if obj.imagen:
            return mark_safe(f'<img src="{obj.imagen.url}" style="height:100px;object-fit:cover;border-radius:6px;" />')
        return "—"
    preview.short_description = "Vista Previa"

class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

# --- FORMULARIO PARA SUBIDA MÚLTIPLE ---
class PropiedadAdminForm(forms.ModelForm):
    fotos_multiples = forms.FileField(
        widget=MultipleFileInput(attrs={'multiple': True}),
        required=False,
        help_text="Selecciona múltiples fotos para subir a la galería de esta propiedad. Puedes arrastrar varias imágenes aquí."
    )

    class Meta:
        model = Propiedad
        fields = '__all__'

@admin.register(Propiedad)
class PropiedadAdmin(SortableAdminBase, admin.ModelAdmin):
    form = PropiedadAdminForm
    list_display = ("titulo", "tipo_operacion", "tipo_propiedad", "region", "comuna", "precio_uf", "publicada", "destacada")
    list_filter = ("tipo_operacion", "tipo_propiedad", "region", "publicada", "destacada")
    search_fields = ("titulo", "descripcion", "comuna", "direccion")
    prepopulated_fields = {"slug": ("titulo",)}
    inlines = [ImagenPropiedadInline]

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        
        # Procesar las imágenes múltiples
        for f in request.FILES.getlist('fotos_multiples'):
            ImagenPropiedad.objects.create(propiedad=obj, imagen=f)

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
    preview.admin_order_field = "imagen"

# core/forms.py
from django import forms
from .models import Lead, REGIONES_CHOICES, TIPO_PROPIEDAD, TIPO_OPERACION, COMUNAS_RM


# ===========================
# Helpers reutilizables
# ===========================
def _strip_digits_plus(value: str) -> str:
    """
    Deja solo dígitos y '+' (útil para teléfonos internacionales).
    """
    if not value:
        return ""
    return "".join(ch for ch in value if ch.isdigit() or ch == "+")


def _parse_int_relaxed(value):
    """
    Convierte strings tipo '120.000.000', '120 000 000', '120,000,000' a int.
    Retorna None si viene vacío.
    """
    if value in (None, "", 0):
        return None
    if isinstance(value, int):
        return value
    digits = "".join(ch for ch in str(value) if ch.isdigit())
    return int(digits) if digits else None


# ===========================
# LeadForm (ModelForm)
# Para contacto rápido
# ===========================
class LeadForm(forms.ModelForm):
    class Meta:
        model = Lead
        fields = ["nombre", "email", "telefono", "mensaje"]
        labels = {
            "nombre": "Nombre",
            "email": "Email",
            "telefono": "Teléfono",
            "mensaje": "Mensaje",
        }
        widgets = {
            "nombre": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Tu nombre",
                "autocomplete": "name",
                "maxlength": 120,
                "aria-label": "Nombre completo",
            }),
            "email": forms.EmailInput(attrs={
                "class": "form-control",
                "placeholder": "tunombre@correo.cl",
                "autocomplete": "email",
                "aria-label": "Correo electrónico",
            }),
            "telefono": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "+56 9 1234 5678",
                "inputmode": "tel",
                "autocomplete": "tel",
                "maxlength": 30,
                "aria-label": "Teléfono de contacto",
            }),
            "mensaje": forms.Textarea(attrs={
                "class": "form-control no-resize",
                "placeholder": "Cuéntanos cuándo te acomoda visitar",
                "rows": 4,
                "maxlength": 600,
                "aria-label": "Mensaje o comentario",
            }),
        }

    def clean_telefono(self):
        tel = self.cleaned_data.get("telefono", "")
        return _strip_digits_plus(tel)

    def clean_email(self):
        email = self.cleaned_data.get("email", "")
        return (email or "").strip().lower()

    def clean_nombre(self):
        nombre = (self.cleaned_data.get("nombre") or "").strip()
        return " ".join(nombre.split())


# ===========================
# BusquedaPropiedadForm
# Filtros del listado
# ===========================
class BusquedaPropiedadForm(forms.Form):
    q = forms.CharField(
        label="",
        required=False,
        widget=forms.TextInput(attrs={
            "placeholder": "Buscar por título o comuna",
            "class": "form-control",
            "aria-label": "Buscar por texto",
        })
    )

    region = forms.ChoiceField(
        choices=[("", "Región")] + REGIONES_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            "class": "form-select form-select-sm",
            "aria-label": "Filtrar por región",
        })
    )

    min_precio = forms.CharField(
        required=False,
        widget=forms.NumberInput(attrs={
            "class": "form-control",
            "placeholder": "UF Desde",
            "aria-label": "Precio mínimo",
            "inputmode": "numeric",
        })
    )

    max_precio = forms.CharField(
        required=False,
        widget=forms.NumberInput(attrs={
            "class": "form-control",
            "placeholder": "UF Hasta",
            "aria-label": "Precio máximo",
            "inputmode": "numeric",
        })
    )

    dormitorios = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={
            "class": "form-control",
            "placeholder": "Dormitorios",
            "aria-label": "Cantidad de dormitorios",
            "min": 0,
        })
    )

    tipo_operacion = forms.ChoiceField(
        choices=[("", "Operación")] + TIPO_OPERACION,
        required=False,
        widget=forms.Select(attrs={
            "class": "form-select form-select-sm",
            "aria-label": "Tipo de operación",
        })
    )

    tipo_propiedad = forms.ChoiceField(
        choices=[("", "Tipo de propiedad")] + TIPO_PROPIEDAD,
        required=False,
        widget=forms.Select(attrs={
            "class": "form-select form-select-sm",
            "aria-label": "Tipo de propiedad",
        })
    )

    comuna = forms.ChoiceField(
        choices=[("", "Comuna")] + [(c, c) for c in COMUNAS_RM],
        required=False,
        widget=forms.Select(attrs={
            "class": "form-select form-select-sm",
            "aria-label": "Comuna",
        })
    )

    moneda = forms.ChoiceField(
        choices=[("", "Moneda"), ("CLP", "CLP"), ("UF", "UF")],
        required=False,
        widget=forms.Select(attrs={
            "class": "form-select form-select-sm",
            "aria-label": "Moneda",
        })
    )

    def clean(self):
        cleaned = super().clean()
        min_raw = cleaned.get("min_precio")
        max_raw = cleaned.get("max_precio")

        min_val = _parse_int_relaxed(min_raw)
        max_val = _parse_int_relaxed(max_raw)

        cleaned["min_precio"] = min_val
        cleaned["max_precio"] = max_val

        if min_val is not None and max_val is not None and min_val > max_val:
            self.add_error("max_precio", "Debe ser mayor o igual que el mínimo.")
        return cleaned


# ===========================
# QuieroPublicarForm
# Para el formulario de "Publica tu propiedad"
# ===========================
class QuieroPublicarForm(forms.Form):
    tipo_operacion = forms.ChoiceField(
        choices=TIPO_OPERACION,
        widget=forms.Select(attrs={
            "class": "form-select",
            "aria-label": "Tipo de operación",
        })
    )
    tipo_propiedad = forms.ChoiceField(
        choices=TIPO_PROPIEDAD,
        widget=forms.Select(attrs={
            "class": "form-select",
            "aria-label": "Tipo de propiedad",
        })
    )
    comuna = forms.ChoiceField(
        choices=[(c, c) for c in COMUNAS_RM],
        widget=forms.Select(attrs={
            "class": "form-select",
            "aria-label": "Comuna",
        })
    )

    # Precio referencial (12 dígitos máx)
    precio_referencial = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Ej: 120000000 o 650000",
            "inputmode": "numeric",
            "aria-label": "Precio referencial",
            "maxlength": "12",
            "pattern": r"\d*",
        })
    )

    # Datos de contacto
    nombre = forms.CharField(
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Tu nombre",
            "autocomplete": "name",
            "maxlength": 120,
            "aria-label": "Nombre completo",
        })
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            "class": "form-control",
            "placeholder": "tunombre@correo.cl",
            "autocomplete": "email",
            "aria-label": "Correo electrónico",
        })
    )
    telefono = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "+56 9 1234 5678",
            "inputmode": "tel",
            "autocomplete": "tel",
            "maxlength": 30,
            "aria-label": "Teléfono de contacto",
        })
    )
    mensaje = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            "class": "form-control no-resize",
            "rows": 4,
            "placeholder": "Detalles clave (opcional)",
            "maxlength": 600,
            "aria-label": "Mensaje o comentario",
        })
    )

    # ---------- Limpiezas específicas ----------
    def clean_precio_referencial(self):
        raw = self.cleaned_data.get("precio_referencial") or ""
        digits = "".join(ch for ch in raw if ch.isdigit())

        if not digits:
            return None

        if len(digits) > 12:
            from django.core.exceptions import ValidationError
            raise ValidationError("Ingresa un valor de hasta 12 dígitos.")

        return int(digits)

    def clean_telefono(self):
        tel = self.cleaned_data.get("telefono", "")
        return _strip_digits_plus(tel)

    def clean_email(self):
        email = self.cleaned_data.get("email", "")
        return (email or "").strip().lower()

    def clean_nombre(self):
        nombre = (self.cleaned_data.get("nombre") or "").strip()
        return " ".join(nombre.split())

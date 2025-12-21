# core/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q
from django.contrib import messages
from .models import Propiedad, CarouselSlide, Lead
from .forms import BusquedaPropiedadForm, LeadForm, QuieroPublicarForm
from django.core.paginator import Paginator
from urllib.parse import urlencode



def home(request):
    # === Slides administrables (máx. 6)
    slides = CarouselSlide.objects.filter(activo=True).order_by("orden", "id")[:6]

    # === Propiedades destacadas (máx. 6)
    destacadas = (
        Propiedad.objects.filter(publicada=True, destacada=True)
        .order_by("-creado")[:6]
    )

    # === Propiedades recientes (máx. 9, sin duplicar destacadas)
    recientes = (
        Propiedad.objects.filter(publicada=True)
        .exclude(id__in=destacadas.values_list("id", flat=True))
        .order_by("-creado")[:9]
    )

    # === Formulario de búsqueda
    form = BusquedaPropiedadForm()

    return render(
        request,
        "core/home.html",
        {
            "slides": slides,
            "destacadas": destacadas,
            "recientes": recientes,
            "form": form,
        },
    )

def propiedad_list(request):
    form = BusquedaPropiedadForm(request.GET or None)
    qs = Propiedad.objects.filter(publicada=True)

    if form.is_valid():
        q = form.cleaned_data.get("q")
        if q:
            qs = qs.filter(
                Q(titulo__icontains=q)
                | Q(descripcion__icontains=q)
                | Q(comuna__icontains=q)
            )

        tipo_operacion = form.cleaned_data.get("tipo_operacion")
        tipo_propiedad = form.cleaned_data.get("tipo_propiedad")
        region = form.cleaned_data.get("region")
        min_precio = form.cleaned_data.get("min_precio")
        max_precio = form.cleaned_data.get("max_precio")
        dormitorios = form.cleaned_data.get("dormitorios")
        comuna = form.cleaned_data.get("comuna")

        if tipo_operacion:
            qs = qs.filter(tipo_operacion=tipo_operacion)
        if tipo_propiedad:
            qs = qs.filter(tipo_propiedad=tipo_propiedad)
        if region:
            qs = qs.filter(region=region)
        # Filtros de precio ahora sobre UF
        if min_precio is not None:
            qs = qs.filter(precio_uf__gte=min_precio)
        if max_precio is not None:
            qs = qs.filter(precio_uf__lte=max_precio)
        if dormitorios:
            qs = qs.filter(dormitorios__gte=dormitorios)
        if comuna:
            qs = qs.filter(comuna=comuna)
    else:
        tipo_operacion = tipo_propiedad = comuna = None

    # ===== TÍTULO DINÁMICO =====
    def choices_dict(field_name):
        return dict(form.fields[field_name].choices)

    prop_labels = choices_dict("tipo_propiedad") if "tipo_propiedad" in form.fields else {}
    op_labels = choices_dict("tipo_operacion") if "tipo_operacion" in form.fields else {}

    def label_prop(v): return prop_labels.get(v, v) if v else None
    def label_op(v): return op_labels.get(v, v) if v else None

    def plural_es(word: str):
        if not word: return word
        if word.endswith("s"): return word
        if word.endswith("ón"): return word[:-2] + "ones"
        return word + "s"

    titulo = ""
    lp, lo = label_prop(form.cleaned_data.get("tipo_propiedad") if form.is_valid() else None), \
             label_op(form.cleaned_data.get("tipo_operacion") if form.is_valid() else None)

    if lp and lo:
        titulo = f"{plural_es(lp)} en {lo}"
    elif lp:
        titulo = f"{plural_es(lp)} disponibles"
    elif lo:
        titulo = f"Propiedades en {lo}"

    if form.is_valid() and form.cleaned_data.get("comuna"):
        titulo = f"{titulo} en {form.cleaned_data['comuna']}"

    # ===== PAGINACIÓN =====
    qs = qs.order_by("-destacada", "-creado")
    paginator = Paginator(qs, 12)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # ===== QUERYSTRING (sin 'page') para que el título/filtros persistan =====
    params = request.GET.copy()
    params.pop("page", None)
    qs_str = params.urlencode()

    context = {
        "form": form,
        "propiedades": page_obj,
        "titulo": titulo,
        "qs": qs_str,  # 👈 usar en los links del paginador
    }
    return render(request, "core/propiedad_list.html", context)

def propiedad_detail(request, slug):
    prop = get_object_or_404(Propiedad, slug=slug, publicada=True)

    form = LeadForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        lead = form.save(commit=False)
        lead.propiedad = prop
        lead.save()
        messages.success(request, "¡Gracias! Te contactaremos pronto.")
        return redirect("core:propiedad_detail", slug=slug)

    return render(request, "core/propiedad_detail.html", {"prop": prop, "form": form})


def contacto(request):
    form = LeadForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        lead = form.save(commit=False)
        lead.propiedad = None          # contacto “general”, sin propiedad asociada
        lead.origen = "contacto"       # para distinguir en el admin
        lead.save()
        messages.success(request, "¡Gracias! Te contactaremos muy pronto")
        return redirect("core:contacto")
    return render(request, "core/contacto.html", {"form": form})

def nosotros(request):
    return render(request, "core/nosotros.html")

def quiero_publicar(request):
    form = QuieroPublicarForm(request.POST or None)
    helper_text = ""
    if request.method == "POST" and form.is_valid():
        cd = form.cleaned_data
        # Guardamos como Lead “sueltito”, sin propiedad, con origen específico
        Lead.objects.create(
            propiedad=None,
            nombre=cd["nombre"],
            email=cd["email"],
            telefono=cd.get("telefono", ""),
            mensaje=(
                f"[{cd['tipo_operacion'].upper()} | {cd['tipo_propiedad']} | {cd['comuna']}"
                f"{' | $'+str(cd['precio_referencial']) if cd.get('precio_referencial') else ''}] "
                f"{cd.get('mensaje','')}"
            ),
            comuna=cd["comuna"],
            origen="publicacion"
        )
        messages.success(request, "¡Gracias! Te contactaremos para publicar tu propiedad.")
        return redirect("core:home")

    # texto breve dependiente de operación (para la UI)
    op = request.POST.get("tipo_operacion") or request.GET.get("tipo_operacion")
    if op == "venta":
        helper_text = "Venta: indica precio estimado de venta y mejoras relevantes."
    elif op == "arriendo":
        helper_text = "Arriendo: indica canon mensual y si incluye gastos comunes."

    return render(request, "core/quiero_publicar.html", {"form": form, "helper_text": helper_text})

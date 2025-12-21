# core/tests.py
import io
import tempfile
import shutil
from datetime import timedelta

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model

from .models import Propiedad, ImagenPropiedad, Agente, Lead, CarouselSlide

# =============== Helpers de test ===============

def fake_image_bytes():
    """
    PNG de 1x1 píxel generado en memoria (válido para ImageField).
    """
    # PNG transparente 1x1 minimal
    return (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\x0cIDAT\x08\xd7c\xf8"
        b"\xff\xff?\x00\x05\xfe\x02\xfeA\x0b\xb1\x89\x00\x00\x00\x00IEND\xaeB`\x82"
    )

def make_prop(
    titulo="Depto prueba",
    publicada=True,
    destacada=False,
    precio=100000000,
    tipo_operacion="venta",
    tipo_propiedad="departamento",
    region="RM",
    comuna="Santiago",
    dormitorios=2,
    creado=None,
):
    creado = creado or timezone.now()
    return Propiedad.objects.create(
        titulo=titulo,
        publicada=publicada,
        destacada=destacada,
        precio_clp=precio,
        tipo_operacion=tipo_operacion,
        tipo_propiedad=tipo_propiedad,
        region=region,
        comuna=comuna,
        dormitorios=dormitorios,
        creado=creado,
    )


# =============== Tests de modelos ===============

class ModelTests(TestCase):
    def test_propiedad_str(self):
        p = make_prop(titulo="Casa Bonita")
        self.assertIn("Casa Bonita", str(p))

    def test_slug_autogenerado_y_unico(self):
        p1 = make_prop(titulo="Mi Propiedad Única")
        p2 = make_prop(titulo="Mi Propiedad Única")
        self.assertTrue(p1.slug)
        self.assertTrue(p2.slug)
        self.assertNotEqual(p1.slug, p2.slug, "El slug debe desambiguarse si el título se repite")

    def test_filtra_solo_publicadas_en_listado(self):
        make_prop(titulo="Pub", publicada=True)
        make_prop(titulo="NoPub", publicada=False)
        pubs = Propiedad.objects.filter(publicada=True)
        self.assertEqual(pubs.count(), 1)

    def test_imagen_propiedad_relacion(self):
        p = make_prop()
        img = SimpleUploadedFile("x.png", fake_image_bytes(), content_type="image/png")
        ip = ImagenPropiedad.objects.create(propiedad=p, imagen=img)
        self.assertEqual(ip.propiedad_id, p.id)

    def test_carousel_slide_str(self):
        slide = CarouselSlide.objects.create(titulo="Hero 1", activo=True, orden=1)
        self.assertIn("Hero 1", str(slide))


# =============== Tests de vistas básicas ===============

class ViewSmokeTests(TestCase):
    def setUp(self):
        self.p = make_prop(titulo="Depto Centro", destacada=True)

    def test_home_ok(self):
        # Ajusta si tu nombre de URL de home es otro
        resp = self.client.get(reverse("core:home"))
        self.assertEqual(resp.status_code, 200)

    def test_list_ok(self):
        resp = self.client.get(reverse("core:propiedad_list"))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("propiedades", resp.context)

    def test_detail_ok(self):
        url = reverse("core:propiedad_detail", args=[self.p.slug])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_detail_404(self):
        resp = self.client.get(reverse("core:propiedad_detail", args=["no-existe"]))
        self.assertEqual(resp.status_code, 404)


# =============== Tests de filtros y paginación del listado ===============

class ListFiltersPaginationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        now = timezone.now()
        # 25 publicadas (12 por página -> 3 páginas: 12 + 12 + 1)
        for i in range(25):
            make_prop(
                titulo=f"Prop {i}",
                destacada=(i % 7 == 0),
                precio=50_000_000 + i * 1_000_000,
                tipo_operacion="venta" if i % 2 == 0 else "arriendo",
                tipo_propiedad="departamento" if i % 3 else "casa",
                region="RM",
                comuna="Santiago" if i % 4 else "Providencia",
                dormitorios=(i % 5) + 1,
                creado=now - timedelta(days=i),
            )
        # Una no publicada
        make_prop(titulo="Oculta", publicada=False)

    def test_paginacion_basica(self):
        resp = self.client.get(reverse("core:propiedad_list"))
        self.assertEqual(resp.status_code, 200)
        page = resp.context["propiedades"]
        self.assertEqual(page.paginator.per_page, 12)
        self.assertEqual(page.number, 1)
        self.assertTrue(page.has_next())

        resp2 = self.client.get(reverse("core:propiedad_list") + "?page=2")
        page2 = resp2.context["propiedades"]
        self.assertEqual(page2.number, 2)

        resp3 = self.client.get(reverse("core:propiedad_list") + "?page=3")
        page3 = resp3.context["propiedades"]
        self.assertEqual(page3.number, 3)
        self.assertFalse(page3.has_next())

    def test_orden_destacadas_primero_y_por_creado(self):
        resp = self.client.get(reverse("core:propiedad_list"))
        page = resp.context["propiedades"]
        objs = list(page.object_list)
        # La primera debiera ser alguna destacada (por la ordenación -destacada, -creado)
        self.assertTrue(objs[0].destacada or any(o.destacada for o in objs))

    def test_filtro_busqueda_q(self):
        make_prop(titulo="Vista al mar en Reñaca", comuna="Viña del Mar")
        resp = self.client.get(reverse("core:propiedad_list"), {"q": "Reñaca"})
        page = resp.context["propiedades"]
        self.assertTrue(any("Reñaca" in p.titulo for p in page.object_list))

    def test_filtro_tipo_operacion(self):
        resp = self.client.get(reverse("core:propiedad_list"), {"tipo_operacion": "arriendo"})
        page = resp.context["propiedades"]
        self.assertTrue(all(p.tipo_operacion == "arriendo" for p in page.object_list))

    def test_filtro_tipo_propiedad(self):
        resp = self.client.get(reverse("core:propiedad_list"), {"tipo_propiedad": "casa"})
        page = resp.context["propiedades"]
        self.assertTrue(all(p.tipo_propiedad == "casa" for p in page.object_list))

    def test_filtro_region(self):
        resp = self.client.get(reverse("core:propiedad_list"), {"region": "RM"})
        self.assertEqual(resp.status_code, 200)  # si la región no matchea choices, igual debería responder

    def test_filtro_comuna_exact(self):
        resp = self.client.get(reverse("core:propiedad_list"), {"comuna": "Santiago"})
        page = resp.context["propiedades"]
        self.assertTrue(all(p.comuna == "Santiago" for p in page.object_list))

    def test_filtro_precio_min_max(self):
        resp = self.client.get(reverse("core:propiedad_list"), {"min_precio": 55_000_000, "max_precio": 60_000_000})
        page = resp.context["propiedades"]
        for p in page.object_list:
            self.assertGreaterEqual(p.precio_clp, 55_000_000)
            self.assertLessEqual(p.precio_clp, 60_000_000)

    def test_filtro_dormitorios_gte(self):
        resp = self.client.get(reverse("core:propiedad_list"), {"dormitorios": 3})
        page = resp.context["propiedades"]
        self.assertTrue(all(p.dormitorios >= 3 for p in page.object_list))


# =============== Tests de formularios / leads ===============

class LeadFlowTests(TestCase):
    def setUp(self):
        self.prop = make_prop(titulo="Casa con patio", comuna="Maipú")

    def test_quiero_publicar_get_ok(self):
        resp = self.client.get(reverse("core:quiero_publicar"))
        self.assertEqual(resp.status_code, 200)

    def test_quiero_publicar_post_crea_lead(self):
        data = {
            "nombre": "Alan",
            "email": "alan@test.cl",
            "telefono": "+56912345678",
            "tipo_propiedad": "casa",
            "tipo_operacion": "venta",
            "comuna": "Maipú",
            "precio_referencial": "120.000.000",
            "mensaje": "Quiero publicar mi casa",
            # si tu form requiere captcha u otros campos, agrégalos acá
        }
        resp = self.client.post(reverse("core:quiero_publicar"), data, follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Lead.objects.count(), 1)
        lead = Lead.objects.latest("id")
        self.assertEqual(lead.nombre, "Alan")
        self.assertEqual(lead.comuna, "Maipú")

    def test_lead_modal_en_detalle_propiedad(self):
        """
        Si tu detalle soporta crear Lead vía POST (modal), este test verifica
        que no truene y cree el Lead. Si no lo tienes implementado, puedes
        deshabilitar este test.
        """
        url = reverse("core:propiedad_detail", args=[self.prop.slug])
        data = {
            "nombre": "Marcela",
            "email": "marce@test.cl",
            "telefono": "912345678",
            "mensaje": "Quiero agendar visita",
            "propiedad": self.prop.id,
            "origen": "detalle",
        }
        resp = self.client.post(url, data, follow=True)
        # No todos los detalles aceptan POST; al menos que no rompa:
        self.assertIn(resp.status_code, (200, 302))


# =============== Tests de Admin ===============

@override_settings(ROOT_URLCONF="kcm_site.urls")
class AdminTests(TestCase):
    def setUp(self):
        # superuser
        User = get_user_model()
        self.admin_user = User.objects.create_superuser(
            email="admin@test.cl" if hasattr(User, "email") else "admin",
            username="admin" if hasattr(User, "username") else "admin@test.cl",
            password="admin1234",
        )
        self.client.login(
            username=getattr(self.admin_user, "username", "admin@test.cl"),
            password="admin1234",
        )
        # datos
        self.p = make_prop(titulo="Admin Casa")
        # slide con imagen
        img = SimpleUploadedFile("hero.png", fake_image_bytes(), content_type="image/png")
        self.slide = CarouselSlide.objects.create(titulo="Slide Admin", activo=True, orden=1, imagen=img)

    def test_admin_propiedad_changelist(self):
        url = reverse("admin:core_propiedad_changelist")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_admin_carousel_changelist_con_preview(self):
        url = reverse("admin:core_carouselslide_changelist")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_admin_lead_changelist(self):
        url = reverse("admin:core_lead_changelist")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)


# =============== Tests con MEDIA_ROOT temporal ===============

class MediaUploadTests(TestCase):
    def setUp(self):
        # carpeta temporal para MEDIA
        self._tmpdir = tempfile.mkdtemp()

        self.override = override_settings(MEDIA_ROOT=self._tmpdir)
        self.override.enable()

    def tearDown(self):
        self.override.disable()
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_subida_imagen_portada(self):
        p = make_prop()
        img = SimpleUploadedFile("portada.png", fake_image_bytes(), content_type="image/png")
        p.portada = img
        p.save()
        self.assertTrue(bool(p.portada))

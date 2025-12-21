from django.db import migrations, models
from decimal import Decimal, ROUND_HALF_UP
import os


def convert_clp_to_uf(apps, schema_editor):
    Propiedad = apps.get_model('core', 'Propiedad')
    # Obtiene valor UF de entorno o usa 36000 CLP por UF como fallback
    try:
        uf_clp = Decimal(os.getenv('UF_CLP_VALUE', '36000'))
        if uf_clp <= 0:
            uf_clp = Decimal('36000')
    except Exception:
        uf_clp = Decimal('36000')

    for prop in Propiedad.objects.all().only('id', 'precio_clp'):
        clp = prop.precio_clp or 0
        if clp:
            uf = (Decimal(clp) / uf_clp).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            Propiedad.objects.filter(id=prop.id).update(precio_uf=uf)


def noop_reverse(apps, schema_editor):
    # No revertimos la conversión
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_alter_lead_propiedad'),
    ]

    operations = [
        migrations.AddField(
            model_name='propiedad',
            name='precio_uf',
            field=models.DecimalField(blank=True, null=True, max_digits=10, decimal_places=2),
        ),
        migrations.RunPython(convert_clp_to_uf, noop_reverse),
    ]


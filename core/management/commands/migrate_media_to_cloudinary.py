# core/management/commands/migrate_media_to_cloudinary.py
from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from core.models import Propiedad, ImagenPropiedad, CarouselSlide, Agente


class Command(BaseCommand):
    """
    Migra imágenes desde MEDIA_ROOT a Cloudinary, pero OJO:

    django-cloudinary-storage (MediaCloudinaryStorage) normalmente construye URLs
    con un prefijo "media/" en el public_id (se nota porque tu .url tiene /media/...).

    En tu caso:
      - BD guarda:      kcm/propiedades/xxxx_32
      - URL entrega:    .../image/upload/v1/media/kcm/propiedades/xxxx_32

    Eso significa que Cloudinary debe tener el asset con public_id:
      media/kcm/propiedades/xxxx_32

    Este comando sube usando public_id con "media/" delante (upload_public_id),
    pero guarda en BD SIN el "media/" (stored_name), para evitar doble "media/media".
    """

    help = "Sube imágenes desde MEDIA_ROOT a Cloudinary con prefijo media/ y mantiene el name limpio en BD."

    IMG_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".gif")

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Simula sin subir ni guardar.")
        parser.add_argument(
            "--only",
            choices=["all", "propiedades", "galeria", "slides", "agentes"],
            default="all",
            help="Migrar solo un subconjunto (por defecto: all).",
        )
        parser.add_argument("--debug", action="store_true", help="Logs detallados.")

    def _norm_rel(self, rel: str) -> str:
        return (rel or "").strip().replace("\\", "/")

    def _resolve_local_file(self, media_root: Path, rel: str) -> Path | None:
        rel = self._norm_rel(rel)
        if not rel:
            return None

        candidate = media_root / rel
        if candidate.exists():
            return candidate

        # Si no tiene extensión, probamos varias.
        lower = rel.lower()
        has_ext = any(lower.endswith(ext) for ext in self.IMG_EXTS)
        if not has_ext:
            base = str(candidate)
            for ext in self.IMG_EXTS:
                cand2 = Path(base + ext)
                if cand2.exists():
                    return cand2

        return None

    def handle(self, *args, **options):
        dry = bool(options["dry_run"])
        only = options["only"]
        debug = bool(options["debug"])

        try:
            import cloudinary.uploader
        except Exception as e:
            self.stdout.write(self.style.ERROR("No se pudo importar cloudinary.uploader."))
            self.stdout.write(self.style.ERROR(f"Detalle: {e}"))
            return

        media_root = Path(str(settings.MEDIA_ROOT))

        total = 0
        migrated = 0
        skipped = 0
        missing = 0
        errors = 0

        self.stdout.write(self.style.WARNING("=== Migración de imágenes a Cloudinary (FIX media/) ==="))
        self.stdout.write(f"MEDIA_ROOT: {media_root}")
        self.stdout.write(f"Dry-run: {dry}")
        self.stdout.write(f"Only: {only}")
        self.stdout.write(f"Debug: {debug}")

        def migrate_field(obj, field_name: str, folder: str):
            nonlocal total, migrated, skipped, missing, errors
            total += 1

            f = getattr(obj, field_name, None)
            if not f:
                skipped += 1
                if debug:
                    self.stdout.write(f"[SKIP-empty-field] obj={obj} field={field_name}")
                return

            rel_name = self._norm_rel(getattr(f, "name", "") or "")
            if not rel_name:
                skipped += 1
                if debug:
                    self.stdout.write(f"[SKIP-no-name] obj={obj} field={field_name}")
                return

            # Si no parece ruta (sin carpeta), saltamos
            if "/" not in rel_name:
                skipped += 1
                if debug:
                    self.stdout.write(f"[SKIP-not-path] obj={obj} field={field_name} name={repr(rel_name)}")
                return

            local_path = self._resolve_local_file(media_root, rel_name)
            if not local_path:
                missing += 1
                if debug:
                    self.stdout.write(f"[MISSING] obj={obj} field={field_name} name={repr(rel_name)}")
                return

            # Nombre que quieres guardar en la BD (sin media/)
            stem = local_path.stem
            stored_name = f"kcm/{folder}/{stem}_{getattr(obj, 'pk', 'na')}"

            # Nombre real con el que DEBE existir en Cloudinary, porque tu .url agrega "media/"
            upload_public_id = f"media/{stored_name}"

            if debug:
                self.stdout.write(
                    f"[DEBUG] obj={obj} field={field_name} "
                    f"stored_name={stored_name} upload_public_id={upload_public_id} local={local_path}"
                )

            self.stdout.write(f"[UPLOAD] {obj} -> {field_name}: {local_path} -> {upload_public_id}")

            if dry:
                migrated += 1
                return

            try:
                cloudinary.uploader.upload(
                    str(local_path),
                    public_id=upload_public_id,
                    overwrite=True,
                    resource_type="image",
                )

                # Guardamos SIN "media/" para que el storage no lo duplique
                setattr(obj, field_name, stored_name)
                obj.save(update_fields=[field_name])

                migrated += 1

            except Exception as e:
                errors += 1
                self.stdout.write(self.style.ERROR(f"[ERROR] obj={obj} field={field_name} err={e}"))

        if only in ("all", "propiedades"):
            for p in Propiedad.objects.all():
                migrate_field(p, "portada", "propiedades")

        if only in ("all", "galeria"):
            for ip in ImagenPropiedad.objects.all():
                migrate_field(ip, "imagen", "galeria")

        if only in ("all", "slides"):
            for s in CarouselSlide.objects.all():
                migrate_field(s, "imagen", "banners")

        if only in ("all", "agentes"):
            for a in Agente.objects.all():
                migrate_field(a, "foto", "agentes")

        self.stdout.write(self.style.SUCCESS("=== Resumen ==="))
        self.stdout.write(f"Total revisados: {total}")
        self.stdout.write(f"Migrados: {migrated}")
        self.stdout.write(f"Saltados: {skipped}")
        self.stdout.write(f"Missing local files: {missing}")
        self.stdout.write(f"Errores: {errors}")

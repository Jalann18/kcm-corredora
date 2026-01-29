# core/management/commands/rollback_first_migration.py
from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from core.models import Propiedad, ImagenPropiedad, CarouselSlide, Agente


class Command(BaseCommand):
    """
    Revierte la "primera migración" que dejó ImageFields con public_id tipo:
      kcm/propiedades/<stem>_<pk>

    y los vuelve a rutas reales locales dentro de MEDIA_ROOT, buscando el archivo
    por el <stem> en disco.

    Uso:
      python manage.py rollback_first_migration --dry-run --debug
      python manage.py rollback_first_migration
    """

    help = "Revierte ImageFields 'kcm/...' a rutas locales existentes en MEDIA_ROOT."

    IMG_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Simula sin guardar cambios.")
        parser.add_argument("--debug", action="store_true", help="Logs detallados.")
        parser.add_argument(
            "--only",
            choices=["all", "propiedades", "galeria", "slides", "agentes"],
            default="all",
            help="Revertir solo un subconjunto (por defecto: all).",
        )

    def _norm(self, s: str) -> str:
        return (s or "").strip().replace("\\", "/")

    def _is_kcm_public_id(self, name: str) -> bool:
        name = self._norm(name)
        return name.startswith("kcm/")

    def _extract_stem_from_public_id(self, name: str) -> str | None:
        """
        Espera algo como:
          kcm/propiedades/<stem>_<pk>
          kcm/galeria/<stem>_<pk>
          kcm/banners/<stem>_<pk>

        Devuelve <stem> (sin extensión).
        """
        name = self._norm(name)
        last = name.split("/")[-1]  # "<stem>_<pk>"
        if "_" not in last:
            return None
        # cortamos por el último "_" (pk al final)
        stem = last.rsplit("_", 1)[0].strip()
        return stem or None

    def _find_candidate_files(self, media_root: Path, stem: str) -> list[Path]:
        """
        Busca en MEDIA_ROOT cualquier archivo cuya 'stem' sea EXACTAMENTE stem,
        con extensión de imagen permitida.
        """
        matches: list[Path] = []
        # glob recursivo
        for p in media_root.rglob("*"):
            if not p.is_file():
                continue
            if p.suffix.lower() not in self.IMG_EXTS:
                continue
            if p.stem == stem:
                matches.append(p)
        return matches

    def _pick_best_match(self, matches: list[Path], prefer_folders: list[str]) -> Path | None:
        """
        Si hay múltiples matches, prioriza los que contengan alguna carpeta preferida.
        prefer_folders: lista de substrings estilo 'propiedades/galeria' (con /).
        """
        if not matches:
            return None
        if len(matches) == 1:
            return matches[0]

        # Normalizamos a strings con /
        norm = [str(m).replace("\\", "/") for m in matches]

        # Preferencias por carpeta
        for pref in prefer_folders:
            for i, m in enumerate(norm):
                if f"/{pref}/" in m or m.endswith(f"/{pref}"):
                    return matches[i]

        # Si no calza, elige el primero ordenado por path (determinista)
        matches_sorted = sorted(matches, key=lambda x: str(x).lower())
        return matches_sorted[0]

    def _to_rel_media(self, media_root: Path, file_path: Path) -> str:
        rel = file_path.relative_to(media_root)
        return self._norm(str(rel))

    def handle(self, *args, **options):
        dry = bool(options["dry_run"])
        debug = bool(options["debug"])
        only = options["only"]

        media_root = Path(str(settings.MEDIA_ROOT))

        self.stdout.write(self.style.WARNING("=== Rollback primera migración (kcm -> media local) ==="))
        self.stdout.write(f"MEDIA_ROOT: {media_root}")
        self.stdout.write(f"Dry-run: {dry}")
        self.stdout.write(f"Debug: {debug}")
        self.stdout.write(f"Only: {only}")

        total = 0
        changed = 0
        missing = 0
        skipped = 0
        ambiguous = 0
        errors = 0

        def rollback_field(obj, field_name: str, prefer_folders: list[str]):
            nonlocal total, changed, missing, skipped, ambiguous, errors

            total += 1

            f = getattr(obj, field_name, None)
            if not f:
                skipped += 1
                return

            current_name = self._norm(getattr(f, "name", "") or "")
            if not current_name:
                skipped += 1
                return

            # Solo revertimos si parece public_id "kcm/..."
            if not self._is_kcm_public_id(current_name):
                skipped += 1
                if debug:
                    self.stdout.write(f"[SKIP-not-kcm] {obj} {field_name} name={current_name}")
                return

            stem = self._extract_stem_from_public_id(current_name)
            if not stem:
                errors += 1
                self.stdout.write(self.style.ERROR(f"[ERROR-no-stem] {obj} {field_name} name={current_name}"))
                return

            matches = self._find_candidate_files(media_root, stem)
            if not matches:
                missing += 1
                self.stdout.write(self.style.NOTICE(f"[MISSING] {obj} {field_name} stem={stem} from={current_name}"))
                return

            if len(matches) > 1:
                ambiguous += 1
                if debug:
                    self.stdout.write(f"[AMBIGUOUS] {obj} {field_name} stem={stem} matches={len(matches)}")

            best = self._pick_best_match(matches, prefer_folders)
            if not best:
                missing += 1
                self.stdout.write(self.style.NOTICE(f"[MISSING-best] {obj} {field_name} stem={stem}"))
                return

            new_rel = self._to_rel_media(media_root, best)

            if debug:
                self.stdout.write(
                    f"[SET] {obj} {field_name}\n"
                    f"  old: {current_name}\n"
                    f"  new: {new_rel}"
                )

            if dry:
                changed += 1
                return

            try:
                setattr(obj, field_name, new_rel)
                obj.save(update_fields=[field_name])
                changed += 1
            except Exception as e:
                errors += 1
                self.stdout.write(self.style.ERROR(f"[ERROR-save] {obj} {field_name}: {e}"))

        # ---- Ejecutamos según --only ----

        if only in ("all", "propiedades"):
            # Portadas suelen estar en media/propiedades/propiedades/...
            for p in Propiedad.objects.all():
                rollback_field(p, "portada", prefer_folders=["propiedades/propiedades", "propiedades"])

        if only in ("all", "galeria"):
            # Galería en media/propiedades/galeria/...
            for ip in ImagenPropiedad.objects.all():
                rollback_field(ip, "imagen", prefer_folders=["propiedades/galeria", "galeria", "propiedades"])

        if only in ("all", "slides"):
            # Slides en media/banners/...
            for s in CarouselSlide.objects.all():
                rollback_field(s, "imagen", prefer_folders=["banners", "banner", "slides"])

        if only in ("all", "agentes"):
            # Agentes en media/agentes/...
            for a in Agente.objects.all():
                rollback_field(a, "foto", prefer_folders=["agentes", "equipo"])

        # ---- Resumen ----
        self.stdout.write(self.style.SUCCESS("=== Resumen ==="))
        self.stdout.write(f"Total revisados: {total}")
        self.stdout.write(f"Actualizados: {changed}")
        self.stdout.write(f"Ambiguos (múltiples matches): {ambiguous}")
        self.stdout.write(f"Missing (sin archivo local): {missing}")
        self.stdout.write(f"Saltados: {skipped}")
        self.stdout.write(f"Errores: {errors}")

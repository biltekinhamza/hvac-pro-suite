from __future__ import annotations

from app.ventilation.part_config import PARTS, list_parts


class VentilationService:
    def parts(self) -> list[dict]:
        return list_parts()

    def get_part(self, code: str) -> dict:
        try:
            return PARTS[code]
        except KeyError as exc:
            raise ValueError("Parca bulunamadi.") from exc


ventilation_service = VentilationService()

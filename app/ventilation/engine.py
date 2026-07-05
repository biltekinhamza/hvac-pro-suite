from __future__ import annotations

import math
from decimal import Decimal

from app.repository import Repository
from app.utils import D, q2
from app.ventilation.agiz import agizlari_getir, toplam_cevres_metre, toplam_civata
from app.ventilation.formulas import calculate_geometry
from app.ventilation.part_config import PARTS


class CostEngine:
    def __init__(self, repo: Repository) -> None:
        self.repo = repo

    def calculate(self, part_code: str, inputs: dict[str, object]) -> dict:
        data = dict(inputs)
        geometry = calculate_geometry(part_code, data)
        sac_option_id = data.get("sac_ozellik_id")

        if sac_option_id in (None, "", "0"):
            sac_option = self.repo.find_square_sheet_option(data.get("sac_kalinlik_mm")) or self.repo.find_first_option_by_name("SAC")
        else:
            sac_option = self.repo.get_material_option(int(sac_option_id))
        if not sac_option:
            raise ValueError("Sac stok kartı bulunamadı.")

        sac_cost = q2(D(geometry["kg"]) * D(sac_option["average_unit_cost"]))
        agizlar = agizlari_getir(part_code, data)
        total_meter = toplam_cevres_metre(agizlar)

        flans_cost = self._flans_cost(part_code, data, total_meter)
        conta_cost = self._meter_cost(data.get("conta_ekle"), data.get("conta_ozellik_id"), "CONTA", total_meter)

        vida_cost = Decimal("0")
        if self._checked(data.get("vida_ekle")):
            option = self._resolve_option_id(data.get("vida_ozellik_id"), "VIDA")
            if option:
                row = self.repo.get_material_option(option)
                vida_cost = q2(Decimal(toplam_civata(agizlar)) * D(row["average_unit_cost"]))

        izolasyon_cost = Decimal("0")
        iz_opt = data.get("izolasyon_ozellik_id")
        if iz_opt not in (None, "", "0"):
            row = self.repo.get_material_option(int(iz_opt))
            izolasyon_cost = q2(D(geometry["kesilen_m2"]) * D(row["average_unit_cost"]))

        boya_cost = Decimal("0")
        if self._checked(data.get("boya_ekle")):
            boya_cost = q2(D(geometry["kesilen_m2"]) * D(data.get("boya_birim_fiyat") or "0"))

        other_cost = q2(flans_cost + conta_cost + vida_cost + izolasyon_cost + boya_cost)
        labor = q2((sac_cost + other_cost) * D("0.10"))
        total = q2(sac_cost + other_cost + labor)

        return {
            "part_name": PARTS[part_code]["title"],
            "kg": geometry["kg"],
            "kesilen_m2": geometry["kesilen_m2"],
            "sac_maliyeti": sac_cost,
            "diger_malzeme_maliyeti": other_cost,
            "boya_maliyeti": boya_cost,
            "iscilik_maliyeti": labor,
            "toplam_maliyet": total,
        }

    def calculate_sale(self, result: dict, profit_rate: object, quantity: int) -> dict:
        unit_cost = D(result["toplam_maliyet"])
        unit_price = q2(unit_cost * (Decimal("1") + (D(profit_rate) / Decimal("100"))))
        line_total = q2(unit_price * Decimal(quantity))
        return {"unit_cost": q2(unit_cost), "unit_price": unit_price, "unit_profit": q2(unit_price - unit_cost), "line_total": line_total}

    def _meter_cost(self, checked: object, option_id: object, keyword: str, total_meter: Decimal) -> Decimal:
        if not self._checked(checked):
            return Decimal("0")
        resolved = self._resolve_option_id(option_id, keyword)
        if resolved is None:
            return Decimal("0")
        row = self.repo.get_material_option(resolved)
        return q2(total_meter * D(row["average_unit_cost"]))

    def _flans_cost(self, part_code: str, data: dict[str, object], total_meter: Decimal) -> Decimal:
        if PARTS[part_code]["group"] != "kare":
            return self._meter_cost(data.get("flans_ekle"), data.get("flans_ozellik_id"), "FLANS", total_meter)

        row = self.repo.find_option_by_name_and_option("FLANS", "20") or self.repo.find_first_option_by_name("FLANS")
        if not row:
            return Decimal("0")
        flans_meter = self._auto_square_flans_meter(part_code, data, total_meter)
        return q2(flans_meter * D(row["average_unit_cost"]))

    def _auto_square_flans_meter(self, part_code: str, data: dict[str, object], total_meter: Decimal) -> Decimal:
        if part_code != "dikdortgen_kanal":
            return total_meter
        length_m = D(data.get("uzunluk") or "0")
        if length_m <= 0:
            return Decimal("0")
        en = D(data.get("agiz_en") or "0")
        boy = D(data.get("agiz_boy") or "0")
        one_mouth_meter = (Decimal("2") * (en + boy)) / Decimal("100")
        piece_count = Decimal(math.ceil(float(length_m / Decimal("1.2"))))
        return one_mouth_meter * piece_count * Decimal("2")

    def _resolve_option_id(self, option_id: object, keyword: str) -> int | None:
        if option_id not in (None, "", "0"):
            return int(option_id)
        row = self.repo.find_first_option_by_name(keyword)
        return int(row["id"]) if row else None

    @staticmethod
    def _checked(value: object) -> bool:
        return str(value).lower() in {"1", "true", "on", "yes"}

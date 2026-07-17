from __future__ import annotations

import asyncio
from decimal import Decimal
import gc
from pathlib import Path
import tempfile
import unittest

import app.repository as repository_module
from app.accounting.parasut_service import ParasutService
from app.database import Database
from app.repository import Repository
from app.ventilation.engine import CostEngine
from app.ventilation.formulas import calculate_geometry
from app.ventilation.part_config import list_parts
from app.ventilation.part_description import part_measure_text


class FormulaTests(unittest.TestCase):
    def test_equal_arm_pairs_are_only_exposed_for_two_arm_parts(self) -> None:
        parts = {part["code"]: part for part in list_parts()}

        self.assertEqual(
            parts["kare_pantolon"]["equal_arm_pairs"],
            [
                {"source": "sol_en", "target": "sag_en"},
                {"source": "sol_boy", "target": "sag_boy"},
            ],
        )
        self.assertTrue(parts["kare_istavroz"]["equal_arm_pairs"])
        self.assertTrue(parts["yuvarlak_istavroz"]["equal_arm_pairs"])
        self.assertEqual(parts["kare_es_2"]["equal_arm_pairs"], [])
        self.assertTrue(all(part["marker_display"] == "focus" for part in parts.values()))

    def test_every_part_field_has_a_valid_dimension_marker(self) -> None:
        parts = {part["code"]: part for part in list_parts()}

        for code, part in parts.items():
            with self.subTest(part=code):
                field_names = [field["name"] for field in part["fields"]]
                marker_fields = [marker["field"] for marker in part["dimension_markers"]]
                self.assertEqual(marker_fields, field_names)
                for marker in part["dimension_markers"]:
                    self.assertEqual(len(marker["line"]), 4)
                    self.assertEqual(len(marker["label"]), 2)
                    self.assertTrue(all(0 <= value <= 100 for value in marker["line"] + marker["label"]))

    def test_square_and_round_elbows_use_clear_angle_guides(self) -> None:
        parts = {part["code"]: part for part in list_parts()}

        for code in ("kare_dirsek", "yuvarlak_dirsek"):
            with self.subTest(part=code):
                marker = next(item for item in parts[code]["dimension_markers"] if item["field"] == "aci")
                self.assertEqual(marker["symbol"], "Açı")
                self.assertEqual(len(marker["segments"]), 2)
                self.assertTrue(marker["path"].startswith("M "))

    def test_round_elbow_r_is_the_centerline_radius(self) -> None:
        parts = {part["code"]: part for part in list_parts()}
        radius_field = next(field for field in parts["yuvarlak_dirsek"]["fields"] if field["name"] == "r")

        self.assertEqual(radius_field["label"], "Merkez Hat Radyusu R (cm)")
        self.assertEqual(
            parts["yuvarlak_dirsek"]["computed_fields"],
            [{"field": "r", "source": "cap", "factor": 0.15, "decimals": 2}],
        )
        result = calculate_geometry(
            "yuvarlak_dirsek",
            {"cap": 500, "aci": 90, "r": 10, "sac_kalinlik_mm": 0.60},
        )
        self.assertAlmostEqual(result["alan_m2"], 1.851, places=3)
        self.assertEqual(result["detay"]["merkez_hat_radyusu_cm"], 75.0)
        self.assertEqual(result["detay"]["r_cap_orani"], 1.5)

    def test_square_reducer_es1_and_saddle_markers_match_their_dimensions(self) -> None:
        parts = {part["code"]: part for part in list_parts()}

        reducer_symbols = [marker["symbol"] for marker in parts["kare_reduksiyon"]["dimension_markers"]]
        self.assertEqual(reducer_symbols, ["A1", "B1", "A2", "B2", "H"])
        offset_marker = next(
            marker for marker in parts["kare_es_1"]["dimension_markers"] if marker["field"] == "kaciklik"
        )
        self.assertEqual(offset_marker["symbol"], "Kaçıklık")
        self.assertEqual(len(offset_marker["segments"]), 3)
        self.assertEqual(parts["kare_saplama"]["computed_fields"], [])
        self.assertEqual(
            [field["name"] for field in parts["kare_saplama"]["fields"]],
            ["agiz_en", "agiz_boy"],
        )
        mouth_depth = next(
            marker for marker in parts["kare_saplama"]["dimension_markers"] if marker["field"] == "agiz_boy"
        )
        self.assertEqual(mouth_depth["line"], [74, 80, 78, 73])

    def test_square_saddle_uses_automatic_50_cm_length(self) -> None:
        result = calculate_geometry(
            "kare_saplama",
            {"agiz_en": 100, "agiz_boy": 50, "boy": 10, "sac_kalinlik_mm": 0.60},
        )

        self.assertEqual(result["detay"]["parca_boyu_cm"], 50.0)
        self.assertEqual(result["detay"]["govde_alani_m2"], 1.5)
        self.assertEqual(part_measure_text("kare_saplama", {"agiz_en": 100, "agiz_boy": 50}), "100x50cm")

    def test_cross_and_coupling_markers_follow_the_correct_axes(self) -> None:
        parts = {part["code"]: part for part in list_parts()}
        square_cross = {
            marker["field"]: marker["line"] for marker in parts["kare_istavroz"]["dimension_markers"]
        }

        self.assertEqual(square_cross["sol_en"], [6, 24, 8, 66])
        self.assertEqual(square_cross["sol_boy"], [6, 24, 14, 34])
        self.assertEqual(square_cross["sag_en"], [93, 25, 91, 54])
        self.assertEqual(square_cross["sag_boy"], [79, 17, 93, 25])
        self.assertEqual(square_cross["alt_boy"], [21, 74, 32, 87])
        round_cross_l1 = next(
            marker for marker in parts["yuvarlak_istavroz"]["dimension_markers"] if marker["field"] == "sol_boy"
        )
        coupling_l = next(
            marker for marker in parts["yuvarlak_mason"]["dimension_markers"] if marker["field"] == "boy"
        )
        self.assertEqual(round_cross_l1["line"], [22, 59, 42, 59])
        self.assertEqual(coupling_l["line"], [54, 16, 69, 22])

    def test_box_uses_hidden_fixed_15_cm_round_outlet(self) -> None:
        parts = {part["code"]: part for part in list_parts()}
        self.assertNotIn("boru_boyu", [field["name"] for field in parts["kutu"]["fields"]])
        result = calculate_geometry(
            "kutu",
            {"en": 100, "boy": 80, "yukseklik": 50, "cap": 400, "boru_boyu": 99, "sac_kalinlik_mm": 0.60},
        )
        self.assertEqual(result["detay"]["yuvarlak_boru_boyu_cm"], 15.0)
        self.assertAlmostEqual(result["detay"]["yuvarlak_boru_cm2"], 1884.96, places=2)
        self.assertEqual(
            part_measure_text("kutu", {"en": 100, "boy": 80, "yukseklik": 50, "cap": 400}),
            "100x80x50cm Ø400mm",
        )

    def test_square_pants_uses_real_dimensions_of_all_three_mouths(self) -> None:
        result = calculate_geometry(
            "kare_pantolon",
            {
                "ana_en": 100,
                "kanal_derinligi": 60,
                "ana_boy": 80,
                "sol_en": 50,
                "sol_boy": 40,
                "sag_en": 50,
                "sag_boy": 40,
                "sac_kalinlik_mm": 0.60,
            },
        )

        self.assertEqual(result["detay"]["govde_cm2"], 25600.0)
        self.assertAlmostEqual(result["detay"]["sol_dirsek_cm2"], 14137.17, places=2)
        self.assertAlmostEqual(result["detay"]["sag_dirsek_cm2"], 14137.17, places=2)
        self.assertEqual(result["detay"]["flans_cm2"], 2040.0)

    def test_round_tee_derives_branch_length_from_main_length_and_branch_diameter(self) -> None:
        result = calculate_geometry(
            "yuvarlak_te",
            {
                "ana_cap": 630,
                "kol_cap": 280,
                "ana_boy": 50,
                "sac_kalinlik_mm": 0.60,
            },
        )

        self.assertEqual(result["detay"]["kol_boyu_cm"], 22.0)
        self.assertAlmostEqual(result["detay"]["kol_cm2"], 1935.22, places=2)

    def test_rectangular_duct_adds_two_flanged_mouths_for_every_1_2_meter_piece(self) -> None:
        result = calculate_geometry(
            "dikdortgen_kanal",
            {
                "agiz_en": 50,
                "agiz_boy": 30,
                "uzunluk": 2.4,
                "sac_kalinlik_mm": 0.60,
            },
        )

        self.assertEqual(result["detay"]["parca_adedi"], 2)
        self.assertEqual(result["detay"]["flans_m2"], 0.192)

    def test_round_damper_calculates_body_and_multiblade_sheet_weight(self) -> None:
        result = calculate_geometry(
            "yuvarlak_klape",
            {
                "cap": 800,
                "sac_kalinlik_mm": 0.80,
            },
        )

        self.assertEqual(result["detay"]["govde_boyu_mm"], 850.0)
        self.assertEqual(result["detay"]["kanat_capi_mm"], 796.0)
        self.assertEqual(result["detay"]["kanat_sayisi"], 4)
        self.assertEqual(result["kg"], 17.41)

    def test_round_damper_uses_200_mm_body_up_to_150_mm_diameter(self) -> None:
        result = calculate_geometry(
            "yuvarlak_klape",
            {
                "cap": 150,
                "sac_kalinlik_mm": 0.60,
            },
        )

        self.assertEqual(result["detay"]["govde_boyu_mm"], 200.0)
        self.assertEqual(result["detay"]["kanat_sayisi"], 1)

    def test_jetcap_scales_catalog_weight_to_selected_sheet_and_adds_waste(self) -> None:
        result = calculate_geometry(
            "yuvarlak_jetkap",
            {
                "cap": 400,
                "sac_kalinlik_mm": 0.90,
            },
        )

        self.assertEqual(result["detay"]["katalog_araligi_mm"], "400")
        self.assertEqual(result["kg"], 18.11)

    def test_jetcap_interpolates_material_area_for_non_catalog_diameter(self) -> None:
        result = calculate_geometry(
            "yuvarlak_jetkap",
            {
                "cap": 224,
                "sac_kalinlik_mm": 0.60,
            },
        )

        self.assertEqual(result["detay"]["katalog_araligi_mm"], "200-225")
        self.assertGreater(result["kg"], 3.5)
        self.assertLess(result["kg"], 4.3)

    def test_round_saddle_uses_hidden_fixed_20_cm_length(self) -> None:
        result = calculate_geometry(
            "yuvarlak_saplama",
            {
                "cap": 400,
                "boy": 999,
                "sac_kalinlik_mm": 0.80,
            },
        )

        self.assertEqual(result["detay"]["boy_mm"], 200.0)
        self.assertEqual(result["detay"]["acilim_m2"], 0.251)
        self.assertEqual(result["kg"], 1.66)

    def test_round_rain_cap_scales_catalog_weight_and_adds_waste(self) -> None:
        result = calculate_geometry(
            "yuvarlak_sapka",
            {
                "cap": 400,
                "sac_kalinlik_mm": 0.90,
            },
        )

        self.assertEqual(result["detay"]["katalog_araligi_mm"], "400")
        self.assertEqual(result["kg"], 6.63)

    def test_round_rain_cap_interpolates_non_catalog_diameter(self) -> None:
        result = calculate_geometry(
            "yuvarlak_sapka",
            {
                "cap": 224,
                "sac_kalinlik_mm": 0.60,
            },
        )

        self.assertEqual(result["detay"]["katalog_araligi_mm"], "200-225")


class FixedRoundCostTests(unittest.TestCase):
    class FakeRepository:
        def get_round_part_price(self, part_code: str, cap_mm: int) -> float | None:
            return 100.0 if (part_code, cap_mm) == ("spiro_boru", 100) else None

        def find_square_sheet_option(self, thickness: object):
            return {"average_unit_cost": 50}

    def test_actual_cost_and_fixed_sale_price_are_calculated_separately(self) -> None:
        engine = CostEngine(self.FakeRepository())
        result = engine.calculate(
            "spiro_boru",
            {"cap": 100, "uzunluk": 2, "sac_kalinlik_mm": 0.60},
        )
        sale = engine.calculate_sale(result, 0, 1)

        self.assertEqual(result["sac_maliyeti"], Decimal("156.00"))
        self.assertEqual(result["iscilik_maliyeti"], Decimal("15.60"))
        self.assertEqual(result["toplam_maliyet"], Decimal("171.60"))
        self.assertEqual(result["sabit_satis_fiyati"], Decimal("200.00"))
        self.assertEqual(sale["unit_price"], Decimal("200.00"))


class QuoteTotalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.old_db = repository_module.db
        repository_module.db = Database(Path(self.temp_dir.name) / "test.sqlite3")
        repository_module.db.initialize()
        self.repository = Repository()

    def tearDown(self) -> None:
        repository_module.db = self.old_db
        gc.collect()
        self.temp_dir.cleanup()

    def test_shipping_is_in_total_but_excluded_from_profit(self) -> None:
        quote_id = self.repository.create_quote(
            "Test",
            30,
            [{
                "part_code": "spiro_boru",
                "part_name": "Spiro Boru",
                "quantity": 2,
                "unit_cost": 100,
                "unit_price": 100,
                "line_total": 200,
                "cut_area_m2": 1,
                "weight_kg": 1,
                "inputs": {},
                "result": {},
            }],
        )
        quote, _items = self.repository.get_quote(quote_id)
        self.assertEqual(Decimal(str(quote["total_amount"])), Decimal("230.00"))

        self.repository.apply_quote_profit_rate(quote_id, 10)
        quote, _items = self.repository.get_quote(quote_id)
        self.assertEqual(Decimal(str(quote["total_amount"])), Decimal("250.00"))

        self.repository.apply_quote_shipping_amount(quote_id, 40)
        quote, _items = self.repository.get_quote(quote_id)
        self.assertEqual(Decimal(str(quote["total_amount"])), Decimal("260.00"))

    def test_sheet_price_lookup_is_exact_and_065_has_its_own_card(self) -> None:
        option = self.repository.find_square_sheet_option("0.65")
        self.assertIsNotNone(option)
        self.assertEqual(option["option_name"], "0.65 mm")
        self.assertIsNone(self.repository.find_square_sheet_option("0.66"))


class ParasutShippingTests(unittest.TestCase):
    class FakeClient:
        def __init__(self) -> None:
            self.offer_payload = None

        async def request(self, method: str, path: str, **kwargs):
            if method == "GET" and path == "/contacts":
                return {"data": [{"id": "contact-1"}]}
            if method == "GET" and path == "/products":
                code = kwargs["params"]["filter[code]"]
                return {"data": [{"id": f"product-{code}"}]}
            if method == "POST" and path == "/sales_offers":
                self.offer_payload = kwargs["json"]
                return {"data": {"id": "offer-1"}}
            raise AssertionError((method, path, kwargs))

    def test_shipping_is_sent_as_a_separate_offer_line(self) -> None:
        client = self.FakeClient()
        service = ParasutService(client)
        offer_id = asyncio.run(service.create_offer_from_quote(
            {"id": 1, "customer_name": "Test", "shipping_amount": 75},
            [{
                "part_code": "spiro_boru",
                "part_name": "Spiro Boru",
                "quantity": 2,
                "unit_price": 100,
                "inputs": {},
            }],
        ))

        self.assertEqual(offer_id, "offer-1")
        details = client.offer_payload["data"]["relationships"]["details"]["data"]
        self.assertEqual(len(details), 2)
        self.assertEqual(details[1]["attributes"]["description"], "Nakliye")
        self.assertEqual(details[1]["attributes"]["unit_price"], 75.0)
        self.assertEqual(
            details[1]["relationships"]["product"]["data"]["id"],
            "product-NAKLIYE",
        )


if __name__ == "__main__":
    unittest.main()

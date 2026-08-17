from __future__ import annotations

import asyncio
from decimal import Decimal
import gc
from pathlib import Path
import tempfile
import unittest

import app.repository as repository_module
from app.accounting.parasut_service import ParasutService
from app.config import Settings
from app.database import Database
from app.quote_pdf import build_quote_pdf
from app.repository import Repository
from app.utils import q2
from app.ventilation.engine import CostEngine
from app.ventilation.formulas import calculate_geometry
from app.ventilation.part_config import list_parts
from app.ventilation.part_description import part_measure_text
from app.ventilation.sales_units import NO_QUANTITY_PARTS, sales_fields


class QuotePdfTests(unittest.TestCase):
    def test_quote_pdf_is_generated_from_customer_prices(self) -> None:
        payload = {
            "quote": {
                "id": 42,
                "customer_name": "Örnek Müşteri",
                "profit_rate": 35,
                "shipping_amount": 250,
                "total_amount": 1450,
                "created_at": "2026-08-03 10:30:00",
            },
            "items": [{
                "part_name": "Kare Dirsek",
                "display_name": "Kare Dirsek (Boyalı)",
                "detail_parts": ["2 adet", "Sac: 0.60 mm", "Ölçüler: 500x400mm"],
                "quantity": 2,
                "unit_cost": 400,
                "unit_price": 600,
                "line_total": 1200,
            }],
        }

        pdf = build_quote_pdf(payload, Settings(_env_file=None, company_name="HVAC Pro Suite", default_vat_rate=20))

        self.assertTrue(pdf.startswith(b"%PDF-"))
        self.assertGreater(len(pdf), 1000)

    def test_sales_units_change_without_changing_line_total(self) -> None:
        spiro = sales_fields("spiro_boru", {"uzunluk": 2.5}, {"alan_m2": 0.8}, 2, 500)
        duct = sales_fields("dikdortgen_kanal", {"uzunluk": 1.2}, {"alan_m2": 2.64}, 17, 11220)
        fitting = sales_fields("kare_dirsek", {}, {"alan_m2": 1}, 3, 300)

        self.assertEqual((spiro["sales_quantity"], spiro["sales_unit"], spiro["sales_unit_price"]), (5.0, "m", 100.0))
        self.assertNotIn("spiro_boru", NO_QUANTITY_PARTS)
        self.assertEqual((duct["sales_quantity"], duct["sales_unit"], duct["sales_unit_price"]), (44.88, "m2", 250.0))
        self.assertNotIn("dikdortgen_kanal", NO_QUANTITY_PARTS)
        self.assertEqual((fitting["sales_quantity"], fitting["sales_unit"], fitting["sales_unit_price"]), (3.0, "adet", 100.0))


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

    def test_single_arm_pants_mouth_markers_share_their_real_corners(self) -> None:
        part = next(item for item in list_parts() if item["code"] == "kare_pantolon_2")
        markers = {marker["field"]: marker for marker in part["dimension_markers"]}

        self.assertEqual(markers["taban_en"]["line"][:2], markers["ana_yukseklik"]["line"][2:])
        self.assertEqual(markers["taban_en"]["line"][2:], markers["taban_boy"]["line"][:2])
        self.assertEqual(markers["ana_cikis_en"]["line"][:2], markers["ana_yukseklik"]["line"][:2])
        self.assertEqual(markers["ana_cikis_en"]["line"][2:], markers["ana_cikis_boy"]["line"][:2])

    def test_round_elbow_measure_includes_angle(self) -> None:
        self.assertEqual(
            part_measure_text("yuvarlak_dirsek", {"cap": 500, "aci": 90}),
            "Ø500mm 90°",
        )

    def test_round_elbow_uses_automatic_centerline_radius(self) -> None:
        parts = {part["code"]: part for part in list_parts()}

        self.assertEqual(
            [field["name"] for field in parts["yuvarlak_dirsek"]["fields"]],
            ["cap", "aci"],
        )
        self.assertEqual(parts["yuvarlak_dirsek"]["computed_fields"], [])
        result = calculate_geometry(
            "yuvarlak_dirsek",
            {"cap": 500, "aci": 90, "sac_kalinlik_mm": 0.60},
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
        self.assertNotIn("flans_cm2", result["detay"])

    def test_single_arm_square_pants_derives_radius_and_branch_exit_length(self) -> None:
        result = calculate_geometry(
            "kare_pantolon_2",
            {
                "taban_en": 100,
                "taban_boy": 50,
                "ana_cikis_en": 80,
                "ana_cikis_boy": 40,
                "ana_yukseklik": 80,
                "kol_en": 40,
                "kol_boy": 30,
                "sac_kalinlik_mm": 0.60,
            },
        )

        self.assertEqual(result["detay"]["kol_donus_radyusu_cm"], 30.0)
        self.assertEqual(result["detay"]["yan_kol_cikis_boyu_cm"], 50.0)
        self.assertEqual(result["detay"]["ana_cikis_en_cm"], 80.0)
        self.assertEqual(result["detay"]["ana_cikis_boy_cm"], 40.0)

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

    def test_rectangular_duct_excludes_ready_flange_from_sheet_area(self) -> None:
        result = calculate_geometry(
            "dikdortgen_kanal",
            {
                "agiz_en": 30,
                "agiz_boy": 30,
                "uzunluk": 1.2,
                "sac_kalinlik_mm": 0.60,
            },
        )

        self.assertEqual(result["detay"]["parca_adedi"], 1)
        self.assertEqual(result["detay"]["acilim_m2"], 1.44)
        self.assertEqual(result["detay"]["kenet_m2"], 0.036)
        self.assertNotIn("flans_m2", result["detay"])
        self.assertEqual(result["kesilen_m2"], 1.476)

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


class RoundMinimumMaterialCostTests(unittest.TestCase):
    class FakeRepository:
        labor_rates = {"fitting": 0, "square_duct": 0, "spiro": 0}

        def get_labor_rates(self) -> dict[str, float]:
            return self.labor_rates

        def find_square_sheet_option(self, thickness: object):
            return {"average_unit_cost": 50}

        def find_option_by_name_and_option(self, name: str, option: str):
            return None

        def find_first_option_by_name(self, name: str):
            return None

    def test_round_part_below_one_m2_is_priced_as_one_m2(self) -> None:
        engine = CostEngine(self.FakeRepository())
        result = engine.calculate(
            "spiro_boru",
            {"cap": 100, "uzunluk": 2, "sac_kalinlik_mm": 0.60},
        )
        sale = engine.calculate_sale(result, 0, 1)

        self.assertEqual(result["kesilen_m2"], 0.661)
        self.assertEqual(result["kg"], 3.12)
        self.assertEqual(result["fiyatlandirilan_sac_m2"], Decimal("1"))
        self.assertEqual(result["sac_maliyeti"], Decimal("235.50"))
        self.assertEqual(result["iscilik_maliyeti"], Decimal("0.00"))
        self.assertEqual(result["toplam_maliyet"], Decimal("235.50"))
        self.assertEqual(sale["unit_price"], Decimal("235.50"))

    def test_square_part_below_one_m2_is_priced_as_one_m2(self) -> None:
        result = CostEngine(self.FakeRepository()).calculate(
            "kare_saplama",
            {"agiz_en": 20, "agiz_boy": 20, "sac_kalinlik_mm": 0.60},
        )

        self.assertLess(result["kesilen_m2"], 1)
        self.assertEqual(result["fiyatlandirilan_sac_m2"], Decimal("1"))
        self.assertEqual(result["sac_maliyeti"], Decimal("235.50"))

    def test_rectangular_duct_bills_uniform_m2_price(self) -> None:
        engine = CostEngine(self.FakeRepository())
        small = engine.calculate(
            "dikdortgen_kanal",
            {"agiz_en": 25, "agiz_boy": 25, "uzunluk": 1, "sac_kalinlik_mm": 0.60},
        )
        large = engine.calculate(
            "dikdortgen_kanal",
            {"agiz_en": 30, "agiz_boy": 30, "uzunluk": 1.2, "sac_kalinlik_mm": 0.60},
        )
        sale_small = engine.calculate_sale(small, 40, 10)
        sale_large = engine.calculate_sale(large, 40, 20)

        self.assertEqual(sale_small["unit_price"], sale_large["unit_price"])
        self.assertEqual(
            sale_large["line_total"],
            q2(sale_large["unit_price"] * large["billable_m2"] * Decimal(20)),
        )
        self.assertEqual(sale_small["unit_price"], q2(sale_small["unit_cost"] * Decimal("1.40")))

    def test_rectangular_duct_below_one_m2_is_billed_as_one_m2(self) -> None:
        engine = CostEngine(self.FakeRepository())
        result = engine.calculate(
            "dikdortgen_kanal",
            {"agiz_en": 15, "agiz_boy": 15, "uzunluk": 1, "sac_kalinlik_mm": 0.60},
        )

        self.assertLess(result["alan_m2"], 1)
        self.assertEqual(result["billable_m2"], Decimal("1"))

    def test_rectangular_duct_minimum_m2_applies_to_the_total_line(self) -> None:
        engine = CostEngine(self.FakeRepository())
        result = engine.calculate(
            "dikdortgen_kanal",
            {"agiz_en": 20, "agiz_boy": 15, "uzunluk": 1.2, "sac_kalinlik_mm": 0.60},
        )
        sale = engine.calculate_sale(result, 30, 10)

        self.assertEqual(result["alan_m2"], 0.84)
        self.assertEqual(
            sale["line_total"],
            q2(sale["unit_price"] * Decimal("8.4")),
        )

    def test_spiro_labor_rate_is_taken_from_admin_setting(self) -> None:
        repository = self.FakeRepository()
        repository.labor_rates = {"fitting": 0, "square_duct": 0, "spiro": 15}
        result = CostEngine(repository).calculate(
            "spiro_boru",
            {"cap": 100, "uzunluk": 2, "sac_kalinlik_mm": 0.60},
        )

        self.assertEqual(result["iscilik_maliyeti"], Decimal("35.33"))
        self.assertEqual(result["toplam_maliyet"], Decimal("270.83"))

    def test_labor_rates_apply_to_their_assigned_part_groups(self) -> None:
        repository = self.FakeRepository()
        repository.labor_rates = {"fitting": 10, "square_duct": 20, "spiro": 30}
        engine = CostEngine(repository)

        fitting = engine.calculate("yuvarlak_dirsek", {"cap": 500, "aci": 90, "sac_kalinlik_mm": 0.60})
        square_duct = engine.calculate(
            "dikdortgen_kanal",
            {"agiz_en": 50, "agiz_boy": 30, "uzunluk": 1, "sac_kalinlik_mm": 0.60},
        )
        spiro = engine.calculate("spiro_boru", {"cap": 100, "uzunluk": 2, "sac_kalinlik_mm": 0.60})

        self.assertEqual(fitting["iscilik_maliyeti"], (fitting["sac_maliyeti"] + fitting["diger_malzeme_maliyeti"]) * Decimal("0.10"))
        self.assertEqual(square_duct["iscilik_maliyeti"], (square_duct["sac_maliyeti"] + square_duct["diger_malzeme_maliyeti"]) * Decimal("0.20"))
        self.assertEqual(spiro["iscilik_maliyeti"], (spiro["sac_maliyeti"] + spiro["diger_malzeme_maliyeti"]) * Decimal("0.30"))

    def test_round_parts_never_add_flange_cost(self) -> None:
        class FlangeRepository(self.FakeRepository):
            def find_first_option_by_name(self, name: str):
                return {"id": 1, "average_unit_cost": 25} if name == "FLANS" else None

            def get_material_option(self, option_id: int):
                return {"id": option_id, "average_unit_cost": 25}

        result = CostEngine(FlangeRepository()).calculate(
            "yuvarlak_reduksiyon",
            {
                "buyuk_cap": 500,
                "kucuk_cap": 300,
                "boy": 40,
                "sac_kalinlik_mm": 0.60,
                "flans_ekle": True,
                "flans_ozellik_id": 1,
            },
        )

        self.assertEqual(result["diger_malzeme_maliyeti"], Decimal("0.00"))


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
            "test-cart-token",
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
                "sales_quantity": 5.126,
                "sales_unit_price": 40.567,
                "inputs": {},
            }],
        ))

        self.assertEqual(offer_id, "offer-1")
        details = client.offer_payload["data"]["relationships"]["details"]["data"]
        self.assertEqual(len(details), 2)
        self.assertEqual(details[0]["attributes"]["quantity"], 5.13)
        self.assertEqual(details[0]["attributes"]["unit_price"], 40.57)
        self.assertEqual(details[1]["attributes"]["description"], "Nakliye")
        self.assertEqual(details[1]["attributes"]["unit_price"], 75.0)
        self.assertEqual(
            details[1]["relationships"]["product"]["data"]["id"],
            "product-NAKLIYE",
        )

    def test_customer_search_returns_parasut_contacts(self) -> None:
        class SearchClient:
            async def request(self, method: str, path: str, **kwargs):
                self.params = kwargs["params"]
                return {
                    "data": [{
                        "id": "42",
                        "attributes": {
                            "name": "Örnek Makine Ltd.",
                            "phone": "05320000000",
                            "tax_number": "1234567890",
                        },
                    }],
                }

        client = SearchClient()
        contacts = asyncio.run(ParasutService(client).search_contacts("Örnek", limit=10))

        self.assertEqual(contacts[0]["name"], "Örnek Makine Ltd.")
        self.assertEqual(contacts[0]["tax_number"], "1234567890")
        self.assertEqual(client.params["filter[name]"], "Örnek")
        self.assertEqual(client.params["filter[account_type]"], "customer")


if __name__ == "__main__":
    unittest.main()

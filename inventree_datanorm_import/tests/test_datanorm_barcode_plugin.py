from importlib import import_module
from importlib.resources import files
import json
from InvenTree.unit_test import InvenTreeTestCase
from inventree_datanorm_import.datanorm_barcode_plugin import DatanormBarcodePlugin
from datanorm import (
    DatanormBaseFile,
    DatanormItem,
    DatanormProductGroupFile,
)
from part.models import Part
from company.models import ManufacturerPart, SupplierPart

GOOD_EAN_13_1 = "3250614315336"
GOOD_EAN_13_2 = "4012195583943"
GOOD_EAN_8 = "90311017"
BAD_EAN1 = "12323"
BAD_EAN2 = "1234567890123"


class TestDatanormBarcodePlugin(InvenTreeTestCase):

    def setUp(self):
        this_package = import_module(
            "inventree_datanorm_import.tests", package="inventree-datanorm-import"
        )
        self.DATANORM_PATH = str(files(this_package).joinpath("datanorm_test.001"))
        self.DATANORM_WRG_PATH = str(files(this_package).joinpath("datanorm_test.WRG"))
        self.DATANORM_PATH_2 = str(files(this_package).joinpath("datanorm_2_test.001"))

        # Remove all parts to start from clean state with each test
        Part.objects.all().delete()
        return super().setUp()

    def test_is_valid_ean_code(self):
        dut = DatanormBarcodePlugin()
        self.assertTrue(dut.is_valid_ean_code(GOOD_EAN_13_1))
        self.assertTrue(dut.is_valid_ean_code(GOOD_EAN_13_2))
        self.assertTrue(dut.is_valid_ean_code(GOOD_EAN_8))
        self.assertFalse(dut.is_valid_ean_code(BAD_EAN1))
        self.assertFalse(dut.is_valid_ean_code(BAD_EAN2))

    def test_create_all_parts(self):
        dut = DatanormBarcodePlugin()
        part = dut.create_all_parts(GOOD_EAN_13_1)
        self.assertEqual(
            part.name, f"Unbekanntes Teil (EAN:{GOOD_EAN_13_1})"
        )  # It will not find attachments!

    def test_create_all_parts_from_datanorm_items(self):
        datanorm_items: list[DatanormItem] = []
        dut = DatanormBarcodePlugin()
        di_1 = DatanormItem("Firmenname")
        DatanormBaseFile(self.DATANORM_PATH).parse(di_1, GOOD_EAN_13_1)
        DatanormProductGroupFile(self.DATANORM_WRG_PATH).parse(di_1)
        datanorm_items.append(di_1)

        di_2 = DatanormItem("Firmenname 2")
        DatanormBaseFile(self.DATANORM_PATH_2).parse(di_2, GOOD_EAN_13_1)
        datanorm_items.append(di_2)

        part = dut.create_all_parts_from_datanorm_items(datanorm_items)
        self.assertEqual(part.name, "Leitungsschutzschalter AC C 16A 3p")
        self.assertEqual(part.keywords, f"MCS316,{GOOD_EAN_13_1}")
        # Query the manufacturer part (we expect only one to exist)
        m_part = ManufacturerPart.objects.get(part=part)
        self.assertEqual(m_part.MPN, "MCS316")
        self.assertEqual(m_part.manufacturer.name, "HAGER")
        # Query the supplier parts (we expect multiple to exist)
        s_part_set = SupplierPart.objects.filter(part=part)
        self.assertEqual(s_part_set[0].SKU, "899977")
        self.assertEqual(s_part_set[0].supplier.name, "Firmenname")
        self.assertEqual(s_part_set[1].SKU, "996634")
        self.assertEqual(s_part_set[1].supplier.name, "Firmenname 2")

    def test_scan(self):
        dut = DatanormBarcodePlugin()

        # create first part with another EAN -> New part will be created
        response_1 = dut.scan(GOOD_EAN_13_1)
        self.assertTrue("part" in response_1.keys())
        expected_response_1 = self.helper_create_expected_response(
            response_1["part"]["pk"]
        )
        self.assertEqual(response_1, expected_response_1)
        self.assertEqual(
            self.helper_get_part_from_response(response_1).barcode_data,
            GOOD_EAN_13_1,
        )

        # create second part with same EAN -> No part will be created, exiting part
        # will be referenced
        response_2 = dut.scan(GOOD_EAN_13_1)
        self.assertEqual(response_2, response_1)

        # detach barcode from existing part -> No part will be created, exiting part
        # will be referenced and barcode is reassigned
        part = self.helper_get_part_from_response(response_1)
        part.unassign_barcode()
        self.assertEqual(
            self.helper_get_part_from_response(response_1).barcode_data, ""
        )
        response_3 = dut.scan(GOOD_EAN_13_1)
        self.assertEqual(response_3, response_1)
        self.assertEqual(
            self.helper_get_part_from_response(response_1).barcode_data,
            GOOD_EAN_13_1,
        )

        # create second part with another EAN -> New part will be created
        response_4 = dut.scan(GOOD_EAN_13_2)
        expected_response_4 = self.helper_create_expected_response(
            response_4["part"]["pk"]
        )
        self.assertEqual(response_4, expected_response_4)
        self.assertEqual(
            self.helper_get_part_from_response(response_4).barcode_data,
            GOOD_EAN_13_2,
        )

        # Try to create third part with bad EAN -> No part will be created
        response_5 = dut.scan(BAD_EAN1)
        expected_response_5 = {}
        self.assertEqual(response_5, expected_response_5)

    def helper_create_expected_response(self, pk: str) -> dict:
        expected_response = {
            "part": {"pk": pk, "api_url": f"/api/part/{pk}/", "web_url": f"/part/{pk}/"}
        }
        return expected_response

    def helper_get_part_from_response(self, response: json) -> Part | None:
        pk = response["part"]["pk"]
        return Part.objects.filter(pk=pk).first()

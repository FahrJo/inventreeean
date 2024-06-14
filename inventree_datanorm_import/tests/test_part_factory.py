from decimal import Decimal
from importlib import import_module
from importlib.resources import files
from common.models import InvenTreeSetting
from InvenTree.unit_test import InvenTreeTestCase
from datanorm import (
    DatanormBaseFile,
    DatanormItem,
    DatanormPriceFile,
    DatanormProductGroupFile,
)
from inventree_datanorm_import.part_factory import PartFactory

GOOD_EAN_13 = "3250614315336"


class TestDatanormPartFactory(InvenTreeTestCase):

    def setUp(self):
        InvenTreeSetting().set_setting("INVENTREE_DEFAULT_CURRENCY", "EUR")
        this_package = import_module(
            "inventree_datanorm_import.tests", package="inventree-datanorm-import"
        )
        self.DATANORM_PATH = str(files(this_package).joinpath("datanorm_test.001"))
        self.DATANORM_WRG_PATH = str(files(this_package).joinpath("datanorm_test.WRG"))
        self.DATPREIS_PATH = str(files(this_package).joinpath("datpreis_test.001"))

        self.MPN = "MCS316"
        return super().setUp()

    # Static methods
    def test_get_si_unit(self):
        result = {"Mtr": "m", "Kg": "kg", "Stk": "", "": "", "Stck": "", "STCK": ""}
        for input, expectation in result.items():
            self.assertEqual(PartFactory.format_si_units(input), expectation)

    def test_get_category_by_name(self):
        category = PartFactory.get_category_by_name("Category 1.1", "Category 1")
        self.assertEqual(category.name, "Category 1.1")
        self.assertEqual(category.parent.name, "Category 1")

    def test_create_empty_part_from_ean(self):
        empty_part = PartFactory.create_empty_part_from_ean(GOOD_EAN_13, "None")
        self.assertEqual(empty_part.name, f"Unbekanntes Teil (EAN:{GOOD_EAN_13})")
        self.assertEqual(empty_part.barcode_data, GOOD_EAN_13)
        self.assertEqual(empty_part.category_path, "None")

    def test_get_company_by_name(self):
        company = PartFactory.get_company_by_name("Company #1")
        self.assertEqual(company.name, "Company #1")
        self.assertFalse(company.is_supplier)
        self.assertFalse(company.is_manufacturer)
        manufacturer = PartFactory.get_company_by_name(
            "Company #1", set_manufacturer=True
        )
        self.assertEqual(company, manufacturer)
        self.assertFalse(manufacturer.is_supplier)
        self.assertTrue(manufacturer.is_manufacturer)
        supplier = PartFactory.get_company_by_name("COMPaNy #1", set_supplier=True)
        self.assertEqual(company, supplier)
        self.assertEqual(supplier.name, "Company #1")
        self.assertTrue(supplier.is_supplier)
        self.assertTrue(supplier.is_manufacturer)
        another_company = PartFactory.get_company_by_name("Company")
        self.assertEqual(company, another_company)
        company.refresh_from_db()
        self.assertTrue(company.is_supplier)
        self.assertTrue(company.is_manufacturer)

    # Object methods
    def test_get_part_from_datanorm_item(self):
        di = self.helper_build_datanorm_item()
        dut = PartFactory(di)
        part = dut.create_part_from_datanorm_item()

        self.assertEqual(part.barcode_data, di.ean)
        self.assertEqual(part.name, di.item_name)
        self.assertEqual(part.keywords, f"{di.matchcode},{di.ean}")
        self.assertEqual(
            part.category_path, f"{di.main_product_group_name}/{di.product_group_name}"
        )

    def test_create_manufacturer_part_from_datanorm_item(self):
        di = self.helper_build_datanorm_item()
        dut = PartFactory(di)

        part = dut.create_part_from_datanorm_item()
        manufacturer_part = dut.create_manufacturer_part_from_datanorm_item(part)
        self.assertEqual(manufacturer_part.MPN, self.MPN)
        self.assertEqual(manufacturer_part.part, part)

    def test_create_supplier_part_from_datanorm_item(self):
        di = self.helper_build_datanorm_item()
        dut = PartFactory(di)

        part = dut.create_part_from_datanorm_item()
        supplier_part = dut.create_supplier_part_from_datanorm_item(part)
        self.assertEqual(supplier_part.SKU, "899977")
        self.assertEqual(supplier_part.part, part)
        self.assertTrue(supplier_part.has_price_breaks)
        self.assertEqual(supplier_part.get_price(2), Decimal("180.00"))
        self.assertEqual(supplier_part.unit_pricing, Decimal("90.00"))
        self.assertEqual(supplier_part.pack_quantity, "1")

    def helper_build_datanorm_item(self) -> DatanormItem:
        di = DatanormItem()
        DatanormBaseFile(self.DATANORM_PATH).parse(di, GOOD_EAN_13)
        DatanormProductGroupFile(self.DATANORM_WRG_PATH).parse(di)
        DatanormPriceFile(self.DATPREIS_PATH).parse(di)
        return di

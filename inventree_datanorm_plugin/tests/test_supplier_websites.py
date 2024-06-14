from InvenTree.unit_test import InvenTreeTestCase
from inventree_datanorm_plugin.supplier_websites import (
    BuerkleWebsite,
    SoneparWebsite,
    WuerthWebsite,
    ZanderWebsite,
    get_supplier_website,
)


class TestSupplierWebsites(InvenTreeTestCase):

    def test_get_supplier_website(self):
        supplier_website = get_supplier_website("J.W.Zander GmbH & Co.KG", "1234")
        self.assertIsInstance(supplier_website, ZanderWebsite)
        supplier_website = get_supplier_website("Adolf Würth GmbH & Co. KG", "1234")
        self.assertIsInstance(supplier_website, WuerthWebsite)
        supplier_website = get_supplier_website("Adolf Wuerth GmbH & Co. KG", "1234")
        self.assertIsInstance(supplier_website, WuerthWebsite)
        supplier_website = get_supplier_website("Alexander Buerkle", "0134989")
        self.assertIsInstance(supplier_website, BuerkleWebsite)
        supplier_website = get_supplier_website("Alexander Bürkle", "0134989")
        self.assertIsInstance(supplier_website, BuerkleWebsite)
        supplier_website = get_supplier_website("Sonepar", "1234")
        self.assertIsInstance(supplier_website, SoneparWebsite)


class TestZanderProductInformation(InvenTreeTestCase):

    def setUp(self):
        self.ZANDER_SKU = "2275151"
        return super().setUp()

    def test_get_parameters(self):
        dut = ZanderWebsite(self.ZANDER_SKU)
        self.assertEqual(dut.parameters["hersteller"], "HAGER")

    def test_get_part_url(self):
        dut = ZanderWebsite(self.ZANDER_SKU)
        link = dut.get_part_url("1234")
        self.assertEqual(link, "https://zander.online/artikel/1234")
        link = dut.get_part_url()
        self.assertEqual(link, "https://zander.online/artikel/2275151")

    def test_get_part_img_url(self):
        dut = ZanderWebsite()
        dut.parameters = {
            "artikel_prefix": "MCS316",
            "artikel_name": "Leitungsschutzschalter AC                         C 16A 3p 415V 3TE 50Hz",  # noqa: E501
            "artikel_nr": "2275151",
        }
        self.assertEqual(
            dut.get_part_img_url(),
            "https://media.zander.online/v1/media/2275151/0/600/MCS316-Leitungsschutzschalter-AC-C-16A-3p-415V-3TE-50Hz.jpg",  # noqa: E501
        )

        dut = ZanderWebsite(2275151)
        self.assertEqual(
            dut.get_part_img_url(),
            "https://media.zander.online/v1/media/2275151/0/600/MCS316-Leitungsschutzschalter-AC-C-16A-3p-415V-3TE-50Hz.jpg",  # noqa: E501
        )


class TestWuerthProductInformation(InvenTreeTestCase):

    def setUp(self):
        self.WUERTH_SKU = "005712 30  100"
        return super().setUp()

    def test_get_parameters(self):
        WuerthWebsite(self.WUERTH_SKU)
        pass

    def test_get_part_url(self):
        dut = WuerthWebsite(self.WUERTH_SKU)
        link = dut.get_part_url("00578  10 1000")
        self.assertEqual(
            link,
            "https://www.wuerth.de/web/media/system/search_redirector.php?SearchResultType=all&EffectiveSearchTerm=&ApiLocale=de_DE&VisibleSearchTerm=00578%20%2010",  # noqa: E501
        )
        link = dut.get_part_url()
        self.assertEqual(
            link,
            "https://www.wuerth.de/web/media/system/search_redirector.php?SearchResultType=all&EffectiveSearchTerm=&ApiLocale=de_DE&VisibleSearchTerm=005712%2030",  # noqa: E501
        )

    def test_get_part_img_url(self):
        dut = WuerthWebsite("019013020 1000")
        self.assertEqual(
            dut.get_part_img_url(),
            "https://media.wuerth.com/source/eshop/stmedia/wuerth/images/std.lang.all/resolutions/category/576px/29578767.jpg",  # noqa: E501
        )


class TestBuerkleProductInformation(InvenTreeTestCase):

    def setUp(self):
        self.BUERKLE_SKU = "0134989"
        return super().setUp()

    def test_get_parameters(self):
        BuerkleWebsite(self.BUERKLE_SKU)
        pass

    def test_get_part_url(self):
        dut = BuerkleWebsite(self.BUERKLE_SKU)
        link = dut.get_part_url("1234")
        self.assertEqual(link, "https://alexander-buerkle.com/de-de/produkt/1234/")
        link = dut.get_part_url()
        self.assertEqual(link, "https://alexander-buerkle.com/de-de/produkt/0134989/")

    def test_get_part_img_url(self):
        dut = BuerkleWebsite(self.BUERKLE_SKU)
        self.assertEqual(
            dut.get_part_img_url(),
            "https://res.cloudinary.com/alexander-buerkle-cloud-services/image/upload/ecommerce/prod/novomind/3439ADF2968728AEE05328C8A8C0E544_DEHA.jpg",  # noqa: E501
        )


class TestSoneparProductInformation(InvenTreeTestCase):

    def setUp(self):
        self.SONEPAR_SKU = "0409027"
        return super().setUp()

    def test_get_parameters(self):
        SoneparWebsite(self.SONEPAR_SKU)
        pass

    def test_get_part_url(self):
        dut = SoneparWebsite(self.SONEPAR_SKU)
        link = dut.get_part_url("1234")
        self.assertEqual(link, "https://www.sonepar.de/dp/1234")
        link = dut.get_part_url()
        self.assertEqual(link, "https://www.sonepar.de/dp/0409027")

    def test_get_part_img_url(self):
        dut = SoneparWebsite(self.SONEPAR_SKU)
        self.assertEqual(dut.get_part_img_url(), "")

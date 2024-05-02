from abc import ABC, abstractmethod
import re
import time
import requests


class SupplierWebsite(ABC):
    sku: str = ""
    parameters: dict | None = None

    def __init__(self, sku: str | None = None):
        self.sku = sku
        if sku is not None:
            self.fetch_part_parameters(sku)

    @abstractmethod
    def fetch_part_parameters(self, sku: str):
        """Fetch part parameters from the website.

        Args:
            sku (str): SKU of the product to fetch the data for.
        """
        pass

    @abstractmethod
    def get_part_img_url(self) -> str:
        """Acquire the URL of the part image

        Returns:
            str: URL of the part image
        """
        pass

    @abstractmethod
    def get_part_url(self, sku: str | None = None) -> str:
        """Acquire the URL of the part website

        Args:
            sku (str | None, optional): SKU of the part. Defaults to None.

        Returns:
            str: URL of the part website
        """
        pass


class BuerkleWebsite(SupplierWebsite):

    def fetch_part_parameters(self, sku: str):
        self.sku = sku
        parameters = None
        client = requests.Session()
        # The following request is neccessary to acquire a valid session ID!
        query = {
            "variables": {"sku": sku},
            "query": "query ProductPage($sku: String!, $tracking: Tracking) {\n  getProductBySku(sku: $sku, tracking: $tracking) {\n    ...productPageFields\n    alternativesEnventa {\n      ...productPageFields\n      __typename\n    }\n    similarProducts {\n      ...productPageFields\n      __typename\n    }\n    baseProducts {\n      ...productPageFields\n      __typename\n    }\n    necessaryAccessories {\n      ...productPageFields\n      __typename\n    }\n    necessarySelections {\n      ...productPageFields\n      __typename\n    }\n    parts {\n      ...productPageFields\n      __typename\n    }\n    accessoriesProducts {\n      ...productPageFields\n      __typename\n    }\n    spareParts {\n      ...productPageFields\n      __typename\n    }\n    replacments {\n      ...productPageFields\n      __typename\n    }\n    __typename\n  }\n}\n\nfragment productPageFields on Product {\n  id\n  slug\n  description\n  categories\n  categoryKey\n  version\n  relationType\n  sku\n  productName\n  ean\n  supplierId\n  supplierProductType\n  supplierProductLink\n  supplierProductNumber\n  supplierUnit\n  oxomiProductNumber\n  image {\n    url\n    label\n    __typename\n  }\n  procuredProduct\n  productCocontractor\n  salesUnit\n  weight\n  packagingSize\n  customTariffNumber\n  salesNumber\n  maxAvailableQuantity\n  quantityUnit\n  topProduct\n  reachInfo\n  isTecselect\n  isAbakus\n  isAbakusPlus\n  isPromotion\n  isUnqualifiedContractProduct\n  onlineAvailable\n  customerArticleNumber\n  pickupStoreFreiburg {\n    channel {\n      name\n      primaryChannel\n      id\n      key\n      address {\n        id\n        externalId\n        primaryAddress\n        name\n        streetName\n        city\n        postalCode\n        country\n        addressExtraLineOne\n        addressExtraLineTwo\n        addressExtraLineThree\n        __typename\n      }\n      __typename\n    }\n    availability {\n      availableQuantity\n      __typename\n    }\n    __typename\n  }\n  productDocumentsDeha {\n    name\n    link\n    __typename\n  }\n  productFeatures {\n    unit\n    featureValueScoped {\n      minValue\n      maxValue\n      __typename\n    }\n    featureValues\n    featureName\n    __typename\n  }\n  __typename\n}",  # noqa: E501
        }
        response = client.post(
            "https://api-prod.alexander-buerkle.com/graphql", json=query
        )
        if response.status_code == 200:
            parameters = response.json()["data"]["getProductBySku"]
        self.parameters = parameters

    def get_part_img_url(self) -> str:
        img_url = ""
        if self.parameters is None:
            self.fetch_part_parameters(self.sku)

        img_url = self.parameters["image"][0]["url"]
        return img_url

    def get_part_url(self, sku: str | None = None) -> str:
        if sku is None:
            sku = self.sku
        return f"https://alexander-buerkle.com/de-de/produkt/{sku}/"


class SoneparWebsite(SupplierWebsite):

    def fetch_part_parameters(self, sku: str):
        self.sku = sku

    def get_part_img_url(self) -> str:
        return ""

    def get_part_url(self, sku: str | None = None) -> str:
        if sku is None:
            sku = self.sku
        return f"https://www.sonepar.de/dp/{sku}"


class WuerthWebsite(SupplierWebsite):

    def fetch_part_parameters(self, sku: str):
        self.sku = sku

    def get_part_img_url(self) -> str:
        img_url = ""
        response = requests.get(self.get_part_url(self.sku))
        if response.status_code == 200:
            match_object = re.search(
                r"<img class=\"img-fluid js-socialshare-media\".*?(src|data-lazy)=\"(?P<URL>\S+?)\"",  # noqa: E501
                response.text,
            )
            if match_object is not None:
                img_url = match_object.group("URL")
        return img_url

    def get_part_url(self, sku: str | None = None) -> str:
        if sku is None:
            sku = self.sku
        sku_escaped = sku[:-5].strip().replace(" ", "%20")  # trim package quantity
        return f"https://www.wuerth.de/web/media/system/search_redirector.php?SearchResultType=all&EffectiveSearchTerm=&ApiLocale=de_DE&VisibleSearchTerm={sku_escaped}"  # noqa: E501


class ZanderWebsite(SupplierWebsite):

    def fetch_part_parameters(self, sku: str):
        self.sku = sku
        parameters = None
        client = requests.Session()
        # The following request is neccessary to acquire a valid session ID!
        client.get(
            f"https://zander.online/api/v1.0/shop/user/open/login?device=&launch=&version=3.119.0&t={int(round(time.time() * 1000))}"  # noqa: E501
        )
        details_url = f"https://zander.online/api/v1.0/shop/article/{sku}/details?menge=1&misc=&t={int(round(time.time() * 1000))}"  # noqa: E501
        response = client.get(details_url)
        if response.status_code == 200:
            parameters = response.json()["result"]["artikel"]
        self.parameters = parameters

    def get_part_img_url(self) -> str:
        img_url = ""
        if self.parameters is None:
            self.fetch_part_parameters(self.sku)

        img_size = 600
        formatted_artikel_prefix = "-".join(
            str(self.parameters["artikel_prefix"]).split()
        )
        formatted_artikle_name = "-".join(str(self.parameters["artikel_name"]).split())
        sku = self.parameters["artikel_nr"]
        img_name = f"{formatted_artikel_prefix}-{formatted_artikle_name}"
        img_url = f"https://media.zander.online/v1/media/{sku}/0/{img_size}/{img_name}.jpg"  # noqa: E501
        return img_url

    def get_part_url(self, sku: str | None = None) -> str:
        if sku is None:
            sku = self.sku
        return f"https://zander.online/artikel/{sku}"


def get_supplier_website(supplier: str, sku: str) -> SupplierWebsite | None:
    """Builds the link for a certain supplier for the product id

    Args:
        supplier (str): Name of the supplier
        sku (str): SKU of the part

    Returns:
        SupplierWebsite: Object wrapper of the suppliers website
    """
    supplier_website = None
    if "WÜRTH" in supplier.upper() or "WUERTH" in supplier.upper():
        supplier_website = WuerthWebsite(sku)
    elif "ZANDER" in supplier.upper():
        supplier_website = ZanderWebsite(sku)
    elif "BÜRKLE" in supplier.upper() or "BUERKLE" in supplier.upper():
        supplier_website = BuerkleWebsite(sku)
    elif "SONEPAR" in supplier.upper():
        supplier_website = SoneparWebsite(sku)
    return supplier_website

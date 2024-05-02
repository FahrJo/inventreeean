from moneyed import Money
import requests
from urllib.parse import urlparse

from django.core.files.base import ContentFile
from datanorm import DatanormItem
from inventree_datanorm_import.supplier_websites import (
    SupplierWebsite,
    get_supplier_website,
)
from part.models import Part, PartCategory
from company.models import Company, ManufacturerPart, SupplierPart
from InvenTree.helpers import hash_barcode


class PartFactory:
    di: DatanormItem
    default_category: str

    def __init__(self, di: DatanormItem, default_category: str = "Fallback Category"):
        """This class provides methods to create part instances based on a DATANORM
        item.

        Args:
            di (DatanormItem): DATANORM item containign all information for the part(s)
            default_category (str, optional): Category to use if not category is
            specified in the datanorm item. Defaults to "Fallback Category".
        """
        self.di = di
        self.default_category = default_category

    @staticmethod
    def format_si_units(unit: str) -> str:
        target_unit = ""
        upper_unit = unit.upper()
        if upper_unit == "STCK" or upper_unit == "STK":
            target_unit = ""  # or "pcs"
        elif upper_unit == "MTR" or upper_unit == "M" or upper_unit == "LFM":
            target_unit = "m"
        elif upper_unit == "VE":
            target_unit = ""
        elif upper_unit == "KG":
            target_unit = "kg"
        return target_unit

    @staticmethod
    def create_empty_part_from_ean(ean: str, default_category) -> Part:
        """create an empty part, attached with an EAN

        Args:
            ean (str): EAN to attach to the created part

        Returns:
            Part: (almost) empty part
        """
        name = f"Unbekanntes Teil (EAN:{ean})"
        category = PartFactory.get_category_by_name(default_category)
        description = f"Bitte Teil manuell vervollständigen! EAN: {ean}"
        part = Part(
            name=name,
            category=category,
            description=description,
            keywords=ean,
            purchaseable=True,
            active=True,
        )
        # Create hash from raw barcode data
        hashed_ean = hash_barcode(ean)
        part.assign_barcode(hashed_ean, ean)
        part.save()
        return part

    @staticmethod
    def get_category_by_name(category_name: str, parent_name: str = "") -> PartCategory:
        """Searches and returns a part category, matching the given name and its
        parents name. If the category did not exist so far, it creates a new one.

        Args:
            category_name (str): Name of the category
            parent_name (str): Name of the parent category

        Returns:
            PartCategory: Existing or newly created category
        """
        if parent_name == "":
            parent = None
            category = PartCategory.objects.filter(name=category_name).first()
        else:
            parent = PartCategory.objects.filter(name=parent_name).first()
            if parent is None:
                parent = PartCategory(name=parent_name)
                parent.save()
            category = PartCategory.objects.filter(
                name=category_name, parent_id=parent.pk
            ).first()

        if category is None:
            category = PartCategory(name=category_name, parent=parent)
            category.save()
        return category

    @staticmethod
    def get_company_by_name(
        company_name: str, set_supplier=False, set_manufacturer=False
    ) -> Company:
        """Searches and returns a company, matching the given name case-insensitive.
        If the company did not exist so far, it creates a new one.

        Args:
            company_name (str): Name of the company
            set_supplier (bool): Set is_supplier property of company
            set_manufacturer (bool): Set is_manufacturer property of company

        Returns:
            Company: Existing or newly created company, marked as supplier \
                     and/or manufacturer
        """
        company = Company.objects.filter(name__contains=company_name).first()
        if company is None:
            company = Company.objects.filter(name__iexact=company_name).first()

        if company is None:
            company = Company(
                name=company_name,
                is_supplier=set_supplier,
                is_manufacturer=set_manufacturer,
            )
        else:
            company.is_supplier |= set_supplier
            company.is_manufacturer |= set_manufacturer
        company.save()
        return company

    def create_part_from_datanorm_item(self) -> Part:
        """Create a base part.

        Returns:
            Part: Newly created part
        """

        # get category
        if self.di.product_group_name == "" and self.di.main_product_group_name == "":
            category = PartFactory.get_category_by_name(self.default_category)
        elif self.di.product_group_name == "":
            category = PartFactory.get_category_by_name(self.di.main_product_group_name)
        else:
            category = PartFactory.get_category_by_name(
                self.di.product_group_name, self.di.main_product_group_name
            )

        keywords = [self.di.matchcode.strip(), self.di.ean]
        part = Part(
            name=self.di.item_name,
            category=category,
            description=self.di.description,
            keywords=",".join(filter(None, keywords)),
            units=PartFactory.format_si_units(self.di.unit_of_measure),
            purchaseable=True,
            active=True,
        )
        # Create hash from raw barcode data
        hashed_ean = hash_barcode(self.di.ean)
        part.assign_barcode(hashed_ean, self.di.ean)
        part.save()
        return part

    def create_manufacturer_part_from_datanorm_item(
        self, part: Part
    ) -> ManufacturerPart | None:
        """Creates a new manufacturer part from the DATANORM item

        Args:
            part (Part): Part, previously created from the DATANORM item

        Returns:
            ManufacturerPart | None: Newly created manufacturer part
        """
        manufacturer_part = None
        manufacturer_name = self.di.manufacturer_name
        if manufacturer_name is not None:
            manufacturer = PartFactory.get_company_by_name(
                manufacturer_name, set_manufacturer=True
            )
            manufacturer.save()
            manufacturer_part = ManufacturerPart(
                part=part, manufacturer=manufacturer, MPN=self.di.alt_article_id
            )
            manufacturer_part.save()
        return manufacturer_part

    def create_supplier_part_from_datanorm_item(self, part: Part) -> SupplierPart:
        """Creates a new supplier part from the DATANORM item

        Args:
            part (Part): Part, previously created from the DATANORM item

        Returns:
            SupplierPart: Newly created supplier part
        """
        supplier_name = (
            self.di.tag
        )  # use tag instead of header information since not every supplier uses this
        sku = self.di.article_id
        link = ""
        supplier = PartFactory.get_company_by_name(supplier_name, set_supplier=True)
        supplier_website = get_supplier_website(supplier_name, sku)
        if supplier_website is not None:
            link = supplier_website.get_part_url()
            # Try to fetch the image from different suppliers until success
            if not part.image:
                self.fetch_and_save_image_to_part(part, supplier_website)
        supplier_part = SupplierPart(
            part=part,
            supplier=supplier,
            SKU=sku,
            link=link,
            pack_quantity=self.di.minimum_packaging_quantity,
            updated=self.di.date,
        )
        price = Money(self.di.price_wholesale, self.di.currency)
        supplier_part.save()
        supplier_part.add_price_break(self.di.price_unit, price)
        supplier_part.save()
        return supplier_part

    def fetch_and_save_image_to_part(
        self, part: Part, supplier_part_website: SupplierWebsite
    ):
        """Fetches the image from the suppliers website and attaches it to the part

        Args:
            part (Part): Part, the image is attached to
            supplier_part_website (SupplierWebsite): Website wrapper of the supplier
        """
        img_url = supplier_part_website.get_part_img_url()
        if img_url:
            name = urlparse(img_url).path.split("/")[-1]
            response = requests.get(img_url)
            if response.status_code == 200:
                part.image.save(name, ContentFile(response.content), save=True)

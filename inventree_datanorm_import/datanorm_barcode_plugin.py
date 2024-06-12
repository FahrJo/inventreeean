import logging
from typing import Iterator
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinLengthValidator

from InvenTree.helpers import hash_barcode
from inventree_datanorm_import.part_factory import PartFactory
from datanorm import (
    DatanormBaseFile,
    DatanormItem,
    DatanormPriceFile,
    DatanormProductGroupFile,
    file_name_is_valid,
)
from plugin import InvenTreePlugin
from plugin.mixins import BarcodeMixin, SettingsMixin
from part.models import Part, PartAttachment
from company.models import SupplierPart

logger = logging.getLogger("inventree")


def log(msg: str, type="info"):
    """Custom logging function

    Args:
        msg (str): log message
        type (str, optional): type of message (info, debug, warn, error).\
                              Defaults to "info".
    """
    if type == "info":
        logger.info(msg)
    elif type == "debug":
        logger.debug(msg)
    elif type == "warn":
        logger.warning(msg)
    elif type == "error":
        logger.error(msg)
    print(f"{type}: {msg}")


class DatanormBarcodePlugin(BarcodeMixin, SettingsMixin, InvenTreePlugin):

    NAME = "DatanormBarcode"
    TITLE = "DATANORM Barcode Scanner"
    DESCRIPTION = "Add new scanned items from DATANORM files to inventory"
    VERSION = "0.0.3"
    AUTHOR = "FahrJo"

    SETTINGS = {
        "DATANORM_PART": {
            "name": _("Datanorm Part"),
            "description": _(
                "Virtual part, holding the datanorm files as attachments. The \
                 comments for all files of the same supplier have to be the same!"
            ),
            "model": "part.part",
        },
        "DEFAULT_CATEGORY": {
            "name": _("Default Category"),
            "description": _(
                "The new parts are assigned to this category if no other category \
                 can be found."
            ),
            "validator": [MinLengthValidator(1)],
        },
        "USE_DEFAULT_CATEGORY": {
            "name": _("Always use Default Category"),
            "description": _(
                "Assign all new parts to the default category, ignoring the \
                 categories in the DATANORM files."
            ),
            "validator": bool,
        },
        "AUTOMATIC_BARCODE_ASSIGNMENT": {
            "name": _("Re-assign barcode to existing part"),
            "description": _(
                "If a barcode is found in the Tags of an existing part, it will be assigned\
                 as additional barcode to that part to speed up the scan for the next times."
            ),
            "validator": bool,
        },
    }

    def scan(self, barcode_data) -> dict:
        """Scan a barcode against this plugin.

        Here we are looking for the barcode in several DATANORM files
        """
        # Attempt to coerce the barcode data into a dict object
        # This is the internal barcode representation that InvenTree uses
        log(f"Barcode: {barcode_data}")
        part = None

        if self.is_valid_ean_code(barcode_data):
            log("Valid EAN code")
            # Search for EAN in keywords of all parts
            part = self.search_for_first_part_with_keyword(barcode_data)
            reassign_barcode = self.get_setting("AUTOMATIC_BARCODE_ASSIGNMENT")

            # Create new part if none exists so far
            if part is None:
                part = self.create_all_parts(barcode_data)
                log(f"Part {part.pk} created")
            elif reassign_barcode == "True" and part.barcode_hash == "":
                hashed_ean = hash_barcode(barcode_data)
                part.assign_barcode(hashed_ean, barcode_data)
                log(f"Barcode reassigned to {part.pk}")

        return self.format_matched_response(part)

    @staticmethod
    def search_for_first_part_with_keyword(keyword) -> Part | None:
        """Returns first part with given keyword

        Args:
            keyword (_type_): keyword to search for

        Returns:
            Part | None: First part found
        """
        return Part.objects.filter(keywords__contains=keyword).first()

    @staticmethod
    def search_for_part_with_name(name) -> Part | None:
        """Returns part with given name if exists

        Args:
            name (_type_): name to search for

        Returns:
            Part | None: First part found
        """
        return Part.objects.filter(name=name).first()

    @staticmethod
    def is_valid_ean_code(code: str) -> bool:
        """To calculate the check digit (13th digit), the first 12 digits are
        multiplied individually by a fixed weighting factor and the sum is calculated.
        The weighting factors always alternate between '1' and '3', starting in this
        order. The last digit is taken from the total and subtracted from '10'.

        Args:
            code (str): Barcode to check

        Returns:
            bool: Result of evaluation
        """
        # everything has to be flipped to work with EAN-8 and EAN-13
        factor = "131313131313"[::-1]
        checksum = int(code[-1])
        flipped_prefix = code[:-1][::-1]
        sum_if_digits = 0

        if len(code) == 13 or len(code) == 8:
            # Iterate over the string
            for i, digit in enumerate(flipped_prefix):
                sum_if_digits += int(digit) * int(factor[i])
            last_digit = sum_if_digits % 10
            computed_checksum = (10 - last_digit) % 10
            return checksum == computed_checksum
        else:
            return False

    def create_all_parts(self, ean: str) -> Part | None:
        """Trys to create all parts, belonging to the EAN.

        Args:
            ean (str): EAN of the part

        Returns:
            Part | None: Newly created part if EAN was found in DATANORM files
        """
        # search EAN in DATANORM files
        datanorm_items = self.search_ean_in_datanorm_files(ean)

        overwrite_category = self.get_setting("DEFAULT_CATEGORY")
        use_overwrite_category = self.get_setting("USE_DEFAULT_CATEGORY")
        if use_overwrite_category == "True":
            self.overwrite_category(datanorm_items, overwrite_category)

        # If EAN was found in a datanornm file, continue
        if len(datanorm_items) > 0:
            part = self.create_all_parts_from_datanorm_items(datanorm_items)
        else:
            part = PartFactory.create_empty_part_from_ean(ean, overwrite_category)
        return part

    def search_ean_in_datanorm_files(self, ean: str) -> list[DatanormItem | None]:
        """Search in DATANORM files for the EAN

        Args:
            ean (str): EAN/GTIN to search for

        Returns:
            DatanormItem | None: DATANORM item, containing all part meta information
        """
        datanorm_items = []
        attachments = self.get_datanorm_files()
        if attachments is not None:
            for file in attachments:
                if file_name_is_valid(DatanormBaseFile, file.basename):

                    datanorm_files = self.get_other_supplier_files(file.comment)
                    datanorm_item = DatanormItem(tag=file.comment)
                    DatanormBaseFile(file.attachment.path).parse(datanorm_item, ean)
                    grp_file = DatanormProductGroupFile(datanorm_files["WRG"])
                    grp_file.encoding = "iso-8859-1"
                    grp_file.parse(datanorm_item)
                    DatanormPriceFile(datanorm_files["DATPREIS"]).parse(datanorm_item)
                    fileinfo = f"{file.basename} ({file.comment})"
                    if datanorm_item.is_valid:
                        datanorm_items.append(datanorm_item)
                        log(f"Found in {fileinfo}")
                    else:
                        log(f"Not found in {fileinfo}")
        return datanorm_items

    def get_datanorm_files(self) -> Iterator[PartAttachment] | None:
        """Iterator for all attachments of the virtual part, defined in the plugin
        settings.

        Yields:
            Iterator[PartAttachment]: Iterator over all files, attached to this \
                                      plugins part
        """
        attachments = None
        pk = self.get_setting("DATANORM_PART")
        if pk:
            virtual_datanorm_part = Part.objects.get(pk=pk)
            attachments = virtual_datanorm_part.part_attachments.iterator()
        else:
            log("No DATANORM files are provided!", "error")
        return attachments

    def get_other_supplier_files(self, datanorm_supplier: str) -> dict:
        """Searches for the connected DATANORM files for a given supplier, based on the
        attachment comments

        Args:
            datanorm_supplier (str): Comment of the DATANORM attachment file

        Returns:
            dict: Product group and pricing file attachment
        """
        files = {"WRG": "", "DATPREIS": ""}
        for file in self.get_datanorm_files():
            if file.comment == datanorm_supplier and file_name_is_valid(
                DatanormProductGroupFile, file.basename
            ):
                files["WRG"] = file.attachment.path
            elif file.comment == datanorm_supplier and file_name_is_valid(
                DatanormPriceFile, file.basename
            ):
                files["DATPREIS"] = file.attachment.path

        return files

    def create_all_parts_from_datanorm_items(
        self, datanorm_items: list[DatanormItem]
    ) -> Part:
        """Create all parts from the given datanorm items.

        Args:
            datanorm_items (list[DatanormItem]): datanorm items, sharing a property

        Returns:
            Part: base part, all other parts refer to.
        """
        # check if part with same name already exists
        part = self.search_for_part_with_name(datanorm_items[0].item_name)
        if part is None:
            # create actual part from first datanorm item
            pf = PartFactory(datanorm_items[0])
            part = pf.create_part_from_datanorm_item()
        else:
            part.keywords += f",{datanorm_items[0].ean}"
            part.save()

        m_part = None
        s_parts: list[SupplierPart] = []
        for datanorm_item in datanorm_items:
            pf_i = PartFactory(datanorm_item)
            # create only one manufacturer part!
            if m_part is None:
                # if part has a manufacturer, create manufacturer part
                m_part = pf_i.create_manufacturer_part_from_datanorm_item(part)

            # create supplier part
            s_parts.append(pf_i.create_supplier_part_from_datanorm_item(part))

        if m_part is not None:
            for s_part in s_parts:
                s_part.manufacturer_part = m_part
                s_part.save()
        return part

    @staticmethod
    def format_matched_response(part: Part) -> dict:
        """Format a response for the scanned data.

        Args:
            part (Part): Part to generate the response for

        Returns:
            dict: Response for the given part
        """
        if part is not None:
            label = part.barcode_model_type()
            response = {label: part.format_matched_response()}
        else:
            response = None
        return response

    @staticmethod
    def overwrite_category(datanorm_items: list[DatanormItem], new_category: str):
        """Overwrite the product group names in all given datanorm items

        Args:
            datanorm_items (list[DatanormItem]): datanorm items to modify
            category (str): new category name
        """
        for di in datanorm_items:
            di.product_group_name = new_category
            di.main_product_group_name = ""

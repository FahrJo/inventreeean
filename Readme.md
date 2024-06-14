# DATANORM Barcode Plugin for InvenTree

If a scanned EAN code is not found for any stored part, your DATANORM files are searched for an article with the EAN. If found, the corresponding part is created with the stored information.

## Installation

### Install from git repository

To install the plugin from this repository, install the plugin in the GUI from as VCS-URL:

```
git+https://github.com/ageffgmbh/inventree-datanorm-plugin
```

### Install from local package

To install the plugin from a local package, you must be logged on to the Inventree server and have activated the Python environment of Inventree:

```bash
source env/bin/activate
```

The plugin can then be installed from the package file, e.g:

```bash
pip install /home/inventree-datanorm-plugin-x.y.z.tar.gz
```

## Setup

After installing the plugin, a (virtual) part must be created in InvenTree, in whose attachment the DATANORM files are attached. It is important that all attachments of the same supplier have the same content in the comment of the attachment (e.g. name of the supplier). This enables the plugin to assign the individual files to an entire data record. This part must then be assigned to the plugin in the plugin settings.

## Behaviour

1. A barcode is scanned (e.g. using a smartphone app).
2. The internal barcode process of Inventree first tries to resolve the barcode. If no existing part with the barcode is found, the barcode is forwarded to the plugin.
3. The plugin first checks whether the barcode is a valid EAN-8/EAN-13 code using the checksum.
4. If the barcode is valid, the EAN/GTIN is searched for in the DATANORM files.
5. If found, the part is created with the corresponding information from the DATANORM file and the EAN is stored as an alternative barcode and as keyword.
6. If a manufacturer can be recognized (name in capital letters at the beginning of the DATANORM field "Short text 1", e.g. "HAGER circuit breaker C16"), a manufacturer part is created. If necessary, a new manufacturer is created.
7. All supplier parts are created on the basis of the DATANORM file(s).
8. The newly created part is then returned to the barcode scanner (e.g. smartphone app).

## Supported Suppliers

- Alexander Bürkle
- Sonepar
- Würth
- Zander

## Known Issues

- Adding new part can not be restricted to a certain user(-group) since the plugin does not get any information about who scanned the barcode.
- Assingment of a barcode manually is broken since the frontend (app/web) first triggers the scan function to check if the barcode to be assigned is already in use. Unfortunatelly, the plugin will immediatelly re-assign the barcode to the existing part or create a new part and attach the barcode to that part. Since the plugin does not get any information on the context of the scan action, this can not be avoided.
- Generation of supplier part urls and fetching of images has to be implemented for all suppliers individually.

## Development

Development of the plugin is best done in a VSCode devcontainer, as described [**here**](https://github.com/inventree/InvenTree/blob/master/docs/docs/develop/devcontainer.md#plugin-development). Install with `pip install -e ../inventree-plugin`.

The plugin can be tested in the Inventree development container: `invoke test -r inventree_datanorm_plugin.tests`.

> To run the tests, the plugin must first be installed in the InvenTree's venv with pip!

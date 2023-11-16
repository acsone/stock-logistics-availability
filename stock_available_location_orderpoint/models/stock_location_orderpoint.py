# Copyright 2023 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import fields, models
from odoo.osv.expression import AND

from odoo.addons.stock.models.stock_location import Location


class StockLocationOrderpoint(models.Model):

    _inherit = "stock.location.orderpoint"

    use_to_compute_available_quantities = fields.Boolean(
        help="(Experimental) Check this if you want to use this orderpoint to compute"
        "the product available quantities. This will uses optional domains to"
        "exclude some locations (e.g. Suppliers - for incoming moves)."
        "Note: If none is checked, every orderpoint will be used."
    )

    def _prepare_orderpoint_domain_location(
        self, location_ids: Location, location_field=False, **kwargs
    ) -> list:
        domain = super()._prepare_orderpoint_domain_location(
            location_ids=location_ids, location_field=location_field
        )
        if "use_to_compute_available_quantities" in kwargs and kwargs.get(
            "use_to_compute_available_quantities"
        ):
            domain = AND([domain, [("use_to_compute_available_quantities", "=", True)]])
        return domain

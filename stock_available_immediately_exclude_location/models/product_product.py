# Copyright 2023 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models
from odoo.osv import expression


class ProductProduct(models.Model):

    _inherit = "product.product"

    def _compute_available_quantities_dict(self):
        """
        change the way immediately_usable_qty is computed by deducing the quants
        in excluded locations
        """
        res, stock_dict = super(
            ProductProduct, self
        )._compute_available_quantities_dict()
        exclude_location_ids = (
            self._get_locations_excluded_from_immediately_usable_qty().ids
        )

        if exclude_location_ids:
            excluded_qty_dict = self.with_context(
                location=exclude_location_ids, compute_child=False
            )._compute_quantities_dict(
                self._context.get("lot_id"),
                self._context.get("owner_id"),
                self._context.get("package_id"),
                self._context.get("from_date"),
                self._context.get("to_date"),
            )

        for product_id in res:
            if exclude_location_ids:
                res[product_id]["immediately_usable_qty"] -= excluded_qty_dict[
                    product_id
                ]["qty_available"]
        return res, stock_dict

    def _get_locations_excluded_from_immediately_usable_qty(self):
        return self.env["stock.location"].search(
            self._get_domain_location_excluded_from_immediately_usable_qty()
        )

    def _get_domain_location_excluded_from_immediately_usable_qty(self):
        """
        Parses the context and returns a list of location_ids based on it that
        should be excluded from the immediately_usable_qty
        """
        quant_domain = self.env["product.product"]._get_domain_locations()[0]
        # The only creteria on the quants are on company_id and location_id
        # fields. The same domain can be safely reused to get the precise list
        # of locations to exclude by adding the criteria on
        # exclude_from_immediately_usable_qty and adapting the domain to work
        # on stock.location.
        # In this way we are always sure that the computation of qties to
        # exclude is always done for locations part of the expected locations
        # provided by the context/
        # replace location_id by id into the quant domain to get the
        # domain to apply to the locations
        location_domain = []
        for element in quant_domain:
            if expression.is_leaf(element):
                location_domain.append(
                    (element[0].replace("location_id.", ""), element[1], element[2])
                )
            else:
                location_domain.append(element)
        return expression.AND(
            [location_domain, [("exclude_from_immediately_usable_qty", "=", True)]]
        )

# Copyright 2023 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models
from odoo.osv import expression
from odoo.tools import ormcache_context


class ProductProduct(models.Model):

    _inherit = "product.product"

    def _compute_available_quantities_dict(self):
        """
        change the way immediately_usable_qty is computed by deducing the quants
        in excluded locations
        """
        res, stock_dict = super()._compute_available_quantities_dict()
        excluded_qty_dict = (
            self._get_qty_available_in_locations_excluded_from_immadiatly_usable_qty()
        )
        for product_id, qty in excluded_qty_dict.items():
            res[product_id]["immediately_usable_qty"] -= qty
        return res, stock_dict

    def _get_qty_available_in_locations_excluded_from_immadiatly_usable_qty(self):
        """Return a dict of qty available by product
        into excluded locations. If no location is excluded
        retrurn an empty dict
        """
        exclude_location_ids = (
            self._get_location_ids_excluded_from_immediately_usable_qty()
        )
        if not exclude_location_ids:
            return {}

        context = self.env.context
        to_date = context.get("to_date")
        to_date = fields.Datetime.to_datetime(to_date)
        dates_in_the_past = False
        if to_date and to_date < fields.Datetime.now():
            dates_in_the_past = True

        products_with_excluded_loc = self.with_context(
            location=exclude_location_ids, compute_child=False
        )

        if dates_in_the_past:
            # we call the original _compute_quantities_dict since
            # the qty_available will be computed from quants and
            # moves
            excluded_qty_dict = products_with_excluded_loc._compute_quantities_dict(
                context.get("lot_id"),
                context.get("owner_id"),
                context.get("package_id"),
                context.get("from_date"),
                to_date,
            )
            return {p: q["qty_available"] for p, q in excluded_qty_dict.items()}
        # we are not in the past, the qty available is the sum of quant's qties
        # into the exluded locations. A simple read_group will do the job.
        # By avoiding the call to _compute_quantities_dict, we avoid 2 useless
        # queries to the database to retrieve the incoming and outgoing moves
        # that are not needed here and therefore improve the performance.
        (
            domain_quant_loc,
            _domain_move_in_loc,
            _domain_move_out_loc,
        ) = products_with_excluded_loc._get_domain_locations()
        domain_quant = [("product_id", "in", self.ids)] + domain_quant_loc
        quant = self.env["stock.quant"].with_context(active_test=False)
        return {
            item["product_id"][0]: item["quantity"]
            for item in quant._read_group(
                domain_quant,
                ["product_id", "quantity", "reserved_quantity"],
                ["product_id"],
                orderby="id",
            )
        }

    @api.model
    @ormcache_context(
        "tuple(self.env.companies.ids)", keys=("tuple(location)", "tuple(warehouse)")
    )
    def _get_location_ids_excluded_from_immediately_usable_qty(self):
        """
        Return the ids of the locations that should be excluded from the
        immediately_usable_qty
        """
        return self._get_locations_excluded_from_immediately_usable_qty().ids

    @api.model
    def _get_locations_excluded_from_immediately_usable_qty(self):
        return self.env["stock.location"].search(
            self._get_domain_location_excluded_from_immediately_usable_qty()
        )

    @api.model
    def _get_domain_location_excluded_from_immediately_usable_qty(self):
        """
        Parses the context and returns a list of location_ids based on it that
        should be excluded from the immediately_usable_qty
        """
        location_domain = self.env[
            "product.product"
        ]._get_domain_location_for_locations()
        return expression.AND(
            [location_domain, [("exclude_from_immediately_usable_qty", "=", True)]]
        )

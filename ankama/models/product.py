# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.constrains('default_code')
    def _check_default_code(self):
        for rec in self:
            if rec.default_code:
                if self.env['product.product'].search_count([('default_code', 'ilike', rec.default_code), ('id', '!=', rec.id)]):
                    raise UserError(_("Another product already exists with this internal reference number."))

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def _get_internal_reference(self, prod):
        prefix = ''
        if prod.categ_id.parent_id.categ_prefix:
            prefix += prod.categ_id.parent_id.categ_prefix.upper() + '-'
        if prod.categ_id.categ_prefix:
            prefix += prod.categ_id.categ_prefix.upper() + '-'
        if not prefix:
            return

        sequence = self.env['ir.sequence'].search([('prefix', '=', prefix)])
        if not sequence:
            seq_data = {
                'name': 'Internal reference %s' % prefix,
                'implementation': 'no_gap',
                'prefix': prefix,
                'padding': 4,
                'number_increment': 1,
            }
            if prod.company_id:
                seq['company_id'] = prod.company_id
            sequence = self.env['ir.sequence'].create(seq_data)

        return sequence._next()

    @api.model
    def create(self, values):
        res = super(ProductTemplate, self).create(values)

        if res.default_code:
            return res

        internal_reference = self._get_internal_reference(res.product_variant_id)
        if internal_reference:
            res.product_variant_id.default_code = internal_reference

        return res

    def write(self, values):
        for rec in self:
            for value in values:
                if value in ['property_account_income_id', 'property_account_expense_id', 'property_account_creditor_price_difference']:
                    self.set_multi_company(value, values[value], rec)

        return super(ProductTemplate, self).write(values)

    def set_multi_company(self, name, value, rec):
        res_id = 'product.template,' + str(rec.id)
        for company in self.env['res.company'].search([('name','!=',self.env.company.name)]):
            reference_name = self.env['account.account'].browse(value).name
            reference_id = self.env['account.account'].sudo().search([('name','=',reference_name), ('company_id','=',company.id)])
            value_to_set = 'account.account,' + str(reference_id.id)

            ir_property = self.env['ir.property'].sudo().search([('name','=',name), ('company_id','=',company.id),('res_id','=',res_id)])
            if ir_property:
                ir_property.sudo().write({'value_reference': value_to_set})
            else:
                generic_ir_property = self.env['ir.property'].search([('name','=',name),('res_id','=',False)])
                if generic_ir_property:
                    generic_ir_property = generic_ir_property[0]
                else:
                    generic_ir_property = self.env['ir.property'].create({
                        'name': name,
                        'fields_id': self.env['ir.model.fields'].search([('name','=',name), ('model_id','=',self.env['ir.model'].search([('model','=','product.template')]).id)]).id,
                        'type': 'many2one',
                    })
                ir_property = self.env['ir.property'].sudo().create({
                    'name': name,
                    'fields_id': generic_ir_property.fields_id.id,
                    'type': generic_ir_property.type,
                    'res_id': res_id,
                    'value_reference': value_to_set,
                    'company_id': company.id,
                })

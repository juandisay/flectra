# -*- coding: utf-8 -*-

from flectra import api, models, fields
from flectra.tools import float_repr

import base64


class AccountEdiFormat(models.Model):
    _inherit = 'account.edi.format'

    def _is_efff(self, filename, tree):
        return self.code == 'efff_1' and tree.tag == '{urn:oasis:names:specification:ubl:schema:xsd:Invoice-2}Invoice'

    def _create_invoice_from_xml_tree(self, filename, tree):
        self.ensure_one()
        if self._is_efff(filename, tree):
            return self._import_ubl(tree, self.env['account.move'])
        return super()._create_invoice_from_xml_tree(filename, tree)

    def _update_invoice_from_xml_tree(self, filename, tree, invoice):
        self.ensure_one()
        if self._is_efff(filename, tree):
            return self._import_ubl(tree, invoice)
        return super()._update_invoice_from_xml_tree(filename, tree, invoice)

    def _is_compatible_with_journal(self, journal):
        self.ensure_one()
        res = super()._is_compatible_with_journal(journal)
        if self.code != 'efff_1':
            return res
        return journal.type == 'sale' and journal.country_code == 'BE'

    def _post_invoice_edi(self, invoices, test_mode=False):
        self.ensure_one()
        if self.code != 'efff_1':
            return super()._post_invoice_edi(invoices, test_mode=test_mode)
        res = {}
        for invoice in invoices:
            attachment = self._export_efff(invoice)
            res[invoice] = {'attachment': attachment}
        return res

    def _export_efff(self, invoice):
        self.ensure_one()
        # Create file content.
        xml_content = b"<?xml version='1.0' encoding='UTF-8'?>"
        xml_content += self.env.ref('account_edi_ubl.export_ubl_invoice')._render(invoice._get_ubl_values())
        vat = invoice.company_id.partner_id.commercial_partner_id.vat
        xml_name = 'efff-%s%s%s.xml' % (vat or '', '-' if vat else '', invoice.name.replace('/', '_'))  # official naming convention
        return self.env['ir.attachment'].create({
            'name': xml_name,
            'datas': base64.encodebytes(xml_content),
            'res_model': 'account.move',
            'res_id': invoice._origin.id,
            'mimetype': 'application/xml'
        })

    def _is_embedding_to_invoice_pdf_needed(self):
        self.ensure_one()
        if self.code != 'efff_1':
            return super()._is_embedding_to_invoice_pdf_needed()
        return False  # ubl must not be embedded to PDF.

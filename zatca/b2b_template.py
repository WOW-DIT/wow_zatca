from .hasher import canonicalize_xml, hash
import base64
import lxml
import frappe
import os

def credit_reference(is_credit_debit=False, prev_invoice=None):
    if is_credit_debit == False:
        return ""
    
    invoice_number = prev_invoice.name
    issue_date = prev_invoice.posting_date
    return f"""
    <cac:BillingReference>
        <cac:InvoiceDocumentReference>
            <cbc:ID>Invoice Number: {invoice_number}; Invoice Issue Date: {issue_date}</cbc:ID>
        </cac:InvoiceDocumentReference>
    </cac:BillingReference>"""


def get_invoice_reason(is_credit_debit=False):
    if is_credit_debit == False:
        return ""
    return f"""<cbc:InstructionNote>Return</cbc:InstructionNote>"""


def standard_invoice(
        invoice,
        company,
        address,
        customer,
        customer_address,
        payment_method,
        pih,        
    ):
    uuid = invoice.uuid
    counter = invoice.invoice_counter

    if invoice.is_return or invoice.is_debit_note:
        is_credit_debit = True
        prev_invoice = frappe.get_doc("Sales Invoice", invoice.return_against)
        
        if invoice.is_return:
            invoice_type = "381"
        elif invoice.is_debit_note:
            invoice_type = "383"
    else:
        is_credit_debit = False
        prev_invoice = None
        invoice_type = "388"

    invoice_str = f"""<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2" xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2" xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" xmlns:ext="urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2">
    <cbc:ProfileID>reporting:1.0</cbc:ProfileID>
    <cbc:ID>INV-001</cbc:ID>
    <cbc:UUID>{uuid}</cbc:UUID>
    <cbc:IssueDate>2025-05-01</cbc:IssueDate>
    <cbc:IssueTime>12:21:28</cbc:IssueTime>
    <cbc:InvoiceTypeCode name="0100000">{invoice_type}</cbc:InvoiceTypeCode>
    <cbc:DocumentCurrencyCode>SAR</cbc:DocumentCurrencyCode>
    <cbc:TaxCurrencyCode>SAR</cbc:TaxCurrencyCode>{credit_reference(is_credit_debit, prev_invoice)}
    <cac:AdditionalDocumentReference>
        <cbc:ID>ICV</cbc:ID>
        <cbc:UUID>{counter}</cbc:UUID>
    </cac:AdditionalDocumentReference>
    <cac:AdditionalDocumentReference>
        <cbc:ID>PIH</cbc:ID>
        <cac:Attachment>
            <cbc:EmbeddedDocumentBinaryObject mimeCode="text/plain">{pih}</cbc:EmbeddedDocumentBinaryObject>
        </cac:Attachment>
    </cac:AdditionalDocumentReference>
    <cac:AccountingSupplierParty>
        <cac:Party>
            <cac:PartyIdentification>
                <cbc:ID schemeID="CRN">{address.crn}</cbc:ID>
            </cac:PartyIdentification>
            <cac:PostalAddress>
                <cbc:StreetName>{address.address_line1} | {address.address_line2}</cbc:StreetName>
                <cbc:BuildingNumber>2322</cbc:BuildingNumber>
                <cbc:CitySubdivisionName>{address.city_subdivision}</cbc:CitySubdivisionName>
                <cbc:CityName>{address.city}</cbc:CityName>
                <cbc:PostalZone>{address.pincode}</cbc:PostalZone>
                <cac:Country>
                    <cbc:IdentificationCode>SA</cbc:IdentificationCode>
                </cac:Country>
            </cac:PostalAddress>
            <cac:PartyTaxScheme>
                <cbc:CompanyID>{address.vat_id}</cbc:CompanyID>
                <cac:TaxScheme>
                    <cbc:ID>VAT</cbc:ID>
                </cac:TaxScheme>
            </cac:PartyTaxScheme>
            <cac:PartyLegalEntity>
                <cbc:RegistrationName>{company.company_name_in_arabic}</cbc:RegistrationName>
            </cac:PartyLegalEntity>
        </cac:Party>
    </cac:AccountingSupplierParty>
    <cac:AccountingCustomerParty>
        <cac:Party>
            <cac:PostalAddress>
                <cbc:StreetName>{customer_address.address_line1} | {customer_address.address_line2}</cbc:StreetName>
                <cbc:BuildingNumber>2322</cbc:BuildingNumber>
                <cbc:CitySubdivisionName>{customer_address.city_subdivision}</cbc:CitySubdivisionName>
                <cbc:CityName>{customer_address.city}</cbc:CityName>
                <cbc:PostalZone>{customer_address.pincode}</cbc:PostalZone>
                <cac:Country>
                    <cbc:IdentificationCode>SA</cbc:IdentificationCode>
                </cac:Country>
            </cac:PostalAddress>
            <cac:PartyTaxScheme>
                <cbc:CompanyID>{customer_address.vat_id}</cbc:CompanyID>
                <cac:TaxScheme>
                    <cbc:ID>VAT</cbc:ID>
                </cac:TaxScheme>
            </cac:PartyTaxScheme>
            <cac:PartyLegalEntity>
                <cbc:RegistrationName>{customer.customer_name_in_arabic} | {customer.customer_name}</cbc:RegistrationName>
            </cac:PartyLegalEntity>
        </cac:Party>
    </cac:AccountingCustomerParty>
    <cac:Delivery>
        <cbc:ActualDeliveryDate>{invoice.supply_date}</cbc:ActualDeliveryDate>
    </cac:Delivery>
    <cac:PaymentMeans>
        <cbc:PaymentMeansCode>{payment_method}</cbc:PaymentMeansCode>{get_invoice_reason(is_credit_debit)}
    </cac:PaymentMeans>
    <cac:AllowanceCharge>
        <cbc:ChargeIndicator>false</cbc:ChargeIndicator>
        <cbc:AllowanceChargeReason>discount</cbc:AllowanceChargeReason>
        <cbc:Amount currencyID="SAR">0.00</cbc:Amount>
        <cac:TaxCategory>
            <cbc:ID>S</cbc:ID>
            <cbc:Percent>15</cbc:Percent>
            <cac:TaxScheme>
                <cbc:ID>VAT</cbc:ID>
            </cac:TaxScheme>
        </cac:TaxCategory>
    </cac:AllowanceCharge>
    <cac:TaxTotal>
        <cbc:TaxAmount currencyID="SAR">{round((invoice.grand_total - invoice.total), 2)}</cbc:TaxAmount>
    </cac:TaxTotal>
    <cac:TaxTotal>
        <cbc:TaxAmount currencyID="SAR">{round((invoice.grand_total - invoice.total), 2)}</cbc:TaxAmount>
        <cac:TaxSubtotal>
            <cbc:TaxableAmount currencyID="SAR">{round(invoice.total, 2)}</cbc:TaxableAmount>
            <cbc:TaxAmount currencyID="SAR">{round((invoice.grand_total - invoice.total), 2)}</cbc:TaxAmount>
             <cac:TaxCategory>
                 <cbc:ID>S</cbc:ID>
                 <cbc:Percent>15.00</cbc:Percent>
                <cac:TaxScheme>
                   <cbc:ID>VAT</cbc:ID>
                </cac:TaxScheme>
             </cac:TaxCategory>
        </cac:TaxSubtotal>
    </cac:TaxTotal>
    <cac:LegalMonetaryTotal>
        <cbc:LineExtensionAmount currencyID="SAR">{round(invoice.total, 2)}</cbc:LineExtensionAmount>
        <cbc:TaxExclusiveAmount currencyID="SAR">{round(invoice.total, 2)}</cbc:TaxExclusiveAmount>
        <cbc:TaxInclusiveAmount currencyID="SAR">{round(invoice.grand_total, 2)}</cbc:TaxInclusiveAmount>
        <cbc:AllowanceTotalAmount currencyID="SAR">0.00</cbc:AllowanceTotalAmount>
        <cbc:PrepaidAmount currencyID="SAR">0.00</cbc:PrepaidAmount>
        <cbc:PayableAmount currencyID="SAR">{round(invoice.grand_total, 2)}</cbc:PayableAmount>
    </cac:LegalMonetaryTotal>{get_lines(invoice.items)}
</Invoice>"""
    
    can_xml = canonicalize_xml(invoice_str)
    invoice_hash = hash(can_xml)
    encoded_invoice = base64.b64encode(invoice_str.encode()).decode()

    return {"invoice_hash": invoice_hash, "invoice": encoded_invoice}


def get_lines(items):
    lines = []
    for id, item in enumerate(items):
        amount_with_vat = round(item.amount + (item.amount * 0.15), 2)
        vat_amount = round((item.amount * 0.15), 2)

        line = f"""<cac:InvoiceLine>
        <cbc:ID>{id+1}</cbc:ID>
        <cbc:InvoicedQuantity unitCode="PCE">{item.qty}</cbc:InvoicedQuantity>
        <cbc:LineExtensionAmount currencyID="SAR">{round(item.amount, 2)}</cbc:LineExtensionAmount>
        <cac:TaxTotal>
             <cbc:TaxAmount currencyID="SAR">{vat_amount}</cbc:TaxAmount>
             <cbc:RoundingAmount currencyID="SAR">{amount_with_vat}</cbc:RoundingAmount>
        </cac:TaxTotal>
        <cac:Item>
            <cbc:Name>{item.item_name}</cbc:Name>
            <cac:ClassifiedTaxCategory>
                <cbc:ID>S</cbc:ID>
                <cbc:Percent>15.00</cbc:Percent>
                <cac:TaxScheme>
                    <cbc:ID>VAT</cbc:ID>
                </cac:TaxScheme>
            </cac:ClassifiedTaxCategory>
        </cac:Item>
        <cac:Price>
            <cbc:PriceAmount currencyID="SAR">{round(item.rate, 2)}</cbc:PriceAmount>
            <cac:AllowanceCharge>
               <cbc:ChargeIndicator>true</cbc:ChargeIndicator>
               <cbc:AllowanceChargeReason>discount</cbc:AllowanceChargeReason>
               <cbc:Amount currencyID="SAR">0.00</cbc:Amount>
            </cac:AllowanceCharge>
        </cac:Price>
    </cac:InvoiceLine>"""
        lines.append(line)

    return "\n    ".join(lines)
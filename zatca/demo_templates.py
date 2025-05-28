import base64
import frappe
from .hasher import canonicalize_xml, hash
from datetime import datetime

def get_demo_templates(docname, b64_csid, private_key, vat_id, crn, uuid, invoice_type):
    pih = "NWZlY2ViNjZmZmM4NmYzOGQ5NTI3ODZjNmQ2OTZjNzljMmRiYzIzOWRkNGU5MWI0NjcyOWQ3M2EyN2ZiNTdlOQ=="
    counter = 1

    if invoice_type == "B2B":
        return [
            {"type": "Standard Invoice", "data": standard_invoice(uuid, pih, counter, vat_id, crn, "388")},
            {"type": "Standard Credit", "data": standard_invoice(uuid, pih, counter, vat_id, crn, "381", True)},
            {"type": "Standard Debit", "data": standard_invoice(uuid, pih, counter, vat_id, crn, "383", True)},
        ]
    elif invoice_type == "B2C":
        return [
            {"type": "Simplified Invoice", "data": signInvoice(docname, uuid, "388")},
            {"type": "Simplified Credit", "data": signInvoice(docname, uuid, "381", True)},
            {"type": "Simplified Debit", "data": signInvoice(docname, uuid, "383", True)},
        ]
    else:
        return [
            {"type": "Standard Invoice", "data": standard_invoice(uuid, pih, counter, vat_id, crn, "388")},
            {"type": "Standard Credit", "data": standard_invoice(uuid, pih, counter, vat_id, crn, "381", True)},
            {"type": "Standard Debit", "data": standard_invoice(uuid, pih, counter, vat_id, crn, "383", True)},
            {"type": "Simplified Invoice", "data": signInvoice(docname, uuid, "388")},
            {"type": "Simplified Credit", "data": signInvoice(docname, uuid, "381", True)},
            {"type": "Simplified Debit", "data": signInvoice(docname, uuid, "383", True)},
        ]

def credit_reference(is_credit_debit=False):
    if is_credit_debit == False:
        return ""
    return """
    <cac:BillingReference>
        <cac:InvoiceDocumentReference>
            <cbc:ID>Invoice Number: {INV-002}; Invoice Issue Date: 2025-04-01</cbc:ID>
        </cac:InvoiceDocumentReference>
    </cac:BillingReference>"""


def get_invoice_reason(is_credit_debit=False):
    if is_credit_debit == False:
        return ""
    return f"""<cbc:InstructionNote>Return</cbc:InstructionNote>"""


def standard_invoice(uuid, pih, counter, vat_id, crn, type, is_credit_debit=False):
    invoice = f"""<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2" xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2" xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" xmlns:ext="urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2">
    <cbc:ProfileID>reporting:1.0</cbc:ProfileID>
    <cbc:ID>INV-001</cbc:ID>
    <cbc:UUID>{uuid}</cbc:UUID>
    <cbc:IssueDate>2025-05-01</cbc:IssueDate>
    <cbc:IssueTime>12:21:28</cbc:IssueTime>
    <cbc:InvoiceTypeCode name="0100000">{type}</cbc:InvoiceTypeCode>
    <cbc:DocumentCurrencyCode>SAR</cbc:DocumentCurrencyCode>
    <cbc:TaxCurrencyCode>SAR</cbc:TaxCurrencyCode>{credit_reference(is_credit_debit)}
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
                <cbc:ID schemeID="CRN">{crn}</cbc:ID>
            </cac:PartyIdentification>
            <cac:PostalAddress>
                <cbc:StreetName>الامير سلطان | Prince Sultan</cbc:StreetName>
                <cbc:BuildingNumber>2322</cbc:BuildingNumber>
                <cbc:CitySubdivisionName>المربع | Al-Murabba</cbc:CitySubdivisionName>
                <cbc:CityName>الرياض | Riyadh</cbc:CityName>
                <cbc:PostalZone>23333</cbc:PostalZone>
                <cac:Country>
                    <cbc:IdentificationCode>SA</cbc:IdentificationCode>
                </cac:Country>
            </cac:PostalAddress>
            <cac:PartyTaxScheme>
                <cbc:CompanyID>{vat_id}</cbc:CompanyID>
                <cac:TaxScheme>
                    <cbc:ID>VAT</cbc:ID>
                </cac:TaxScheme>
            </cac:PartyTaxScheme>
            <cac:PartyLegalEntity>
                <cbc:RegistrationName>شركة توريد التكنولوجيا بأقصى سرعة المحدودة | Maximum Speed Tech Supply LTD</cbc:RegistrationName>
            </cac:PartyLegalEntity>
        </cac:Party>
    </cac:AccountingSupplierParty>
    <cac:AccountingCustomerParty>
        <cac:Party>
            <cac:PostalAddress>
                <cbc:StreetName>صلاح الدين | Salah Al-Din</cbc:StreetName>
                <cbc:BuildingNumber>1111</cbc:BuildingNumber>
                <cbc:CitySubdivisionName>المروج | Al-Murooj</cbc:CitySubdivisionName>
                <cbc:CityName>الرياض | Riyadh</cbc:CityName>
                <cbc:PostalZone>12222</cbc:PostalZone>
                <cac:Country>
                    <cbc:IdentificationCode>SA</cbc:IdentificationCode>
                </cac:Country>
            </cac:PostalAddress>
            <cac:PartyTaxScheme>
                <cbc:CompanyID>399999999800003</cbc:CompanyID>
                <cac:TaxScheme>
                    <cbc:ID>VAT</cbc:ID>
                </cac:TaxScheme>
            </cac:PartyTaxScheme>
            <cac:PartyLegalEntity>
                <cbc:RegistrationName>شركة نماذج فاتورة المحدودة | Fatoora Samples LTD</cbc:RegistrationName>
            </cac:PartyLegalEntity>
        </cac:Party>
    </cac:AccountingCustomerParty>
    <cac:Delivery>
        <cbc:ActualDeliveryDate>2025-05-01</cbc:ActualDeliveryDate>
    </cac:Delivery>
    <cac:PaymentMeans>
        <cbc:PaymentMeansCode>10</cbc:PaymentMeansCode>{get_invoice_reason(is_credit_debit)}
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
        <cbc:TaxAmount currencyID="SAR">0.6</cbc:TaxAmount>
    </cac:TaxTotal>
    <cac:TaxTotal>
        <cbc:TaxAmount currencyID="SAR">0.6</cbc:TaxAmount>
        <cac:TaxSubtotal>
            <cbc:TaxableAmount currencyID="SAR">4.00</cbc:TaxableAmount>
            <cbc:TaxAmount currencyID="SAR">0.60</cbc:TaxAmount>
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
        <cbc:LineExtensionAmount currencyID="SAR">4.00</cbc:LineExtensionAmount>
        <cbc:TaxExclusiveAmount currencyID="SAR">4.00</cbc:TaxExclusiveAmount>
        <cbc:TaxInclusiveAmount currencyID="SAR">4.60</cbc:TaxInclusiveAmount>
        <cbc:AllowanceTotalAmount currencyID="SAR">0.00</cbc:AllowanceTotalAmount>
        <cbc:PrepaidAmount currencyID="SAR">0.00</cbc:PrepaidAmount>
        <cbc:PayableAmount currencyID="SAR">4.60</cbc:PayableAmount>
    </cac:LegalMonetaryTotal>
    <cac:InvoiceLine>
        <cbc:ID>1</cbc:ID>
        <cbc:InvoicedQuantity unitCode="PCE">2.000000</cbc:InvoicedQuantity>
        <cbc:LineExtensionAmount currencyID="SAR">4.00</cbc:LineExtensionAmount>
        <cac:TaxTotal>
             <cbc:TaxAmount currencyID="SAR">0.60</cbc:TaxAmount>
             <cbc:RoundingAmount currencyID="SAR">4.60</cbc:RoundingAmount>
        </cac:TaxTotal>
        <cac:Item>
            <cbc:Name>قلم رصاص</cbc:Name>
            <cac:ClassifiedTaxCategory>
                <cbc:ID>S</cbc:ID>
                <cbc:Percent>15.00</cbc:Percent>
                <cac:TaxScheme>
                    <cbc:ID>VAT</cbc:ID>
                </cac:TaxScheme>
            </cac:ClassifiedTaxCategory>
        </cac:Item>
        <cac:Price>
            <cbc:PriceAmount currencyID="SAR">2.00</cbc:PriceAmount>
            <cac:AllowanceCharge>
               <cbc:ChargeIndicator>true</cbc:ChargeIndicator>
               <cbc:AllowanceChargeReason>discount</cbc:AllowanceChargeReason>
               <cbc:Amount currencyID="SAR">0.00</cbc:Amount>
            </cac:AllowanceCharge>
        </cac:Price>
    </cac:InvoiceLine>
</Invoice>"""
    
    can_xml = canonicalize_xml(invoice)
    invoice_hash = hash(can_xml)
    encoded_invoice = base64.b64encode(invoice.encode()).decode()

    return {"invoice_hash": invoice_hash, "invoice": encoded_invoice}


@frappe.whitelist(allow_guest=True)
def signInvoice(
    docname,
    uuid_value=None,
    type="388",
    is_credit_debit=False,
):
    import requests

    if not uuid_value:
        import uuid
        uuid_value = str(uuid.uuid4())

    egsunit = frappe.get_doc("EGSUnit", docname)
    company = frappe.get_doc("Company", egsunit.company)
    private_key = egsunit.private_key
    certificate = base64.b64decode(egsunit.certificate).decode()
    crn = egsunit.crn_number
    vat_id = egsunit.vat_number

    url = "http://localhost:3000/sign-invoice"

    items = [
        {"id": "1", "name": "Pizza", "quantity": 1, "tax_exclusive_price": 115.0, "VAT_percent": 0.15}
    ]
    
    previous_invoice_hash = "NWZlY2ViNjZmZmM4NmYzOGQ5NTI3ODZjNmQ2OTZjNzljMmRiYzIzOWRkNGU5MWI0NjcyOWQ3M2EyN2ZiNTdlOQ=="

    today = datetime.now()
    issue_date = datetime.strftime(today, "%Y-%m-%d")
    issue_time = "09:00:00"

    payload = {
        "invoice": {
            "egs_info": {
                "uuid": uuid_value,
                "custom_id": egsunit.custom_id,
                "model": egsunit.model,
                "CRN_number": crn,
                "VAT_name": company.company_name_in_arabic,
                "VAT_number": vat_id,
                "location": {
                    "city": "Jeddah",
                    "city_subdivision": "Makkah",
                    "street": "An naseem",
                    "plot_identification": "12345",
                    "building": "3211",
                    "postal_zone": "24151"
                },
                "branch_name": "Jeddah",
                "branch_industry": "Digital Marketing"
            },
            "invoice_counter_number": 1,
            "invoice_serial_number": "INV-001",
            "issue_date": issue_date,
            "issue_time": issue_time,
            "previous_invoice_hash": previous_invoice_hash,
            "line_items": items,
            "b2b": False,
            "customer_address": {
                "city": "Jeddah",
                "city_subdivision": "Makkah",
                "street": "Umm Almumineen Habibah",
                "plot_identification": "6775",
                "building": "3673",
                "postal_zone": "12312",
                "CRN_number": "",
                "VAT_name": "",
                "VAT_number": ""
            },
        },
        "certificate": f"-----BEGIN CERTIFICATE-----\n{certificate}\n-----END CERTIFICATE-----",
        "private_key": private_key,
    }

    if is_credit_debit:
        payload["invoice"]["cancelation"] = {
            "canceled_invoice_number": "INV-002",
            "payment_method": "42",
            "cancelation_type": type,
            "reason": "Return"
        }

    response = requests.request("POST", url, json=payload).json()

    if response['message'] == "success":
        encoded_invoice = response['data']['invoice']
        invoice_hash = response['data']['invoice_hash']
        qr = response['data']['qr']
        
        return {"invoice_hash": invoice_hash, "invoice": encoded_invoice, "qr": qr}


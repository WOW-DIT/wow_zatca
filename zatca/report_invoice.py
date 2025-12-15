import requests
from requests.auth import HTTPBasicAuth
import frappe
import base64
from lxml import etree
from io import StringIO, BytesIO
from pyqrcode import create as qr_create
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
import os

def base_url(env):
    if env == "Production":
        url = "https://gw-fatoora.zatca.gov.sa/e-invoicing/core/"
    else:
        url = "https://gw-fatoora.zatca.gov.sa/e-invoicing/simulation/"

    return url

def get_region(company):
    if not company:
        company = frappe.local.flags.company

    if company:
        return frappe.get_cached_value("Company", company, "country")

    return frappe.flags.country or frappe.get_system_settings("country")



def clear_invoice(invoice, csid, secret, version, env, accepted_types):
    if accepted_types == "B2C":
        clearance_status = "0"
    else:
        clearance_status = "1"

    url = f"{base_url(env)}invoices/clearance/single"
    headers = {
        "Accept-Language": "en",
        "Clearance-Status": clearance_status,
        "Accept-Version": version,
    }
    body = {
        "invoiceHash": invoice.invoice_hash,
        "uuid": invoice.uuid,
        "invoice": invoice.xml_invoice,
    }
    auth = HTTPBasicAuth(csid, secret)

    response = requests.post(url, json=body, headers=headers, auth=auth)
    status_code = response.status_code    
    
    if status_code == 200:
        data = response.json()
        new_invoice = data["clearedInvoice"]

        invoice.xml_invoice = new_invoice
        invoice.invoice_qrcode = extract_qrcode(invoice, invoice.xml_invoice)

        frappe.msgprint("Invoice is cleared successfully.")

    elif status_code == 303:
        report_invoice(invoice, csid, secret, version, env)

    elif status_code == 202:
        ## Save warning message
        data = response.json()
        new_invoice = data["clearedInvoice"]

        invoice.xml_invoice = new_invoice
        invoice.qrcode, invoice.invoice_hash = extract_qrcode(invoice, invoice.xml_invoice)

        invoice.warning_message = str(response.json()["validationResults"]["warningMessages"])
        frappe.msgprint("WARNING: Invoice submitted with warnings. Check them in (ZATCA) tab -> Warning Message")

    elif status_code == 400:
        ## Save warning message
        invoice.error_message = str(response.json()["validationResults"]["warningMessages"])
        frappe.throw(f"ERROR: Invoice clearance failed: {response.text}")


def report_invoice(invoice, csid, secret, version, env):
    url = f"{base_url(env)}invoices/reporting/single"
    headers = {
        "Accept-Language": "en",
        "Clearance-Status": "0",
        "Accept-Version": version,
    }
    body = {
        "invoiceHash": invoice.invoice_hash,
        "uuid": invoice.uuid,
        "invoice": invoice.xml_invoice,
    }
    auth = HTTPBasicAuth(csid, secret)

    response = requests.post(url, json=body, headers=headers, auth=auth)
    status_code = response.status_code

    if status_code == 200:
        frappe.msgprint("Invoice is reported successfully")

    elif status_code == 202:
        ## Save warning message
        invoice.warning_message = str(response.json()["validationResults"]["warningMessages"])
        frappe.msgprint(f"WARNING: Invoice submitted with warnings. Check them in (ZATCA) tab -> Warning Message")

    elif status_code == 400:
        ## Save warning message
        invoice.error_message = str(response.json()["validationResults"])
        frappe.throw(f"ERROR: Invoice reporting failed: {response.text}")


def check_compliance(
    invoice,
    csid,
    secret,
    version,
    env,
):
    try:
        url = f'{base_url(env)}compliance/invoices'
        payload = {
            "invoiceHash": invoice.invoice_hash,
            "uuid": invoice.uuid,
            "invoice": invoice.xml_invoice,
        }
        headers = {
            "Accept-Version": version,
            "Accept-Language": "en",
        }
        auth = HTTPBasicAuth(csid, secret)
        response = requests.post(url, json=payload, headers=headers, auth=auth)

        if response.status_code == 200:
            return {"success": True, "data": response.json()}
        return {"success": False, "data": response.json()}

    except Exception as e:
        return {"success": False, "data": str(e)}
    

def extract_qrcode(invoice, encoded_xml: str) -> str:
    xml = base64.b64decode(encoded_xml.encode()).decode()
    xml_bytes = xml.encode("utf-8")
    xml_file = BytesIO(xml_bytes)
    root = etree.parse(xml_file)

    namespaces = {
        "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
        "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
        'ds': 'http://www.w3.org/2000/09/xmldsig#',
    }

    qr_code = root.xpath(
        "//cac:AdditionalDocumentReference[cbc:ID='QR']/cac:Attachment/cbc:EmbeddedDocumentBinaryObject/text()",
        namespaces=namespaces,
    )

    # invoice_hash = root.xpath(
    #     "//ds:Reference[@Id='invoiceSignedData']/ds:DigestValue/text()",
    #     namespaces=namespaces,
    # )
    qr_code_str = qr_code[0].strip()

    return qr_code_str#, invoice_hash[0]


def save_qrcode_file(doc, encoded_qrcode):
    region = get_region(doc.company)
    if region not in ["Saudi Arabia"]:
        return

    qr_image = BytesIO()
    url = qr_create(encoded_qrcode, error="L")
    url.png(qr_image, scale=5, quiet_zone=1)

    name = frappe.generate_hash(doc.name, 5)

    # making file
    filename = f"QRCode-{name}.png".replace(os.path.sep, "__")
    _file = frappe.get_doc(
        {
            "doctype": "File",
            "file_name": filename,
            "is_private": 0,
            "content": qr_image.getvalue(),
            "attached_to_doctype": doc.doctype,
            "attached_to_name": doc.name,
            "attached_to_field": "ksa_einv_qr",
        }
    )

    _file.save(ignore_permissions=True)

    # assigning to document
    doc.db_set("ksa_einv_qr", _file.file_url)
    doc.notify_update()

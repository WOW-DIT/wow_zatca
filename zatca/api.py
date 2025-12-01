import frappe
import requests
import base64
from .report_invoice import report_invoice, clear_invoice, save_qrcode_file
from .b2b_template import standard_invoice
import uuid


def base_url(env):
    if env == "Production":
        url = "https://gw-fatoora.zatca.gov.sa/e-invoicing/core/"
    else:
        url = "https://gw-fatoora.zatca.gov.sa/e-invoicing/simulation/"

    return url


def get_payment_method(payment_method):
    payment_methods = {
        "Cash": "10",
        "Bank Card": "48",
        "Credit Card": "54",
        "Debit Card": "55",
        "Bank Transfer": "42"
    }

    return payment_methods[payment_method]


@frappe.whitelist(allow_guest=True)
def sign_invoice(doc, method):
    # doc = frappe.get_doc("Sales Invoice", invoice_name)
    company = frappe.get_doc('Company', doc.company)
    uuid_value = str(uuid.uuid4())

    invoice_items = doc.items
    if str(company.zatca_v2) == "0":
        return

    device_id = frappe.defaults.get_user_default('egsunit', user=frappe.session.user)

    if device_id == None or device_id == '':
        frappe.throw("Default EGSUnit is missing")

    egsunit = frappe.get_doc("EGSUnit", device_id)
    address = frappe.get_doc("Address", egsunit.address)
    customer = frappe.get_doc('Customer', doc.customer)

    certificate = f"-----BEGIN CERTIFICATE-----\n{base64.b64decode(egsunit.certificate).decode()}\n-----END CERTIFICATE-----"
    csid = egsunit.certificate
    secret = egsunit.api_secret
    version = egsunit.version
    env = egsunit.env

    payment_method = get_payment_method(doc.payment_method)

    customerAddress = {}
    b2b = False
    items = []

    if customer.customer_type == "Company" and doc.invoice_type == "B2B":
        b2b = True
        customerAddresses = frappe.get_list('Address', fields=['name', 'address_title', 'address_line1', 'address_line2', 'state','city', 'country', 'pincode', 'additional_no', 'building_no', 'vat_id' , 'crn'])
        for add in customerAddresses:
            add_doc = frappe.get_doc('Address', add.name)
            for link in add_doc.links:
                if link.link_name == customer.name:
                    customerAddress = add
                    break

    item_id = 1
    for item in invoice_items:
        items.append({"id":str(item_id) , "name":item.item_name , "quantity":item.qty , "tax_exclusive_price" :(item.amount) , "VAT_percent":0.15})
        item_id += 1

    if b2b == True and len(customerAddress) == 0:
        frappe.throw("Customer Address Information is missing")

    previous_invoices = frappe.db.sql("""
        SELECT i.name, i.invoice_counter AS counter, i.invoice_hash
        FROM `tabSales Invoice` AS i
        WHERE i.company = %s AND i.docstatus = %s AND i.egsunit = %s
        ORDER BY i.invoice_counter DESC
        LIMIT 1;
    """, (company.name, 1, egsunit.name), as_dict=True)

    if len(previous_invoices) > 0:
        previous_invoice = previous_invoices[0]
        invoice_counter = int(previous_invoice.counter) + 1
        previous_invoice_hash = previous_invoice.invoice_hash
    else:
        invoice_counter = 1
        previous_invoice_hash = "NWZlY2ViNjZmZmM4NmYzOGQ5NTI3ODZjNmQ2OTZjNzljMmRiYzIzOWRkNGU5MWI0NjcyOWQ3M2EyN2ZiNTdlOQ=="

    doc.invoice_counter = invoice_counter
    doc.egsunit = device_id
    doc.uuid = uuid_value

    if b2b:
        invoice_data = standard_invoice(
            invoice=doc,
            company=company,
            address=address,
            customer=customer,
            customer_address=customerAddress,
            payment_method=payment_method,
            pih=previous_invoice_hash,
        )

        doc.xml_invoice = invoice_data["invoice"]
        doc.invoice_hash = invoice_data['invoice_hash']

        # frappe.throw(doc.xml_invoice)
        clear_invoice(
            invoice=doc,
            csid=csid,
            secret=secret,
            version=version,
            env=env,
            accepted_types=egsunit.type,
        )

        try:
            save_qrcode_file(doc, doc.invoice_qrcode)
        except:
            frappe.msgprint("Invoice reported but, failed to save QRCode image locally.")

        return

    
    url = "http://localhost:3000/sign-invoice"
    payload = {
        "invoice": {
            "egs_info": {
                "uuid": uuid_value,
                "custom_id": egsunit.custom_id,
                "model": egsunit.model,
                "CRN_number": egsunit.crn_number,
                "VAT_name": egsunit.vat_name,
                "VAT_number": egsunit.vat_number,
                "location": {
                    "city": address.city,
                    "city_subdivision": address.state,
                    "street": address.address_line2,
                    "plot_identification": address.additional_no,
                    "building": address.building_no,
                    "postal_zone": address.pincode
                },
                "branch_name": egsunit.branch_name,
                "branch_industry": egsunit.branch_industry
            },
            "invoice_counter_number": invoice_counter,
            "invoice_serial_number": doc.name,
            "issue_date": str(doc.posting_date),
            "issue_time": str(doc.posting_time).split(".")[0],
            "previous_invoice_hash": previous_invoice_hash,
            "line_items": items,
            "b2b": b2b,
            "customer_address": {
                "city": customerAddress.city if b2b else "",
                "city_subdivision": customerAddress.state if b2b else "",
                "street": customerAddress.address_line2 if b2b else "",
                "plot_identification": customerAddress.additional_no if b2b else "",
                "building": customerAddress.building_no if b2b else "",
                "postal_zone": customerAddress.pincode if b2b else "",
                "CRN_number": customerAddress.crn if b2b else "",
                "VAT_name": customer.name if b2b else "",
                "VAT_number": customerAddress.vat_id if b2b else ""
            }
        },
        "certificate": certificate,
        "private_key": egsunit.private_key
    }

    if doc.is_return == 1:
        old_invoice = frappe.get_doc("Sales Invoice", doc.return_against)
        payload["invoice"]["cancelation"] = {
            "canceled_invoice_number": old_invoice.name,
            "payment_method": payment_method,
            "cancelation_type": "381",
            "reason": "Return"
        }

    if doc.is_debit_note == 1:
        old_invoice = frappe.get_doc("Sales Invoice", doc.amended_from)
        payload["invoice"]["cancelation"] = {
            "canceled_invoice_number": old_invoice.name,
            "payment_method": payment_method,
            "cancelation_type": "383",
            "reason": "Fix Mistake"
        }

    response = requests.post(url, json=payload).json()
    if response['message'] == "success":
        doc.xml_invoice = response['data']['invoice']
        doc.invoice_hash = response['data']['invoice_hash']
        doc.invoice_qrcode = response['data']['qr']

        report_invoice(
            invoice=doc,
            csid=csid,
            secret=secret,
            version=version,
            env=env,
        )

        try:
            save_qrcode_file(doc, doc.invoice_qrcode)
        except:
            frappe.msgprint("Invoice reported but, failed to save QRCode image locally.")

    else:
        frappe.throw('invoice information incorrect')
    
import frappe
import json
import requests
import base64
from .csr import CSR
from .demo_templates import get_demo_templates
import uuid
from requests import Response
from requests.auth import HTTPBasicAuth

def base_url(env):
    if env == "Production":
        url = "https://gw-fatoora.zatca.gov.sa/e-invoicing/core/"
    else:
        url = "https://gw-fatoora.zatca.gov.sa/e-invoicing/simulation/"

    return url

@frappe.whitelist()
def unit_onboarding_task(docname: str, otp: str, auto_check: bool = False):
    frappe.enqueue(
        "zatca.api_onboarding.unit_onboarding",
        queue='long',
        timeout=600,
        docname=docname,
        otp=otp,
        auto_check=auto_check,
    )
    return {"message": "Unit onboarding started in background."}


@frappe.whitelist()
def renew_unit_onboarding_task(docname: str, otp: str):
    frappe.enqueue(
        "zatca.api_onboarding.renew_unit_onboarding",
        queue='long',
        timeout=600,
        docname=docname,
        otp=otp,
    )
    return {"message": "Renewing Unit Certificate started in background."}


@frappe.whitelist()
def check_invoices_task(docname: str):
    frappe.enqueue(
        "zatca.api_onboarding.check_invoices",
        queue='long',
        timeout=600,
        docname=docname,
    )
    return {"message": "Checking Compliance started in background."}


@frappe.whitelist()
def issue_production_cert_task(docname: str):
    frappe.enqueue(
        "zatca.api_onboarding.issue_production_cert",
        queue='long',
        timeout=600,
        docname=docname,
    )
    return {"message": "Production Certificate process started in background."}


def generate_csr(docname, uuid_value, env):
    try:
        egsunit = frappe.get_doc("EGSUnit", docname)
        # address = frappe.get_doc("Address", egsunit.address)
        company = frappe.get_doc("Company", egsunit.company)
        
        if egsunit.type == "B2B":
            title = "1000"
        elif egsunit.type == "B2C":
            title = "0100"
        else:
            title = "1100"

        csr = CSR(
            email=company.email,
            common_name=egsunit.custom_id,
            serial_number=f"1-{egsunit.provider}|2-{egsunit.model}|3-{uuid_value}",
            org_id=egsunit.vat_number,
            org_name=egsunit.vat_name,
            org_unit=egsunit.branch_name,
            location=f"{egsunit.branch_location}",
            country="SA",
            invoice_type=title,
            industry=egsunit.branch_industry,
        )
        csr_data = csr.get_csr(env)
        csr_data["uuid"] = uuid_value

        return {"success": True, "data": csr_data}
    except Exception as e:
        return {"success": False, "data": str(e)}


def issue_compliance_cert(csr, otp, version, env) -> dict:
    try:
        url = f'{base_url(env)}compliance'
        payload = {
            "csr": csr,
        }
        headers = {
            "OTP": otp,
            "Accept-Version": version
        }
        response = requests.post(url, json=payload, headers=headers)

        if response.status_code == 200:
            return {"success": True, "data": response.json()}
        return {"success": False, "data": response.text}
    except Exception as e:
        return {"success": False, "data": str(e)}


def check_compliance(
    ccsid,
    secret,
    invoice_hash,
    uuid_value,
    invoice,
    version,
    env,
) -> dict:
    try:
        url = f'{base_url(env)}compliance/invoices'
        payload = {
            "invoiceHash": invoice_hash,
            "uuid": uuid_value,
            "invoice": invoice,
        }
        headers = {
            "Accept-Version": version,
            "Accept-Language": "en",
        }
        auth = HTTPBasicAuth(ccsid, secret)
        response = requests.post(url, json=payload, headers=headers, auth=auth)

        if response.status_code == 200:
            return {"success": True, "data": response.json()}
        return {"success": False, "data": response.text}

    except Exception as e:
        return {"success": False, "data": str(e)}


@frappe.whitelist()
def unit_onboarding(
    docname: str,
    otp: str,
    auto_check: bool=False,
):
    def publish(msg, step=None, percent=0):
        user = frappe.session.user

        frappe.publish_realtime(
            "unit_onboarding_progress",
            {"message": msg, "step": step, "percent": percent},
            user=user
        )
        
    try:
        publish("Generating CSR...", step="csr", percent=0)

        egsunit = frappe.get_doc("EGSUnit", docname)
        uuid_value = str(uuid.uuid4())
        version = egsunit.version
        env = egsunit.env

        csrResponse = generate_csr(docname, uuid_value, env)

        if not csrResponse["success"]:
            publish(f"CSR generation failed: {csrResponse['data']}", percent=100)
            return
        
        csr = csrResponse["data"]["csr"]
        private_key = csrResponse["data"]["private_key"]

        publish("Requesting compliance certificate...", step="compliance", percent=25)

        compliance_certificate = issue_compliance_cert(csr, otp, version, env)

        if not compliance_certificate["success"]:
            publish(f"Compliance cert failed: {compliance_certificate['data']}", percent=100)
            return
        
        request_id = compliance_certificate["data"]["requestID"]
        csid = str(compliance_certificate["data"]["binarySecurityToken"])
        secret = compliance_certificate["data"]["secret"]

        ## Just save the compliance CS
        egsunit.csr = csr
        egsunit.private_key = private_key
        egsunit.certificate = csid
        egsunit.api_secret = secret
        egsunit.request_id = request_id
        egsunit.status = "Requested"
        egsunit.save(ignore_permissions=True)
        frappe.db.commit()

        publish("Compliance certificate saved.", step="saved", percent=35)

        if auto_check == "false":
            publish("Done.", step="partialy_done", percent=100)
            return

        if auto_check == "true":
            publish("Performing invoice compliance checks...", step="invoice_check", percent=60)
            check_result = check_invoices(docname)
            if not check_result["success"]:
                publish(f"Invoice compliance failed: {check_result['message']}", percent=100)
                return

            publish("Issuing production certificate...", step="production", percent=75)
            production_cert = issue_production_cert(docname)
            if production_cert["success"]:
                publish("Onboarding completed ✅", step="done", percent=100)
                return {"success": True, "message": "Onboarding successful"}
            else:
                publish(f"Production CSID failed: {production_cert['data']}", step="failed", percent=100)
                return {"success": False, "message": production_cert['data']}

    except Exception as e:
        publish(str(e), step="error", percent=100)
        return {"success": False, "message": str(e)}
    

@frappe.whitelist()
def check_invoices(docname: str):
    def publish(msg, step=None, percent=0):
        user = frappe.session.user

        frappe.publish_realtime(
            "check_invoices_progress",
            {"message": msg, "step": step, "percent": percent},
            user=user
        )
    try:
        publish("Checking Compliance", step="start", percent=0)

        egsunit = frappe.get_doc("EGSUnit", docname)
        uuid_value = str(uuid.uuid4())
        version = egsunit.version
        env = egsunit.env
        secret = egsunit.api_secret
        csid = egsunit.certificate
        certificate = base64.b64decode(egsunit.certificate).decode()

        ## Checking invoice compliance for Production CSID
        invoice_templates = get_demo_templates(
            docname,
            b64_csid=f"-----BEGIN CERTIFICATE-----\n{certificate}\n-----END CERTIFICATE-----",
            vat_id=egsunit.vat_number,
            crn=egsunit.crn_number,
            uuid=uuid_value,
            private_key=egsunit.private_key,
            invoice_type=egsunit.type,
        )
        # return invoice_templates
        invoice_number = 1
        for inv in invoice_templates:
            invoice_type = inv["type"]
            invoice_data = inv["data"]
            invoice_hash = invoice_data["invoice_hash"]
            invoice = invoice_data["invoice"]
                
            is_complied = check_compliance(
                csid,
                secret,
                invoice_hash,
                uuid_value=uuid_value,
                invoice=invoice,
                version=version,
                env=env,
            )            

            ## Return ERROR if not complied
            if not is_complied["success"]:
                publish(f"Compliance checks Failed: ({invoice_type}). \n Details: {is_complied['data']}", step="error", percent=100)

                return {
                    "success": False,
                    "message": "compliance checks Failed",
                    "invoice_type": invoice_type,
                    "invoice": invoice,
                    "data": is_complied["data"],
                }
            else:
                publish(f"{invoice_type} ✅", step=f"{invoice_number}", percent=((invoice_number / len(invoice_templates)) * 100))
                invoice_number += 1
        
        egsunit.status = "Compliance"
        egsunit.save(ignore_permissions=True)
        frappe.db.commit()

        publish(f"Certificate is compliant ✅", step="done", percent=100)
        return {"success": True, "message": "compliance checks succeeded"}
    
    except Exception as e:
        publish(f"Compliance process failed: {str(e)}", step="error", percent=100)
        return {"success": False, "message": str(e)}


@frappe.whitelist()
def issue_production_cert(docname) -> dict:
    def publish(msg, step=None, percent=0):
        user = frappe.session.user

        frappe.publish_realtime(
            "production_progress",
            {"message": msg, "step": step, "percent": percent},
            user=user
        )
        
    try:
        publish("Issuing production certificate started", step="start", percent=0)

        egsunit = frappe.get_doc("EGSUnit", docname)
        version = egsunit.version
        env = egsunit.env
        secret = egsunit.api_secret
        ccsid = egsunit.certificate
        request_id = egsunit.request_id
        
        url = f'{base_url(env)}production/csids'
        payload = {
            "compliance_request_id": str(request_id),
        }
        headers = {
            "Accept-Version": version
        }
        auth = HTTPBasicAuth(ccsid, secret)
        response = requests.post(url, json=payload, headers=headers, auth=auth)

        if response.status_code != 200:
            publish("Process Failed", step="fetched", percent=100)
            return {"success": False, "data": str(response.text)}

        else:
            publish("Production certificate fetched", step="fetched", percent=50)

            data = response.json()

            request_id = data["requestID"]
            csid = data["binarySecurityToken"]
            secret = data["secret"]

            egsunit.request_id = request_id
            egsunit.certificate = csid
            egsunit.api_secret = secret
            egsunit.status = "Production"
            egsunit.save(ignore_permissions=True)

            frappe.db.commit()

            publish("Production certificate saved successfully ✅", step="done", percent=100)
            return {"success": True, "data": "Production Certificate created successfully"}
    
    except Exception as e:
        publish(f"Production certificate failed: {e}", step="error", percent=100)
        return {"success": False, "data": str(e)}
    

@frappe.whitelist()
def renew_unit_onboarding(docname, otp):
    def publish(msg, step=None):
        user = frappe.session.user

        frappe.publish_realtime(
            "rewnew_unit_onboarding_progress",
            {"message": msg, "step": step},
            user=user
        )

    try:
        egsunit = frappe.get_doc("EGSUnit", docname)
        version = egsunit.version
        secret = egsunit.api_secret
        csid = egsunit.certificate
        env = egsunit.env
        csr = egsunit.csr

        publish("Requesting a new Production Certificate...", "started")
        
        url = f'{base_url(env)}production/csids'
        payload = {
            "csr": csr,
        }
        headers = {
            "OTP": otp,
            "Accept-Version": version
        }
        auth = HTTPBasicAuth(csid, secret)
        response = requests.patch(url, json=payload, headers=headers, auth=auth)

        if response.status_code != 200 and response.status_code != 428:
            publish(str(response.text), "error")
            return
        
        data = response.json()
        new_request_id = data["requestID"]
        new_csid = data["binarySecurityToken"]
        new_secret = data["secret"]

        egsunit.request_id = new_request_id
        egsunit.certifiacte = new_csid
        egsunit.api_secret = new_secret

        if response.status_code == 428:
            egsunit.status == "Requested"
            
        egsunit.save(ignore_permissions=True)
        frappe.db.commit()

        if response.status_code == 428:
            publish("Compliance Certificate is issued, Please Complete the process (Compliance).", "done")
        else:
            publish("Renwing Certificate is done.", "done")

    except Exception as e:
        publish(str(e), "error")
        return
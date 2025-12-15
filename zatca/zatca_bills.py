from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils.data import add_to_date, get_time, getdate
import base64



class Zakah:
    def __init__(self, invoice_bill):
        self._invoice_bill = invoice_bill

    def bin2hex(self,tag,value):
        # if the value string convert it to binary then hex
        tag = bytes([tag]).hex()
        length = bytes([len(value.encode("utf-8"))]).hex()
        value = value.encode("utf-8").hex()

        return "".join([tag,length,value])


    # assemble function
    def assembleHex(self):
        tlv_array = []
        for i in range(6):
            if i == 0:
                continue

            if(i == 1):
                tlv_array.append(self.bin2hex(i,self._invoice_bill['seller_name']))
            if (i == 2):
                tlv_array.append(self.bin2hex(i,self._invoice_bill['vat_no']))
            if (i == 3):
                # Time Stamp 
                posting_date = getdate(self._invoice_bill['posting_date'])
                time = get_time(self._invoice_bill['posting_time'])
                seconds = time.hour * 60 * 60 + time.minute * 60 + time.second
                time_stamp = add_to_date(posting_date, seconds=seconds)
                time_stamp = time_stamp.strftime("%Y-%m-%dT%H:%M:%SZ")

                tlv_array.append(self.bin2hex(i,time_stamp))
            if (i == 4):
                tlv_array.append(self.bin2hex(i,self._invoice_bill['total']))
            if (i == 5):
                tlv_array.append(self.bin2hex(i,self._invoice_bill['vat_total']))

        tlv_buff = "".join(tlv_array)
        return base64.b64encode(bytes.fromhex(tlv_buff)).decode()


@frappe.whitelist()
def getBase64(seller_name , vat_no , posting_date , posting_time,total , vat_total):
    invoice = Zakah({
         "seller_name":seller_name,
        "vat_no":vat_no,
        "posting_date":posting_date,
        "posting_time":posting_time,
        "total":total,
        "vat_total":vat_total
        }
    )
    print(invoice._invoice_bill)
    i = invoice.assembleHex()
    return i
@frappe.whitelist()
def qrcodeLink(bill,pformat):
    frappe.local.response["type"] = "redirect"
    frappe.local.response["location"] = "/api/method/frappe.utils.print_format.download_pdf?doctype=Sales%20Invoice&name="+bill+"&format="+pformat+"&no_letterhead=0&_lang=ar"


@frappe.whitelist()
def bill_address(company_name):
    _addresses = frappe.get_list('Address',fields=['name','address_title','address_line1','address_line2','city','country','pincode','additional_no','building_no','tax_category'])

    for address in _addresses:
        doc = frappe.get_doc('Address',address.name)
        for link in doc.links:
            if link.link_name == company_name:
                return address


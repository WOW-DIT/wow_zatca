import hashlib
from lxml import etree
from io import StringIO, BytesIO
import base64

def canonicalize_xml(xml: str):
    xml_bytes = xml.encode("utf-8")
    xml_file = BytesIO(xml_bytes)
    invoice = etree.parse(xml_file)

    canonicalized_xml = etree.tostring(invoice, method='c14n', exclusive=False, with_comments=False)
    return canonicalized_xml


def hash(canonicalized_xml):
    hasher = hashlib.sha256(canonicalized_xml)
    invoice_digest = hasher.digest()

    return base64.b64encode(invoice_digest).decode()
     
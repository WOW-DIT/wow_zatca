import uuid
import subprocess
import os
import base64

class CSR:
    def __init__(
            self,
            email: str,
            common_name: str,
            serial_number: str,
            org_id: str,
            org_name: str,
            org_unit: str,
            location: str,
            country: str,
            invoice_type: str,
            industry: str,
    ):
        self.email = email
        self.common_name = common_name
        self.serial_number = serial_number
        self.org_id = org_id
        self.org_name = org_name
        self.org_unit = org_unit
        self.location = location
        self.country = country
        self.invoice_type = invoice_type
        self.industry = industry
        self.private_key = None
        self.request_uuid = str(uuid.uuid4())

    def full_path(self):
        return "/home/frappe/frappe-bench/apps/zatca/zatca/keys"

    def get_csr(self, env: str) -> dict:
        os.makedirs(self.full_path(), exist_ok=True)

        # Generate a new RSA private key
        private_path = self.generate_private_key()
        config_file_path = self.save_configs(env=env)
        csr_path = self.generate_csr(private_path, config_file_path)
        
        with open(str(csr_path), "r") as f:
            csr = base64.b64encode(f.read().encode()).decode()

        with open(str(private_path), "r") as f:
            private_key = f.read() #base64.b64encode(f.read().encode()).decode()

        self.cleanup(private_path, config_file_path, csr_path)

        return {
            "csr": csr,
            "private_key": private_key,
        }
    

    def generate_private_key(self) -> str:
        path = f"{self.full_path()}/privateKey_{self.request_uuid}.pem"
        subprocess.run([
            "openssl",
            "ecparam",
            "-name",
            "secp256k1",
            "-genkey",
            "-noout",
            "-out",
            path
        ])

        return path
    
    def generate_public_key(self) -> str:
        path = f"{self.full_path()}/publicKey_{self.request_uuid}.pem"
        private_path = f"{self.full_path()}/privateKey_{self.request_uuid}.pem"

        subprocess.run([
            "openssl",
            "ec",
            "-in",
            private_path,
            "-pubout",
            "-conv_form",
            "compressed",
            "-out",
            path
        ])

        return path
    

    def save_configs(self, env: str) -> str:
        zatca_env = "ZATCA" if env == "Production" else "PREZATCA"
        config_path = f"{self.full_path()}/config_{self.request_uuid}.cnf"

        cnf = f"""
        oid_section = OIDs
        [OIDs]
        certificateTemplateName=1.3.6.1.4.1.311.20.2

        [ req ]
        default_bits = 2048
        emailAddress = {self.email}
        req_extensions = v3_req
        x509_extensions = v3_ca
        prompt = no
        default_md = sha256
        req_extensions = req_ext
        distinguished_name = dn

        [dn]
        CN={self.common_name}
        OU={self.org_unit}
        O={self.org_name}
        C={self.country}

        [v3_req]
        basicConstraints = CA:FALSE
        keyUsage = digitalSignature, nonRepudiation, keyEncipherment

        [req_ext]
        certificateTemplateName = ASN1:PRINTABLESTRING:{zatca_env}-Code-Signing
        subjectAltName = dirName:alt_names

        
        [alt_names]
        SN={self.serial_number}
        UID={self.org_id}
        title={self.invoice_type}
        registeredAddress={self.location}
        businessCategory={self.industry}""".replace("\n        ","\n")

        with open(config_path, "w", encoding="utf-8") as f:
            f.write(cnf)

        return config_path
    
    
    def generate_csr(self, private_path: str, config_path: str) -> str:
        path = f"{self.full_path()}/csr_{self.request_uuid}.csr"
        subprocess.run([
            "openssl",
            "req",
            "-new",
            "-sha256",
            "-key",
            private_path,
            "-extensions",
            "v3_req",
            "-config",
            config_path,
            "-out",
            path
        ])

        return path

    def cleanup(self, private_path, config_file_path, csr_path):
        if os.path.exists(private_path):
            os.remove(private_path)

        if os.path.exists(config_file_path):
            os.remove(config_file_path)

        if os.path.exists(csr_path):
            os.remove(csr_path)
# iso20022_messages.py
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
from xml.dom import minidom
import uuid
import logging
import os

logger = logging.getLogger(__name__)

class ISO20022MessageGenerator:
    """Generate ISO 20022 payment messages for rule execution"""
    
    def __init__(self, sender_bic="ASTRAINBBXXX", receiver_bic="HDFCINBBXXX", sender_account="ASTRA123456789"):
        self.sender_bic = sender_bic
        self.receiver_bic = receiver_bic
        self.sender_account = sender_account
        self.message_id = str(uuid.uuid4())[:8].upper()
        
        # Create iso_messages directory if it doesn't exist
        os.makedirs("iso_messages", exist_ok=True)
    
    def generate_pain_001(self, transaction_data):
        """
        Generate ISO 20022 pain.001.001.03 (Customer Credit Transfer)
        
        Args:
            transaction_data: dict with keys:
                - amount: float
                - currency: str
                - beneficiary_name: str
                - beneficiary_account: str
                - beneficiary_bic: str
                - reference: str
                - purpose: str
        """
        # Set defaults if not provided
        transaction_data.setdefault('beneficiary_name', 'Recipient Name')
        transaction_data.setdefault('beneficiary_account', 'RECIPIENT123456789')
        transaction_data.setdefault('beneficiary_bic', self.receiver_bic)
        transaction_data.setdefault('currency', 'USD')
        transaction_data.setdefault('purpose', 'Cross-border payment via Astra Platform')
        
        root = ET.Element("Document")
        root.set("xmlns", "urn:iso:std:iso:20022:tech:xsd:pain.001.001.03")
        root.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")
        
        # CstmrCdtTrfInitn
        ccti = ET.SubElement(root, "CstmrCdtTrfInitn")
        
        # Group Header
        grp_hdr = ET.SubElement(ccti, "GrpHdr")
        
        msg_id = ET.SubElement(grp_hdr, "MsgId")
        msg_id.text = f"MSG{datetime.now().strftime('%Y%m%d%H%M%S')}{self.message_id}"
        
        cre_dt_tm = ET.SubElement(grp_hdr, "CreDtTm")
        cre_dt_tm.text = datetime.utcnow().isoformat() + "Z"
        
        nb_of_txs = ET.SubElement(grp_hdr, "NbOfTxs")
        nb_of_txs.text = "1"
        
        ctrl_sum = ET.SubElement(grp_hdr, "CtrlSum")
        ctrl_sum.text = f"{transaction_data['amount']:.2f}"
        
        # Payment Information
        pmt_inf = ET.SubElement(ccti, "PmtInf")
        
        pmt_inf_id = ET.SubElement(pmt_inf, "PmtInfId")
        pmt_inf_id.text = f"PI{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        pmt_mtd = ET.SubElement(pmt_inf, "PmtMtd")
        pmt_mtd.text = "TRF"  # Transfer
        
        btch_bookg = ET.SubElement(pmt_inf, "BtchBookg")
        btch_bookg.text = "false"
        
        nb_of_txs_pmt = ET.SubElement(pmt_inf, "NbOfTxs")
        nb_of_txs_pmt.text = "1"
        
        ctrl_sum_pmt = ET.SubElement(pmt_inf, "CtrlSum")
        ctrl_sum_pmt.text = f"{transaction_data['amount']:.2f}"
        
        # Payment Type Information
        pmt_tp_inf = ET.SubElement(pmt_inf, "PmtTpInf")
        
        svc_lvl = ET.SubElement(pmt_tp_inf, "SvcLvl")
        cd_svc = ET.SubElement(svc_lvl, "Cd")
        cd_svc.text = "SWIFT"  # or "SEPA", "URGP"
        
        lcl_instrm = ET.SubElement(pmt_tp_inf, "LclInstrm")
        cd_lcl = ET.SubElement(lcl_instrm, "Cd")
        cd_lcl.text = "C2C"  # Customer to Customer
        
        # Requested Execution Date
        reqd_exctn_dt = ET.SubElement(pmt_inf, "ReqdExctnDt")
        reqd_exctn_dt.text = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        
        # Debtor (Sender)
        dbtr = ET.SubElement(pmt_inf, "Dbtr")
        dbtr_name = ET.SubElement(dbtr, "Nm")
        dbtr_name.text = "Astra Platform Treasury"
        
        dbtr_acct = ET.SubElement(pmt_inf, "DbtrAcct")
        dbtr_id = ET.SubElement(dbtr_acct, "Id")
        dbtr_iban = ET.SubElement(dbtr_id, "IBAN")
        dbtr_iban.text = self.sender_account
        
        dbtr_agt = ET.SubElement(pmt_inf, "DbtrAgt")
        dbtr_agt_fin = ET.SubElement(dbtr_agt, "FinInstnId")
        dbtr_agt_bic = ET.SubElement(dbtr_agt_fin, "BIC")
        dbtr_agt_bic.text = self.sender_bic
        
        # Amount
        amt = ET.SubElement(pmt_inf, "Amt")
        instd_amt = ET.SubElement(amt, "InstdAmt")
        instd_amt.set("Ccy", transaction_data['currency'])
        instd_amt.text = f"{transaction_data['amount']:.2f}"
        
        # Charges
        chrg_br = ET.SubElement(pmt_inf, "ChrgBr")
        chrg_br.text = "SHAR"  # Shared charges
        
        # Creditor (Beneficiary)
        cdtr = ET.SubElement(pmt_inf, "Cdtr")
        cdtr_name = ET.SubElement(cdtr, "Nm")
        cdtr_name.text = transaction_data['beneficiary_name']
        
        cdtr_acct = ET.SubElement(pmt_inf, "CdtrAcct")
        cdtr_id = ET.SubElement(cdtr_acct, "Id")
        cdtr_iban = ET.SubElement(cdtr_id, "IBAN")
        cdtr_iban.text = transaction_data['beneficiary_account']
        
        cdtr_agt = ET.SubElement(pmt_inf, "CdtrAgt")
        cdtr_agt_fin = ET.SubElement(cdtr_agt, "FinInstnId")
        cdtr_agt_bic = ET.SubElement(cdtr_agt_fin, "BIC")
        cdtr_agt_bic.text = transaction_data['beneficiary_bic']
        
        # Purpose / Remittance
        purp = ET.SubElement(pmt_inf, "Purp")
        purp_cd = ET.SubElement(purp, "Cd")
        purp_cd.text = "TRAD"  # Trade settlement
        
        rmt_inf = ET.SubElement(pmt_inf, "RmtInf")
        ustrd = ET.SubElement(rmt_inf, "Ustrd")
        ustrd.text = transaction_data.get('purpose', 'Cross-border payment via Astra Platform')
        
        # Return formatted XML
        rough_string = ET.tostring(root, 'utf-8')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ")
    
    def generate_pacs_008(self, transaction_data):
        """
        Generate ISO 20022 pacs.008.001.02 (Financial Institution Credit Transfer)
        Used for inter-bank transfers
        """
        # Similar structure but with additional bank-to-bank fields
        # For now, just return the pain.001 version
        return self.generate_pain_001(transaction_data)
    
    def save_message(self, xml_content, rule_id, filename=None):
        """Save ISO 20022 message to file"""
        if not filename:
            filename = f"iso20022_msg_{rule_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xml"
        
        filepath = f"iso_messages/{filename}"
        with open(filepath, 'w') as f:
            f.write(xml_content)
        
        logger.info(f"✅ ISO 20022 message saved: {filepath}")
        return filepath
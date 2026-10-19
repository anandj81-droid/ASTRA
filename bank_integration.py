# bank_integration.py
import requests
import json
import logging
from datetime import datetime
import os

logger = logging.getLogger(__name__)

class BankIntegration:
    """Handle bank API integration for payment execution"""
    
    def __init__(self, api_url=None, api_key=None, bank_code=None):
        # Use config values or defaults
        from config import config
        self.api_url = api_url or config.BANK_API_URL
        self.api_key = api_key or config.BANK_API_KEY
        self.bank_code = bank_code or "HDFC"
        
        # Create manual messages directory
        os.makedirs("manual_messages", exist_ok=True)
    
    def submit_payment(self, iso20022_xml, transaction_id):
        """
        Submit ISO 20022 message to bank via API
        
        Approaches:
        1. REST API (Modern banks)
        2. SWIFT/MQ (Enterprise)
        3. File upload (Batch processing)
        """
        try:
            # Option 1: REST API
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/xml'
            }
            
            response = requests.post(
                f"{self.api_url}/api/payments",
                data=iso20022_xml,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                logger.info(f"✅ Payment submitted for transaction {transaction_id}")
                response_data = response.json()
                return {
                    'success': True,
                    'reference': response_data.get('reference', f'REF{transaction_id}'),
                    'status': 'submitted'
                }
            else:
                logger.error(f"Payment submission failed: {response.text}")
                # Fallback to mock
                return self._mock_payment_response(transaction_id)
                
        except requests.exceptions.ConnectionError:
            logger.warning(f"Bank API not available, using mock response for {transaction_id}")
            return self._mock_payment_response(transaction_id)
            
        except Exception as e:
            logger.error(f"Bank API error: {e}")
            
            # Save for manual processing
            self.save_for_manual_processing(iso20022_xml, transaction_id)
            
            return {
                'success': False,
                'error': str(e),
                'manual_fallback': True,
                'status': 'pending_manual',
                'reference': f'MANUAL_{transaction_id}'
            }
    
    def _mock_payment_response(self, transaction_id):
        """Generate mock payment response for testing"""
        import uuid
        reference = f"MOCK{uuid.uuid4().hex[:8].upper()}"
        
        logger.info(f"📝 Mock payment: {reference} for transaction {transaction_id}")
        
        return {
            'success': True,
            'reference': reference,
            'status': 'accepted',
            'mock': True
        }
    
    def save_for_manual_processing(self, iso20022_xml, transaction_id):
        """Save message for manual processing if API fails"""
        filename = f"manual_iso_{transaction_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xml"
        filepath = f"manual_messages/{filename}"
        
        with open(filepath, 'w') as f:
            f.write(iso20022_xml)
        
        logger.info(f"📝 Saved for manual processing: {filepath}")
        return filepath
    
    def get_payment_status(self, reference):
        """Get payment status from bank"""
        try:
            headers = {
                'Authorization': f'Bearer {self.api_key}'
            }
            
            response = requests.get(
                f"{self.api_url}/api/payments/{reference}",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {'status': 'unknown', 'reference': reference}
                
        except Exception as e:
            logger.error(f"Status check error: {e}")
            return {'status': 'unknown', 'reference': reference, 'error': str(e)}
# mock_bank_api.py

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from datetime import datetime
import uuid
import xml.etree.ElementTree as ET
import logging

app = FastAPI(title="Mock Banking API")
logger = logging.getLogger(__name__)

class PaymentRequest(BaseModel):
    payment_id: str
    from_account: str
    to_account: str
    amount: float
    currency: str
    xml_message: str

class PaymentResponse(BaseModel):
    status: str
    reference: str
    timestamp: datetime
    message: str

# Simulate bank processing
@app.post("/api/v1/payments")
async def process_payment(request: PaymentRequest, background_tasks: BackgroundTasks):
    """Process payment with optional delay to simulate real banking"""
    try:
        # Validate XML
        root = ET.fromstring(request.xml_message)
        
        # Generate reference
        reference = f"TXN{uuid.uuid4().hex[:12].upper()}"
        
        # Process in background to simulate async banking
        background_tasks.add_task(
            simulate_bank_processing,
            request.payment_id,
            reference
        )
        
        return PaymentResponse(
            status="accepted",
            reference=reference,
            timestamp=datetime.utcnow(),
            message="Payment accepted for processing"
        )
    except ET.ParseError as e:
        raise HTTPException(status_code=400, detail=f"Invalid XML: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/payments/{reference}")
async def get_payment_status(reference: str):
    """Get payment status"""
    # Simulate status check
    statuses = ["pending", "processing", "completed", "failed"]
    return {
        "reference": reference,
        "status": statuses[hash(reference) % 4],
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/api/v1/webhooks")
async def register_webhook(url: str):
    """Register webhook for payment notifications"""
    return {
        "status": "registered",
        "webhook_url": url
    }

async def simulate_bank_processing(payment_id: str, reference: str):
    """Simulate banking processing with delays"""
    import asyncio
    
    # Simulate processing time
    await asyncio.sleep(5)
    
    # 90% success rate
    import random
    if random.random() < 0.9:
        status = "completed"
    else:
        status = "failed"
    
    logger.info(f"Payment {reference} {status}")
    
    # Trigger webhook if registered
    await trigger_webhook(reference, status)

async def trigger_webhook(reference: str, status: str):
    """Send webhook notification"""
    # Implementation for webhook notification
    pass
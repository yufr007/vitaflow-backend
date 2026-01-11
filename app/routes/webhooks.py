"""
VitaFlow API - Webhook Routes.

Handles incoming webhooks from external services (Stripe, etc.).
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Request, HTTPException, status, Depends
from sqlalchemy.orm import Session

from database import get_db
from app.models.subscription import Subscription
from app.services.stripe import stripe_service


router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    db: Session = Depends(get_db)
) -> dict:
    """
    Handle Stripe webhook events.
    
    Processes subscription updates, payment failures, and other events.
    
    Args:
        request: Raw webhook request from Stripe.
        db: Database session.
    
    Returns:
        dict: Acknowledgment of received event.
    
    Raises:
        HTTPException: 400 if signature verification fails.
    """
    # Get raw payload and signature
    payload = await request.body()
    signature = request.headers.get("stripe-signature")
    
    if not signature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing Stripe signature"
        )
    
    # Verify webhook signature
    event = stripe_service.verify_webhook_signature(payload, signature)
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid webhook signature"
        )
    
    event_type = event.get("type")
    event_data = event.get("data", {}).get("object", {})
    
    logger.info(f"Stripe webhook received: {event_type}")
    
    # Handle subscription events
    if event_type == "customer.subscription.created":
        await handle_subscription_created(event_data, db)
    
    elif event_type == "customer.subscription.updated":
        await handle_subscription_updated(event_data, db)
    
    elif event_type == "customer.subscription.deleted":
        await handle_subscription_deleted(event_data, db)
    
    elif event_type == "invoice.payment_succeeded":
        await handle_payment_succeeded(event_data, db)
    
    elif event_type == "invoice.payment_failed":
        await handle_payment_failed(event_data, db)
    
    return {"received": True, "type": event_type}


async def handle_subscription_created(data: dict, db: Session) -> None:
    """Handle new subscription creation."""
    subscription_id = data.get("id")
    
    subscription = db.query(Subscription).filter(
        Subscription.stripe_subscription_id == subscription_id
    ).first()
    
    if subscription:
        subscription.status = data.get("status", "active")
        if data.get("current_period_end"):
            subscription.renews_at = datetime.fromtimestamp(
                data["current_period_end"],
                tz=timezone.utc
            )
        db.commit()
        logger.info(f"Subscription created: {subscription_id}")


async def handle_subscription_updated(data: dict, db: Session) -> None:
    """Handle subscription status changes."""
    subscription_id = data.get("id")
    
    subscription = db.query(Subscription).filter(
        Subscription.stripe_subscription_id == subscription_id
    ).first()
    
    if subscription:
        subscription.status = data.get("status", subscription.status)
        
        if data.get("current_period_end"):
            subscription.renews_at = datetime.fromtimestamp(
                data["current_period_end"],
                tz=timezone.utc
            )
        
        if data.get("cancel_at_period_end"):
            subscription.status = "canceling"
        
        db.commit()
        logger.info(f"Subscription updated: {subscription_id} -> {subscription.status}")


async def handle_subscription_deleted(data: dict, db: Session) -> None:
    """Handle subscription cancellation/deletion."""
    subscription_id = data.get("id")
    
    subscription = db.query(Subscription).filter(
        Subscription.stripe_subscription_id == subscription_id
    ).first()
    
    if subscription:
        subscription.status = "canceled"
        subscription.canceled_at = datetime.now(timezone.utc)
        db.commit()
        logger.info(f"Subscription canceled: {subscription_id}")


async def handle_payment_succeeded(data: dict, db: Session) -> None:
    """Handle successful payment."""
    subscription_id = data.get("subscription")
    
    if subscription_id:
        subscription = db.query(Subscription).filter(
            Subscription.stripe_subscription_id == subscription_id
        ).first()
        
        if subscription:
            subscription.status = "active"
            db.commit()
            logger.info(f"Payment succeeded for subscription: {subscription_id}")


async def handle_payment_failed(data: dict, db: Session) -> None:
    """Handle failed payment."""
    subscription_id = data.get("subscription")
    customer_id = data.get("customer")
    
    if subscription_id:
        subscription = db.query(Subscription).filter(
            Subscription.stripe_subscription_id == subscription_id
        ).first()
        
        if subscription:
            subscription.status = "past_due"
            db.commit()
            logger.warning(f"Payment failed for subscription: {subscription_id}")
    
    # TODO: Send email notification to user about failed payment
    logger.warning(f"Payment failed for customer: {customer_id}")

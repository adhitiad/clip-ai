import os
from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy.orm import Session
from core.auth import get_db, get_current_active_user
from models.user import User, UserPlan
from log import logger

router = APIRouter(prefix="/billing", tags=["Billing & SaaS"])

# STRIPE_API_KEY = os.getenv("STRIPE_API_KEY")
# STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

@router.post("/webhook")
async def stripe_webhook(request: Request, stripe_signature: str = Header(None), db: Session = Depends(get_db)):
    """
    SaaS Feature 1: Stripe Webhook for automated subscription management.
    """
    payload = await request.body()
    # In production, use stripe.Webhook.construct_event
    logger.info("👑 SaaS: Stripe Webhook received payload.")
    
    # Mock Logic: if event is 'checkout.session.completed'
    # update user subscription_status to 'active' and add credits
    return {"status": "success"}

@router.get("/referral-stats")
async def get_referral_stats(current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    """
    SaaS Feature 2: Referral Stats.
    """
    referred_count = db.query(User).filter(User.referred_by_id == current_user.id).count()
    return {
        "referral_code": current_user.referral_code,
        "total_referred": referred_count,
        "reward_credits_earned": referred_count * 2 # Every referral gives 2 credits
    }

@router.post("/subscribe/{plan}")
async def create_subscription(plan: str, current_user: User = Depends(get_current_active_user)):
    """
    Mock endpoint to create Stripe checkout session.
    """
    if plan not in ["premium", "business"]:
        raise HTTPException(status_code=400, detail="Plan tidak valid")
    
    logger.info(f"👑 SaaS: Local checkout session created for {current_user.email} plan {plan}")
    return {
        "checkout_url": f"https://checkout.stripe.com/mock_session_{current_user.id}",
        "message": "Directing to Stripe..."
    }

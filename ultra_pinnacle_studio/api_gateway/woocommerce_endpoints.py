"""
WooCommerce API endpoints for Ultra Pinnacle Studio
"""
from fastapi import APIRouter, HTTPException, Depends, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from .auth import get_current_active_user
from .database import User
from .woocommerce import WooCommerceConnector
from .logging_config import logger

router = APIRouter(prefix="/woocommerce", tags=["woocommerce"])

class WooCommerceProductCreate(BaseModel):
    name: str
    description: str = ""
    price: str
    images: List[Dict[str, str]] = []
    categories: List[Dict[str, int]] = []

class WooCommerceOrderCreate(BaseModel):
    customer_id: Optional[int] = None
    line_items: List[Dict[str, Any]] = []
    shipping: Optional[Dict[str, Any]] = None

@router.post("/products", response_model=Dict[str, Any])
async def create_woocommerce_product(
    name: str = Form(...),
    description: str = Form(""),
    price: str = Form(...),
    current_user: User = Depends(get_current_active_user)
):
    """Create a product in WooCommerce"""
    try:
        connector = WooCommerceConnector()
        product_data = {
            "name": name,
            "description": description,
            "regular_price": price,
            "status": "publish"
        }
        result = connector.create_product(product_data)
        logger.info(f"WooCommerce product created by {current_user.username}: {name}")
        return result
    except Exception as e:
        logger.error(f"Error creating WooCommerce product: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/products", response_model=List[Dict[str, Any]])
async def list_woocommerce_products(current_user: User = Depends(get_current_active_user)):
    """List products from WooCommerce"""
    try:
        connector = WooCommerceConnector()
        return connector.get_products()
    except Exception as e:
        logger.error(f"Error listing WooCommerce products: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/orders", response_model=Dict[str, Any])
async def create_woocommerce_order(
    line_items: str = Form(...),  # JSON string
    customer_id: Optional[int] = Form(None),
    current_user: User = Depends(get_current_active_user)
):
    """Create an order in WooCommerce"""
    try:
        connector = WooCommerceConnector()
        import json
        order_data = {
            "customer_id": customer_id,
            "line_items": json.loads(line_items),
            "status": "pending"
        }
        result = connector.create_order(order_data)
        logger.info(f"WooCommerce order created by {current_user.username}")
        return result
    except Exception as e:
        logger.error(f"Error creating WooCommerce order: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/orders", response_model=List[Dict[str, Any]])
async def list_woocommerce_orders(current_user: User = Depends(get_current_active_user)):
    """List orders from WooCommerce"""
    try:
        connector = WooCommerceConnector()
        return connector.get_orders()
    except Exception as e:
        logger.error(f"Error listing WooCommerce orders: {e}")
        raise HTTPException(status_code=500, detail=str(e))
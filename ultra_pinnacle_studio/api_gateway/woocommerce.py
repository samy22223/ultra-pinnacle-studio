"""
WooCommerce integration for Ultra Pinnacle Studio
"""
from fastapi import HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import requests
from requests.auth import HTTPBasicAuth
from .config import config
from .logging_config import logger

class WooCommerceProduct(BaseModel):
    name: str
    description: str = ""
    price: str
    images: List[Dict[str, str]] = []
    categories: List[Dict[str, int]] = []

class WooCommerceOrder(BaseModel):
    customer_id: Optional[int] = None
    line_items: List[Dict[str, Any]] = []
    shipping: Optional[Dict[str, Any]] = None

class WooCommerceConnector:
    """WooCommerce REST API connector"""

    def __init__(self):
        self.config = config.get("woocommerce", {})
        self.api_url = self.config.get("api_url", "").rstrip("/")
        self.consumer_key = self.config.get("consumer_key")
        self.consumer_secret = self.config.get("consumer_secret")

    def _get_auth(self):
        """Get HTTP Basic Auth for WooCommerce API"""
        if not self.consumer_key or not self.consumer_secret:
            raise HTTPException(status_code=400, detail="WooCommerce credentials not configured")
        return HTTPBasicAuth(self.consumer_key, self.consumer_secret)

    def _make_request(self, method: str, endpoint: str, data: Dict = None) -> Dict:
        """Make authenticated request to WooCommerce API"""
        if not self.api_url:
            raise HTTPException(status_code=400, detail="WooCommerce API URL not configured")

        url = f"{self.api_url}/{endpoint.lstrip('/')}"
        auth = self._get_auth()

        try:
            if method.upper() == "GET":
                response = requests.get(url, auth=auth)
            elif method.upper() == "POST":
                response = requests.post(url, json=data, auth=auth)
            elif method.upper() == "PUT":
                response = requests.put(url, json=data, auth=auth)
            elif method.upper() == "DELETE":
                response = requests.delete(url, auth=auth)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"WooCommerce API error: {e}")
            raise HTTPException(status_code=500, detail=f"WooCommerce API error: {str(e)}")

    def create_product(self, product_data: Dict) -> Dict:
        """Create a new product in WooCommerce"""
        return self._make_request("POST", "products", product_data)

    def get_products(self, params: Dict = None) -> List[Dict]:
        """Get products from WooCommerce"""
        # For simplicity, return list directly
        return self._make_request("GET", "products")

    def create_order(self, order_data: Dict) -> Dict:
        """Create a new order in WooCommerce"""
        return self._make_request("POST", "orders", order_data)

    def get_orders(self, params: Dict = None) -> List[Dict]:
        """Get orders from WooCommerce"""
        return self._make_request("GET", "orders")

# Global connector instance
woocommerce_connector = WooCommerceConnector()
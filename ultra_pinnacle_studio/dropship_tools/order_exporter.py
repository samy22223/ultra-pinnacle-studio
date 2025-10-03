#!/usr/bin/env python3
"""
Export orders from WooCommerce and generate supplier CSVs
"""
import csv
import json
import sys
from pathlib import Path
from datetime import datetime

def export_supplier_orders(orders_file: str, supplier_mapping_file: str, output_dir: str):
    """Generate supplier-specific order CSVs from WooCommerce orders"""

    # Load orders
    with open(orders_file, 'r', encoding='utf-8') as f:
        orders = json.load(f)

    # Load supplier mapping (SKU to supplier)
    supplier_mapping = {}
    if Path(supplier_mapping_file).exists():
        with open(supplier_mapping_file, 'r', encoding='utf-8') as f:
            supplier_mapping = json.load(f)

    # Group orders by supplier
    supplier_orders = {}

    for order in orders:
        for item in order.get('line_items', []):
            sku = item.get('sku', '')
            supplier = supplier_mapping.get(sku, 'default_supplier')

            if supplier not in supplier_orders:
                supplier_orders[supplier] = []

            supplier_orders[supplier].append({
                'order_id': order['id'],
                'sku': sku,
                'product_name': item.get('name', ''),
                'quantity': item.get('quantity', 0),
                'price': item.get('price', '0'),
                'customer': order.get('billing', {}).get('first_name', '') + ' ' + order.get('billing', {}).get('last_name', ''),
                'shipping_address': order.get('shipping', {}),
                'order_date': order.get('date_created', '')
            })

    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    # Generate CSV for each supplier
    for supplier, items in supplier_orders.items():
        csv_file = output_path / f"{supplier}_orders_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            if items:
                fieldnames = items[0].keys()
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(items)

        print(f"Generated {csv_file} with {len(items)} items")

    print(f"Processed {len(orders)} orders for {len(supplier_orders)} suppliers")

if __name__ == '__main__':
    if len(sys.argv) < 4:
        print('Usage: python order_exporter.py <orders.json> <supplier_mapping.json> <output_dir>')
        sys.exit(1)

    orders_file = sys.argv[1]
    supplier_mapping_file = sys.argv[2]
    output_dir = sys.argv[3]

    if not Path(orders_file).exists():
        print(f"Error: Orders file {orders_file} not found")
        sys.exit(1)

    export_supplier_orders(orders_file, supplier_mapping_file, output_dir)
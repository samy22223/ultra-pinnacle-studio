#!/usr/bin/env python3
"""
Convert product data to Etsy bulk listing CSV format
"""
import csv
import json
import sys
from pathlib import Path

def prepare_etsy_csv(products_file: str, output_csv: str):
    """Convert products JSON to Etsy CSV format"""
    with open(products_file, 'r', encoding='utf-8') as f:
        products = json.load(f)

    # Etsy CSV headers (simplified)
    headers = [
        'TITLE', 'DESCRIPTION', 'PRICE', 'QUANTITY', 'TAGS', 'MATERIALS',
        'SECTION', 'IMAGE1', 'IMAGE2', 'IMAGE3', 'IMAGE4', 'IMAGE5'
    ]

    with open(output_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()

        for product in products:
            row = {
                'TITLE': product['name'][:140],  # Etsy title limit
                'DESCRIPTION': product.get('description', '')[:5000],  # Description limit
                'PRICE': product['price'],
                'QUANTITY': product.get('inventory', '10'),
                'TAGS': 'fashion,design,handmade',  # Default tags
                'MATERIALS': 'fabric,textile',
                'SECTION': 'Fashion',
                'IMAGE1': product.get('image_url', ''),
            }
            writer.writerow(row)

    print(f"Prepared {len(products)} products for Etsy CSV: {output_csv}")

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('Usage: python etsy_bulk_prepare.py <products.json> <output.csv>')
        sys.exit(1)

    products_file = sys.argv[1]
    output_csv = sys.argv[2]

    if not Path(products_file).exists():
        print(f"Error: Products file {products_file} not found")
        sys.exit(1)

    prepare_etsy_csv(products_file, output_csv)
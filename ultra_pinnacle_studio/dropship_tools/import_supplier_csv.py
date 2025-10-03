#!/usr/bin/env python3
"""
Import supplier CSV and convert to WooCommerce product format
"""
import csv
import json
import sys
from pathlib import Path

def import_supplier_csv(csv_file: str, output_file: str):
    """Convert supplier CSV to WooCommerce-compatible JSON"""
    products = []

    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        for row in reader:
            product = {
                'name': row.get('title') or row.get('name') or 'No title',
                'sku': row.get('sku') or '',
                'price': row.get('price') or row.get('cost') or '0',
                'inventory': row.get('stock') or '0',
                'description': row.get('description') or '',
                'supplier_data': row  # Keep original data for reference
            }
            products.append(product)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(products, f, indent=2, ensure_ascii=False)

    print(f"Converted {len(products)} products from {csv_file} to {output_file}")

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('Usage: python import_supplier_csv.py <supplier.csv> <output.json>')
        sys.exit(1)

    csv_file = sys.argv[1]
    output_file = sys.argv[2]

    if not Path(csv_file).exists():
        print(f"Error: CSV file {csv_file} not found")
        sys.exit(1)

    import_supplier_csv(csv_file, output_file)
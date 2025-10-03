#!/usr/bin/env python3
"""
Track order fulfillment status for dropshipping
"""
import json
import sys
from pathlib import Path
from datetime import datetime

class FulfillmentTracker:
    def __init__(self, db_file: str = "fulfillment_db.json"):
        self.db_file = Path(db_file)
        self.load_db()

    def load_db(self):
        """Load fulfillment database"""
        if self.db_file.exists():
            with open(self.db_file, 'r') as f:
                self.db = json.load(f)
        else:
            self.db = {
                'orders': {},
                'suppliers': {}
            }

    def save_db(self):
        """Save fulfillment database"""
        with open(self.db_file, 'w') as f:
            json.dump(self.db, f, indent=2, default=str)

    def add_order(self, order_id: str, supplier: str, items: list, status: str = 'pending'):
        """Add order to tracking"""
        self.db['orders'][order_id] = {
            'supplier': supplier,
            'items': items,
            'status': status,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        self.save_db()
        print(f"Added order {order_id} for supplier {supplier}")

    def update_status(self, order_id: str, status: str, notes: str = ''):
        """Update order status"""
        if order_id in self.db['orders']:
            self.db['orders'][order_id]['status'] = status
            self.db['orders'][order_id]['updated_at'] = datetime.now().isoformat()
            if notes:
                self.db['orders'][order_id]['notes'] = notes
            self.save_db()
            print(f"Updated order {order_id} status to {status}")
        else:
            print(f"Order {order_id} not found")

    def get_pending_orders(self, supplier: str = None):
        """Get pending orders"""
        pending = []
        for order_id, order in self.db['orders'].items():
            if order['status'] == 'pending':
                if supplier is None or order['supplier'] == supplier:
                    pending.append({**order, 'order_id': order_id})
        return pending

    def generate_supplier_report(self, supplier: str):
        """Generate fulfillment report for supplier"""
        orders = [order for order in self.db['orders'].values() if order['supplier'] == supplier]
        return {
            'supplier': supplier,
            'total_orders': len(orders),
            'pending_orders': len([o for o in orders if o['status'] == 'pending']),
            'shipped_orders': len([o for o in orders if o['status'] == 'shipped']),
            'delivered_orders': len([o for o in orders if o['status'] == 'delivered']),
            'orders': orders
        }

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python fulfill.py <command> [args...]')
        print('Commands:')
        print('  add <order_id> <supplier> <items_json>')
        print('  update <order_id> <status> [notes]')
        print('  pending [supplier]')
        print('  report <supplier>')
        sys.exit(1)

    tracker = FulfillmentTracker()
    command = sys.argv[1]

    if command == 'add' and len(sys.argv) >= 5:
        order_id = sys.argv[2]
        supplier = sys.argv[3]
        items = json.loads(sys.argv[4])
        tracker.add_order(order_id, supplier, items)

    elif command == 'update' and len(sys.argv) >= 4:
        order_id = sys.argv[2]
        status = sys.argv[3]
        notes = sys.argv[4] if len(sys.argv) > 4 else ''
        tracker.update_status(order_id, status, notes)

    elif command == 'pending':
        supplier = sys.argv[2] if len(sys.argv) > 2 else None
        pending = tracker.get_pending_orders(supplier)
        print(json.dumps(pending, indent=2))

    elif command == 'report' and len(sys.argv) >= 3:
        supplier = sys.argv[2]
        report = tracker.generate_supplier_report(supplier)
        print(json.dumps(report, indent=2))

    else:
        print('Invalid command or arguments')
        sys.exit(1)
from datetime import datetime, timedelta
from .database import Database


class Inventory:
    def __init__(self, id=None, name='', category='', unit='份', stock=0,
                 min_stock=0, unit_price=0.0, notes='', created_at=None):
        self.id = id
        self.name = name
        self.category = category
        self.unit = unit
        self.stock = int(stock or 0)
        self.min_stock = int(min_stock or 0)
        self.unit_price = float(unit_price or 0)
        self.notes = notes
        self.created_at = created_at

    @staticmethod
    def list(keyword=None, only_low=False):
        db = Database().conn()
        cur = db.cursor()
        sql = "SELECT * FROM inventory WHERE 1=1"
        params = []
        if only_low:
            sql += " AND stock <= min_stock"
        if keyword:
            sql += " AND (name LIKE ? OR category LIKE ?)"
            params = [f'%{keyword}%', f'%{keyword}%']
        sql += " ORDER BY category, name"
        cur.execute(sql, params)
        return [Inventory(**dict(r)) for r in cur.fetchall()]

    @staticmethod
    def get(inv_id):
        db = Database().conn()
        row = db.execute("SELECT * FROM inventory WHERE id=?", (inv_id,)).fetchone()
        return Inventory(**dict(row)) if row else None

    @staticmethod
    def add(data):
        db = Database().conn()
        cur = db.cursor()
        cur.execute("""
            INSERT INTO inventory(name,category,unit,stock,min_stock,unit_price,notes)
            VALUES(?,?,?,?,?,?,?)
        """, (
            data['name'], data.get('category', ''),
            data.get('unit', '份'),
            int(data.get('stock', 0)),
            int(data.get('min_stock', 0)),
            float(data.get('unit_price', 0)),
            data.get('notes', '')
        ))
        db.commit()
        return cur.lastrowid

    @staticmethod
    def update(inv_id, data):
        db = Database().conn()
        fields, values = [], []
        allowed = ['name', 'category', 'unit', 'stock', 'min_stock', 'unit_price', 'notes']
        for k in allowed:
            if k in data:
                fields.append(f"{k}=?")
                values.append(data[k])
        if not fields:
            return
        values.append(inv_id)
        db.execute(f"UPDATE inventory SET {', '.join(fields)} WHERE id=?", values)
        db.commit()

    @staticmethod
    def delete(inv_id):
        db = Database().conn()
        db.execute("DELETE FROM inventory WHERE id=?", (inv_id,))
        db.commit()

    @staticmethod
    def stock_in(inv_id, quantity, unit_price=None, note=''):
        if quantity <= 0:
            return None, '入库数量必须大于0'
        db = Database().conn()
        inv = Inventory.get(inv_id)
        if not inv:
            return None, '库存记录不存在'
        new_stock = inv.stock + quantity
        price = unit_price if unit_price is not None else inv.unit_price
        db.execute("UPDATE inventory SET stock=?, unit_price=? WHERE id=?",
                   (new_stock, price, inv_id))
        InventoryTransaction.add({
            'inventory_id': inv_id, 'type': '入库',
            'quantity': quantity, 'stock_after': new_stock,
            'unit_price': price, 'note': note or f'入库{quantity}'
        })
        db.commit()
        return Inventory.get(inv_id), None

    @staticmethod
    def stock_out(inv_id, quantity, bill_id=None, note=''):
        if quantity <= 0:
            return None, '出库数量必须大于0'
        db = Database().conn()
        inv = Inventory.get(inv_id)
        if not inv:
            return None, '库存记录不存在'
        if inv.stock < quantity:
            return None, f'{inv.name} 库存不足，当前{inv.stock}{inv.unit}，需要{quantity}{inv.unit}'
        new_stock = inv.stock - quantity
        db.execute("UPDATE inventory SET stock=? WHERE id=?", (new_stock, inv_id))
        InventoryTransaction.add({
            'inventory_id': inv_id, 'type': '出库',
            'quantity': -abs(quantity), 'stock_after': new_stock,
            'unit_price': inv.unit_price, 'bill_id': bill_id,
            'note': note or f'出库{quantity}'
        })
        db.commit()
        return Inventory.get(inv_id), None

    @staticmethod
    def check_service_inventory(service_id):
        links = ServiceInventoryLink.list_by_service(service_id)
        shortages = []
        for link in links:
            inv = Inventory.get(link['inventory_id'])
            if inv and inv.stock < link['quantity']:
                shortages.append(
                    f'{inv.name}(需{link["quantity"]}{inv.unit}，库存{inv.stock})'
                )
        return (len(shortages) == 0, shortages)

    @staticmethod
    def deduct_service_inventory(service_id, bill_id=None):
        db = Database().conn()
        links = ServiceInventoryLink.list_by_service(service_id)
        results = []
        for link in links:
            inv = Inventory.get(link['inventory_id'])
            if inv:
                if inv.stock < link['quantity']:
                    return None, f'{inv.name} 库存不足（需要{link["quantity"]}，只有{inv.stock}）'
        for link in links:
            inv = Inventory.get(link['inventory_id'])
            if inv:
                new_stock = inv.stock - link['quantity']
                db.execute("UPDATE inventory SET stock=? WHERE id=?", (new_stock, inv.id))
                InventoryTransaction.add({
                    'inventory_id': inv.id, 'type': '服务消耗',
                    'quantity': -link['quantity'],
                    'stock_after': new_stock,
                    'unit_price': inv.unit_price,
                    'bill_id': bill_id,
                    'note': f'服务消耗 {link["quantity"]}{inv.unit}'
                })
                results.append(inv.name)
        db.commit()
        return results, None

    @staticmethod
    def low_stock_count():
        db = Database().conn()
        row = db.execute("SELECT COUNT(*) FROM inventory WHERE stock <= min_stock").fetchone()
        return row[0] if row else 0

    @staticmethod
    def low_stock_items():
        return Inventory.list(only_low=True)

    @staticmethod
    def consumption_last_7_days():
        db = Database().conn()
        cur = db.cursor()
        since = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d 00:00:00')
        cur.execute("""
            SELECT COALESCE(SUM(ABS(it.quantity)), 0) as total_used,
                   COALESCE(SUM(ABS(it.quantity) * it.unit_price), 0) as total_value
            FROM inventory_transactions it
            WHERE it.type IN ('出库','服务消耗') AND it.created_at >= ?
        """, (since,))
        row = cur.fetchone()
        return {'total_used': row[0] or 0, 'total_value': round(row[1] or 0, 2)}

    def to_dict(self):
        return {
            'id': self.id, 'name': self.name, 'category': self.category,
            'unit': self.unit, 'stock': self.stock, 'min_stock': self.min_stock,
            'unit_price': self.unit_price, 'notes': self.notes,
            'created_at': self.created_at,
            'is_low': self.stock <= self.min_stock
        }


class InventoryTransaction:
    def __init__(self, id=None, inventory_id=None, type='', quantity=0,
                 stock_after=0, unit_price=0.0, bill_id=None, note='',
                 created_at=None):
        self.id = id
        self.inventory_id = inventory_id
        self.type = type
        self.quantity = quantity
        self.stock_after = stock_after
        self.unit_price = unit_price
        self.bill_id = bill_id
        self.note = note
        self.created_at = created_at

    @staticmethod
    def add(data):
        db = Database().conn()
        cur = db.cursor()
        cur.execute("""
            INSERT INTO inventory_transactions(inventory_id,type,quantity,
                stock_after,unit_price,bill_id,note)
            VALUES(?,?,?,?,?,?,?)
        """, (
            data['inventory_id'], data['type'],
            int(data.get('quantity', 0)),
            int(data.get('stock_after', 0)),
            float(data.get('unit_price', 0)),
            data.get('bill_id'),
            data.get('note', '')
        ))
        db.commit()
        return cur.lastrowid

    @staticmethod
    def list_by_inventory(inv_id, limit=50):
        db = Database().conn()
        cur = db.cursor()
        cur.execute("""
            SELECT it.*, i.name as inv_name, i.unit as inv_unit
            FROM inventory_transactions it
            LEFT JOIN inventory i ON it.inventory_id = i.id
            WHERE it.inventory_id=? ORDER BY it.created_at DESC LIMIT ?
        """, (inv_id, limit))
        return [dict(r) for r in cur.fetchall()]


class ServiceInventoryLink:
    @staticmethod
    def list_by_service(service_id):
        db = Database().conn()
        cur = db.cursor()
        cur.execute("""
            SELECT sl.*, i.name as inv_name, i.unit as inv_unit, i.stock as inv_stock
            FROM service_inventory_links sl
            LEFT JOIN inventory i ON sl.inventory_id = i.id
            WHERE sl.service_id=?
        """, (service_id,))
        return [dict(r) for r in cur.fetchall()]

    @staticmethod
    def set_links(service_id, links):
        db = Database().conn()
        db.execute("DELETE FROM service_inventory_links WHERE service_id=?", (service_id,))
        for link in links:
            db.execute("""
                INSERT INTO service_inventory_links(service_id,inventory_id,quantity)
                VALUES(?,?,?)
            """, (service_id, link['inventory_id'], link.get('quantity', 1)))
        db.commit()

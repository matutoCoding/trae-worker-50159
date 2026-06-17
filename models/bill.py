import json
from .database import Database


class Bill:
    STATUS_UNPAID = 'unpaid'
    STATUS_PAID = 'paid'
    STATUS_REFUND = 'refund'

    def __init__(self, id=None, appointment_id=None, pet_id=None, service_id=None,
                 workstation_id=None, base_amount=0, discount_amount=0,
                 final_amount=0, price_capped=0, paid_status=STATUS_UNPAID,
                 paid_at=None, created_at=None,
                 overtime_minutes=0, overtime_fee=0,
                 weight_surcharge=0, species_surcharge=0,
                 extra_items_text='', extra_items_fee=0):
        self.id = id
        self.appointment_id = appointment_id
        self.pet_id = pet_id
        self.service_id = service_id
        self.workstation_id = workstation_id
        self.base_amount = base_amount
        self.discount_amount = discount_amount
        self.final_amount = final_amount
        self.price_capped = price_capped
        self.paid_status = paid_status
        self.paid_at = paid_at
        self.created_at = created_at
        self.overtime_minutes = overtime_minutes
        self.overtime_fee = overtime_fee
        self.weight_surcharge = weight_surcharge
        self.species_surcharge = species_surcharge
        self.extra_items_text = extra_items_text
        self.extra_items_fee = extra_items_fee

    @staticmethod
    def add(bill_data):
        db = Database().conn()
        cur = db.cursor()
        cur.execute(
            """INSERT INTO bills(appointment_id,pet_id,service_id,workstation_id,
               base_amount,discount_amount,final_amount,price_capped,paid_status,
               overtime_minutes,overtime_fee,weight_surcharge,species_surcharge,
               extra_items_text,extra_items_fee)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (bill_data['appointment_id'], bill_data['pet_id'], bill_data['service_id'],
             bill_data.get('workstation_id'), bill_data['base_amount'],
             bill_data.get('discount_amount', 0), bill_data['final_amount'],
             bill_data.get('price_capped', 0),
             bill_data.get('paid_status', Bill.STATUS_UNPAID),
             bill_data.get('overtime_minutes', 0),
             bill_data.get('overtime_fee', 0),
             bill_data.get('weight_surcharge', 0),
             bill_data.get('species_surcharge', 0),
             bill_data.get('extra_items_text', ''),
             bill_data.get('extra_items_fee', 0))
        )
        db.commit()
        return cur.lastrowid

    @staticmethod
    def mark_paid(bill_id):
        from datetime import datetime
        db = Database().conn()
        db.execute(
            "UPDATE bills SET paid_status=?, paid_at=? WHERE id=?",
            (Bill.STATUS_PAID, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), bill_id)
        )
        db.commit()

    @staticmethod
    def get(bill_id):
        db = Database().conn()
        row = db.execute("SELECT * FROM bills WHERE id=?", (bill_id,)).fetchone()
        if row:
            return Bill(**dict(row))
        return None

    @staticmethod
    def get_by_appointment(appt_id):
        db = Database().conn()
        row = db.execute("SELECT * FROM bills WHERE appointment_id=?", (appt_id,)).fetchone()
        if row:
            return Bill(**dict(row))
        return None

    @staticmethod
    def list(paid_status=None, date_from=None, date_to=None, keyword=None):
        db = Database().conn()
        cur = db.cursor()
        sql = """
            SELECT b.*, a.start_time, a.end_time,
                   p.name as pet_name, p.owner_name, p.owner_phone,
                   w.name as ws_name, s.name as service_name
            FROM bills b
            LEFT JOIN appointments a ON b.appointment_id = a.id
            LEFT JOIN pets p ON b.pet_id = p.id
            LEFT JOIN workstations w ON b.workstation_id = w.id
            LEFT JOIN services s ON b.service_id = s.id
            WHERE 1=1
        """
        params = []
        if paid_status:
            sql += " AND b.paid_status=?"
            params.append(paid_status)
        if date_from:
            sql += " AND date(b.created_at) >= date(?)"
            params.append(date_from)
        if date_to:
            sql += " AND date(b.created_at) <= date(?)"
            params.append(date_to)
        if keyword:
            sql += """ AND (p.name LIKE ? OR p.owner_name LIKE ? OR s.name LIKE ?)"""
            kw = f'%{keyword}%'
            params.extend([kw, kw, kw])
        sql += " ORDER BY b.created_at DESC LIMIT 200"
        cur.execute(sql, params)
        return [dict(r) for r in cur.fetchall()]

    @staticmethod
    def stats_summary(date_from=None, date_to=None):
        db = Database().conn()
        cur = db.cursor()
        sql = """
            SELECT COUNT(*) as bill_count,
                   COALESCE(SUM(CASE WHEN paid_status='paid' THEN final_amount ELSE 0 END), 0) as paid_total,
                   COALESCE(SUM(CASE WHEN paid_status='unpaid' THEN final_amount ELSE 0 END), 0) as unpaid_total,
                   COALESCE(SUM(final_amount), 0) as total_amount,
                   COALESCE(SUM(price_capped), 0) as cap_count
            FROM bills WHERE 1=1
        """
        params = []
        if date_from:
            sql += " AND date(created_at) >= date(?)"
            params.append(date_from)
        if date_to:
            sql += " AND date(created_at) <= date(?)"
            params.append(date_to)
        cur.execute(sql, params)
        row = cur.fetchone()
        result = dict(row) if row else {}
        for k in ['bill_count', 'paid_total', 'unpaid_total', 'total_amount', 'cap_count']:
            if result.get(k) is None:
                result[k] = 0
        return result

    @staticmethod
    def count_by_pet(pet_id):
        db = Database().conn()
        cur = db.cursor()
        cur.execute("SELECT COUNT(*) FROM bills WHERE pet_id=?", (pet_id,))
        return cur.fetchone()[0]

    @staticmethod
    def count_by_service(service_id):
        db = Database().conn()
        cur = db.cursor()
        cur.execute("SELECT COUNT(*) FROM bills WHERE service_id=?", (service_id,))
        return cur.fetchone()[0]

    def get_extra_items(self):
        if not self.extra_items_text:
            return {}
        try:
            return json.loads(self.extra_items_text)
        except (json.JSONDecodeError, TypeError):
            items = {}
            for line in self.extra_items_text.split('\n'):
                line = line.strip()
                if '=' in line:
                    k, v = line.rsplit('=', 1)
                    try:
                        items[k.strip()] = float(v.strip())
                    except ValueError:
                        pass
            return items

    def to_dict(self):
        return {
            'id': self.id, 'appointment_id': self.appointment_id,
            'pet_id': self.pet_id, 'service_id': self.service_id,
            'workstation_id': self.workstation_id,
            'base_amount': self.base_amount,
            'discount_amount': self.discount_amount,
            'final_amount': self.final_amount,
            'price_capped': self.price_capped,
            'paid_status': self.paid_status,
            'paid_at': self.paid_at, 'created_at': self.created_at,
            'overtime_minutes': self.overtime_minutes,
            'overtime_fee': self.overtime_fee,
            'weight_surcharge': self.weight_surcharge,
            'species_surcharge': self.species_surcharge,
            'extra_items_text': self.extra_items_text,
            'extra_items_fee': self.extra_items_fee
        }

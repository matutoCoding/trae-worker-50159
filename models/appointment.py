from datetime import datetime, timedelta
from .database import Database


class Appointment:
    STATUS_PENDING = 'pending'
    STATUS_CONFIRMED = 'confirmed'
    STATUS_COMPLETED = 'completed'
    STATUS_CANCELLED = 'cancelled'

    def __init__(self, id=None, pet_id=None, workstation_id=None, service_id=None,
                 start_time=None, end_time=None, status=STATUS_PENDING,
                 alloc_score=0.0, notes=None, created_at=None):
        self.id = id
        self.pet_id = pet_id
        self.workstation_id = workstation_id
        self.service_id = service_id
        self.start_time = start_time
        self.end_time = end_time
        self.status = status
        self.alloc_score = alloc_score
        self.notes = notes
        self.created_at = created_at

    @staticmethod
    def add(appt_data):
        db = Database().conn()
        cur = db.cursor()
        cur.execute(
            """INSERT INTO appointments(pet_id,workstation_id,service_id,start_time,end_time,status,alloc_score,notes)
               VALUES(?,?,?,?,?,?,?,?)""",
            (appt_data['pet_id'], appt_data.get('workstation_id'), appt_data['service_id'],
             appt_data['start_time'], appt_data['end_time'],
             appt_data.get('status', Appointment.STATUS_PENDING),
             appt_data.get('alloc_score', 0.0), appt_data.get('notes'))
        )
        db.commit()
        return cur.lastrowid

    @staticmethod
    def update(appt_id, appt_data):
        db = Database().conn()
        cur = db.cursor()
        fields, values = [], []
        for k, v in appt_data.items():
            fields.append(f"{k}=?")
            values.append(v)
        values.append(appt_id)
        cur.execute(f"UPDATE appointments SET {','.join(fields)} WHERE id=?", values)
        db.commit()

    @staticmethod
    def delete(appt_id):
        db = Database().conn()
        db.execute("DELETE FROM appointments WHERE id=?", (appt_id,))
        db.commit()

    @staticmethod
    def get(appt_id):
        db = Database().conn()
        row = db.execute("SELECT * FROM appointments WHERE id=?", (appt_id,)).fetchone()
        if row:
            return Appointment(**dict(row))
        return None

    @staticmethod
    def list_by_date(date_str, status=None):
        db = Database().conn()
        cur = db.cursor()
        sql = """
            SELECT a.*, p.name as pet_name, p.species as pet_species,
                   p.breed as pet_breed, p.owner_name, p.owner_phone,
                   w.name as ws_name, w.type as ws_type,
                   s.name as service_name, s.category as service_category,
                   s.duration, s.base_price, s.cap_price, s.is_package
            FROM appointments a
            LEFT JOIN pets p ON a.pet_id = p.id
            LEFT JOIN workstations w ON a.workstation_id = w.id
            LEFT JOIN services s ON a.service_id = s.id
            WHERE date(a.start_time) = date(?)
        """
        params = [date_str]
        if status:
            sql += " AND a.status=?"
            params.append(status)
        sql += " ORDER BY a.start_time ASC"
        cur.execute(sql, params)
        return [dict(r) for r in cur.fetchall()]

    @staticmethod
    def list_by_workstation(ws_id, start_date, end_date):
        db = Database().conn()
        cur = db.cursor()
        cur.execute(
            """SELECT * FROM appointments WHERE workstation_id=?
               AND date(start_time) BETWEEN date(?) AND date(?)
               AND status != 'cancelled'
               ORDER BY start_time ASC""",
            (ws_id, start_date, end_date)
        )
        return [Appointment(**dict(r)) for r in cur.fetchall()]

    @staticmethod
    def list_conflicting(ws_id, start_time, end_time, exclude_id=None):
        db = Database().conn()
        cur = db.cursor()
        sql = """SELECT * FROM appointments WHERE workstation_id=?
                 AND status != 'cancelled'
                 AND start_time < ? AND end_time > ?"""
        params = [ws_id, end_time, start_time]
        if exclude_id:
            sql += " AND id != ?"
            params.append(exclude_id)
        cur.execute(sql, params)
        return [Appointment(**dict(r)) for r in cur.fetchall()]

    @staticmethod
    def list(keyword=None):
        db = Database().conn()
        cur = db.cursor()
        sql = """
            SELECT a.*, p.name as pet_name, p.owner_name,
                   w.name as ws_name, s.name as service_name
            FROM appointments a
            LEFT JOIN pets p ON a.pet_id = p.id
            LEFT JOIN workstations w ON a.workstation_id = w.id
            LEFT JOIN services s ON a.service_id = s.id
        """
        params = []
        if keyword:
            sql += """ WHERE p.name LIKE ? OR p.owner_name LIKE ?
                        OR w.name LIKE ? OR s.name LIKE ?"""
            kw = f'%{keyword}%'
            params = [kw, kw, kw, kw]
        sql += " ORDER BY a.created_at DESC LIMIT 200"
        cur.execute(sql, params)
        return [dict(r) for r in cur.fetchall()]

    def to_dict(self):
        return {
            'id': self.id, 'pet_id': self.pet_id,
            'workstation_id': self.workstation_id,
            'service_id': self.service_id,
            'start_time': self.start_time, 'end_time': self.end_time,
            'status': self.status, 'alloc_score': self.alloc_score,
            'notes': self.notes, 'created_at': self.created_at
        }

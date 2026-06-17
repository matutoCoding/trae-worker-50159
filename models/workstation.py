from .database import Database


class Workstation:
    def __init__(self, id=None, name=None, type=None, capacity=1, equipment=None,
                 status='active', load_score=0.0):
        self.id = id
        self.name = name
        self.type = type
        self.capacity = capacity
        self.equipment = equipment
        self.status = status
        self.load_score = load_score

    @staticmethod
    def add(ws_data):
        db = Database().conn()
        cur = db.cursor()
        cur.execute(
            "INSERT INTO workstations(name,type,capacity,equipment,status,load_score) VALUES(?,?,?,?,?,?)",
            (ws_data['name'], ws_data['type'], ws_data.get('capacity', 1),
             ws_data.get('equipment'), ws_data.get('status', 'active'), 0.0)
        )
        db.commit()
        return cur.lastrowid

    @staticmethod
    def update(ws_id, ws_data):
        db = Database().conn()
        cur = db.cursor()
        cur.execute(
            "UPDATE workstations SET name=?,type=?,capacity=?,equipment=?,status=? WHERE id=?",
            (ws_data['name'], ws_data['type'], ws_data.get('capacity', 1),
             ws_data.get('equipment'), ws_data.get('status', 'active'), ws_id)
        )
        db.commit()

    @staticmethod
    def delete(ws_id):
        db = Database().conn()
        db.execute("DELETE FROM workstations WHERE id=?", (ws_id,))
        db.commit()

    @staticmethod
    def get(ws_id):
        db = Database().conn()
        row = db.execute("SELECT * FROM workstations WHERE id=?", (ws_id,)).fetchone()
        if row:
            return Workstation(**dict(row))
        return None

    @staticmethod
    def list(status=None, ws_type=None):
        db = Database().conn()
        cur = db.cursor()
        sql, params = "SELECT * FROM workstations WHERE 1=1", []
        if status:
            sql += " AND status=?"
            params.append(status)
        if ws_type:
            sql += " AND type=?"
            params.append(ws_type)
        sql += " ORDER BY load_score ASC, id ASC"
        cur.execute(sql, params)
        return [Workstation(**dict(r)) for r in cur.fetchall()]

    @staticmethod
    def update_load_score(ws_id, score):
        db = Database().conn()
        db.execute("UPDATE workstations SET load_score=? WHERE id=?", (score, ws_id))
        db.commit()

    def to_dict(self):
        return {
            'id': self.id, 'name': self.name, 'type': self.type,
            'capacity': self.capacity, 'equipment': self.equipment,
            'status': self.status, 'load_score': self.load_score
        }

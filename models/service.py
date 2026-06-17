from .database import Database


class Service:
    def __init__(self, id=None, name=None, category=None, duration=None,
                 base_price=None, cap_price=None, description=None, is_package=0):
        self.id = id
        self.name = name
        self.category = category
        self.duration = duration
        self.base_price = base_price
        self.cap_price = cap_price
        self.description = description
        self.is_package = is_package

    @staticmethod
    def add(svc_data):
        db = Database().conn()
        cur = db.cursor()
        cur.execute(
            """INSERT INTO services(name,category,duration,base_price,cap_price,description,is_package)
               VALUES(?,?,?,?,?,?,?)""",
            (svc_data['name'], svc_data['category'], svc_data['duration'],
             svc_data['base_price'], svc_data['cap_price'],
             svc_data.get('description'), svc_data.get('is_package', 0))
        )
        db.commit()
        return cur.lastrowid

    @staticmethod
    def update(svc_id, svc_data):
        db = Database().conn()
        cur = db.cursor()
        cur.execute(
            """UPDATE services SET name=?,category=?,duration=?,base_price=?,cap_price=?,description=?,is_package=?
               WHERE id=?""",
            (svc_data['name'], svc_data['category'], svc_data['duration'],
             svc_data['base_price'], svc_data['cap_price'],
             svc_data.get('description'), svc_data.get('is_package', 0), svc_id)
        )
        db.commit()

    @staticmethod
    def delete(svc_id):
        db = Database().conn()
        db.execute("DELETE FROM services WHERE id=?", (svc_id,))
        db.commit()

    @staticmethod
    def get(svc_id):
        db = Database().conn()
        row = db.execute("SELECT * FROM services WHERE id=?", (svc_id,)).fetchone()
        if row:
            return Service(**dict(row))
        return None

    @staticmethod
    def list(category=None, is_package=None):
        db = Database().conn()
        cur = db.cursor()
        sql, params = "SELECT * FROM services WHERE 1=1", []
        if category:
            sql += " AND category=?"
            params.append(category)
        if is_package is not None:
            sql += " AND is_package=?"
            params.append(1 if is_package else 0)
        sql += " ORDER BY is_package ASC, id ASC"
        cur.execute(sql, params)
        return [Service(**dict(r)) for r in cur.fetchall()]

    def to_dict(self):
        return {
            'id': self.id, 'name': self.name, 'category': self.category,
            'duration': self.duration, 'base_price': self.base_price,
            'cap_price': self.cap_price, 'description': self.description,
            'is_package': self.is_package
        }

from .database import Database


class Pet:
    def __init__(self, id=None, name=None, species=None, breed=None, weight=None,
                 age=None, owner_name=None, owner_phone=None, notes=None, created_at=None):
        self.id = id
        self.name = name
        self.species = species
        self.breed = breed
        self.weight = weight
        self.age = age
        self.owner_name = owner_name
        self.owner_phone = owner_phone
        self.notes = notes
        self.created_at = created_at

    @staticmethod
    def add(pet_data):
        db = Database().conn()
        cur = db.cursor()
        cur.execute(
            "INSERT INTO pets(name,species,breed,weight,age,owner_name,owner_phone,notes) VALUES(?,?,?,?,?,?,?,?)",
            (pet_data['name'], pet_data['species'], pet_data.get('breed'),
             pet_data.get('weight'), pet_data.get('age'),
             pet_data['owner_name'], pet_data['owner_phone'],
             pet_data.get('notes'))
        )
        db.commit()
        return cur.lastrowid

    @staticmethod
    def update(pet_id, pet_data):
        db = Database().conn()
        cur = db.cursor()
        cur.execute(
            """UPDATE pets SET name=?,species=?,breed=?,weight=?,age=?,owner_name=?,owner_phone=?,notes=? WHERE id=?""",
            (pet_data['name'], pet_data['species'], pet_data.get('breed'),
             pet_data.get('weight'), pet_data.get('age'),
             pet_data['owner_name'], pet_data['owner_phone'],
             pet_data.get('notes'), pet_id)
        )
        db.commit()

    @staticmethod
    def delete(pet_id):
        db = Database().conn()
        db.execute("DELETE FROM pets WHERE id=?", (pet_id,))
        db.commit()

    @staticmethod
    def get(pet_id):
        db = Database().conn()
        row = db.execute("SELECT * FROM pets WHERE id=?", (pet_id,)).fetchone()
        if row:
            return Pet(**dict(row))
        return None

    @staticmethod
    def list(keyword=None):
        db = Database().conn()
        cur = db.cursor()
        if keyword:
            cur.execute(
                "SELECT * FROM pets WHERE name LIKE ? OR owner_name LIKE ? OR owner_phone LIKE ? ORDER BY created_at DESC",
                (f'%{keyword}%', f'%{keyword}%', f'%{keyword}%')
            )
        else:
            cur.execute("SELECT * FROM pets ORDER BY created_at DESC")
        return [Pet(**dict(r)) for r in cur.fetchall()]

    def to_dict(self):
        return {
            'id': self.id, 'name': self.name, 'species': self.species,
            'breed': self.breed, 'weight': self.weight, 'age': self.age,
            'owner_name': self.owner_name, 'owner_phone': self.owner_phone,
            'notes': self.notes, 'created_at': self.created_at
        }

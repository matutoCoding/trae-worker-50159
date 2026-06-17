from .database import Database


class Member:
    LEVELS = ['普通', '银卡', '金卡', '钻石']

    def __init__(self, id=None, owner_name='', owner_phone='', level='普通',
                 balance=0.0, points=0, total_recharged=0.0, total_spent=0.0,
                 notes='', created_at=None):
        self.id = id
        self.owner_name = owner_name
        self.owner_phone = owner_phone
        self.level = level
        self.balance = float(balance or 0)
        self.points = int(points or 0)
        self.total_recharged = float(total_recharged or 0)
        self.total_spent = float(total_spent or 0)
        self.notes = notes
        self.created_at = created_at

    @staticmethod
    def list(keyword=None):
        db = Database().conn()
        cur = db.cursor()
        sql = "SELECT * FROM members WHERE 1=1"
        params = []
        if keyword:
            sql += " AND (owner_name LIKE ? OR owner_phone LIKE ?)"
            params = [f'%{keyword}%', f'%{keyword}%']
        sql += " ORDER BY created_at DESC"
        cur.execute(sql, params)
        return [Member(**dict(r)) for r in cur.fetchall()]

    @staticmethod
    def get(member_id):
        db = Database().conn()
        row = db.execute("SELECT * FROM members WHERE id=?", (member_id,)).fetchone()
        return Member(**dict(row)) if row else None

    @staticmethod
    def get_by_phone(phone):
        if not phone:
            return None
        db = Database().conn()
        row = db.execute("SELECT * FROM members WHERE owner_phone=?", (phone,)).fetchone()
        return Member(**dict(row)) if row else None

    @staticmethod
    def add(data):
        db = Database().conn()
        cur = db.cursor()
        cur.execute("""
            INSERT INTO members(owner_name,owner_phone,level,balance,points,
                                total_recharged,total_spent,notes)
            VALUES(?,?,?,?,?,?,?,?)
        """, (
            data['owner_name'], data['owner_phone'],
            data.get('level', '普通'),
            float(data.get('balance', 0)),
            int(data.get('points', 0)),
            float(data.get('total_recharged', 0)),
            float(data.get('total_spent', 0)),
            data.get('notes', '')
        ))
        db.commit()
        return cur.lastrowid

    @staticmethod
    def update(member_id, data):
        db = Database().conn()
        fields, values = [], []
        allowed = ['owner_name', 'owner_phone', 'level', 'balance', 'points',
                   'total_recharged', 'total_spent', 'notes']
        for k in allowed:
            if k in data:
                fields.append(f"{k}=?")
                values.append(data[k])
        if not fields:
            return
        values.append(member_id)
        db.execute(f"UPDATE members SET {', '.join(fields)} WHERE id=?", values)
        db.commit()

    @staticmethod
    def recharge(member_id, amount, note=''):
        if amount <= 0:
            return None, '充值金额必须大于0'
        db = Database().conn()
        member = Member.get(member_id)
        if not member:
            return None, '会员不存在'
        new_balance = round(member.balance + amount, 2)
        new_total = round(member.total_recharged + amount, 2)
        db.execute("UPDATE members SET balance=?, total_recharged=? WHERE id=?",
                   (new_balance, new_total, member_id))
        tx_id = MemberTransaction.add({
            'member_id': member_id,
            'type': 'recharge',
            'amount': amount,
            'points_delta': 0,
            'balance_after': new_balance,
            'points_after': member.points,
            'note': note or f'充值¥{amount:.2f}'
        })
        db.commit()
        return Member.get(member_id), None

    @staticmethod
    def consume(member_id, amount, points_award=0, bill_id=None, note=''):
        if amount < 0:
            return None, '消费金额不能为负'
        db = Database().conn()
        member = Member.get(member_id)
        if not member:
            return None, '会员不存在'
        if amount > 0 and member.balance + 0.01 < amount:
            return None, f'余额不足，当前余额¥{member.balance:.2f}'
        new_balance = round(member.balance - amount, 2)
        new_points = member.points + int(points_award or 0)
        new_spent = round(member.total_spent + amount, 2)
        db.execute("UPDATE members SET balance=?, points=?, total_spent=? WHERE id=?",
                   (new_balance, new_points, new_spent, member_id))
        tx_id = MemberTransaction.add({
            'member_id': member_id,
            'type': 'consume',
            'amount': -abs(amount) if amount > 0 else 0,
            'points_delta': int(points_award or 0),
            'balance_after': new_balance,
            'points_after': new_points,
            'bill_id': bill_id,
            'note': note or (f'消费¥{amount:.2f}' if amount > 0 else '积分赠送')
        })
        db.commit()
        return Member.get(member_id), None

    @staticmethod
    def award_points(member_id, points, bill_id=None, note=''):
        if points <= 0:
            return None, '赠送积分必须大于0'
        db = Database().conn()
        member = Member.get(member_id)
        if not member:
            return None, '会员不存在'
        new_points = member.points + int(points)
        db.execute("UPDATE members SET points=? WHERE id=?",
                   (new_points, member_id))
        MemberTransaction.add({
            'member_id': member_id,
            'type': 'award',
            'amount': 0,
            'points_delta': int(points),
            'balance_after': member.balance,
            'points_after': new_points,
            'bill_id': bill_id,
            'note': note or f'赠送{points}积分'
        })
        db.commit()
        return Member.get(member_id), None

    @staticmethod
    def count():
        db = Database().conn()
        row = db.execute("SELECT COUNT(*) FROM members").fetchone()
        return row[0] if row else 0

    @staticmethod
    def delete(member_id):
        db = Database().conn()
        db.execute("DELETE FROM member_transactions WHERE member_id=?", (member_id,))
        db.execute("DELETE FROM members WHERE id=?", (member_id,))
        db.commit()

    @staticmethod
    def total_balance():
        db = Database().conn()
        row = db.execute("SELECT COALESCE(SUM(balance),0) FROM members").fetchone()
        return row[0] if row else 0

    @staticmethod
    def count_pets(member_id):
        db = Database().conn()
        row = db.execute("SELECT COUNT(*) FROM pets WHERE member_id=?", (member_id,)).fetchone()
        return row[0] if row else 0

    @staticmethod
    def count_bills(member_id):
        db = Database().conn()
        row = db.execute("SELECT COUNT(*) FROM bills WHERE member_id=?", (member_id,)).fetchone()
        return row[0] if row else 0

    def to_dict(self):
        return {
            'id': self.id, 'owner_name': self.owner_name,
            'owner_phone': self.owner_phone, 'level': self.level,
            'balance': self.balance, 'points': self.points,
            'total_recharged': self.total_recharged,
            'total_spent': self.total_spent,
            'notes': self.notes, 'created_at': self.created_at
        }


class MemberTransaction:
    def __init__(self, id=None, member_id=None, type='', amount=0, points_delta=0,
                 balance_after=0, points_after=0, bill_id=None, note='',
                 created_at=None):
        self.id = id
        self.member_id = member_id
        self.type_ = type
        self.amount = amount
        self.points_delta = points_delta
        self.balance_after = balance_after
        self.points_after = points_after
        self.bill_id = bill_id
        self.note = note
        self.created_at = created_at

    @staticmethod
    def add(data):
        db = Database().conn()
        cur = db.cursor()
        cur.execute("""
            INSERT INTO member_transactions(member_id,type,amount,points,
                balance_after,points_after,bill_id,note)
            VALUES(?,?,?,?,?,?,?,?)
        """, (
            data['member_id'], data['type'],
            float(data.get('amount', 0)),
            int(data.get('points_delta', 0)),
            float(data.get('balance_after', 0)),
            int(data.get('points_after', 0)),
            data.get('bill_id'),
            data.get('note', '')
        ))
        db.commit()
        return cur.lastrowid

    @staticmethod
    def list_by_member(member_id, limit=50):
        db = Database().conn()
        cur = db.cursor()
        cur.execute("""
            SELECT * FROM member_transactions
            WHERE member_id=? ORDER BY created_at DESC LIMIT ?
        """, (member_id, limit))
        rows = cur.fetchall()
        results = []
        for r in rows:
            d = dict(r)
            results.append(MemberTransaction(
                id=d.get('id'),
                member_id=d.get('member_id'),
                type=d.get('type', ''),
                amount=d.get('amount', 0),
                points_delta=d.get('points', 0),
                balance_after=d.get('balance_after', 0),
                points_after=d.get('points_after', 0),
                bill_id=d.get('bill_id'),
                note=d.get('note', ''),
                created_at=d.get('created_at')
            ))
        return results

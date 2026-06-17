import sqlite3
import os
from datetime import datetime


class Database:
    _instance = None
    _conn = None

    def __new__(cls, db_path=None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            if db_path is None:
                db_path = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    'petshop.db'
                )
            cls._conn = sqlite3.connect(db_path)
            cls._conn.row_factory = sqlite3.Row
            cls._conn.execute("PRAGMA foreign_keys = ON")
            cls._instance._init_tables()
            cls._instance._migrate()
            cls._instance._seed_data()
        return cls._instance

    def _init_tables(self):
        cur = self._conn.cursor()
        cur.executescript('''
            CREATE TABLE IF NOT EXISTS pets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                species TEXT NOT NULL,
                breed TEXT,
                weight REAL,
                age INTEGER,
                owner_name TEXT NOT NULL,
                owner_phone TEXT NOT NULL,
                notes TEXT,
                member_id INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (member_id) REFERENCES members(id)
            );

            CREATE TABLE IF NOT EXISTS workstations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                type TEXT NOT NULL,
                capacity INTEGER DEFAULT 1,
                equipment TEXT,
                status TEXT DEFAULT 'active',
                load_score REAL DEFAULT 0.0
            );

            CREATE TABLE IF NOT EXISTS services (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                duration INTEGER NOT NULL,
                base_price REAL NOT NULL,
                cap_price REAL NOT NULL,
                description TEXT,
                is_package INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pet_id INTEGER NOT NULL,
                workstation_id INTEGER,
                service_id INTEGER NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                alloc_score REAL DEFAULT 0.0,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (pet_id) REFERENCES pets(id),
                FOREIGN KEY (workstation_id) REFERENCES workstations(id),
                FOREIGN KEY (service_id) REFERENCES services(id)
            );

            CREATE TABLE IF NOT EXISTS bills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                appointment_id INTEGER NOT NULL UNIQUE,
                pet_id INTEGER NOT NULL,
                service_id INTEGER NOT NULL,
                workstation_id INTEGER,
                base_amount REAL NOT NULL,
                discount_amount REAL DEFAULT 0,
                final_amount REAL NOT NULL,
                price_capped INTEGER DEFAULT 0,
                paid_status TEXT DEFAULT 'unpaid',
                paid_at TEXT,
                member_id INTEGER,
                balance_used REAL DEFAULT 0,
                points_awarded INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                overtime_minutes INTEGER DEFAULT 0,
                overtime_fee REAL DEFAULT 0,
                weight_surcharge REAL DEFAULT 0,
                species_surcharge REAL DEFAULT 0,
                extra_items_text TEXT DEFAULT '',
                extra_items_fee REAL DEFAULT 0,
                FOREIGN KEY (appointment_id) REFERENCES appointments(id),
                FOREIGN KEY (pet_id) REFERENCES pets(id),
                FOREIGN KEY (service_id) REFERENCES services(id),
                FOREIGN KEY (workstation_id) REFERENCES workstations(id),
                FOREIGN KEY (member_id) REFERENCES members(id)
            );

            CREATE TABLE IF NOT EXISTS members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_name TEXT NOT NULL,
                owner_phone TEXT NOT NULL UNIQUE,
                level TEXT DEFAULT '普通',
                balance REAL DEFAULT 0,
                points INTEGER DEFAULT 0,
                total_recharged REAL DEFAULT 0,
                total_spent REAL DEFAULT 0,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS member_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                member_id INTEGER NOT NULL,
                type TEXT NOT NULL,
                amount REAL DEFAULT 0,
                points INTEGER DEFAULT 0,
                balance_after REAL DEFAULT 0,
                points_after INTEGER DEFAULT 0,
                bill_id INTEGER,
                note TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (member_id) REFERENCES members(id),
                FOREIGN KEY (bill_id) REFERENCES bills(id)
            );

            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT,
                unit TEXT DEFAULT '份',
                stock INTEGER DEFAULT 0,
                min_stock INTEGER DEFAULT 0,
                unit_price REAL DEFAULT 0,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS inventory_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                inventory_id INTEGER NOT NULL,
                type TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                stock_after INTEGER DEFAULT 0,
                unit_price REAL DEFAULT 0,
                bill_id INTEGER,
                note TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (inventory_id) REFERENCES inventory(id),
                FOREIGN KEY (bill_id) REFERENCES bills(id)
            );

            CREATE TABLE IF NOT EXISTS service_inventory_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                service_id INTEGER NOT NULL,
                inventory_id INTEGER NOT NULL,
                quantity INTEGER DEFAULT 1,
                FOREIGN KEY (service_id) REFERENCES services(id),
                FOREIGN KEY (inventory_id) REFERENCES inventory(id)
            );

            CREATE INDEX IF NOT EXISTS idx_appts_ws_time ON appointments(workstation_id, start_time, end_time);
            CREATE INDEX IF NOT EXISTS idx_appts_status ON appointments(status);
            CREATE INDEX IF NOT EXISTS idx_bills_paid ON bills(paid_status);
            CREATE INDEX IF NOT EXISTS idx_members_phone ON members(owner_phone);
            CREATE INDEX IF NOT EXISTS idx_member_tx_member ON member_transactions(member_id);
            CREATE INDEX IF NOT EXISTS idx_inv_low ON inventory(stock, min_stock);
            CREATE INDEX IF NOT EXISTS idx_inv_tx_inv ON inventory_transactions(inventory_id);
        ''')
        self._conn.commit()

    def _migrate(self):
        cur = self._conn.cursor()

        cur.execute("PRAGMA user_version")
        current_version = cur.fetchone()[0]

        if current_version < 1:
            cur.execute("PRAGMA table_info(bills)")
            columns = [col[1] for col in cur.fetchall()]
            migrations = [
                ('overtime_minutes', 'INTEGER DEFAULT 0'),
                ('overtime_fee', 'REAL DEFAULT 0'),
                ('weight_surcharge', 'REAL DEFAULT 0'),
                ('species_surcharge', 'REAL DEFAULT 0'),
                ('extra_items_text', "TEXT DEFAULT ''"),
                ('extra_items_fee', 'REAL DEFAULT 0'),
            ]
            for col_name, col_def in migrations:
                if col_name not in columns:
                    try:
                        cur.execute(f"ALTER TABLE bills ADD COLUMN {col_name} {col_def}")
                        print(f"[迁移 v1] bills 表新增字段: {col_name}")
                    except sqlite3.OperationalError:
                        pass

            cur.execute("PRAGMA user_version = 1")
            current_version = 1
            print("[迁移] 数据库版本已升级到 v1")

        if current_version < 2:
            cur.execute("PRAGMA table_info(pets)")
            pet_columns = [col[1] for col in cur.fetchall()]
            if 'member_id' not in pet_columns:
                try:
                    cur.execute("ALTER TABLE pets ADD COLUMN member_id INTEGER REFERENCES members(id)")
                    print("[迁移 v2] pets 表新增字段: member_id")
                except sqlite3.OperationalError:
                    pass

            cur.execute("PRAGMA table_info(bills)")
            bill_columns = [col[1] for col in cur.fetchall()]
            for col_name, col_def in [
                ('member_id', 'INTEGER REFERENCES members(id)'),
                ('balance_used', 'REAL DEFAULT 0'),
                ('points_awarded', 'INTEGER DEFAULT 0'),
            ]:
                if col_name not in bill_columns:
                    try:
                        cur.execute(f"ALTER TABLE bills ADD COLUMN {col_name} {col_def}")
                        print(f"[迁移 v2] bills 表新增字段: {col_name}")
                    except sqlite3.OperationalError:
                        pass

            new_tables = [
                ("members", """
                    CREATE TABLE IF NOT EXISTS members (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        owner_name TEXT NOT NULL,
                        owner_phone TEXT NOT NULL UNIQUE,
                        level TEXT DEFAULT '普通',
                        balance REAL DEFAULT 0,
                        points INTEGER DEFAULT 0,
                        total_recharged REAL DEFAULT 0,
                        total_spent REAL DEFAULT 0,
                        notes TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """),
                ("member_transactions", """
                    CREATE TABLE IF NOT EXISTS member_transactions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        member_id INTEGER NOT NULL,
                        type TEXT NOT NULL,
                        amount REAL DEFAULT 0,
                        points INTEGER DEFAULT 0,
                        balance_after REAL DEFAULT 0,
                        points_after INTEGER DEFAULT 0,
                        bill_id INTEGER,
                        note TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (member_id) REFERENCES members(id),
                        FOREIGN KEY (bill_id) REFERENCES bills(id)
                    )
                """),
                ("inventory", """
                    CREATE TABLE IF NOT EXISTS inventory (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        category TEXT,
                        unit TEXT DEFAULT '份',
                        stock INTEGER DEFAULT 0,
                        min_stock INTEGER DEFAULT 0,
                        unit_price REAL DEFAULT 0,
                        notes TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """),
                ("inventory_transactions", """
                    CREATE TABLE IF NOT EXISTS inventory_transactions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        inventory_id INTEGER NOT NULL,
                        type TEXT NOT NULL,
                        quantity INTEGER NOT NULL,
                        stock_after INTEGER DEFAULT 0,
                        unit_price REAL DEFAULT 0,
                        bill_id INTEGER,
                        note TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (inventory_id) REFERENCES inventory(id),
                        FOREIGN KEY (bill_id) REFERENCES bills(id)
                    )
                """),
                ("service_inventory_links", """
                    CREATE TABLE IF NOT EXISTS service_inventory_links (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        service_id INTEGER NOT NULL,
                        inventory_id INTEGER NOT NULL,
                        quantity INTEGER DEFAULT 1,
                        FOREIGN KEY (service_id) REFERENCES services(id),
                        FOREIGN KEY (inventory_id) REFERENCES inventory(id)
                    )
                """),
            ]
            for tname, tsql in new_tables:
                try:
                    cur.execute(tsql)
                    print(f"[迁移 v2] 新建表: {tname}")
                except sqlite3.OperationalError as e:
                    print(f"[迁移 v2] 表 {tname} 已存在: {e}")

            new_indexes = [
                ("idx_members_phone", "members", "CREATE INDEX IF NOT EXISTS idx_members_phone ON members(owner_phone)"),
                ("idx_member_tx_member", "member_transactions", "CREATE INDEX IF NOT EXISTS idx_member_tx_member ON member_transactions(member_id)"),
                ("idx_inv_low", "inventory", "CREATE INDEX IF NOT EXISTS idx_inv_low ON inventory(stock, min_stock)"),
                ("idx_inv_tx_inv", "inventory_transactions", "CREATE INDEX IF NOT EXISTS idx_inv_tx_inv ON inventory_transactions(inventory_id)"),
            ]
            for iname, _, isql in new_indexes:
                try:
                    cur.execute(isql)
                    print(f"[迁移 v2] 新建索引: {iname}")
                except sqlite3.OperationalError:
                    pass

            cur.execute("PRAGMA user_version = 2")
            print("[迁移] 数据库版本已升级到 v2")

        self._conn.commit()

    def _seed_data(self):
        cur = self._conn.cursor()
        cur.execute("SELECT COUNT(*) FROM workstations")
        if cur.fetchone()[0] == 0:
            workstations = [
                ('A1-美容台', '标准美容', 1, '升降台,吹水机', 0),
                ('A2-美容台', '标准美容', 1, '升降台,吹水机', 0),
                ('A3-美容台', '标准美容', 1, '升降台,吹水机,专用剪刀', 0),
                ('B1-SPA间', 'SPA护理', 2, '浴缸,臭氧机,烘干机', 0),
                ('B2-SPA间', 'SPA护理', 2, '浴缸,臭氧机,烘干机', 0),
                ('C1-医疗美容', '特殊美容', 1, '医疗级设备,保定笼', 0),
            ]
            cur.executemany(
                "INSERT INTO workstations(name,type,capacity,equipment,load_score) VALUES(?,?,?,?,?)",
                workstations
            )

        cur.execute("SELECT COUNT(*) FROM services")
        if cur.fetchone()[0] == 0:
            services = [
                ('基础洗澡', '清洁类', 45, 68.0, 88.0, '包含洗澡+吹干+基础护理', 0),
                ('深度清洁浴', '清洁类', 60, 98.0, 138.0, '药浴+深度清洁+护毛素', 0),
                ('造型修剪', '修剪类', 90, 158.0, 228.0, '全身造型修剪', 0),
                ('局部修剪', '修剪类', 30, 58.0, 58.0, '脚毛/腹毛/脸部局部修剪', 0),
                ('SPA精油护理', 'SPA类', 60, 188.0, 268.0, '精油按摩+护理', 0),
                ('药浴治疗', '医疗类', 75, 168.0, 258.0, '皮肤病药浴治疗', 0),
                ('幼犬套餐', '套餐', 120, 288.0, 288.0, '洗澡+修剪+SPA全套', 1),
                ('尊享全套', '套餐', 180, 398.0, 398.0, '全套清洁+造型+SPA+护理', 1),
            ]
            cur.executemany(
                "INSERT INTO services(name,category,duration,base_price,cap_price,description,is_package) VALUES(?,?,?,?,?,?,?)",
                services
            )

        cur.execute("SELECT COUNT(*) FROM pets")
        if cur.fetchone()[0] == 0:
            pets = [
                ('豆豆', '犬', '金毛', 28.5, 3, '张三', '13800138001', '性格温顺'),
                ('咪咪', '猫', '英短蓝猫', 4.2, 2, '李四', '13800138002', '怕生人需安静环境'),
                ('旺财', '犬', '柯基', 12.0, 5, '王五', '13800138003', '活泼好动'),
                ('雪球', '犬', '比熊', 5.8, 4, '赵六', '13800138004', '毛发易打结'),
            ]
            cur.executemany(
                "INSERT INTO pets(name,species,breed,weight,age,owner_name,owner_phone,notes) VALUES(?,?,?,?,?,?,?,?)",
                pets
            )

        cur.execute("SELECT COUNT(*) FROM members")
        if cur.fetchone()[0] == 0:
            members = [
                ('张三', '13800138001', '银卡', 500.0, 380, 1000.0, 620.0, '长期老客户'),
                ('李四', '13800138002', '金卡', 1200.0, 1260, 2000.0, 1840.0, '每周固定来'),
            ]
            cur.executemany(
                "INSERT INTO members(owner_name,owner_phone,level,balance,points,total_recharged,total_spent,notes) VALUES(?,?,?,?,?,?,?,?)",
                members
            )
            cur.execute("UPDATE pets SET member_id=1 WHERE owner_phone='13800138001'")
            cur.execute("UPDATE pets SET member_id=2 WHERE owner_phone='13800138002'")

        cur.execute("SELECT COUNT(*) FROM inventory")
        if cur.fetchone()[0] == 0:
            inventory = [
                ('宠物沐浴露', '洗护耗材', '瓶', 50, 10, 45.0, '通用型'),
                ('护毛素', '洗护耗材', '瓶', 30, 5, 60.0, ''),
                ('药浴液', '医疗耗材', '瓶', 20, 5, 120.0, '皮肤病专用'),
                ('SPA精油', 'SPA耗材', '瓶', 15, 3, 180.0, '进口精油'),
                ('指甲钳刀片', '工具耗材', '片', 100, 20, 5.0, ''),
                ('棉签', '清洁耗材', '包', 200, 50, 2.0, ''),
                ('美容围脖', '防护耗材', '个', 5, 2, 8.0, '低库存示例'),
            ]
            cur.executemany(
                "INSERT INTO inventory(name,category,unit,stock,min_stock,unit_price,notes) VALUES(?,?,?,?,?,?,?)",
                inventory
            )
            cur.execute("SELECT id FROM services WHERE name='深度清洁浴'")
            row = cur.fetchone()
            svc_bath = row[0] if row else 2
            cur.execute("SELECT id FROM services WHERE name='SPA精油护理'")
            row = cur.fetchone()
            svc_spa = row[0] if row else 5
            cur.execute("SELECT id FROM services WHERE name='药浴治疗'")
            row = cur.fetchone()
            svc_med = row[0] if row else 6
            links = [
                (svc_bath, 1, 1),
                (svc_bath, 2, 1),
                (svc_spa, 4, 1),
                (svc_med, 3, 1),
            ]
            cur.executemany(
                "INSERT INTO service_inventory_links(service_id,inventory_id,quantity) VALUES(?,?,?)",
                links
            )

        self._conn.commit()

    def conn(self):
        return self._conn

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None


def reset_db():
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'petshop.db')
    db_path = os.path.abspath(db_path)
    try:
        if Database._instance:
            Database._instance.close()
        Database._instance = None
        Database._conn = None
        if os.path.exists(db_path):
            os.remove(db_path)
    except Exception as e:
        print(f'[reset_db] warning: {e}')

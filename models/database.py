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
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
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
                FOREIGN KEY (workstation_id) REFERENCES workstations(id)
            );

            CREATE INDEX IF NOT EXISTS idx_appts_ws_time ON appointments(workstation_id, start_time, end_time);
            CREATE INDEX IF NOT EXISTS idx_appts_status ON appointments(status);
            CREATE INDEX IF NOT EXISTS idx_bills_paid ON bills(paid_status);
        ''')
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
        self._conn.commit()

    def conn(self):
        return self._conn

    def close(self):
        if self._conn:
            self._conn.close()

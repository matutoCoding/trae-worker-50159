import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import reset_db
reset_db()

from models import Member, Pet, Inventory, ServiceInventoryLink
from models.inventory import ServiceInventoryLink
from modules import BillingEngine, BackupManager

print('='*60)
print('宠物店 - 会员/库存/备份 专项测试')
print('='*60)

# 1. 会员系统测试
print('\n[1] 会员系统测试')
m1_id = Member.add({'owner_name': '王小明', 'owner_phone': '13800138000',
                     'level': '金卡', 'balance': 500.0, 'points': 200})
m1 = Member.get(m1_id)
print(f'  ✅ 创建会员: {m1.owner_name} {m1.level} 余额¥{m1.balance}')
m2, err = Member.recharge(m1.id, 200, note='充200送20活动')
assert m2.balance == 700, f'充值后余额应为700，实际{m2.balance}'
print(f'  ✅ 充值200: 余额¥{m2.balance}')
m3, err = Member.consume(m1.id, 150, points_award=50, note='测试消费')
assert m3.balance == 550, f'消费后余额应为550，实际{m3.balance}'
assert m3.points == 250, f'消费后积分应为250，实际{m3.points}'
print(f'  ✅ 消费150赠50积分: 余额¥{m3.balance} 积分{m3.points}')
assert Member.count() >= 2, f'会员数应该>=2(含种子)，实际{Member.count()}'
total = Member.total_balance()
print(f'  ✅ 会员统计: {Member.count()}名 储值合计¥{total:.2f}')

# 2. 库存系统测试
print('\n[2] 库存系统测试')
inv_count_before = len(Inventory.list())
print(f'  初始耗材: {inv_count_before} 种')
inv_id1 = Inventory.add({'name': '测试梳子', 'category': '工具', 'unit': '把',
                          'stock': 5, 'min_stock': 3, 'unit_price': 25.0})
inv1 = Inventory.get(inv_id1)
print(f'  ✅ 新增耗材: {inv1.name} 库存{inv1.stock}')
inv2, err = Inventory.stock_in(inv_id1, 10, note='进货10把')
assert inv2.stock == 15, f'入库后库存应为15，实际{inv2.stock}'
print(f'  ✅ 入库10把: 库存{inv2.stock}')
inv3, err = Inventory.stock_out(inv_id1, 4, note='盘点损耗')
assert inv3.stock == 11, f'出库后库存应为11，实际{inv3.stock}'
print(f'  ✅ 出库4把: 库存{inv3.stock}')
low_items = Inventory.low_stock_items()
print(f'  低库存预警: {len(low_items)} 项')
low_count = Inventory.low_stock_count()
assert low_count == len(low_items)
print(f'  ✅ 低库存统计: {low_count} 项')

# 3. 服务-耗材关联与自动扣库
print('\n[3] 服务耗材关联与开单扣库测试')
from models import Service, Appointment, Workstation
services = Service.list()
service = services[0]
print(f'  服务项目: {service.name}')
ServiceInventoryLink.set_links(service.id, [
    {'inventory_id': inv_id1, 'quantity': 1}
])
links = ServiceInventoryLink.list_by_service(service.id)
print(f'  ✅ 设置关联: {len(links)} 项耗材')
ok, warns = Inventory.check_service_inventory(service.id)
assert ok, f'库存应该足够，实际warns={warns}'
print(f'  ✅ 库存预检: 充足')
# 直接 UPDATE 数据库把库存改少，避免通过 stock_out 触发安全检查
from models import Database
db = Database().conn()
db.execute("UPDATE inventory SET stock=0 WHERE id=?", (inv_id1,))
db.commit()
inv_empty = Inventory.get(inv_id1)
print(f'  已将库存清零: {inv_empty.stock}')
ok, warns = Inventory.check_service_inventory(service.id)
assert not ok, f'库存不足应该检测到'
print(f'  ✅ 低库存预检: 不足提示正确: {warns}')
# 恢复库存
db.execute("UPDATE inventory SET stock=11 WHERE id=?", (inv_id1,))
db.commit()

# 4. 数据备份测试
print('\n[4] 数据备份与恢复测试')
before = BackupManager.list_backups()
print(f'  备份列表初始: {len(before)} 个')
bk, err = BackupManager.create_backup()
assert bk is not None, f'备份失败: {err}'
print(f'  ✅ 创建备份: {bk["filename"]} ({bk["size_kb"]}KB)')
after = BackupManager.list_backups()
assert len(after) == len(before) + 1, '备份数应该+1'
print(f'  ✅ 备份列表: {len(after)} 个')
print(f'  备份目录: {BackupManager.backup_dir()}')

# 5. Dashboard统计测试
print('\n[5] Dashboard统计测试')
stats = BillingEngine.get_dashboard_stats()
print(f'  会员数: {stats.get("member_count")}')
print(f'  储值合计: ¥{stats.get("member_total_balance", 0):.2f}')
print(f'  低库存: {stats.get("low_stock_count")} 项')
print(f'  近7天耗材消耗: {stats.get("inv_consumed_7d")} 件 / ¥{stats.get("inv_consumed_value_7d", 0):.2f}')
print(f'  低库存明细: {len(stats.get("low_stock_items", []))} 项')
assert 'member_count' in stats and 'member_total_balance' in stats
assert 'low_stock_count' in stats and 'inv_consumed_7d' in stats
print('  ✅ Dashboard 统计字段完整')

print('\n' + '='*60)
print('🎉 全部测试通过！')
print('='*60)

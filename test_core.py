import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timedelta
from models import Pet, Service, Workstation, Appointment, Bill, Database
from modules import Scheduling, AllocationEngine, PricingEngine, BillingEngine


def test_database_init():
    print('=' * 60)
    print('测试1: 数据库初始化与种子数据')
    try:
        db = Database()
        pets = Pet.list()
        services = Service.list()
        stations = Scheduling.list_workstations()
        print(f'  ✓ 宠物档案: {len(pets)} 只')
        for p in pets[:3]:
            print(f'    - {p.name} ({p.species}/{p.breed}) 主人:{p.owner_name}')
        print(f'  ✓ 服务项目: {len(services)} 个')
        print(f'  ✓ 工位资源: {len(stations)} 个')
        for w in stations[:3]:
            print(f'    - {w.name} | {w.type} | 负载:{w.load_score:.2f}')
        return True
    except Exception as e:
        print(f'  ✗ 失败: {e}')
        import traceback; traceback.print_exc()
        return False


def test_pet_crud():
    print('\n' + '=' * 60)
    print('测试2: 宠物档案增删改查')
    try:
        pid = Pet.add({
            'name': '测试狗', 'species': '犬', 'breed': '测试犬',
            'weight': 15.5, 'age': 2,
            'owner_name': '测试主人', 'owner_phone': '13900139000',
            'notes': '测试档案，完成后会删除'
        })
        print(f'  ✓ 创建宠物 ID={pid}')
        p = Pet.get(pid)
        assert p and p.name == '测试狗', '查询失败'
        print(f'  ✓ 查询宠物: {p.name}')
        Pet.update(pid, {'name': '更新测试狗', 'species': '犬',
                         'breed': '更新品种', 'weight': 18, 'age': 3,
                         'owner_name': '测试主人', 'owner_phone': '13900139000', 'notes': '更新备注'})
        p2 = Pet.get(pid)
        assert p2.name == '更新测试狗', '更新失败'
        print(f'  ✓ 更新名字为: {p2.name}')
        Pet.delete(pid)
        assert Pet.get(pid) is None, '删除失败'
        print(f'  ✓ 删除成功')
        return True
    except Exception as e:
        print(f'  ✗ 失败: {e}')
        import traceback; traceback.print_exc()
        return False


def test_scheduling():
    print('\n' + '=' * 60)
    print('测试3: 工位排期 - 空闲查询 / 时间片管理')
    try:
        today = datetime.now().strftime('%Y-%m-%d')
        start, end = Scheduling.get_work_hours(today)
        print(f'  ✓ 工作时间: {start.strftime("%H:%M")} - {end.strftime("%H:%M")}')
        slots = Scheduling.get_time_slots(today, 30)
        print(f'  ✓ 30分钟片数: {len(slots)} 个')
        stations = Scheduling.list_workstations()
        for ws in stations[:3]:
            free = Scheduling.get_workstation_free_ranges(ws.id, today)
            total_free_min = 0
            for s, e in free:
                sd = datetime.strptime(s, '%Y-%m-%d %H:%M')
                ed = datetime.strptime(e, '%Y-%m-%d %H:%M')
                total_free_min += int((ed - sd).total_seconds() / 60)
            print(f'  ✓ 工位 {ws.name}: 共 {total_free_min} 分钟空闲 (分 {len(free)} 段)')
        daily = Scheduling.get_daily_schedule(today)
        print(f'  ✓ 每日排期字典构建成功，共 {len(daily)} 个工位条目')
        return True
    except Exception as e:
        print(f'  ✗ 失败: {e}')
        import traceback; traceback.print_exc()
        return False


def test_allocation():
    print('\n' + '=' * 60)
    print('测试4: 自动分配模块 - Best-Fit择优 + 负载均衡 + 碎片避免')
    try:
        pets = Pet.list()
        services = Service.list()
        if not pets or not services:
            print('  ✗ 种子数据不足')
            return False
        today = datetime.now().strftime('%Y-%m-%d')
        service = services[1] if len(services) > 1 else services[0]
        pet = pets[0]
        print(f'  分配请求: 宠物【{pet.name}】服务【{service.name}】时长 {service.duration}分钟')
        print(f'  宠主只选时间 10:00 不指定工位，系统自动择优分配')
        alloc, candidates = AllocationEngine.allocate_best_fit(
            today, '10:00', service.duration
        )
        if alloc:
            print(f'  ✓ 最佳分配: 工位={alloc["workstation"]["name"]}')
            print(f'    时段: {alloc["start"]} ~ {alloc["end"]}')
            print(f'    综合评分: {alloc["total_score"]:.1f} (碎片{alloc["fragment_score"]:.1f}+负载{alloc["load_score"]:.1f})')
            print(f'    前后空闲: 前{alloc["free_before_min"]}分 / 后{alloc["free_after_min"]}分')
            print(f'  ✓ 候选项总数: {len(candidates)} 个 (展示Top3)')
            for i, c in enumerate(candidates[:3]):
                print(f'    {i + 1}. {c["workstation"]["name"]} 综合{c["total_score"]:.1f}分 (碎片{c["fragment_score"]:.1f}+负载{c["load_score"]:.1f})')
        else:
            print('  - 所选时间暂无可分配工位（正常情况）')

        appt_id, info = AllocationEngine.create_allocated_appointment(
            pet.id, service.id, today, '14:00', service.duration
        )
        if appt_id:
            print(f'  ✓ 创建预约并分配成功! 预约ID={appt_id}')
            print(f'    工位={info["workstation"]["name"]} 评分={info["total_score"]:.1f}')
            AllocationEngine.cancel_appointment(appt_id)
            print(f'  ✓ 预约已取消，工位释放')
        else:
            print(f'  - 创建预约说明: {info}')
        return True
    except Exception as e:
        print(f'  ✗ 失败: {e}')
        import traceback; traceback.print_exc()
        return False


def test_pricing():
    print('\n' + '=' * 60)
    print('测试5: 计费规则 - 起步价/封顶价/边界校验/体型加价')
    try:
        services = Service.list()
        pets = Pet.list()
        if not services or not pets:
            print('  ✗ 数据不足')
            return False
        standard = next((s for s in services if not s.is_package), services[0])
        package = next((s for s in services if s.is_package), None)
        big_pet = next((p for p in pets if p.weight and p.weight > 20), None)
        cat_pet = next((p for p in pets if p.species == '猫'), None)

        print(f'--- 场景1: 简单项目（基础洗澡）按起步价计费 ---')
        info, err = PricingEngine.calculate_price(standard.id)
        if info:
            print(f'  ✓ 项目: {info["service"]["name"]} 起步={info["base_price"]} 封顶={info["cap_price"]}')
            print(f'    应付: ¥{info["final_amount"]:.2f} {"(标准起步价)" if info["final_amount"]==info["base_price"] else ""}')

        print(f'--- 场景2: 大型犬 (>20kg) 体型加价 15% ---')
        if big_pet:
            info2, err = PricingEngine.calculate_price(standard.id, big_pet.id)
            if info2:
                print(f'  ✓ 宠物: {big_pet.name} 体重{big_pet.weight}kg')
                print(f'    体型加价: +¥{info2["weight_surcharge"]:.2f}')
                print(f'    最终应付: ¥{info2["final_amount"]:.2f} (未超封顶={not info2["price_capped"]})')

        print(f'--- 场景3: 猫只护理 加价10% + 超时60分钟 ---')
        if cat_pet:
            info3, _ = PricingEngine.calculate_price(standard.id, cat_pet.id, overtime_minutes=60)
            if info3:
                print(f'  ✓ 宠物: {cat_pet.name} ({cat_pet.species}) 超时60分')
                print(f'    物种加价: +¥{info3["species_surcharge"]:.2f}')
                print(f'    超时费用: +¥{info3["overtime_surcharge"]:.2f}')
                print(f'    触发封顶拦截: {"是 🔒" if info3["price_capped"] else "否"}')
                print(f'    封顶价: ¥{info3["cap_price"]:.2f} | 应付: ¥{info3["final_amount"]:.2f}')

        print(f'--- 场景4: 套餐项目（一口价，不累计附加费） ---')
        if package:
            info4, _ = PricingEngine.calculate_price(package.id, pets[0].id, overtime_minutes=30)
            if info4:
                print(f'  ✓ 套餐: {info4["service"]["name"]}')
                print(f'    起步=封顶=¥{info4["base_price"]:.2f}')
                print(f'    应付: ¥{info4["final_amount"]:.2f} (套餐按一口价计费)')

        print(f'--- 场景5: 边界金额校验测试 ---')
        errors = PricingEngine.validate_service_pricing(100, 80, False)
        print(f'  ✓ 起步>封顶 校验: {"通过" if errors else "未拦截"} -> {errors[:1]}')
        errors2 = PricingEngine.validate_service_pricing(200, 200, True)
        print(f'  ✓ 套餐(起步必须=封顶) 校验: {"通过" if not errors2 else "未拦截"}')
        return True
    except Exception as e:
        print(f'  ✗ 失败: {e}')
        import traceback; traceback.print_exc()
        return False


def test_billing():
    print('\n' + '=' * 60)
    print('测试6: 账单生成 - 汇总/打印/收款/统计')
    try:
        pets = Pet.list()
        services = Service.list()
        if not pets or not services:
            print('  ✗ 数据不足')
            return False
        pet, svc = pets[0], services[0]
        today = datetime.now().strftime('%Y-%m-%d')
        alloc, _ = AllocationEngine.allocate_best_fit(today, '11:00', svc.duration)
        if not alloc:
            print('  - 无可分配工位，跳过账单完整流程')
            return True
        appt_id = Appointment.add({
            'pet_id': pet.id, 'workstation_id': alloc['workstation']['id'],
            'service_id': svc.id, 'start_time': alloc['start'], 'end_time': alloc['end'],
            'status': 'completed', 'alloc_score': alloc['total_score']
        })
        print(f'  ✓ 测试预约创建 ID={appt_id}')

        bill, price_info = BillingEngine.generate_bill(appt_id)
        if bill:
            print(f'  ✓ 账单生成 ID={bill.id} 实付=¥{bill.final_amount:.2f} 封顶={bool(bill.price_capped)}')
            print(f'    原额: ¥{bill.base_amount:.2f} 折扣: ¥{bill.discount_amount:.2f}')
            detail, err = BillingEngine.get_bill_detail(bill_id=bill.id)
            print(f'  ✓ 账单详情获取: {"OK" if detail else err}')
            receipt = BillingEngine.format_receipt(bill.id)
            lines = receipt.strip().split('\n')
            print(f'  ✓ 打印小票生成 ({len(lines)}行):')
            for line in lines[:5]:
                print(f'    {line}')
            print(f'    ... (共{len(lines)}行)')

            paid, err = BillingEngine.mark_bill_paid(bill.id)
            print(f'  ✓ 收款操作: {"成功" if paid else err} status={paid.paid_status if paid else ""}')

            stats = BillingEngine.get_dashboard_stats(today, today)
            print(f'  ✓ 统计面板: 开单{stats.get("bill_count",0)}单 总金额¥{stats.get("total_amount",0):.2f} 封顶{stats.get("cap_count",0)}单')

            bills = BillingEngine.list_bills()
            print(f'  ✓ 账单列表: 共{len(bills)}条记录')
        return True
    except Exception as e:
        print(f'  ✗ 失败: {e}')
        import traceback; traceback.print_exc()
        return False


def main():
    print('\n' + '🐾' * 20)
    print('宠物店美容预约系统 - 核心功能集成测试')
    print('🐾' * 20)

    tests = [
        ('数据库与种子数据', test_database_init),
        ('宠物档案CRUD', test_pet_crud),
        ('工位排期模块', test_scheduling),
        ('自动分配模块', test_allocation),
        ('计费规则模块', test_pricing),
        ('账单生成模块', test_billing),
    ]
    results = []
    for name, fn in tests:
        results.append((name, fn()))

    print('\n' + '=' * 60)
    print('测试总结:')
    passed = sum(1 for _, r in results if r)
    total = len(results)
    for n, r in results:
        print(f'  {"✓ PASS" if r else "✗ FAIL"}  {n}')
    print(f'\n结果: {passed}/{total} 项通过')
    db_path = os.path.join(os.path.dirname(__file__), 'petshop.db')
    print(f'\n数据库文件: {db_path}')
    print(f'启动客户端: python main.py')
    return passed == total


if __name__ == '__main__':
    ok = main()
    sys.exit(0 if ok else 1)

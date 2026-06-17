import json
import os
import shutil
from datetime import datetime
from models import Bill, Appointment, Pet, Workstation, Service, Member, Inventory
from models.inventory import ServiceInventoryLink
from .pricing import PricingEngine


class BillingEngine:
    SHOP_NAME = '萌宠之家美容中心'
    SHOP_PHONE = '400-888-9999'
    SHOP_ADDRESS = '阳光路123号宠物天地'
    POINTS_PER_YUAN = 1

    @staticmethod
    def generate_bill(appointment_id, overtime_minutes=0, extra_items=None,
                      discount_amount=0, notes=None, balance_used=0, member_id=None):
        appt = Appointment.get(appointment_id)
        if not appt:
            return None, '预约记录不存在'
        existing = Bill.get_by_appointment(appointment_id)
        if existing:
            return existing, '该预约已有账单'

        ok, shortages = Inventory.check_service_inventory(appt.service_id)
        if not ok:
            return None, '耗材库存不足: ' + '、'.join(shortages)

        price_info, err = PricingEngine.calculate_price(
            appt.service_id,
            pet_id=appt.pet_id,
            overtime_minutes=overtime_minutes,
            extra_items=extra_items,
            discount_amount=discount_amount
        )
        if err:
            return None, err

        is_package = price_info['is_package']

        if is_package:
            overtime_minutes = 0
            extra_items = None

        extra_items_text = json.dumps(extra_items, ensure_ascii=False) if extra_items else ''

        pet = Pet.get(appt.pet_id)
        if member_id:
            member = Member.get(member_id)
        else:
            member = pet.get_member() if pet else None
        member_id = member.id if member else None
        balance_used = float(balance_used or 0)
        balance_used = min(balance_used, price_info['final_amount'])
        if balance_used > 0 and member and member.balance + 0.01 < balance_used:
            return None, f'会员余额不足，当前余额¥{member.balance:.2f}'

        points_awarded = 0
        if member:
            points_awarded = int(round(price_info['final_amount'] * BillingEngine.POINTS_PER_YUAN))

        bill_id = Bill.add({
            'appointment_id': appointment_id,
            'pet_id': appt.pet_id,
            'service_id': appt.service_id,
            'workstation_id': appt.workstation_id,
            'base_amount': price_info['raw_amount'],
            'discount_amount': price_info['discount_amount'],
            'final_amount': price_info['final_amount'],
            'price_capped': price_info['price_capped'],
            'paid_status': Bill.STATUS_UNPAID,
            'overtime_minutes': overtime_minutes,
            'overtime_fee': price_info.get('overtime_surcharge', 0),
            'weight_surcharge': price_info.get('weight_surcharge', 0),
            'species_surcharge': price_info.get('species_surcharge', 0),
            'extra_items_text': extra_items_text,
            'extra_items_fee': price_info.get('extra_items_surcharge', 0),
            'member_id': member_id,
            'balance_used': balance_used,
            'points_awarded': points_awarded
        })

        if member:
            if balance_used > 0:
                Member.consume(member.id, balance_used, points_award=points_awarded,
                               bill_id=bill_id,
                               note=f'开单消费¥{price_info["final_amount"]:.2f}，余额抵扣¥{balance_used:.2f}')
            elif points_awarded > 0:
                Member.award_points(member.id, points_awarded, bill_id=bill_id,
                                    note=f'开单消费¥{price_info["final_amount"]:.2f}，赠送{points_awarded}积分')

        inv_result, inv_err = Inventory.deduct_service_inventory(appt.service_id, bill_id=bill_id)
        if inv_err:
            return None, inv_err

        Appointment.update(appointment_id, {'status': Appointment.STATUS_COMPLETED})

        bill = Bill.get(bill_id)
        return bill, price_info

    @staticmethod
    def get_bill_detail(bill_id=None, appointment_id=None):
        if bill_id:
            bill = Bill.get(bill_id)
        elif appointment_id:
            bill = Bill.get_by_appointment(appointment_id)
        else:
            return None, '需要提供账单ID或预约ID'
        if not bill:
            return None, '账单不存在'

        appt = Appointment.get(bill.appointment_id)
        pet = Pet.get(bill.pet_id)
        svc = Service.get(bill.service_id)
        ws = Workstation.get(bill.workstation_id) if bill.workstation_id else None
        member = Member.get(bill.member_id) if bill.member_id else None

        price_info = {
            'base_price': float(svc.base_price) if svc else 0,
            'cap_price': float(svc.cap_price) if svc else 0,
            'is_package': bool(svc.is_package) if svc else False,
            'weight_surcharge': bill.weight_surcharge or 0,
            'species_surcharge': bill.species_surcharge or 0,
            'overtime_surcharge': bill.overtime_fee or 0,
            'extra_items_surcharge': bill.extra_items_fee or 0,
            'discount_amount': bill.discount_amount or 0,
            'raw_amount': bill.base_amount,
            'final_amount': bill.final_amount,
            'price_capped': bill.price_capped,
            'extra_items': bill.get_extra_items(),
            'overtime_minutes': bill.overtime_minutes or 0,
            'balance_used': bill.balance_used or 0,
            'points_awarded': bill.points_awarded or 0
        }

        result = {
            'bill': bill.to_dict(),
            'appointment': appt.to_dict() if appt else None,
            'pet': pet.to_dict() if pet else None,
            'service': svc.to_dict() if svc else None,
            'workstation': ws.to_dict() if ws else None,
            'member': member.to_dict() if member else None,
            'pricing': price_info
        }
        return result, None

    @staticmethod
    def format_receipt(bill_id):
        detail, err = BillingEngine.get_bill_detail(bill_id=bill_id)
        if err:
            return err

        bill = detail['bill']
        pet = detail['pet'] or {}
        svc = detail['service'] or {}
        ws = detail['workstation'] or {}
        pricing = detail['pricing'] or {}
        appt = detail['appointment'] or {}
        member = detail['member'] or {}

        lines = []
        lines.append('=' * 48)
        lines.append(f'{BillingEngine.SHOP_NAME:^48}')
        lines.append(f'{"消 费 结 账 单":^48}')
        lines.append('=' * 48)
        lines.append(f'  账单编号: B{bill["id"]:08d}')
        lines.append(f'  开单时间: {bill["created_at"]}')
        lines.append(f'  预约时间: {appt.get("start_time","")} ~ {appt.get("end_time","")}')
        lines.append(f'  服务工位: {ws.get("name","-")} ({ws.get("type","-")})')
        if member:
            lines.append(f'  会员信息: {member.get("owner_name","-")} [{member.get("level","普通")}] +{bill.get("points_awarded",0)}积分')
        lines.append('-' * 48)
        lines.append(f'  宠主姓名: {pet.get("owner_name","-")}')
        lines.append(f'  联系电话: {pet.get("owner_phone","-")}')
        lines.append(f'  宠物信息: {pet.get("name","-")} [{pet.get("species","-")}/{pet.get("breed","-")}]')
        lines.append('-' * 48)
        lines.append(f'  服务项目: {svc.get("name","-")}')
        lines.append(f'  项目分类: {svc.get("category","-")}{" [套餐]" if svc.get("is_package") else ""}')
        lines.append(f'  项目时长: {svc.get("duration",0)} 分钟')
        lines.append('-' * 48)
        lines.append('  费用明细:')
        if pricing.get('is_package'):
            lines.append(f'    套餐一口价:          ¥{pricing.get("base_price",0):>8.2f}')
        else:
            lines.append(f'    起步价:              ¥{pricing.get("base_price",0):>8.2f}')
            if pricing.get('weight_surcharge', 0) > 0:
                lines.append(f'    大型犬加价:          ¥{pricing.get("weight_surcharge",0):>8.2f}')
            if pricing.get('species_surcharge', 0) > 0:
                lines.append(f'    猫只护理加价:        ¥{pricing.get("species_surcharge",0):>8.2f}')
            if pricing.get('overtime_minutes', 0) > 0:
                lines.append(f'    超时服务({pricing["overtime_minutes"]}分钟):  ¥{pricing.get("overtime_surcharge",0):>8.2f}')
            extra_items = pricing.get('extra_items', {})
            if extra_items:
                for k, v in extra_items.items():
                    lines.append(f'    {k}:              ¥{float(v):>8.2f}')
        if pricing.get('discount_amount', 0) > 0:
            lines.append(f'    优惠折扣:           -¥{pricing.get("discount_amount",0):>8.2f}')
        if bill.get('price_capped'):
            lines.append(f'    *已按封顶价计费')
        if pricing.get('balance_used', 0) > 0:
            lines.append(f'    会员余额抵扣:       -¥{pricing.get("balance_used",0):>8.2f}')
        lines.append('-' * 48)
        lines.append(f'  原价合计:              ¥{bill["base_amount"]:>8.2f}')
        if bill.get('discount_amount', 0) > 0:
            lines.append(f'  优惠抵扣:             -¥{bill["discount_amount"]:>8.2f}')
        if pricing.get('balance_used', 0) > 0:
            lines.append(f'  余额抵扣:             -¥{pricing.get("balance_used",0):>8.2f}')
        cash_pay = max(0, round(bill["final_amount"] - pricing.get('balance_used', 0), 2))
        if cash_pay > 0:
            lines.append(f'  应付现付:              ¥{cash_pay:>8.2f}')
        lines.append(f'  合计应付:              ¥{bill["final_amount"]:>8.2f}')
        if pricing.get('points_awarded', 0) > 0:
            lines.append(f'  赠送积分:              +{pricing.get("points_awarded",0)}')
        lines.append(f'  支付状态: {"[已结清]" if bill["paid_status"]=="paid" else "[待支付]"}')
        if bill.get('paid_at'):
            lines.append(f'  支付时间: {bill["paid_at"]}')
        lines.append('-' * 48)
        lines.append(f'  联系电话: {BillingEngine.SHOP_PHONE}')
        lines.append(f'  门店地址: {BillingEngine.SHOP_ADDRESS}')
        lines.append('=' * 48)
        lines.append(f'  {datetime.now().strftime("%Y-%m-%d %H:%M:%S"):^48}')
        lines.append('')
        return '\n'.join(lines)

    @staticmethod
    def list_bills(paid_status=None, date_from=None, date_to=None, keyword=None):
        return Bill.list(paid_status, date_from, date_to, keyword)

    @staticmethod
    def mark_bill_paid(bill_id):
        bill = Bill.get(bill_id)
        if not bill:
            return None, '账单不存在'
        if bill.paid_status == Bill.STATUS_PAID:
            return bill, '账单已处于已支付状态'
        Bill.mark_paid(bill_id)
        return Bill.get(bill_id), None

    @staticmethod
    def get_dashboard_stats(date_from=None, date_to=None):
        if not date_from:
            date_from = datetime.now().strftime('%Y-%m-01')
        if not date_to:
            date_to = datetime.now().strftime('%Y-%m-%d')
        stats = Bill.stats_summary(date_from, date_to)
        pet_count = len(Pet.list())
        ws_count = len(Workstation.list())
        stats['pet_count'] = pet_count
        stats['workstation_count'] = ws_count
        stats['date_range'] = f'{date_from} ~ {date_to}'
        stats['member_count'] = Member.count()
        stats['member_total_balance'] = round(Member.total_balance(), 2)
        stats['low_stock_count'] = Inventory.low_stock_count()
        consumption = Inventory.consumption_last_7_days()
        stats['inv_consumed_7d'] = consumption['total_used']
        stats['inv_consumed_value_7d'] = consumption['total_value']
        stats['low_stock_items'] = [i.to_dict() for i in Inventory.low_stock_items()]
        return stats


class BackupManager:
    @staticmethod
    def backup_dir():
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        d = os.path.join(base, 'backups')
        if not os.path.exists(d):
            os.makedirs(d, exist_ok=True)
        return d

    @staticmethod
    def list_backups():
        backups = []
        d = BackupManager.backup_dir()
        for fname in os.listdir(d):
            if fname.startswith('petshop_') and fname.endswith('.db'):
                fpath = os.path.join(d, fname)
                size_kb = round(os.path.getsize(fpath) / 1024, 1)
                ts = fname.replace('petshop_', '').replace('.db', '')
                try:
                    ts_fmt = datetime.strptime(ts, '%Y%m%d_%H%M%S').strftime('%Y-%m-%d %H:%M:%S')
                except:
                    ts_fmt = ts
                backups.append({
                    'filename': fname, 'path': fpath,
                    'size_kb': size_kb, 'created_at': ts_fmt
                })
        backups.sort(key=lambda x: x['created_at'], reverse=True)
        return backups

    @staticmethod
    def create_backup():
        db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'petshop.db')
        if not os.path.exists(db_path):
            return None, '当前数据库文件不存在'
        fname = f'petshop_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db'
        dest = os.path.join(BackupManager.backup_dir(), fname)
        try:
            shutil.copy2(db_path, dest)
        except Exception as e:
            return None, f'备份失败: {e}'
        size_kb = round(os.path.getsize(dest) / 1024, 1)
        return {'filename': fname, 'path': dest, 'size_kb': size_kb}, None

    @staticmethod
    def restore_backup(filename):
        if not filename:
            return False, '请指定备份文件'
        d = BackupManager.backup_dir()
        src = os.path.join(d, filename)
        if not os.path.exists(src):
            return False, f'备份文件不存在: {filename}'
        db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'petshop.db')
        try:
            from models import Database
            Database.close()
            Database._instance = None
            Database._conn = None
        except:
            pass
        try:
            if os.path.exists(db_path):
                safe_name = f'petshop_before_restore_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db'
                safe_path = os.path.join(d, safe_name)
                shutil.copy2(db_path, safe_path)
            shutil.copy2(src, db_path)
        except Exception as e:
            return False, f'恢复失败: {e}'
        return True, '恢复成功，请重新启动程序'

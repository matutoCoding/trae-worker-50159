from datetime import datetime
from models import Bill, Appointment, Pet, Workstation, Service
from .pricing import PricingEngine


class BillingEngine:
    SHOP_NAME = '萌宠之家美容中心'
    SHOP_PHONE = '400-888-9999'
    SHOP_ADDRESS = '阳光路123号宠物天地'

    @staticmethod
    def generate_bill(appointment_id, overtime_minutes=0, extra_items=None,
                      discount_amount=0, notes=None):
        appt = Appointment.get(appointment_id)
        if not appt:
            return None, '预约记录不存在'
        existing = Bill.get_by_appointment(appointment_id)
        if existing:
            return existing, '该预约已有账单'

        price_info, err = PricingEngine.calculate_price(
            appt.service_id,
            pet_id=appt.pet_id,
            overtime_minutes=overtime_minutes,
            extra_items=extra_items,
            discount_amount=discount_amount
        )
        if err:
            return None, err

        bill_id = Bill.add({
            'appointment_id': appointment_id,
            'pet_id': appt.pet_id,
            'service_id': appt.service_id,
            'workstation_id': appt.workstation_id,
            'base_amount': price_info['raw_amount'],
            'discount_amount': price_info['discount_amount'],
            'final_amount': price_info['final_amount'],
            'price_capped': price_info['price_capped'],
            'paid_status': Bill.STATUS_UNPAID
        })

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

        price_info, _ = PricingEngine.calculate_price(
            bill.service_id, bill.pet_id
        )

        result = {
            'bill': bill.to_dict(),
            'appointment': appt.to_dict() if appt else None,
            'pet': pet.to_dict() if pet else None,
            'service': svc.to_dict() if svc else None,
            'workstation': ws.to_dict() if ws else None,
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

        lines = []
        lines.append('=' * 48)
        lines.append(f'{BillingEngine.SHOP_NAME:^48}')
        lines.append(f'{"消 费 结 账 单":^48}')
        lines.append('=' * 48)
        lines.append(f'  账单编号: B{bill["id"]:08d}')
        lines.append(f'  开单时间: {bill["created_at"]}')
        lines.append(f'  预约时间: {appt.get("start_time","")} ~ {appt.get("end_time","")}')
        lines.append(f'  服务工位: {ws.get("name","-")} ({ws.get("type","-")})')
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
        lines.append(f'    起步价:              ¥{pricing.get("base_price",0):>8.2f}')
        if pricing.get('weight_surcharge', 0) > 0:
            lines.append(f'    大型犬加价:          ¥{pricing.get("weight_surcharge",0):>8.2f}')
        if pricing.get('species_surcharge', 0) > 0:
            lines.append(f'    猫只护理加价:        ¥{pricing.get("species_surcharge",0):>8.2f}')
        if pricing.get('overtime_surcharge', 0) > 0:
            lines.append(f'    超时服务费:          ¥{pricing.get("overtime_surcharge",0):>8.2f}')
        if pricing.get('extra_items_surcharge', 0) > 0:
            lines.append(f'    额外项目费:          ¥{pricing.get("extra_items_surcharge",0):>8.2f}')
        if pricing.get('discount_amount', 0) > 0:
            lines.append(f'    优惠折扣:           -¥{pricing.get("discount_amount",0):>8.2f}')
        if bill.get('price_capped'):
            lines.append(f'    *已按封顶价计费')
        lines.append('-' * 48)
        lines.append(f'  合计应付:              ¥{bill["final_amount"]:>8.2f}')
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
        return stats

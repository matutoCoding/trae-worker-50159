from models import Service, Pet


class PricingEngine:
    OVERTIME_RATE_PER_MIN = 1.5
    WEIGHT_SURCHARGE_THRESHOLD = 20.0
    WEIGHT_SURCHARGE_RATE = 0.15
    SPECIAL_SPECIES_SURCHARGE = {
        '猫': 0.10
    }

    @staticmethod
    def validate_service_pricing(base_price, cap_price, is_package=False):
        errors = []
        if base_price is None or base_price < 0:
            errors.append('起步价不能为负数')
        if cap_price is None or cap_price < 0:
            errors.append('封顶价不能为负数')
        if is_package:
            if abs(base_price - cap_price) > 0.01:
                errors.append('套餐项目的起步价必须等于封顶价')
        else:
            if base_price > cap_price:
                errors.append('起步价不能高于封顶价')
        return errors

    @staticmethod
    def validate_amount_bounds(amount, base_price, cap_price):
        errors = []
        if amount < 0:
            errors.append('金额不能为负数')
        if amount + 0.01 < base_price:
            errors.append(f'金额低于起步价 ¥{base_price:.2f}')
        if amount - 0.01 > cap_price:
            errors.append(f'金额高于封顶价 ¥{cap_price:.2f}，系统将按封顶价计费')
        return errors

    @staticmethod
    def _calc_weight_surcharge(base_price, weight):
        if weight and weight > PricingEngine.WEIGHT_SURCHARGE_THRESHOLD:
            return round(base_price * PricingEngine.WEIGHT_SURCHARGE_RATE, 2)
        return 0.0

    @staticmethod
    def _calc_species_surcharge(base_price, species):
        rate = PricingEngine.SPECIAL_SPECIES_SURCHARGE.get(species, 0)
        if rate > 0:
            return round(base_price * rate, 2)
        return 0.0

    @staticmethod
    def _calc_overtime_surcharge(overtime_minutes):
        if overtime_minutes and overtime_minutes > 0:
            return round(overtime_minutes * PricingEngine.OVERTIME_RATE_PER_MIN, 2)
        return 0.0

    @staticmethod
    def _calc_extra_items_surcharge(extra_items):
        if not extra_items:
            return 0.0
        return round(sum(float(v) for v in extra_items.values() if v), 2)

    @staticmethod
    def calculate_price(service_id, pet_id=None, overtime_minutes=0, extra_items=None,
                        discount_amount=0):
        svc = Service.get(service_id)
        if not svc:
            return None, '服务项目不存在'

        base_price = float(svc.base_price)
        cap_price = float(svc.cap_price)
        is_package = bool(svc.is_package)

        errors = PricingEngine.validate_service_pricing(base_price, cap_price, is_package)
        if errors:
            return None, '; '.join(errors)

        raw_amount = base_price

        if not is_package:
            weight = None
            species = None
            if pet_id:
                pet = Pet.get(pet_id)
                if pet:
                    weight = pet.weight
                    species = pet.species

            weight_fee = PricingEngine._calc_weight_surcharge(base_price, weight)
            species_fee = PricingEngine._calc_species_surcharge(base_price, species)
            overtime_fee = PricingEngine._calc_overtime_surcharge(overtime_minutes)
            extra_fee = PricingEngine._calc_extra_items_surcharge(extra_items)

            raw_amount += weight_fee + species_fee + overtime_fee + extra_fee
        else:
            raw_amount = cap_price

        price_capped = 0
        final_amount = raw_amount

        if discount_amount and discount_amount > 0:
            final_amount -= discount_amount
            if final_amount < 0:
                final_amount = 0

        if final_amount < base_price and not is_package:
            final_amount = base_price
        elif discount_amount <= 0 and raw_amount > cap_price and not is_package:
            final_amount = cap_price
            price_capped = 1
        elif not is_package and raw_amount > cap_price:
            final_amount = cap_price - discount_amount
            if final_amount < 0:
                final_amount = 0
            price_capped = 1

        final_amount = round(final_amount, 2)
        bound_errors = PricingEngine.validate_amount_bounds(final_amount, base_price, cap_price)

        result = {
            'service': svc.to_dict(),
            'base_price': round(base_price, 2),
            'cap_price': round(cap_price, 2),
            'is_package': is_package,
            'weight_surcharge': 0.0,
            'species_surcharge': 0.0,
            'overtime_surcharge': 0.0,
            'extra_items_surcharge': 0.0,
            'discount_amount': round(float(discount_amount or 0), 2),
            'raw_amount': round(raw_amount, 2),
            'final_amount': final_amount,
            'price_capped': price_capped,
            'bound_warnings': [e for e in bound_errors if '将按封顶价' in e or '低于起步价' in e]
        }

        if not is_package and pet_id:
            pet = Pet.get(pet_id)
            if pet:
                result['weight_surcharge'] = PricingEngine._calc_weight_surcharge(base_price, pet.weight)
                result['species_surcharge'] = PricingEngine._calc_species_surcharge(base_price, pet.species)
        if not is_package:
            result['overtime_surcharge'] = PricingEngine._calc_overtime_surcharge(overtime_minutes)
            result['extra_items_surcharge'] = PricingEngine._calc_extra_items_surcharge(extra_items)

        return result, None

    @staticmethod
    def get_overtime_minutes(appt_end_time, actual_end_time_str):
        from datetime import datetime
        try:
            appt_end = datetime.strptime(appt_end_time, '%Y-%m-%d %H:%M')
            actual_end = datetime.strptime(actual_end_time_str, '%Y-%m-%d %H:%M')
            delta = int((actual_end - appt_end).total_seconds() / 60)
            return max(0, delta)
        except (ValueError, TypeError):
            return 0

    @staticmethod
    def preview_services_pricing(service_ids, pet_id=None):
        results = []
        total_base = 0.0
        total_final = 0.0
        total_cap = 0.0
        for sid in service_ids:
            price_info, err = PricingEngine.calculate_price(sid, pet_id)
            if price_info:
                results.append(price_info)
                total_base += price_info['base_price']
                total_final += price_info['final_amount']
                total_cap += price_info['cap_price']
        return {
            'items': results,
            'total_base': round(total_base, 2),
            'total_cap': round(total_cap, 2),
            'total_final': round(total_final, 2)
        }

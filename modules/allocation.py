from datetime import datetime, timedelta
from models import Workstation, Appointment
from .scheduling import Scheduling


class AllocationEngine:
    PERFECT_FIT_BONUS = 100.0
    LOAD_BALANCE_WEIGHT = 30.0
    FRAGMENT_PENALTY_WEIGHT = 0.8
    SMALL_FRAGMENT_THRESHOLD = 30
    SMALL_FRAGMENT_EXTRA_PENALTY = 50.0

    @staticmethod
    def _parse_range(s, e):
        return datetime.strptime(s, '%Y-%m-%d %H:%M'), datetime.strptime(e, '%Y-%m-%d %H:%M')

    @staticmethod
    def _minutes_between(dt1, dt2):
        return int((dt2 - dt1).total_seconds() / 60)

    @staticmethod
    def find_available_slots(date_str, duration_minutes, ws_type=None):
        workstations = Scheduling.list_workstations(status='active', ws_type=ws_type)
        available = []
        for ws in workstations:
            free_ranges = Scheduling.get_workstation_free_ranges(ws.id, date_str)
            for s, e in free_ranges:
                sdt, edt = AllocationEngine._parse_range(s, e)
                total_min = AllocationEngine._minutes_between(sdt, edt)
                if total_min >= duration_minutes:
                    cur = sdt
                    while AllocationEngine._minutes_between(cur, edt) >= duration_minutes:
                        cur_end = cur + timedelta(minutes=duration_minutes)
                        available.append({
                            'workstation': ws.to_dict(),
                            'start': cur.strftime('%Y-%m-%d %H:%M'),
                            'end': cur_end.strftime('%Y-%m-%d %H:%M'),
                            'free_before_min': AllocationEngine._minutes_between(sdt, cur),
                            'free_after_min': AllocationEngine._minutes_between(cur_end, edt)
                        })
                        cur += timedelta(minutes=Scheduling.SLOT_MINUTES)
        return available

    @staticmethod
    def _calc_fragment_score(free_before, free_after, duration):
        before_penalty = 0
        if free_before > 0 and free_before < duration:
            before_penalty = free_before * AllocationEngine.FRAGMENT_PENALTY_WEIGHT
            if free_before <= AllocationEngine.SMALL_FRAGMENT_THRESHOLD:
                before_penalty += AllocationEngine.SMALL_FRAGMENT_EXTRA_PENALTY
        after_penalty = 0
        if free_after > 0 and free_after < duration:
            after_penalty = free_after * AllocationEngine.FRAGMENT_PENALTY_WEIGHT
            if free_after <= AllocationEngine.SMALL_FRAGMENT_THRESHOLD:
                after_penalty += AllocationEngine.SMALL_FRAGMENT_EXTRA_PENALTY
        perfect_bonus = 0
        if free_before == 0 and free_after == 0:
            perfect_bonus = AllocationEngine.PERFECT_FIT_BONUS
        elif free_before == 0 or free_after == 0:
            perfect_bonus = AllocationEngine.PERFECT_FIT_BONUS * 0.5
        return perfect_bonus - before_penalty - after_penalty

    @staticmethod
    def _calc_load_score(workstation_dict):
        max_load = 10.0
        load = workstation_dict.get('load_score', 0.0)
        normalized_load = min(load / max_load, 1.0)
        return (1.0 - normalized_load) * AllocationEngine.LOAD_BALANCE_WEIGHT

    @staticmethod
    def allocate_best_fit(date_str, start_time_str, duration_minutes, ws_type=None,
                          exclude_appt_id=None):
        start_dt = datetime.strptime(start_time_str, '%H:%M')
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        full_start = datetime.combine(date_obj, start_dt.time())
        full_end = full_start + timedelta(minutes=duration_minutes)
        full_start_str = full_start.strftime('%Y-%m-%d %H:%M')
        full_end_str = full_end.strftime('%Y-%m-%d %H:%M')

        workstations = Scheduling.list_workstations(status='active', ws_type=ws_type)
        candidates = []

        for ws in workstations:
            if not Scheduling.is_workstation_available(ws.id, full_start_str, full_end_str, exclude_appt_id):
                continue
            free_ranges = Scheduling.get_workstation_free_ranges(ws.id, date_str)
            target_range = None
            for s, e in free_ranges:
                sdt, edt = AllocationEngine._parse_range(s, e)
                if sdt <= full_start and full_end <= edt:
                    target_range = (sdt, edt)
                    break
            if not target_range:
                continue
            free_before = AllocationEngine._minutes_between(target_range[0], full_start)
            free_after = AllocationEngine._minutes_between(full_end, target_range[1])
            frag_score = AllocationEngine._calc_fragment_score(free_before, free_after, duration_minutes)
            load_score = AllocationEngine._calc_load_score(ws.to_dict())
            total_score = frag_score + load_score
            candidates.append({
                'workstation': ws.to_dict(),
                'start': full_start_str,
                'end': full_end_str,
                'free_before_min': free_before,
                'free_after_min': free_after,
                'fragment_score': frag_score,
                'load_score': load_score,
                'total_score': total_score
            })

        if not candidates:
            return None, candidates

        candidates.sort(key=lambda x: x['total_score'], reverse=True)
        return candidates[0], candidates

    @staticmethod
    def allocate_best_fit_in_window(date_str, start_time_str, end_time_str,
                                    duration_minutes, ws_type=None):
        start_dt = datetime.strptime(start_time_str, '%H:%M')
        end_dt = datetime.strptime(end_time_str, '%H:%M')
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        full_start_limit = datetime.combine(date_obj, start_dt.time())
        full_end_limit = datetime.combine(date_obj, end_dt.time())

        cur = full_start_limit
        all_candidates = []
        best_allocation = None

        while cur + timedelta(minutes=duration_minutes) <= full_end_limit:
            cur_hm = cur.strftime('%H:%M')
            alloc, candidates = AllocationEngine.allocate_best_fit(
                date_str, cur_hm, duration_minutes, ws_type
            )
            if alloc:
                all_candidates.extend(candidates)
                if best_allocation is None or alloc['total_score'] > best_allocation['total_score']:
                    best_allocation = alloc
            cur += timedelta(minutes=Scheduling.SLOT_MINUTES)

        all_candidates.sort(key=lambda x: x['total_score'], reverse=True)
        return best_allocation, all_candidates

    @staticmethod
    def create_allocated_appointment(pet_id, service_id, date_str, start_time_str,
                                     duration_minutes, ws_type=None, notes=None):
        alloc, candidates = AllocationEngine.allocate_best_fit(
            date_str, start_time_str, duration_minutes, ws_type
        )
        if not alloc:
            return None, '在所选时间没有可用的工位，请尝试其他时间'
        ws = alloc['workstation']
        appt_id = Appointment.add({
            'pet_id': pet_id,
            'workstation_id': ws['id'],
            'service_id': service_id,
            'start_time': alloc['start'],
            'end_time': alloc['end'],
            'status': Appointment.STATUS_CONFIRMED,
            'alloc_score': alloc['total_score'],
            'notes': notes
        })
        AllocationEngine._recalc_workstation_load(ws['id'])
        return appt_id, alloc

    @staticmethod
    def reallocate_appointment(appt_id):
        appt = Appointment.get(appt_id)
        if not appt:
            return None, '预约不存在'
        from models import Service
        svc = Service.get(appt.service_id)
        if not svc:
            return None, '服务项目不存在'
        date_str = appt.start_time.split(' ')[0]
        start_hm = appt.start_time.split(' ')[1][:5]
        alloc, candidates = AllocationEngine.allocate_best_fit(
            date_str, start_hm, svc.duration, exclude_appt_id=appt_id
        )
        if not alloc:
            return None, '没有可重分配的工位'
        old_ws_id = appt.workstation_id
        Appointment.update(appt_id, {
            'workstation_id': alloc['workstation']['id'],
            'alloc_score': alloc['total_score']
        })
        AllocationEngine._recalc_workstation_load(alloc['workstation']['id'])
        if old_ws_id:
            AllocationEngine._recalc_workstation_load(old_ws_id)
        return appt_id, alloc

    @staticmethod
    def _recalc_workstation_load(ws_id):
        today = datetime.now().strftime('%Y-%m-%d')
        future_7 = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
        appts = Appointment.list_by_workstation(ws_id, today, future_7)
        total_minutes = 0
        for a in appts:
            if a.status == Appointment.STATUS_CANCELLED:
                continue
            sd, ed = AllocationEngine._parse_range(a.start_time, a.end_time)
            total_minutes += AllocationEngine._minutes_between(sd, ed)
        capacity = 8 * 60 * 7
        load_score = round(total_minutes / capacity * 10, 2)
        Workstation.update_load_score(ws_id, load_score)

    @staticmethod
    def cancel_appointment(appt_id):
        appt = Appointment.get(appt_id)
        if not appt:
            return
        ws_id = appt.workstation_id
        Appointment.update(appt_id, {'status': Appointment.STATUS_CANCELLED})
        if ws_id:
            AllocationEngine._recalc_workstation_load(ws_id)

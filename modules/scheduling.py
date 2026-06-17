from datetime import datetime, timedelta
from models import Workstation, Appointment


class Scheduling:
    WORK_START_HOUR = 9
    WORK_END_HOUR = 21
    SLOT_MINUTES = 15

    @staticmethod
    def add_workstation(name, ws_type, capacity=1, equipment=None, status='active'):
        if not name or not ws_type:
            raise ValueError('工位名称和类型不能为空')
        return Workstation.add({
            'name': name, 'type': ws_type, 'capacity': capacity,
            'equipment': equipment, 'status': status
        })

    @staticmethod
    def update_workstation(ws_id, **kwargs):
        return Workstation.update(ws_id, kwargs)

    @staticmethod
    def delete_workstation(ws_id):
        return Workstation.delete(ws_id)

    @staticmethod
    def list_workstations(status=None, ws_type=None):
        return Workstation.list(status, ws_type)

    @staticmethod
    def get_workstation(ws_id):
        return Workstation.get(ws_id)

    @staticmethod
    def get_work_hours(date_str):
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        start = datetime.combine(date_obj, datetime.min.time()).replace(hour=Scheduling.WORK_START_HOUR)
        end = datetime.combine(date_obj, datetime.min.time()).replace(hour=Scheduling.WORK_END_HOUR)
        return start, end

    @staticmethod
    def get_time_slots(date_str, slot_minutes=None):
        if slot_minutes is None:
            slot_minutes = Scheduling.SLOT_MINUTES
        start, end = Scheduling.get_work_hours(date_str)
        slots = []
        current = start
        while current < end:
            slot_end = current + timedelta(minutes=slot_minutes)
            if slot_end <= end:
                slots.append((current.strftime('%Y-%m-%d %H:%M'), slot_end.strftime('%Y-%m-%d %H:%M')))
            current = slot_end
        return slots

    @staticmethod
    def is_workstation_available(ws_id, start_time, end_time, exclude_appt_id=None):
        conflicts = Appointment.list_conflicting(ws_id, start_time, end_time, exclude_appt_id)
        return len(conflicts) == 0

    @staticmethod
    def get_workstation_occupied_ranges(ws_id, date_str):
        next_day = (datetime.strptime(date_str, '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d')
        appts = Appointment.list_by_workstation(ws_id, date_str, next_day)
        return [(a.start_time, a.end_time, a.id) for a in appts
                if a.status != Appointment.STATUS_CANCELLED]

    @staticmethod
    def get_workstation_free_ranges(ws_id, date_str):
        start, end = Scheduling.get_work_hours(date_str)
        occupied = sorted(
            Scheduling.get_workstation_occupied_ranges(ws_id, date_str),
            key=lambda x: x[0]
        )
        free_ranges = []
        cur_start = start
        for occ_s, occ_e, _ in occupied:
            occ_s_dt = datetime.strptime(occ_s, '%Y-%m-%d %H:%M')
            occ_e_dt = datetime.strptime(occ_e, '%Y-%m-%d %H:%M')
            if cur_start < occ_s_dt:
                free_ranges.append((
                    cur_start.strftime('%Y-%m-%d %H:%M'),
                    min(occ_s_dt, end).strftime('%Y-%m-%d %H:%M')
                ))
            cur_start = max(cur_start, occ_e_dt)
            if cur_start >= end:
                break
        if cur_start < end:
            free_ranges.append((
                cur_start.strftime('%Y-%m-%d %H:%M'),
                end.strftime('%Y-%m-%d %H:%M')
            ))
        return free_ranges

    @staticmethod
    def get_free_ranges_with_capacity(date_str, duration_minutes):
        from modules import AllocationEngine
        return AllocationEngine.find_available_slots(date_str, duration_minutes)

    @staticmethod
    def get_daily_schedule(date_str):
        workstations = Scheduling.list_workstations()
        schedule = {}
        for ws in workstations:
            schedule[ws.id] = {
                'workstation': ws.to_dict(),
                'occupied': Scheduling.get_workstation_occupied_ranges(ws.id, date_str),
                'free': Scheduling.get_workstation_free_ranges(ws.id, date_str)
            }
        return schedule

    @staticmethod
    def get_appointment_detail(appt_id):
        appt = Appointment.get(appt_id)
        if not appt:
            return None
        from models import Pet, Workstation, Service
        result = appt.to_dict()
        pet = Pet.get(appt.pet_id)
        if pet:
            result['pet'] = pet.to_dict()
        ws = Workstation.get(appt.workstation_id) if appt.workstation_id else None
        if ws:
            result['workstation'] = ws.to_dict()
        svc = Service.get(appt.service_id)
        if svc:
            result['service'] = svc.to_dict()
        return result

    @staticmethod
    def update_appointment_status(appt_id, status):
        valid = [
            Appointment.STATUS_PENDING, Appointment.STATUS_CONFIRMED,
            Appointment.STATUS_COMPLETED, Appointment.STATUS_CANCELLED
        ]
        if status not in valid:
            raise ValueError(f'无效状态: {status}')
        Appointment.update(appt_id, {'status': status})

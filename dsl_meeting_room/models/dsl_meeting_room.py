# -*- coding: utf-8 -*-

from odoo import models, fields, api,_
from datetime import datetime
import logging
from odoo.exceptions import ValidationError
from datetime import date
import re




_logger = logging.getLogger(__name__)


class MeetingRoom(models.Model):
    _name = 'dsl.meeting.room'
    _description = 'Meeting Room'
    

    name = fields.Char(string='Name', required=True)
    code = fields.Char(string='Room Number' , required=True)
    image = fields.Binary(string="Image")
    capacity = fields.Integer(string="Capacity")
    note = fields.Text(String="Note")
    active = fields.Boolean(default=True)


    @api.depends('name', 'code')
    def name_get(self):
        result = []
        for room in self:
            name = f"[{room.code}] {room.name}"
            result.append((room.id, name))
        return result

class MeetingFacility(models.Model):
    _name = 'dsl.meeting.facility'
    _description = 'Booking Facilities'

    name = fields.Char(String="Facilities", required=True)
    code = fields.Char(String="Code", readonly=True)
    note = fields.Text(String="Note")
    active = fields.Boolean(default=True)

    @api.model
    def create(self, vals):
        vals['code'] = self.env['ir.sequence'].next_by_code('dsl.meeting.facility')
        res = super(MeetingFacility, self).create(vals)
        return res

    @api.depends('name', 'code')
    def name_get(self):
        result = []
        for facility in self:
            name = f"[{facility.code}] {facility.name}"
            result.append((facility.id, name))
        return result

class BookingRoom(models.Model):
    _name = 'dsl.booking.room'
    _description = 'Booking Room'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'code'
    

    
    code = fields.Char(string='Code', readonly=True , default=lambda self: ('New'))
    booking_room = fields.Many2one('dsl.meeting.room', string="Meeting Room" ,tracking=True)
    room_image = fields.Binary(string="Meeting Room Image" , related= "booking_room.image", max_width=100, max_height=100)
    meeting_date = fields.Date(string="Meeting Date" ,tracking=True)
    meeting_duration = fields.Float(string="Duration", compute='_compute_meeting_duration', store=True ,tracking=True)
    start_time = fields.Char(string="Start Time" ,tracking=True)
    end_time = fields.Char(string="End Time" ,tracking=True)
    room_no = fields.Char(string='Room Number', related= "booking_room.code")
    state = fields.Selection([('draft', 'Draft'),
                              ('request', 'Request Sent'),
                              ('approve', 'Approved'),
                              ('reject', 'Rejected')], string="Status", default='draft')
    booking_employee = fields.Many2one('hr.employee', string="Booking Employee", default=lambda self: self.env.user.employee_id.id, tracking=True)
    # active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company.id ,tracking=True)
    booking_facility_line = fields.One2many('dsl.booking.room.line', 'booking_id', string="Facility Details" ,tracking=True)
    note = fields.Char(string="Note")
    purpose_meeting = fields.Char(string="Purpose of Meeting" ,tracking=True)
    participant_count = fields.Integer(string="Participant Count" ,tracking=True)



    @api.model
    def create(self, vals):
        vals['code'] = self.env['ir.sequence'].next_by_code('dsl.booking.room')
        res = super(BookingRoom, self).create(vals)
        return res



    @api.depends('start_time', 'end_time')
    def _compute_meeting_duration(self):
        for record in self:
            if record.start_time and record.end_time:
                try:

                    if not re.search('[:.]', record.start_time) or not re.search('[:.]', record.end_time):
                        raise ValidationError("Invalid time format. Use ' : ' or ' . ' for splitting the minutes.")

                    start_time = record.start_time if re.search('[:.]', record.start_time) else f"{record.start_time}:00"
                    end_time = record.end_time if re.search('[:.]', record.end_time) else f"{record.end_time}:00"

                    start_time_parts = re.split('[:.]', start_time)
                    end_time_parts = re.split('[:.]', end_time)

                    if len(start_time_parts) != 2:
                        raise ValueError(f"Start time format is incorrect: {record.start_time}")
                    if len(end_time_parts) != 2:
                        raise ValueError(f"End time format is incorrect: {record.end_time}")

                    start_hours, start_minutes = map(int, start_time_parts)
                    end_hours, end_minutes = map(int, end_time_parts)


                    start_time_minutes = start_hours * 60 + start_minutes
                    end_time_minutes = end_hours * 60 + end_minutes


                    duration_minutes = end_time_minutes - start_time_minutes
                    if duration_minutes < 0:
                        duration_minutes += 24 * 60


                    record.meeting_duration = duration_minutes / 60.0
                except ValueError as e:
                    record.meeting_duration = 0.0
            else:
                record.meeting_duration = 0.0
    


    @api.constrains('meeting_date', 'start_time', 'end_time', 'booking_room')
    def _check_conflicting_booking(self):
        for record in self:
            if record.state == 'draft' and record.meeting_date and record.start_time and record.end_time and record.booking_room:
                domain = [
                    ('id', '!=', record.id),
                    ('meeting_date', '=', record.meeting_date),
                    ('booking_room', '=', record.booking_room.id),
                    '|', '&',
                    ('start_time', '<', record.end_time),
                    ('end_time', '>', record.start_time),
                    ('start_time', '<', record.end_time),
                    ('end_time', '>', record.start_time)
                ]
                conflicting_records = self.search(domain)
                if conflicting_records:
                    raise ValidationError(("Conflicting booking found for the selected date, time, and meeting room. Please choose a different date/time or meeting room."))
    
    

    @api.constrains('meeting_date')
    def _check_past_date(self):
        for record in self:
            if record.meeting_date:
                current_date = datetime.now().date()
                if record.meeting_date < current_date:
                    raise ValidationError("You cannot save or request a booking for a past date.")

    

    def write(self, vals):
        if self.state == 'request' and any(field in vals for field in ['booking_room', 'meeting_date', 'start_time', 'end_time', 'booking_employee']):
            raise ValidationError("You cannot edit a booking that is in the 'Request' state.")

        if self.state == 'approve' and any(field in vals for field in ['state', 'booking_room', 'meeting_date', 'start_time', 'end_time', 'booking_employee']):
            raise ValidationError("You cannot edit a booking that is in the 'Approve' state.")

        return super(BookingRoom, self).write(vals)


    def draft(self):
        self.state = "draft"
    
    def request(self):
        self.state = "request"

    def approve(self):
        self.state = "approve"

    def reject(self):
        self.state = "reject"



class BookingRoomLines(models.Model):
    _name = 'dsl.booking.room.line'
    _description = 'Booking Room Line'
    


    booking_id = fields.Many2one('dsl.booking.room', string="Booking ID", ondelete='cascade')
    facility_name = fields.Many2one('dsl.meeting.facility', string="Room Facility")
    facility_quantity = fields.Float(string="Quantity")



class Dashboard(models.Model):
    _name = 'dsl.dashboard'
    _description = 'Dashboard'

    name = fields.Char(string='Name', default='Dashboard')
    total_meeting_rooms = fields.Integer(string='Total Meeting Rooms', compute='_compute_total_meeting_rooms')
    total_facilities = fields.Integer(string='Total Facilities', compute='_compute_total_facilities')
    today_bookings = fields.Integer(string='Today Bookings', compute='_compute_today_bookings')
    my_bookings = fields.Integer(string='My Bookings', compute='_compute_my_bookings')

    @api.depends()
    def _compute_total_meeting_rooms(self):
        for record in self:
            record.total_meeting_rooms = self.env['dsl.meeting.room'].search_count([])

    @api.depends()
    def _compute_total_facilities(self):
        for record in self:
            record.total_facilities = self.env['dsl.meeting.facility'].search_count([])

    @api.depends()
    def _compute_today_bookings(self):
        today = date.today()
        for record in self:
            record.today_bookings = self.env['dsl.booking.room'].search_count([('meeting_date', '=', today)])

    @api.depends()
    def _compute_my_bookings(self):
        my_id = self.env.user.employee_id.id
        for record in self:
            record.my_bookings = self.env['dsl.booking.room'].search_count([('booking_employee', '=', my_id)])

    
    def create_booking(self):
        view_id = self.env.ref('dsl_meeting_room.view_booking_room_form').id
        action = {
            'name': _('Book Meeting Room'),
            'view_mode': 'form',
            'res_model': 'dsl.booking.room',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'view_id': view_id,
        }
        return action
        pass

    def view_calendar(self):
        view_id = self.env.ref('dsl_meeting_room.view_booking_room_calendar').id
        action = {
            'name': _('Booking Room'),
            'view_mode': 'calendar',
            'res_model': 'dsl.booking.room',
            'type': 'ir.actions.act_window',
            'view_id': view_id,
        }
        return action
        pass


    def action_view_today_bookings(self):
        self.ensure_one()
        action = {
            'name': _('Today Bookings'),
            'view_mode': 'tree,form,calendar',
            'res_model': 'dsl.booking.room',
            'type': 'ir.actions.act_window',
            'context': {},
            'domain': [('meeting_date', '=', fields.Date.context_today(self))],
            'help': _('Click to view today bookings.'),
        }
        return action
        

    def action_view_my_bookings(self):
        self.ensure_one()
        action = {
            'name': _('My Bookings'),
            'view_mode': 'tree,form,calendar',
            'res_model': 'dsl.booking.room',
            'type': 'ir.actions.act_window',
            'context': {},
            'domain': [('booking_employee.user_id', '=', self.env.uid)],
            'help': _('Click to view your bookings.'),
        }
        return action

    def action_view_meeting_facility(self):
        self.ensure_one()
        action = {
            'name': _('Meeting Facility'),
            'view_mode': 'tree,form',
            'res_model': 'dsl.meeting.facility',
            'type': 'ir.actions.act_window',
            'domain': [],
            'context': {},
            'help': _('Add a new record.'),
        }
        return action


    def action_view_meeting_rooms(self):
        self.ensure_one()
        action = {
            'name': _('Meeting Rooms'),
            'view_mode': 'tree,form',
            'res_model': 'dsl.meeting.room',
            'type': 'ir.actions.act_window',
            'context': {},
            'domain': [],
            'help': _('Click to create a new meeting room.'),
        }
        return action
 



    

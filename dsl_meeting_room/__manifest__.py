# -*- coding: utf-8 -*-
{
    'name': "DSL Meeting Room Booking",

    'summary': """
        User can request meeting room and manager can approve""",

    'description': """
        User can request meeting room and manager can approve
    """,

    'author': "Ibrahim Khalil Ullah",
    'website': "https://daffodilsoft.com/",

    'category': 'HRM',
    'version': '0.1',

    
    'depends': ['base','mail','hr'],


    
    'data': [
        'data/ir_sequence.xml',
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/dsl_meeting_room.xml',
        'views/dsl_meeting_facility.xml',
        'views/dsl_booking_room.xml',
        'views/dsl_meeting_dashboard.xml',
    ],
    

}

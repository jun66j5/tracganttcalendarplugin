# -*- coding: utf-8 -*-
from trac.ticket import ITicketChangeListener, Ticket, ITicketManipulator
from trac.config import Option, Configuration
from trac.core import *


class CompleteTicketObserver(Component):
    implements(ITicketChangeListener)

    complete_conditions = Option('ganttcalendar', 'complete_conditions', '対応済,不正', u"""complete_fieldで指定した進捗率を100%にする解決方法のリスト""")
    complete_field = Option('ganttcalendar', 'complete_field', 'complete', u"""進捗率を設定したフィールド""")

    def __init__(self):
        pass

    def ticket_changed(self, ticket, comment, author, old_values):
        complete_conditions = Configuration.getlist(self.config,'ganttcalendar','complete_conditions',"'対応済,不正,重複'")
        complete_field = Configuration.get(self.config,'ganttcalendar','complete_field','complete')

        self.log.debug("complete_conditions: %s" % complete_conditions)
        self.log.debug("status: %s" % ticket.values['status'])
        self.log.debug("complete: %s" % ticket.values[complete_field])

        if complete_conditions == None or ticket.values['status'] != 'closed':
            return 

        complete_flag = False

        for cc in complete_conditions:
           if ticket.values['resolution'] == cc:
               complete_flag = True

        if complete_flag:
            ticket.values[complete_field] = 100
            db = self.env.get_db_cnx()
            cursor = db.cursor()
            save_custom_field_value(db, ticket.id, 'complete', ticket.values[complete_field])
            db.commit()

        self.log.debug("flag: %s" % complete_flag)
        self.log.debug("complete(after): %s" % ticket.values[complete_field])

def save_custom_field_value( db, ticket_id, field, value ):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM ticket_custom "
                   "WHERE ticket=%s and name=%s", (ticket_id, field))
    if cursor.fetchone():
        cursor.execute("UPDATE ticket_custom SET value=%s "
                       "WHERE ticket=%s AND name=%s",
                       (value, ticket_id, field))
    else:
        cursor.execute("INSERT INTO ticket_custom (ticket,name, "
                       "value) VALUES(%s,%s,%s)",
                       (ticket_id, field, value))


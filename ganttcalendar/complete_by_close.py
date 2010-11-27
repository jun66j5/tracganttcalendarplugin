# -*- coding: utf-8 -*-
from trac.ticket import ITicketChangeListener, Ticket, ITicketManipulator
from trac.config import Option
from trac.core import *
import datetime
from trac.util.translation import domain_functions

# i18n support for plugins, available since Trac r7705
# use _, tag_ and N_ as usual, e.g. _("this is a message text")
_, tag_, N_, add_domain = domain_functions('ganttcalendar', 
    '_', 'tag_', 'N_', 'add_domain')

class CompleteTicketObserver(Component):
    implements(ITicketChangeListener)

    complete_conditions = Option('ganttcalendar', 'complete_conditions', 'fixed, invalid', """The resolutions to change the ticket progress to 100% when ticket closed""")
    complete_field = Option('ganttcalendar', 'complete_field', 'complete', """Field define progress value for ticket.""")

    def __init__(self):
        import pkg_resources
        locale_dir = pkg_resources.resource_filename(__name__, 'locale')
        add_domain(self.env.path, locale_dir)

    def ticket_created(self, ticket):
        """Called when a ticket is created."""
        self.watch_complete(ticket)

    def ticket_changed(self, ticket, comment, author, old_values):
        """Called when a ticket is modified.

        `old_values` is a dictionary containing the previous values of the
        fields that have changed.
        """
        self.watch_complete(ticket, old_values)

    def ticket_deleted(self, ticket):
        """Called when a ticket is deleted."""
        pass


    def watch_complete(self, ticket, old_values={}):

        def readTicketValue(field, default=''):
            # for UPDATE: save_ticket_change
            if old_values.has_key(field):
                return old_values[field]
            # for INSERT: save_ticket_change
            else:
                cursor = self.env.get_db_cnx().cursor()
                cursor.execute("SELECT * FROM ticket_custom where ticket=%s and name=%s" , (ticket.id, field))
                val = cursor.fetchone()
                if val:
                    return val[2]
                return default
        ########################

        def writeTicketValue(field, oldvalue, newvalue):
            cl = ticket.get_changelog()
            if cl: # for ticket_changed
                most_recent_change = cl[-1];
                change_time = most_recent_change[0]
                author = most_recent_change[1]
            else:  # for ticket_created
                change_time = ticket.time_created
                author = ticket.values["reporter"]
            self.log.debug("oldvalue: '%s', newvalue: '%s'" % (oldvalue, newvalue))
            #self.log.debug("changelog: %s" % cl)
            db = self.env.get_db_cnx()
            if cl:
                save_ticket_change( db, ticket.id, author, change_time, field, oldvalue, newvalue, self.log)
            save_custom_field_value( db, ticket.id, field, newvalue)
            db.commit();
        ########################


        complete_field = self.config['ganttcalendar'].get('complete_field', default='complete') or 'complete'
        due_assign = ticket.values.get('due_assign')
        due_close  = ticket.values.get('due_close')
        complete   = ticket.values.get(complete_field)
        #self.log.debug("ticket.values: %s" % ticket.values)

        if not (due_assign or due_close) or (complete == None):
            return;

        oldstatus  = old_values.get('status')
        status     = ticket.values.get('status')
        resolution = ticket.values.get('resolution')
        complete_conditions = self.config['ganttcalendar'].getlist('complete_conditions', default='fixed, invalid')
        self.log.debug("oldstatus: %s, status: %s, resolution: %s, complete_conditions: %s" % (oldstatus, status, resolution, complete_conditions))

        # complete by close
        if (status == 'closed' and oldstatus) \
          and resolution in complete_conditions:
            writeTicketValue( complete_field, readTicketValue(complete_field), '100')
        # initial value
        elif complete == '':
            writeTicketValue( complete_field, readTicketValue(complete_field), '0')

    ########################


def identity(x):
    return x;

try:
    from trac import __version__
    import trac.util.datefmt
    if __version__ < '0.12':
        to_timestamp = trac.util.datefmt.to_timestamp
    else:
        to_timestamp = trac.util.datefmt.to_utimestamp
except Exception:
    to_timestamp = identity

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

DONTUPDATE = "DONTUPDATE"

def save_ticket_change( db, ticket_id, author, change_time, field, oldvalue, newvalue, log, dontinsert=False):
    """tries to save a ticket change,

       dontinsert means do not add the change if it didnt already exist
    """
    if type(change_time) == datetime.datetime:
        change_time = to_timestamp(change_time)
    cursor = db.cursor();
    sql = """SELECT * FROM ticket_change
             WHERE ticket=%s and author=%s and time=%s and field=%s"""

    cursor.execute(sql, (ticket_id, author, change_time, field))
    if cursor.fetchone():
        if oldvalue == DONTUPDATE:
            cursor.execute("""UPDATE ticket_change  SET  newvalue=%s
                       WHERE ticket=%s and author=%s and time=%s and field=%s""",
                           ( newvalue, ticket_id, author, change_time, field))

        else:
            cursor.execute("""UPDATE ticket_change  SET oldvalue=%s, newvalue=%s
                       WHERE ticket=%s and author=%s and time=%s and field=%s""",
                           (oldvalue, newvalue, ticket_id, author, change_time, field))
    else:
        if oldvalue == DONTUPDATE:
            oldvalue = '0'
        if not dontinsert:
            cursor.execute("""INSERT INTO ticket_change  (ticket,time,author,field, oldvalue, newvalue)
                        VALUES(%s, %s, %s, %s, %s, %s)""",
                           (ticket_id, change_time, author, field, oldvalue, newvalue))

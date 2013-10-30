# -*- coding: utf-8 -*-

import time
from datetime import date

from trac.core import Component, implements, TracError
from trac.ticket import ITicketManipulator
from trac.util.datefmt import format_date

from ganttcalendar.translation import _


class TicketValidator(Component):

    implements(ITicketManipulator)

    def prepare_ticket(req, ticket, fields, actions):
        """not currently called"""

    def validate_ticket(self, req, ticket):
        """Validate a ticket after it's been populated from user input.

        Must return a list of `(field, message)` tuples, one for each problem
        detected. `field` can be `None` to indicate an overall problem with the
        ticket. Therefore, a return value of `[]` means everything is OK."""
        errors = []


        # due_assign, due_close field
        dueDate     = {'due_assign':None, 'due_close':None}
        format      = str(self.config['ganttcalendar'].get('format', default='%Y/%m/%d')) or '%Y/%m/%d'
        format_hint = format.replace('%Y', 'YYYY', 1).replace('%y', 'YY', 1) \
                            .replace('%m', 'MM', 1).replace('%d', 'DD', 1)

        for field in ('due_assign', 'due_close'):
            due = ticket.values.get(field)
            if due:
                try:
                    if isinstance(due, str):
                        t = time.strptime(due, format)
                        dueDate[field]       = date( t[0],t[1],t[2])
                        ticket.values[field] = format_date( dueDate[field], format)
                    else:
                        dueDate[field]       = due
                except( TracError, ValueError, TypeError):
                    dueDate[field]       = None
                    label = self.config['ticket-custom'].get(field+'.label', default='')
                    errors.append(( u"%s(%s)" % (label, field), _("'%s' is invalid date format. Please input format as %s.") % (due, format_hint) ))

        if (dueDate['due_assign'] and dueDate['due_close']) \
          and (dueDate['due_assign'] > dueDate['due_close']):

            label_close  = self.config['ticket-custom'].get('due_close.label', default=_('Start date'))
            label_assign = self.config['ticket-custom'].get('due_assign.label', default=_('End date'))
            errors.append(( u"%s(due_close)" % label_close,
              _("%s '%s' must be after %s '%s'.") % (label_close, ticket.values['due_close'], label_assign, ticket.values['due_assign']) ))

        # complete field
        complete_field = self.config['ganttcalendar'].get('complete_field', default='complete') or 'complete'
        complete = ticket.values.get(complete_field)

        if complete:
            try:
                n = int(complete)
                if n <0 or n >100: raise Exception
                ticket.values[complete_field] = str(n)
            except:
                label = self.config['ticket-custom'].get(complete_field+'.label', default=_('Progress') )
                errors.append(( u"%s(%s)" % (label, complete_field), _("'%s' is invalid value. It must be integer in the range from 0 to 100.") % complete ))

        return errors

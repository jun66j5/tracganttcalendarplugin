# -*- coding: utf-8 -*-
import re, calendar, time, sys
from datetime import datetime, date, timedelta
from genshi.builder import tag

from trac.core import *
from trac.web import IRequestHandler
from trac.web.chrome import INavigationContributor, ITemplateProvider, \
                            add_script, add_stylesheet
from trac.util.datefmt import to_datetime, format_date, parse_date

from trac.ticket.api import TicketSystem
from trac.util.translation import _

class TicketGanttChartPlugin(Component):
    implements(INavigationContributor, IRequestHandler, ITemplateProvider)

    substitutions = ['$USER']

    # _get_constraints: internal method
    def _get_constraints(self, req):
        constraints = {}
        field_names = [f['name'] for f in self.ticket_fields]
        field_names.append('id')

        # For clients without JavaScript, we remove constraints here if
        # requested
        remove_constraints = {}
        to_remove = [k[10:] for k in req.args.keys()
                     if k.startswith('rm_filter_')]
        if to_remove: # either empty or containing a single element
            match = re.match(r'(\w+?)_(\d+)$', to_remove[0])
            if match:
                remove_constraints[match.group(1)] = int(match.group(2))
            else:
                remove_constraints[to_remove[0]] = -1

        for field in [k for k in req.args.keys() if k in field_names]:
            vals = req.args[field]
            if not isinstance(vals, (list, tuple)):
                vals = [vals]
            if vals:
                mode = req.args.get(field + '_mode')
                if mode:
                    vals = [mode + x for x in vals]
                if field in remove_constraints:
                    idx = remove_constraints[field]
                    if idx >= 0:
                        del vals[idx]
                        if not vals:
                            continue
                    else:
                        continue
                constraints[field] = vals

        return constraints
    
    # INavigationContributor methods
    def get_active_navigation_item(self, req):
        return 'ticketgantt'
    
    def get_navigation_items(self, req):
        if req.perm.has_permission('TICKET_VIEW'):
            yield ('mainnav', 'ticketgantt',tag.a(u'ガントチャート', href=req.href.ticketgantt()))

    # IRequestHandler methods
    def match_request(self, req):
        return re.match(r'/ticketgantt(?:_trac)?(?:/.*)?$', req.path_info)

    def adjust( self, x_start, x_end, term):
        if x_start > term or x_end < 0:
            x_start= done_end= None
        else:
            if x_start < 0:
                x_start= 0
            if x_end > term:
                x_end= term
        return x_start, x_end

    def process_request(self, req):
        req.perm.assert_permission('TICKET_VIEW')
        req.perm.require('TICKET_VIEW')
        self.log.debug("process_request " + str(globals().get('__file__')))
        ymonth = req.args.get('month')
        yyear = req.args.get('year')
        baseday = req.args.get('baseday')
        selected_milestone = req.args.get('selected_milestone')
        selected_component = req.args.get('selected_component')
        show_my_ticket = req.args.get('show_my_ticket')
        show_closed_ticket = req.args.get('show_closed_ticket')
        sorted_field = req.args.get('sorted_field')
        if sorted_field == None:
            sorted_field = 'component'

        if baseday != None:
            baseday = parse_date( baseday).date()
        else:
            baseday = date.today()

        cday = date.today()
        if not (not ymonth or not yyear):
            cday = date(int(yyear),int(ymonth),1)

        # cal next month
        nmonth = cday.replace(day=1).__add__(timedelta(days=32)).replace(day=1)

        # cal previous month
        pmonth = cday.replace(day=1).__add__(timedelta(days=-1)).replace(day=1)

        first_date= cday.replace(day=1)
        days_term= (first_date.__add__(timedelta(100)).replace(day=1)-first_date).days

        # process ticket
        db = self.env.get_db_cnx()
        cursor = db.cursor();
        sql = ""
        condition=""
        if show_my_ticket == 'on':
            if condition != "":
                condition += " AND "
            condition += "owner ='" + req.authname + "'"
        if show_closed_ticket != 'on':
            if condition != "":
                condition += " AND "
            condition += "status <> 'closed'"
        if selected_milestone != None and selected_milestone !="":
            if condition != "":
                condition += " AND "
            condition += "milestone ='" + selected_milestone +"'"
        if selected_component != None and selected_component !="":
            if condition != "":
                condition += " AND "
            condition += "component ='" + selected_component +"'"

        self.ticket_fields = TicketSystem(self.env).get_ticket_fields()
        fields = {}
        for field in self.ticket_fields:
            if field['name'] == 'owner' and field['type'] == 'select':
                # Make $USER work when restrict_owner = true
                field['options'].insert(0, '$USER')
            field_data = {}
            field_data.update(field)
            del field_data['name']
            fields[field['name']] = field_data

        labels = dict([(f['name'], f['label']) for f in self.ticket_fields])
        labels['changetime'] = _('Modified')
        labels['time'] = _('Created')

        modes = {}
        modes['text'] = [
            {'name': _("contains"), 'value': "~"},
            {'name': _("doesn't contain"), 'value': "!~"},
            {'name': _("begins with"), 'value': "^"},
            {'name': _("ends with"), 'value': "$"},
            {'name': _("is"), 'value': ""},
            {'name': _("is not"), 'value': "!"}
        ]
        modes['textarea'] = [
            {'name': _("contains"), 'value': "~"},
            {'name': _("doesn't contain"), 'value': "!~"},
        ]
        modes['select'] = [
            {'name': _("is"), 'value': ""},
            {'name': _("is not"), 'value': "!"}
        ]

        constraints = self._get_constraints(req)
        
        # Join with ticket_custom table as necessary
        custom_join = ""
        custom_fields = [f['name'] for f in self.ticket_fields if 'custom' in f]
        for k in [k for k in constraints if k in custom_fields]:
           custom_join += (" LEFT OUTER JOIN ticket_custom AS %s ON " \
                      "(t.id=%s.ticket AND %s.name='%s')" % (k, k, k, k))
        
        def get_constraint_sql(name, value, mode, neg):
            if name not in custom_fields:
                name = 't.' + name
            else:
                name = name + '.value'
            value = value[len(mode) + neg:]

            if mode == '':
                return ("COALESCE(%s,'')%s=%%s" % (name, neg and '!' or ''),
                        value)
            if not value:
                return None
            db = self.env.get_db_cnx()
            value = db.like_escape(value)
            if mode == '~':
                value = '%' + value + '%'
            elif mode == '^':
                value = value + '%'
            elif mode == '$':
                value = '%' + value
            return ("COALESCE(%s,'') %s%s" % (name, neg and 'NOT ' or '',
                                              db.like()),
                    value)

        constraints_data = {}
        for k, v in constraints.items():
            constraint = {'values': [], 'mode': ''}
            for val in v:
                neg = val.startswith('!')
                if neg:
                    val = val[1:]
                mode = ''
                if val[:1] in ('~', '^', '$') \
                                    and not val in self.substitutions:
                    mode, val = val[:1], val[1:]
                constraint['mode'] = (neg and '!' or '') + mode
                constraint['values'].append(val)
            constraints_data[k] = constraint

        clauses = []
        args = []
        for k, v in constraints.items():
            if req:
                v = [val.replace('$USER', req.authname) for val in v]
            # Determine the match mode of the constraint (contains,
            # starts-with, negation, etc.)
            neg = v[0].startswith('!')
            mode = ''
            if len(v[0]) > neg and v[0][neg] in ('~', '^', '$'):
                mode = v[0][neg]

            # Special case id ranges
            if k == 'id':
                ranges = Ranges()
                for r in v:
                    r = r.replace('!', '')
                    ranges.appendrange(r)
                ids = []
                id_clauses = []
                for a,b in ranges.pairs:
                    if a == b:
                        ids.append(str(a))
                    else:
                        id_clauses.append('id BETWEEN %s AND %s')
                        args.append(a)
                        args.append(b)
                if ids:
                    id_clauses.append('id IN (%s)' % (','.join(ids)))
                if id_clauses:
                    clauses.append('%s(%s)' % (neg and 'NOT ' or '',
                                               ' OR '.join(id_clauses)))
            # Special case for exact matches on multiple values
            elif not mode and len(v) > 1:
                if k not in custom_fields:
                    col = 't.' + k
                else:
                    col = k + '.value'
                clauses.append("COALESCE(%s,'') %sIN (%s)"
                               % (col, neg and 'NOT ' or '',
                                  ','.join(['%s' for val in v])))
                args += [val[neg:] for val in v]
            elif len(v) > 1:
                constraint_sql = filter(None,
                                        [get_constraint_sql(k, val, mode, neg)
                                         for val in v])
                if not constraint_sql:
                    continue
                if neg:
                    clauses.append("(" + " AND ".join(
                        [item[0] for item in constraint_sql]) + ")")
                else:
                    clauses.append("(" + " OR ".join(
                        [item[0] for item in constraint_sql]) + ")")
                args += [item[1] for item in constraint_sql]
            elif len(v) == 1:
                constraint_sql = get_constraint_sql(k, v[0], mode, neg)
                if constraint_sql:
                    clauses.append(constraint_sql[0])
                    args.append(constraint_sql[1])

        clauses = filter(None, clauses)
        if condition != "":
            condition = "WHERE " + condition + " "
            
            if clauses:
                condition += "AND "
                condition += (" AND ".join(clauses))
        else:
            if clauses:
                condition = "WHERE " + (" AND ".join(clauses))

        sql = ("SELECT id, type, summary, owner, t.description, status, a.value, c.value, cmp.value, milestone, component "
                "FROM ticket t "
                "JOIN ticket_custom a ON a.ticket = t.id AND a.name = 'due_assign' "
                "JOIN ticket_custom c ON c.ticket = t.id AND c.name = 'due_close' "
                "JOIN ticket_custom cmp ON cmp.ticket = t.id AND cmp.name = 'complete' "
                "%s %s ORDER by %s , a.value ") % (custom_join, condition, sorted_field)
        
        self.log.debug(sql)
        cursor.execute(sql, args)

        tickets=[]
        for id, type, summary, owner, description, status, due_assign, due_close, complete, milestone, component in cursor:
            due_assign_date = None
            due_close_date = None
            try:
                due_assign_date = parse_date(due_assign).date()
            except ( TracError, ValueError, TypeError):
                continue
            try:
                due_close_date = parse_date(due_close).date()
            except ( TracError, ValueError, TypeError):
                continue
            if complete != None and len(complete)>1 and complete[len(complete)-1]=='%':
                complete = complete[0:len(complete)-1]
            try:
                if int(complete) >100:
                    complete = "100"
            except:
                complete = "0"
            complete = int(complete)
            if due_assign_date > due_close_date:
                continue
            if milestone == None or milestone == "":
                milestone = "*"
            if component == None or component == "":
                component = "*"
            ticket = {'id':id, 'type':type, 'summary':summary, 'owner':owner, 'description': description, 'status':status,
                    'due_assign':due_assign_date, 'due_close':due_close_date, 'complete': complete, 
                    'milestone': milestone,'component': component}
            #calc chart
            base = (baseday -first_date).days + 1
            done_start= done_end= None
            late_start= late_end= None
            todo_start= todo_end= None
            all_start=(due_assign_date-first_date).days
            all_end=(due_close_date-first_date).days + 1
            done_start= all_start
            done_end= done_start + (all_end - all_start)*int(complete)/100.0
            if all_end <= base < days_term:
                late_start= done_end
                late_end= all_end
            elif done_end <= base < all_end:
                late_start= done_end
                late_end= todo_start= base
                todo_end= all_end
            else:
                todo_start= done_end
                todo_end= all_end
            #
            done_start, done_end= self.adjust(done_start,done_end,days_term)
            late_start, late_end= self.adjust(late_start,late_end,days_term)
            todo_start, todo_end= self.adjust(todo_start,todo_end,days_term)
            all_start, all_end= self.adjust(all_start,all_end,days_term)

            if done_start != None:
                ticket.update({'done_start':done_start,'done_end':done_end})
            if late_start != None:
                ticket.update({'late_start':late_start,'late_end':late_end})
            if todo_start != None:
                ticket.update({'todo_start':todo_start,'todo_end':todo_end})
            if all_start != None:
                ticket.update({'all_start':all_start})

            self.log.debug(ticket)
            tickets.append(ticket)

        # milestones
        milestones = {'':None}
        sql = ("SELECT name, due, completed, description FROM milestone")
        self.log.debug(sql)
        cursor.execute(sql)
        for name, due, completed, description in cursor:
            due_date = to_datetime(due, req.tz).date()
            item = { 'due':due_date, 'completed':completed != 0,'description':description}
            if due==0:
                del item['due']
            milestones.update({name:item})
        # componet
        components = [{}]
        sql = ("SELECT name FROM component")
        self.log.debug(sql)
        cursor.execute(sql)
        for name, in cursor:
            components.append({'name':name})

        holidays = {}
        sql = "SELECT date,description from holiday"
        try:
            cursor.execute(sql)
            for hol_date,hol_desc in cursor:
                holidays[format_date(parse_date(hol_date, tzinfo=req.tz))]= hol_desc
        except:
            pass

        data = {'baseday': baseday, 'current':cday, 'prev':pmonth, 'next':nmonth}
        data.update({'show_my_ticket': show_my_ticket, 'show_closed_ticket': show_closed_ticket, 'sorted_field': sorted_field})
        data.update({'selected_milestone':selected_milestone,'selected_component': selected_component})
        data.update({'tickets':tickets,'milestones':milestones,'components':components})
        data.update({'holidays':holidays,'first_date':first_date,'days_term':days_term})
        data.update({'parse_date':parse_date,'format_date':format_date,'calendar':calendar})
        data.update({'fields':fields, 'constraints':constraints_data, 'labels':labels, 'modes': modes})

        add_stylesheet(req, 'common/css/report.css')
        add_script(req, 'common/js/query.js')

        return 'gantt.html', data, None

    def get_templates_dirs(self):
        from pkg_resources import resource_filename
        return [resource_filename(__name__, 'templates')]

    def get_htdocs_dirs(self):
        from pkg_resources import resource_filename
        return [('tc', resource_filename(__name__, 'htdocs'))]

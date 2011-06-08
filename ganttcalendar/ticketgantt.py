# -*- coding: utf-8 -*-
import re, calendar, time, sys
from datetime import datetime, date, timedelta
from genshi.builder import tag

from trac.core import *
from trac.web import IRequestHandler
from trac.web.chrome import INavigationContributor, ITemplateProvider, \
                            add_script, add_stylesheet, add_script_data, add_warning
from trac.util.datefmt import to_datetime, to_utimestamp

from trac.ticket.api import TicketSystem
#from trac.util.translation import _
from trac.config import IntOption, BoolOption, Option
from trac import __version__
from trac.util.translation import domain_functions


from trac.util import Ranges

# i18n support for plugins, available since Trac r7705
# use _, tag_ and N_ as usual, e.g. _("this is a message text")
_, tag_, N_, add_domain = domain_functions('ganttcalendar', 
    '_', 'tag_', 'N_', 'add_domain')

month_tbl = {
  1: 'January',
  2: 'February',
  3: 'March',
  4: 'April',
  5: 'May',
  6: 'June',
  7: 'July',
  8: 'August',
  9: 'September',
  10: 'October',
  11: 'November',
  12: 'December'
}

class TicketGanttChartPlugin(Component):
    implements(INavigationContributor, IRequestHandler, ITemplateProvider)

    first_day = IntOption('ganttcalendar', 'first_day', '0', """Begin of week:  0 == Sunday, 1 == Monday (default: 0)""")
    show_ticket_summary = BoolOption('ganttcalendar', 'show_ticket_summary', 'false', """Show ticket summary at gantchart bar. (default: false)""")
    normal_mode = IntOption('ganttcalendar', 'default_zoom_mode', '3', """Default zoom mode in gantchar. (default: 3)""")
    format = Option('ganttcalendar', 'format', '%Y/%m/%d', """Date format for due assign and due finish""")

    substitutions = ['$USER']
    clause_re = re.compile(r'(?P<clause>\d+)_(?P<field>.+)$')
    remove_re = re.compile(r'rm_filter_\d+_(.+)_(\d+)$')
    add_re = re.compile(r'add_(\d+)$')

    def __init__(self):
        import pkg_resources
        locale_dir = pkg_resources.resource_filename(__name__, 'locale')
        add_domain(self.env.path, locale_dir)

    # _get_constraints: internal method
    def _get_constraints(self, req=None, arg_list=[]):
        fields = TicketSystem(self.env).get_ticket_fields()
        synonyms = TicketSystem(self.env).get_field_synonyms()
        fields = dict((f['name'], f) for f in fields)
        fields['id'] = {'type': 'id'}
        fields.update((k, fields[v]) for k, v in synonyms.iteritems())

        clauses = []
        if req is not None:
            # For clients without JavaScript, we remove constraints here if
            # requested
            remove_constraints = {}
            for k in req.args:
                match = self.remove_re.match(k)
                if match:
                    field = match.group(1)
                    if fields[field]['type'] == 'radio':
                        index = -1
                    else:
                        index = int(match.group(2))
                    remove_constraints[k[10:match.end(1)]] = index
            
            # Get constraints from form fields, and add a constraint if
            # requested for clients without JavaScript
            add_num = None
            constraints = {}
            for k, vals in req.args.iteritems():
                match = self.add_re.match(k)
                if match:
                    add_num = match.group(1)
                    continue
                match = self.clause_re.match(k)
                if not match:
                    continue
                field = match.group('field')
                clause_num = int(match.group('clause'))
                if field not in fields:
                    continue
                if not isinstance(vals, (list, tuple)):
                    vals = [vals]
                if vals:
                    mode = req.args.get(k + '_mode')
                    if mode:
                        vals = [mode + x for x in vals]
                    if fields[field]['type'] == 'time':
                        ends = req.args.getlist(k + '_end')
                        if ends:
                            vals = [start + '..' + end 
                                    for (start, end) in zip(vals, ends)]
                    if k in remove_constraints:
                        idx = remove_constraints[k]
                        if idx >= 0:
                            del vals[idx]
                            if not vals:
                                continue
                        else:
                            continue
                    field = synonyms.get(field, field)
                    clause = constraints.setdefault(clause_num, {})
                    clause.setdefault(field, []).extend(vals)
            if add_num is not None:
                field = req.args.get('add_filter_' + add_num,
                                     req.args.get('add_clause_' + add_num))
                if field:
                    clause = constraints.setdefault(int(add_num), {})
                    modes = self.get_modes().get(fields[field]['type'])
                    mode = modes and modes[0]['value'] or ''
                    clause.setdefault(field, []).append(mode)
            clauses.extend(each[1] for each in sorted(constraints.iteritems()))
        
        # Get constraints from query string
        clauses.append({})
        for field, val in arg_list or req.arg_list:
            if field == "or":
                clauses.append({})
            elif field in fields:
                clauses[-1].setdefault(field, []).append(val)
        clauses = filter(None, clauses)
        
        return clauses

    @staticmethod
    def get_modes():
        modes = {}
        modes['text'] = [
            {'name': _("contains"), 'value': "~"},
            {'name': _("doesn't contain"), 'value': "!~"},
            {'name': _("begins with"), 'value': "^"},
            {'name': _("ends with"), 'value': "$"},
            {'name': _("is"), 'value': ""},
            {'name': _("is not"), 'value': "!"},
        ]
        modes['textarea'] = [
            {'name': _("contains"), 'value': "~"},
            {'name': _("doesn't contain"), 'value': "!~"},
        ]
        modes['select'] = [
            {'name': _("is"), 'value': ""},
            {'name': _("is not"), 'value': "!"},
        ]
        modes['id'] = [
            {'name': _("is"), 'value': ""},
            {'name': _("is not"), 'value': "!"},
        ]
        return modes
    
    # INavigationContributor methods
    def get_active_navigation_item(self, req):
        return 'ticketgantt'
    
    def get_navigation_items(self, req):
        if req.perm.has_permission('TICKET_VIEW'):
            yield ('mainnav', 'ticketgantt',tag.a(_('Gantt chart'), href=req.href.ticketgantt()))

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
            sorted_field = 'milestone'
        show_ticket_summary = req.args.get('show_ticket_summary')
        show_ticket_status = req.args.get('show_ticket_status')

        ts = TicketSystem(self.env)
        if not 'complete' in ts.get_custom_fields():
            add_warning(req, _("'complete' field is not defined. Please define it."))
        normal_mode  = req.args.get('normal')
        current_mode = req.args.get('zoom')
        zoom_modes   = [1, 2, 3, 4, 5, 6] # zoom modes
        if normal_mode == None:
            normal_mode  = self.config['ganttcalendar'].getint('default_zoom_mode', default=3)
            current_mode = normal_mode = zoom_modes[normal_mode % 6 -1]
        else:
            current_mode = zoom_modes[int(current_mode) % 6 -1]
        zoom_months = {1:1, 2:2, 3:3, 4:4, 5:5, 6:6} # zoom mode: months term
        months_term = zoom_months[current_mode]

        # first_day=   0: sunday (default) 1: monday 2: tuesday 3: wednesday 4: thursday 5: friday 6: saturday
        first_day = self.config['ganttcalendar'].getint('first_day', default=0)
        weekdays = [6, 0, 1, 2, 3, 4, 5]
        first_wkday = weekdays[first_day % 7]
        # first_wkday= 0: monday 1: tuesday 2: wednesday 3: thursday 4: friday 5: saturday 6: sunday (default)

        dateFormat = str(self.config['ganttcalendar'].get('format', default='%Y/%m/%d') or '%Y/%m/%d')

        if baseday != None:
            t = time.strptime(baseday, dateFormat)
            baseday = date(t[0] ,t[1] ,t[2])
        else:
            baseday = date.today()
            show_ticket_status = 'on'
            show_ticket_summary = self.config['ganttcalendar'].getbool('show_ticket_summary', default='false')
            if show_ticket_summary:
                show_ticket_summary = 'on'
            else:
                show_ticket_summary = None

        if show_ticket_summary:
            ticket_margin = 12
        else:
            ticket_margin = 0

        cday = date.today()
        if not (not ymonth or not yyear):
            cday = date(int(yyear),int(ymonth),1)

        # cal next month
        nmonth = cday.replace(day=1).__add__(timedelta(days=32)).replace(day=1)

        # cal previous month
        pmonth = cday.replace(day=1).__add__(timedelta(days=-1)).replace(day=1)

        first_date= cday.replace(day=1)
        days_term= (first_date.__add__(timedelta(months_term*32)).replace(day=1)-first_date).days

        # process ticket
        db = self.env.get_db_cnx()
        cursor = db.cursor();
        sql = ""
        condition=""

        # filter for Trac 0.12.1
        ### __init__
        self.fields = TicketSystem(self.env).get_ticket_fields()
        self.time_fields = set(f['name'] for f in self.fields
                               if f['type'] == 'time')

        self.constraints = self._get_constraints(req)

        constraint_cols = {}
        for clause in self.constraints:
            for k, v in clause.iteritems():
                constraint_cols.setdefault(k, []).append(v)
        self.constraint_cols = constraint_cols

        ### display_html
        owner_field = [f for f in self.fields if f['name'] == 'owner']
        if owner_field:
            TicketSystem(self.env).eventually_restrict_owner(owner_field[0])

        ###### template_data
        clauses_data = []
        for clause in self.constraints:
            constraints = {}
            for k, v in clause.items():
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
                constraints[k] = constraint
            clauses_data.append(constraints)

        fields_data = {'id': {'type': 'id', 'label': _("Ticket")}}
        for field in self.fields:
            name = field['name']
            if name == 'owner' and field['type'] == 'select':
                # Make $USER work when restrict_owner = true
                field = field.copy()
                field['options'].insert(0, '$USER')
            fields_data[name] = field

        ###### get_sql
        custom_join = ""
        custom_fields = [f['name'] for f in self.fields if 'custom' in f]

        # Join with ticket_custom table as necessary
        for k in [k for k in self.constraint_cols if k in custom_fields]:
            qk = db.quote(k)
            custom_join += (" LEFT OUTER JOIN ticket_custom AS %s ON " \
                            "(t.id=%s.ticket AND %s.name='%s')" % (qk, qk, qk, k))

        def get_timestamp(date):
            if date:
                try:
                    t = time.strptime(date, dateFormat)
                    return to_utimestamp(date(t[0] ,t[1] ,t[2]))
                except TracError, e:
                    errors.append(unicode(e))
            return None
        ########################
        def get_constraint_sql(name, value, mode, neg):
            if name not in custom_fields:
                col = 't.' + name
            else:
                col = '%s.value' % db.quote(name)
            value = value[len(mode) + neg:]

            if name in self.time_fields:
                if '..' in value:
                    (start, end) = [each.strip() for each in 
                                    value.split('..', 1)]
                else:
                    (start, end) = (value.strip(), '')
                col_cast = db.cast(col, 'int64')
                start = get_timestamp(start)
                end = get_timestamp(end)
                if start is not None and end is not None:
                    return ("%s(%s>=%%s AND %s<%%s)" % (neg and 'NOT ' or '',
                                                        col_cast, col_cast),
                            (start, end))
                elif start is not None:
                    return ("%s%s>=%%s" % (neg and 'NOT ' or '', col_cast),
                            (start, ))
                elif end is not None:
                    return ("%s%s<%%s" % (neg and 'NOT ' or '', col_cast),
                            (end, ))
                else:
                    return None
                
            if mode == '~' and name == 'keywords':
                words = value.split()
                clauses, args = [], []
                for word in words:
                    cneg = ''
                    if word.startswith('-'):
                        cneg = 'NOT '
                        word = word[1:]
                        if not word:
                            continue
                    clauses.append("COALESCE(%s,'') %s%s" % (col, cneg,
                                                             db.like()))
                    args.append('%' + db.like_escape(word) + '%')
                if not clauses:
                    return None
                return ((neg and 'NOT ' or '')
                        + '(' + ' AND '.join(clauses) + ')', args)

            if mode == '':
                return ("COALESCE(%s,'')%s=%%s" % (col, neg and '!' or ''),
                        (value, ))

            if not value:
                return None
            value = db.like_escape(value)
            if mode == '~':
                value = '%' + value + '%'
            elif mode == '^':
                value = value + '%'
            elif mode == '$':
                value = '%' + value
            return ("COALESCE(%s,'') %s%s" % (col, neg and 'NOT ' or '',
                                              db.like()),
                    (value, ))
        ########################
        def get_clause_sql(constraints):
            db = self.env.get_db_cnx()
            clauses = []
            for k, v in constraints.iteritems():
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
                        try:
                            ranges.appendrange(r)
                        except Exception:
                            errors.append(_('Invalid ticket id list: '
                                            '%(value)s', value=r))
                    ids = []
                    id_clauses = []
                    for a, b in ranges.pairs:
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
                elif not mode and len(v) > 1 and k not in self.time_fields:
                    if k not in custom_fields:
                        col = 't.' + k
                    else:
                        col = '%s.value' % db.quote(k)
                    clauses.append("COALESCE(%s,'') %sIN (%s)"
                                   % (col, neg and 'NOT ' or '',
                                      ','.join(['%s' for val in v])))
                    args.extend([val[neg:] for val in v])
                elif v:
                    constraint_sql = [get_constraint_sql(k, val, mode, neg)
                                      for val in v]
                    constraint_sql = filter(None, constraint_sql)
                    if not constraint_sql:
                        continue
                    if neg:
                        clauses.append("(" + " AND ".join(
                            [item[0] for item in constraint_sql]) + ")")
                    else:
                        clauses.append("(" + " OR ".join(
                            [item[0] for item in constraint_sql]) + ")")
                    for item in constraint_sql:
                        args.extend(item[1])
            return " AND ".join(clauses)
        ########################

        # Disable owner Option
        if self.constraint_cols.has_key('owner'):
            show_my_ticket = None
        elif show_my_ticket == 'on':
            if condition != "":
                condition += " AND "
            condition += "owner ='" + req.authname + "'"
        # Sync resolution Filter
        if self.constraint_cols.has_key('resolution'):
            show_closed_ticket = 'on'
        # Sync status Filter
        elif self.constraint_cols.has_key('status'):
            if [li for li in self.constraint_cols['status']
                     if 'closed' in li]:
                show_closed_ticket = 'on'
            else:
                show_closed_ticket = None
        elif show_closed_ticket != 'on':
            if condition != "":
                condition += " AND "
            condition += "status <> 'closed'"
        # Disable milestone Option
        if self.constraint_cols.has_key('milestone'):
            selected_milestone = None
        elif selected_milestone != None and selected_milestone !="":
            if condition != "":
                condition += " AND "
            condition += "milestone ='" + selected_milestone +"'"
        # Disable component Option
        if self.constraint_cols.has_key('component'):
            selected_component = None
        elif selected_component != None and selected_component !="":
            if condition != "":
                condition += " AND "
            condition += "component ='" + selected_component +"'"

        args = []
        errors = []
        clauses = filter(None, (get_clause_sql(c) for c in self.constraints))
        if condition != "":
            condition = "WHERE " + condition + " "
            
            if clauses:
                condition += "AND ( "
                condition += (" OR ".join('(%s)' % c for c in clauses)) + " )"
        else:
            if clauses:
                condition = "WHERE " + (" OR ".join('(%s)' % c for c in clauses))

        sql = ("SELECT id, type, summary, owner, t.description, status, resolution, priority, a.value, c.value, cmp.value, est.value, tot.value, milestone, component "
                "FROM ticket t "
                "JOIN ticket_custom a ON a.ticket = t.id AND a.name = 'due_assign' "
                "JOIN ticket_custom c ON c.ticket = t.id AND c.name = 'due_close' "
                "JOIN ticket_custom cmp ON cmp.ticket = t.id AND cmp.name = 'complete' "
                "LEFT OUTER JOIN ticket_custom est ON est.ticket = t.id AND est.name = 'estimatedhours' "
                "LEFT OUTER JOIN ticket_custom tot ON tot.ticket = t.id AND tot.name = 'totalhours' "
                "%s %s ORDER by %s , a.value ") % (custom_join, condition, sorted_field)
        
        self.log.debug(sql)
        #self.log.debug(custom_join)
        #self.log.debug(condition)
        self.log.debug(clauses)
        self.log.debug(args)

        if not errors:
            cursor.execute(sql, args)
        else:
            for error in errors:
                add_warning(req, error)

        sum_estimatedhours = 0.0
        sum_totalhours = 0.0
        sum_est_isNone = True

        tickets=[]
        for id, type, summary, owner, description, status, resolution, priority, due_assign, due_close, complete, estimatedhours, totalhours, milestone, component in cursor:
            due_assign_date = None
            due_close_date = None
            try:
                t = time.strptime(due_assign, dateFormat)
                due_assign_date = date(t[0],t[1],t[2])
            except ( TracError, ValueError, TypeError):
                continue
            try:
                t = time.strptime(due_close, dateFormat)
                due_close_date = date(t[0],t[1],t[2])
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
            # time tracking
            if estimatedhours != None:
                estimatedhours = float(estimatedhours)
                sum_estimatedhours += estimatedhours
                sum_est_isNone = False
            if totalhours != None:
                totalhours = float(totalhours)
                sum_totalhours += totalhours
            else: totalhours = 0.0
            ticket = {'id':id, 'type':type, 'summary':summary, 'owner':owner, 'description': description, 'status':status,
                    'resolution':resolution, 'priority':priority,
                    'due_assign':due_assign_date, 'due_close':due_close_date, 'complete': complete, 
                    'estimatedhours':estimatedhours, 'totalhours':totalhours,
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
            if all_end <= base:
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
                ticket.update({'all_start':all_start,'all_end':all_end})

            self.log.debug(ticket)
            tickets.append(ticket)
        # time tracking
        if sum_est_isNone: sum_estimatedhours = None

        # milestones
        milestones = {'':None}
        sql = ("SELECT name, due, completed, description FROM milestone")
        self.log.debug(sql)
        cursor.execute(sql)
        for name, due, completed, description in cursor:
            due_date = None
            if due!=0:
                due_date = to_datetime(due, req.tz).date()
            item = { 'due':due_date, 'completed':completed != 0,'description':description}
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
                holidays[hol_date]= hol_desc
        except:
            pass

        data = {'baseday': baseday, 'current':cday, 'prev':pmonth, 'next':nmonth, 'month_tbl': month_tbl}
        data.update({'show_my_ticket': show_my_ticket, 'show_closed_ticket': show_closed_ticket, 'sorted_field': sorted_field})
        data.update({'show_ticket_summary': show_ticket_summary, 'show_ticket_status': show_ticket_status, 'ti_mrgn': ticket_margin})
        data.update({'selected_milestone':selected_milestone,'selected_component': selected_component})
        data.update({'tickets':tickets,'milestones':milestones,'components':components})
        data.update({'sum_estimatedhours':sum_estimatedhours, 'sum_totalhours':sum_totalhours})
        data.update({'holidays':holidays,'first_date':first_date,'days_term':days_term})
        data.update({'calendar':calendar})
        data.update({'dateFormat': dateFormat ,'first_wkday':first_wkday,'normal':normal_mode,'zoom':current_mode, '_':_})
        data.update({'fields':fields_data, 'clauses':clauses_data, 'modes': self.get_modes()})

        ### display_html
        properties = dict((name, dict((key, field[key])
                                      for key in ('type', 'label', 'options')
                                      if key in field))
                          for name, field in data['fields'].iteritems())
        add_script_data(req, {'properties': properties,
                              'modes': data['modes']})

        add_stylesheet(req, 'common/css/report.css')
        if __version__ > '0.12':
            # >= Trac 0.12.1
            add_script(req, 'common/js/query.js')
        else:
            # only Trac 0.12, not compatible with Trac 0.11.x
            add_script(req, 'tc/js/query.js')

        return 'gantt.html', data, None

    def get_templates_dirs(self):
        from pkg_resources import resource_filename
        return [resource_filename(__name__, 'templates')]

    def get_htdocs_dirs(self):
        from pkg_resources import resource_filename
        return [('tc', resource_filename(__name__, 'htdocs'))]

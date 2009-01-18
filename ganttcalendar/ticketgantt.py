#encoding=utf-8
import re, calendar, time
from datetime import datetime, date, timedelta
from genshi.builder import tag

from trac.core import *
from trac.web import IRequestHandler
from trac.web.chrome import INavigationContributor, ITemplateProvider
from trac.util.datefmt import to_datetime, utc, parse_date

class TicketGanttChartPlugin(Component):
    implements(INavigationContributor, IRequestHandler, ITemplateProvider)

    # INavigationContributor methods
    def get_active_navigation_item(self, req):
        return 'ticketgantt'
    
    def get_navigation_items(self, req):
        if req.perm.has_permission('TICKET_VIEW'):
            yield ('mainnav', 'ticketgantt',tag.a(u'ガントチャート', href=req.href.ticketgantt()))

    # IRequestHandler methods
    def match_request(self, req):
        return re.match(r'/ticketgantt(?:_trac)?(?:/.*)?$', req.path_info)

    def calendarRange(self, y, m):
        w,mdays = calendar.monthrange(y,m)
        w = (w + 1) % 7
        firstDay = date(y,m,1)-timedelta(days=w)

        lastDay = date(y,m,mdays)
        w = (lastDay.weekday()+1)%7
        lastDay = lastDay + timedelta(days=(6-w))
        return firstDay, lastDay

    def process_request(self, req):
        ymonth = req.args.get('month')
        yyear = req.args.get('year')
        baseday = req.args.get('baseday')
        selected_item = req.args.get('selected_item')
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
        first,last = self.calendarRange(cday.year, cday.month)
        # process ticket
        db = self.env.get_db_cnx()
        cursor = db.cursor();
        sql = ""
        condition=""
        if selected_item == None or selected_item == "":
            if show_my_ticket=="on" or show_closed_ticket!="on":
                condition = "WHERE " + self.generate_where(show_my_ticket,
                                                    show_closed_ticket,
                                                    req.authname)
            sql = ("SELECT id, type, summary, owner, t.description, status, a.value, c.value, cmp.value, %s from ticket t "
                        "JOIN ticket_custom a ON a.ticket = t.id AND a.name = 'due_assign' "
                        "JOIN ticket_custom c ON c.ticket = t.id AND c.name = 'due_close' "
                        "JOIN ticket_custom cmp ON cmp.ticket = t.id AND cmp.name = 'complete' "
                        "%s ORDER by %s , a.value ") % (sorted_field ,condition, sorted_field)
        else:
            if show_my_ticket=="on" or show_closed_ticket!="on":
                condition = "AND " + self.generate_where(show_my_ticket,
                                                show_closed_ticket,
                                                req.authname)
            sql = ("SELECT id, type, summary, owner, t.description, status, a.value, c.value, cmp.value, %s from ticket t "
                        "JOIN ticket_custom a ON a.ticket = t.id AND a.name = 'due_assign' "
                        "JOIN ticket_custom c ON c.ticket = t.id AND c.name = 'due_close' "
                        "JOIN ticket_custom cmp ON cmp.ticket = t.id AND cmp.name = 'complete' "
                        "WHERE %s = '%s' %s ORDER by %s , a.value "
                ) % (sorted_field, sorted_field, selected_item, condition, sorted_field)
        self.log.debug(sql)
        cursor.execute(sql)

        tickets=[]
        for id, type, summary, owner, description, status, due_assign, due_close, complete, item in cursor:
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
            if item == None or item == "":
                item = "*"
            if complete != None and len(complete)>1 and complete[len(complete)-1]=='%':
                complete = complete[0:len(complete)-1]
            ticket = {'id':id, 'type':type, 'summary':summary, 'owner':owner, 'description': description, 'status':status, 'due_assign':due_assign_date, 'due_close':due_close_date, 'complete': complete, sorted_field: item}
            self.log.debug(ticket)
            tickets.append(ticket)

        # get roadmap
        items = [""]
        if selected_item=='milestone':
            sql = ("SELECT name, due, completed, description from MILESTONE")
            self.log.debug(sql)
            cursor.execute(sql)

            for name, due, completed, description in cursor:
                if due!=0:
                    due_time = to_datetime(due, utc).date()
                    item = {'name':name, 'due':due_date, 'completed':completed != 0,'description':description}
                    items.append(milestone)
        else:
            sql = ("SELECT name from %s") % (sorted_field)
            self.log.debug(sql)
            cursor.execute(sql)
            for name, in cursor:
                items.append({'name':name})

        data = {'baseday': baseday, 'current':cday, 'prev':pmonth, 'next':nmonth, 'first':first, 'last':last, 'tickets':tickets, 'items':items,
                'show_my_ticket': show_my_ticket, 'show_closed_ticket': show_closed_ticket, 'selected_item': selected_item, 'sorted_field': sorted_field}
        return 'gantt.html', data, None

    def generate_where(self,show_my,show_closed,owner):
        sql=""
        if show_my=="on":
            sql = sql + "owner = '" + owner + "'"
            if show_closed!="on":
                sql = sql + " AND status <> 'closed'"
        else:
            if show_closed!="on":
                sql = sql + "status <> 'closed'"
        self.log.debug("generated sql: "+sql)
        return sql

    def get_templates_dirs(self):
        from pkg_resources import resource_filename
        return [resource_filename(__name__, 'templates')]

    def get_htdocs_dirs(self):
        from pkg_resources import resource_filename
        return [('tc', resource_filename(__name__, 'htdocs'))]

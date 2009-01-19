#encoding=utf-8
import re, calendar, time
from datetime import datetime, date, timedelta
from genshi.builder import tag

from trac.core import *
from trac.web import IRequestHandler
from trac.web.chrome import INavigationContributor, ITemplateProvider
from trac.util.datefmt import to_datetime, parse_date

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

    def process_request(self, req):
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

        if condition != "":
            condition = "WHERE " + condition + " "

        sql = ("SELECT id, type, summary, owner, t.description, status, a.value, c.value, cmp.value, milestone, component "
                "FROM ticket t "
                "JOIN ticket_custom a ON a.ticket = t.id AND a.name = 'due_assign' "
                "JOIN ticket_custom c ON c.ticket = t.id AND c.name = 'due_close' "
                "JOIN ticket_custom cmp ON cmp.ticket = t.id AND cmp.name = 'complete' "
                "%sORDER by %s , a.value ") % (condition, sorted_field)

        self.log.debug(sql)
        cursor.execute(sql)

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
            if milestone == None or milestone == "":
                milestone = "*"
            if component == None or component == "":
                component = "*"
            ticket = {'id':id, 'type':type, 'summary':summary, 'owner':owner, 'description': description, 'status':status,
                    'due_assign':due_assign_date, 'due_close':due_close_date, 'complete': complete, 
                    'milestone': milestone,'component': component}
            self.log.debug(ticket)
            tickets.append(ticket)

        # milestones
        milestones = [{}]
        sql = ("SELECT name, due, completed, description FROM milestone")
        self.log.debug(sql)
        cursor.execute(sql)
        for name, due, completed, description in cursor:
            due_date = to_datetime(due, req.tz).date()
            item = {'name':name, 'due':due_date, 'completed':completed != 0,'description':description}
            if due==0:
                del item['due']
            milestones.append(item)
        # componet
        components = [{}]
        sql = ("SELECT name FROM component")
        self.log.debug(sql)
        cursor.execute(sql)
        for name, in cursor:
            components.append({'name':name})

        data = {'baseday': baseday, 'current':cday, 'prev':pmonth, 'next':nmonth, 'tickets':tickets,
                'show_my_ticket': show_my_ticket, 'show_closed_ticket': show_closed_ticket, 'sorted_field': sorted_field,
                'milestones':milestones,'components':components,
                'selected_milestone':selected_milestone,'selected_component': selected_component}
        return 'gantt.html', data, None

    def get_templates_dirs(self):
        from pkg_resources import resource_filename
        return [resource_filename(__name__, 'templates')]

    def get_htdocs_dirs(self):
        from pkg_resources import resource_filename
        return [('tc', resource_filename(__name__, 'htdocs'))]

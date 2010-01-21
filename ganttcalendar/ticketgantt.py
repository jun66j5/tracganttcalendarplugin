# -*- coding: utf-8 -*-
import re, calendar, time, sys
from datetime import datetime, date, timedelta
from genshi.builder import tag

from trac.core import *
from trac.web import IRequestHandler
from trac.web.chrome import INavigationContributor, ITemplateProvider
from trac.util.datefmt import to_datetime, format_date, parse_date

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

        return 'gantt.html', data, None

    def get_templates_dirs(self):
        from pkg_resources import resource_filename
        return [resource_filename(__name__, 'templates')]

    def get_htdocs_dirs(self):
        from pkg_resources import resource_filename
        return [('tc', resource_filename(__name__, 'htdocs'))]

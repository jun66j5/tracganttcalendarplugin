# -*- coding: utf-8 -*-
import re, calendar, time
from datetime import date, timedelta

from genshi.builder import tag

from trac.core import Component, implements, TracError
from trac.web import IRequestHandler
from trac.web.chrome import INavigationContributor, ITemplateProvider
from trac.util.datefmt import to_datetime
from trac.config import BoolOption

from ganttcalendar.translation import _


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

class TicketCalendarPlugin(Component):
    implements(INavigationContributor, IRequestHandler, ITemplateProvider)

    show_weekly_view = BoolOption('ganttcalendar', 'show_weekly_view', 'false', """Set weekly view as default in calendar. (default: false)""")

    # INavigationContributor methods
    def get_active_navigation_item(self, req):
        return 'ticketcalendar'

    def get_navigation_items(self, req):
        if req.perm.has_permission('TICKET_VIEW'):
            yield ('mainnav', 'ticketcalendar',tag.a(_('Calendar'), href=req.href.ticketcalendar()))

    # IRequestHandler methods
    def match_request(self, req):
        return re.match(r'/ticketcalendar(?:_trac)?(?:/.*)?$', req.path_info)

    def calendarRange(self, y, m, wk):
        calendar.setfirstweekday(wk)
        li = calendar.monthcalendar(y,m)
        days = li[0].count(0)
        firstDay = date(y,m,1) - timedelta(days)
        days = li[-1].count(0)
        lastDay = date(y,m,max(li[-1])) + timedelta(days)
        return firstDay, lastDay

    def process_request(self, req):
        req.perm.assert_permission('TICKET_VIEW')
        req.perm.require('TICKET_VIEW')
        self.log.debug("process_request " + str(globals().get('__file__')))
        year  = req.args.get('year')
        month = req.args.get('month')
        day   = req.args.get('day') or '1'
        weekly_view = int(req.args.get('weekly') or '0')
        show_my_ticket = req.args.get('show_my_ticket')
        show_closed_ticket = req.args.get('show_closed_ticket')
        selected_milestone = req.args.get('selected_milestone')

        if year and month:
            cday = date(int(year),int(month),int(day))
        else:
            cday = date.today()
            show_closed_ticket = 'on'
            weekly_view = int(self.show_weekly_view)

        # first_day=   0: sunday (default) 1: monday 2: tuesday 3: wednesday 4: thursday 5: friday 6: saturday
        first_day = self.config['ganttcalendar'].getint('first_day', default=0)
        weekdays = [6, 0, 1, 2, 3, 4, 5]
        first_wkday = weekdays[first_day % 7]
        # first_wkday= 0: monday 1: tuesday 2: wednesday 3: thursday 4: friday 5: saturday 6: sunday (default)

        dateFormat = str(self.config['ganttcalendar'].get('format', default='%Y/%m/%d') or '%Y/%m/%d')

        first, last = self.calendarRange(cday.year, cday.month, first_wkday)

        if weekly_view:
            first = first + timedelta(weeks=(cday-first).days/7)
            last = first + timedelta(days=6)
            prev = first - timedelta(weeks=1)
            next = first + timedelta(weeks=1)
        else:
            prev = cday.replace(day=1).__add__(timedelta(days=-1)).replace(day=1)
            next = cday.replace(day=1).__add__(timedelta(days=32)).replace(day=1)

        # process ticket
        db = self.env.get_db_cnx()
        cursor = db.cursor();
        my_ticket_sql = ""
        self.log.debug("myticket")
        self.log.debug(show_my_ticket)
        if show_my_ticket=="on":
            my_ticket_sql = "AND owner = '" + req.authname + "'"
        closed_ticket_sql = ""
        if show_closed_ticket != 'on':
            closed_ticket_sql = "AND status <> 'closed'"
        selected_milestone_sql = ""
        if selected_milestone != None and selected_milestone != "":
            selected_milestone_sql = "AND milestone = '" + selected_milestone  + "'"

        sql = ("SELECT id, type, summary, owner, description, status, resolution, priority, a.value, c.value, cmp.value, est.value, tot.value from ticket t "
                    "JOIN ticket_custom a ON a.ticket = t.id AND a.name = 'due_assign' "
                    "JOIN ticket_custom c ON c.ticket = t.id AND c.name = 'due_close' "
                    "JOIN ticket_custom cmp ON cmp.ticket = t.id AND cmp.name = 'complete' "
                    "LEFT OUTER JOIN ticket_custom est ON est.ticket = t.id AND est.name = 'estimatedhours' "
                    "LEFT OUTER JOIN ticket_custom tot ON tot.ticket = t.id AND tot.name = 'totalhours' "
                    "WHERE ((a.value >= '%s' AND a.value <= '%s' ) "
                    "OR (c.value >= '%s' AND c.value <= '%s')) %s %s %s" %
                    (first.strftime(dateFormat),
                        last.strftime(dateFormat),
                        first.strftime(dateFormat),
                        last.strftime(dateFormat),
                        my_ticket_sql,
                        closed_ticket_sql,
                        selected_milestone_sql))

        self.log.debug(sql)
        cursor.execute(sql)

        sum_estimatedhours = 0.0
        sum_totalhours = 0.0
        sum_est_isNone = True

        tickets=[]
        for id, type, summary, owner, description, status, resolution, priority, due_assign, due_close, complete, estimatedhours, totalhours in cursor:
            due_assign_date = None
            due_close_date = None
            try:
                t = time.strptime(due_assign, dateFormat)
                due_assign_date = date(t[0],t[1],t[2])
            except ( TracError, ValueError, TypeError):
                pass
            try:
                t = time.strptime(due_close, dateFormat)
                due_close_date = date(t[0],t[1],t[2])
            except ( TracError, ValueError, TypeError):
                pass
            if complete != None and len(complete)>1 and complete[len(complete)-1]=='%':
                complete = complete[0:len(complete)-1]
            try:
                if int(complete) >100:
                    complete = "100"
            except:
                complete = "0"
            complete = int(complete)
            if (due_assign_date and due_close_date) \
              and (due_assign_date > due_close_date):
                continue
            # time tracking
            if estimatedhours != None:
                estimatedhours = float(estimatedhours)
                sum_estimatedhours += estimatedhours
                sum_est_isNone = False
            if totalhours != None:
                totalhours = float(totalhours)
                sum_totalhours += totalhours
            else: totalhours = 0.0
            ticket = {'id':id, 'type':type, 'summary':summary, 'owner':owner, 'description': description,
                      'status':status, 'resolution':resolution, 'priority':priority,
                      'due_assign':due_assign_date, 'due_close':due_close_date, 'complete': complete,
                      'estimatedhours':estimatedhours, 'totalhours':totalhours}
            tickets.append(ticket)
        # time tracking
        if sum_est_isNone: sum_estimatedhours = None

        # get roadmap
        sql = ("SELECT name, due, completed, description FROM milestone")
        self.log.debug(sql)
        cursor.execute(sql)

        milestones = [{}]
        for name, due, completed, description in cursor:
            milestone = {'name':name, 'completed':completed != 0,'description':description}
            if due!=0:
                milestone['due']= to_datetime(due, req.tz).date()
            milestones.append(milestone)

        holidays = {}
        sql = "SELECT date,description from holiday"
        try:
            cursor.execute(sql)
            for hol_date,hol_desc in cursor:
                holidays[hol_date]= hol_desc
        except:
            pass

        #days
        days={}
        for d in range((last-first).days+1):
            mday= first + timedelta(d)
            mday_str= mday.isoformat()
            days[mday]={}
            #day kind
            days[mday]['kind']= 'active'
            if mday_str in holidays.keys():
                days[mday]['holiday_desc']= holidays[mday_str]
                days[mday]['kind']= 'holiday'
            if mday == date.today():
                days[mday]['kind']= 'today'
            elif mday.weekday() in (5,6):
                days[mday]['kind']= 'holiday'
            #ticket
            days[mday]['ticket']=[]
            for t in range(len(tickets)):
                if mday == tickets[t].get('due_assign') == tickets[t].get('due_close'):
                    days[mday]['ticket'].append({'img':'bw','num':t})
                elif mday == tickets[t].get('due_assign'):
                    days[mday]['ticket'].append({'img':'from','num':t})
                elif mday == tickets[t].get('due_close'):
                    days[mday]['ticket'].append({'img':'to','num':t})
            #milestone
            days[mday]['milestone']=[]
            for m in range(len(milestones)):
                if mday== milestones[m].get('due'):
                    days[mday]['milestone'].append(m)

        data = {'current':cday, 'prev':prev, 'next':next, 'weekly':weekly_view, 'first':first, 'last':last,
                'tickets':tickets, 'milestones':milestones,'days':days,
                'sum_estimatedhours':sum_estimatedhours, 'sum_totalhours':sum_totalhours,
                'show_my_ticket': show_my_ticket, 'show_closed_ticket': show_closed_ticket, 'selected_milestone': selected_milestone,
                '_':_,'dateFormat':dateFormat, 'holidays':holidays, 'month_tbl': month_tbl}

        return 'calendar.html', data, None

    def get_templates_dirs(self):
        from pkg_resources import resource_filename
        return [resource_filename(__name__, 'templates')]

    def get_htdocs_dirs(self):
        from pkg_resources import resource_filename
        return [('tc', resource_filename(__name__, 'htdocs'))]

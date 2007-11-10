import re, calendar, time
from datetime import datetime, date, timedelta
from genshi.builder import tag

from trac.core import *
from trac.web import IRequestHandler
from trac.web.chrome import INavigationContributor, ITemplateProvider
from trac.context import Context
from trac.util.datefmt import to_datetime, utc

class TicketGanttChartPlugin(Component):
    implements(INavigationContributor, IRequestHandler, ITemplateProvider)

    # INavigationContributor methods
    def get_active_navigation_item(self, req):
        return 'ticketgantt'
    
    def get_navigation_items(self, req):
        yield ('mainnav', 'ticketgantt',
               tag.a('Gantt', href=req.href.ticketgantt()))
    
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

    def dateToString(self, dt):
       m = dt.month
       if m < 10:
          m = '0'+str(m)
       d = dt.day
       if d < 10:
          d = '0'+str(d)
       return str(dt.year)+"/"+str(m)+"/"+str(d)
    
    def process_request(self, req):
        ymonth = req.args.get('month')
        yyear = req.args.get('year')
        baseday = req.args.get('baseday')
        selected_milestone = req.args.get('selected_milestone')
        show_my_ticket = req.args.get('show_my_ticket')
#        self.log.debug("show_my_ticket:"+str(show_my_ticket))
#        self.log.debug("username="+req.authname)

        if baseday != None:
           r = re.match(r'^(\d+)/(\d+)/(\d+)$', baseday)
           baseday = date(int(r.group(1)), int(r.group(2)), int(r.group(3)))
        else:
           baseday = date.today()

        cday = date.today()
        if not (not ymonth or not yyear):
            cday = date(int(yyear),int(ymonth),1)

        # cal next month
        nm = cday.month + 1
        ny  = cday.year
        if nm > 12:
            ny = ny + 1
            nm = 1
        nmonth = datetime(ny,nm,1)
        
        # cal previous month
        pm = cday.month - 1
        py = cday.year
        if pm < 1:
            py = py -1
            pm = 12
        pmonth = date(py,pm,1)
        first,last = self.calendarRange(cday.year, cday.month)
# process ticket
        db = self.env.get_db_cnx()
        cursor = db.cursor();
        sql = ""
        if selected_milestone == None or selected_milestone == "":
           myticketsql = ""
           if show_my_ticket=="on":
               myticketsql = "WHERE owner = '" + req.authname + "'"

           sql = ("SELECT id, type, summary, owner, t.description, status, a.value, c.value, cmp.value, milestone from ticket t "
                          "JOIN ticket_custom a ON a.ticket = t.id AND a.name = 'due_assign' "
                          "JOIN ticket_custom c ON c.ticket = t.id AND c.name = 'due_close' "
                          "JOIN ticket_custom cmp ON cmp.ticket = t.id AND cmp.name = 'complete' "
                          "LEFT JOIN milestone m ON m.name = t.milestone %s ORDER by m.due , milestone , a.value ") % (myticketsql)
        else:
           myticketsql = ""
           if show_my_ticket=="on":
               myticketsql = "AND owner = '"+req.authname + "'"
           sql = ("SELECT id, type, summary, owner, t.description, status, a.value, c.value, cmp.value, milestone from ticket t "
                          "JOIN ticket_custom a ON a.ticket = t.id AND a.name = 'due_assign' "
                          "JOIN ticket_custom c ON c.ticket = t.id AND c.name = 'due_close' "
                          "JOIN ticket_custom cmp ON cmp.ticket = t.id AND cmp.name = 'complete' "
                          "LEFT JOIN milestone m ON m.name = t.milestone WHERE milestone = '%s' %s ORDER by m.due , milestone , a.value "
                  ) % (selected_milestone, myticketsql)
        self.log.debug(sql)
        cursor.execute(sql)

        tickets=[]
        for id, type, summary, owner, description, status, due_assign, due_close, complete, milestone in cursor:
           due_assign_date = None
           due_close_date = None
           try:
              t = time.strptime(due_assign,"%Y/%m/%d")
              due_assign_date = date(t[0],t[1],t[2])
           except ValueError, TypeError:
              continue
           try:
              t = time.strptime(due_close,"%Y/%m/%d")
              due_close_date = date(t[0],t[1],t[2])
           except ValueError, TypeError:
              continue
           if milestone == None or milestone == "":
              milestone = "*"
           ticket = {'id':id, 'type':type, 'summary':summary, 'owner':owner, 'description': description, 'status':status, 'due_assign':due_assign_date, 'due_close':due_close_date, 'complete': complete, 'milestone': milestone}
           self.log.debug(ticket)
           tickets.append(ticket)

        # get roadmap
        sql = ("SELECT name, due, completed, description from MILESTONE")
        self.log.debug(sql)
        cursor.execute(sql)

        milestones = [""]

        for name, due, completed, description in cursor:
           if due!=0:
               due_time = to_datetime(due, utc)
               due_date = date(due_time.year, due_time.month, due_time.day)
               milestone = {'name':name, 'due':due_date, 'completed':completed != 0,'description':description}
               milestones.append(milestone)

        data = {'baseday': baseday, 'current':cday, 'prev':pmonth, 'next':nmonth, 'first':first, 'last':last, 'tickets':tickets, 'milestones':milestones,
                'show_my_ticket': show_my_ticket, 'selected_milestone': selected_milestone}
        return 'gantt.html', data, None

    def get_templates_dirs(self):
        from pkg_resources import resource_filename
        return [resource_filename(__name__, 'templates')]

    def get_htdocs_dirs(self):
        from pkg_resources import resource_filename
        return [('tc', resource_filename(__name__, 'htdocs'))]

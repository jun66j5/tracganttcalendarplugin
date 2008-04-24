# -*- coding: utf-8 -*-
import re, calendar, time
from datetime import datetime, date, timedelta, tzinfo

from trac.core import *
from trac.web import IRequestHandler
from trac.web.chrome import INavigationContributor, ITemplateProvider
from trac.util import Markup

from datefmt_ext import to_datetime, utc

class TicketGanttChartPlugin(Component):
    implements(INavigationContributor, IRequestHandler, ITemplateProvider)

    # INavigationContributor methods
    def get_active_navigation_item(self, req):
        return 'ticketgantt'

    def get_navigation_items(self, req):
        yield ('mainnav', 'ticketgantt',
               Markup(u'<a href="%s">ガント</a>', req.href.ticketgantt()))

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
        selected_item = req.args.get('selected_item')
        show_my_ticket = req.args.get('show_my_ticket')
        show_closed_ticket = req.args.get('show_closed_ticket')
        sorted_field = req.args.get('sorted_field')
        if sorted_field == None:
           sorted_field = 'component'

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
              t = time.strptime(due_assign,"%Y/%m/%d")
              due_assign_date = date(t[0],t[1],t[2])
           except ValueError, TypeError:
              continue
           try:
              t = time.strptime(due_close,"%Y/%m/%d")
              due_close_date = date(t[0],t[1],t[2])
           except ValueError, TypeError:
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
                    due_time = to_datetime(due, utc)
                    due_date = date(due_time.year, due_time.month, due_time.day)
                    item = {'name':name[0], 'due':due_date, 'completed':completed != 0,'description':description}
                    items.append(milestone)
        else:
            sql = ("SELECT name from %s") % (sorted_field)
            self.log.debug(sql)
            cursor.execute(sql)
            for name in cursor:
                items.append({'name':name[0]})

        data = {'baseday': baseday, 'current':cday, 'prev':pmonth, 'next':nmonth, 'first':first, 'last':last, 'tickets':tickets, 'items':items,
                'show_my_ticket': show_my_ticket, 'show_closed_ticket': show_closed_ticket, 'selected_item': selected_item, 'sorted_field': sorted_field}


        # create hdf
        dw = 12;
        ti = 25;
        cur = date(cday.year, cday.month, 1)
        first = date(cday.year, cday.month, 1)
        base = (baseday - first).days

        m1 = calendar.monthrange(cday.year, cday.month)[1];
        tmp = cday + timedelta(days=m1)
        m2 = calendar.monthrange(tmp.year, tmp.month)[1]
        tmp = cday + timedelta(days=(m1+m2))
        m3 = calendar.monthrange(tmp.year, tmp.month)[1]
        term = m1 + m2 + m3

        cdays = []
        c = cur
        for i in range(0, term, 1):
            chdf = self.to_datehdf(c)
            chdf['monthrange'] = calendar.monthrange(c.year, c.month)[1]
            cdays.append(chdf)
            c = c + timedelta(days=1)

        m_line = -1
        if selected_item == 'milestone':
            for ml in items:
                if ml != "" and ml['name'] == selected_item:
                    m_line = (ml['due'] - first).days

        graph = {
            'dw':dw, 'ti':ti,
            'cur':self.to_datehdf(cur), 'first':self.to_datehdf(first),
            'base':base,
            'term':term,
            'numticket':len(tickets),
            'm_line':m_line,
            'cdays':cdays
        }

        ts = []
        for t in tickets:
            url = "%s/%d" % (req.href.ticket(), t['id'])

            cls = (t['due_close'] - first).days
            assign = (t['due_assign'] - first).days
            barw = (cls - assign + 1) * dw
            gap = 0
            if assign < 0:
                gap = -assign
                assign = 0
            if assign > term:
                assign = -1
            if cls < 0 and not (assign != -1):
                cls = 0
            if (cls - assign + assign) > term:
                cls = term - 1
            todow = (cls - assign + 1) * dw

            if assign * dw + todow > term * dw:
               todow = (term - assign) * dw

            latew = 0
            if base > assign:
               latew = (base - assign + 1) * dw
               if latew > todow:
                  latew = todow

            complete = t['complete']
            if complete == None or complete == "" or todow <= 0:
               complete = 0
            else:
               complete = int(complete) * barw / 100 - (gap) * dw
               if assign * dw + complete > term * dw:
                  complete = (term - assign) * dw

            ts.append({'ticket':t,
                       'url':url, 'short_summary':t['summary'][0:10],
                       'assign':assign, 'todow':todow, 'latew':latew, 'complete':complete
                      })

        req.hdf['gan'] = {
            'weekdays':[u"月", u"火", u"水", u"木", u"金", u"土", u"日"],
            'baseday':self.to_datehdf(baseday),
            'current':self.to_datehdf(cday),
            'prev':self.to_datehdf(pmonth),
            'next':self.to_datehdf(nmonth),
            'first':self.to_datehdf(first),
            'last':self.to_datehdf(last),
            'tickets':ts,
            'items':items,
            'show_my_ticket':show_my_ticket, 'show_closed_ticket':show_closed_ticket,
            'selected_item':selected_item, 'sorted_field':sorted_field,
            'graph':graph
        }

        return 'gantt.cs', None

    def to_datehdf(self, date):
        return {'to_s':date, 'year':date.year, 'month':date.month, 'day':date.day, 'weekday':date.weekday()}

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

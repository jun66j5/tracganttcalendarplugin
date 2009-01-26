# encoding: utf-8

from trac.admin import IAdminPanelProvider
from trac.core import *
from trac.util.translation import _
from trac.util.datefmt import format_date, parse_date
from holiday import holidays_tbl

class HolidayAdminPanel(Component):
    implements(IAdminPanelProvider)

    def get_admin_panels(self, req):
        if 'TRAC_ADMIN' in req.perm:
            yield ('ganttcalendar', u'ガント・カレンダー', 'holiday', u'祝日設定')

    def render_admin_panel(self, req, cat, page, path_info):
        tbl_chk = True
        db = self.env.get_db_cnx()
        cursor = db.cursor();
        sql = "SELECT count(*) from holiday"
        try:
            cursor.execute(sql)
        except:
            tbl_chk = False

        if req.method == 'POST':
            if req.args.get('add'):
                keydate = format_date(parse_date( req.args.get('date'), tzinfo=req.tz))
                sql = "SELECT count(*) FROM holiday WHERE date='" + keydate + "'"
                cursor.execute(sql)
                for cnt, in cursor:
                    dup_chk = cnt
                if dup_chk == 1:
                    raise TracError(_('Holiday %(date)s already exists.',date=keydate))
                sql = "INSERT INTO holiday VALUES('" + keydate +"','" + req.args.get('description') + "')"
                cursor.execute(sql)
                db.commit()
                req.redirect(req.href.admin(cat, page))

            elif req.args.get('remove'):
                sel = req.args.get('sel')
                if not sel:
                    raise TracError(_('No holiday selected'))
                if not isinstance(sel, list):
                    sel = [sel]
                for name in sel:
                    keydate = format_date(parse_date( name, tzinfo=req.tz))
                    sql = "DELETE FROM holiday WHERE date ='" + keydate+ "'"
                    cursor.execute(sql)
                db.commit()
                req.redirect(req.href.admin(cat, page))

            elif req.args.get('create_table'):
                sql = "CREATE TABLE holiday (date TEXT, description TEXT)"
                cursor.execute(sql)
                sql = "CREATE UNIQUE INDEX idx_holiday ON holiday(date ASC)"
                cursor.execute(sql)
                db.commit()
                for h in holidays_tbl.keys():
                    sql = "INSERT INTO holiday VALUES('"+ format_date(parse_date(h))+ "','"+ holidays_tbl[h]+ "')"
                    cursor.execute(sql)
                db.commit()
                req.redirect(req.href.admin(cat, page))

        #list
        holidays = []
        if tbl_chk:
            sql = "SELECT date,description FROM holiday ORDER BY date"
            cursor.execute(sql)
            for hol_date,hol_desc in cursor:
                holidays.append( { 'date': format_date(parse_date(hol_date, tzinfo=req.tz)), 'description': hol_desc})
        return 'admin_holiday.html',{'holidays': holidays,'tbl_chk':tbl_chk}


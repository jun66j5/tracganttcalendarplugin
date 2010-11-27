# -*- coding: utf-8 -*-

from trac.admin import IAdminPanelProvider
from trac.core import *
from trac.util.translation import domain_functions
import locale

# i18n support for plugins, available since Trac r7705
# use _, tag_ and N_ as usual, e.g. _("this is a message text")
_, tag_, N_, add_domain = domain_functions('ganttcalendar', 
    '_', 'tag_', 'N_', 'add_domain')


class HolidayAdminPanel(Component):
    implements(IAdminPanelProvider)

    def __init__(self):
        import pkg_resources
        locale_dir = pkg_resources.resource_filename(__name__, 'locale')
        add_domain(self.env.path, locale_dir)


    def get_admin_panels(self, req):
        if 'TRAC_ADMIN' in req.perm:
            yield ('ganttcalendar', u'Ganttcalendar', 'holiday', _('Holiday Setting'))

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
                keydate = req.args.get('date')
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
                    keydate = name
                    sql = "DELETE FROM holiday WHERE date ='" + keydate+ "'"
                    cursor.execute(sql)
                db.commit()
                req.redirect(req.href.admin(cat, page))

            elif req.args.get('create_table'):
                (loc,enc) = locale.getdefaultlocale()

                self.log.info("loc:"+loc)
                if (loc.find("ko_")==0) or (loc.find("Korean_")==0):
                   from holiday_ko import holidays_tbl
                   self.log.info("import holiday_ko")
                elif (loc.find("ja_")==0) or (loc.find("Japanese_")==0):
                   from holiday_ja import holidays_tbl
                   self.log.info("import holiday_ja")
                else:
                   holidays_tbl={}
                   self.log.info("create empty holiday table")

                sql = "CREATE TABLE holiday (date TEXT, description TEXT)"
                cursor.execute(sql)
                db_type = self.config['trac'].get('database').split(':')[0].lower()
                if db_type != 'mysql':
                    # SQLite, PostgreSQL
                    sql = "CREATE UNIQUE INDEX idx_holiday ON holiday(date ASC)"
                else:
                    # MySQL
                    sql = "CREATE UNIQUE INDEX idx_holiday ON holiday(date(10) ASC)"
                cursor.execute(sql)
                db.commit()
                for h in holidays_tbl.keys():
                    sql = "INSERT INTO holiday VALUES('"+ h+ "','"+ holidays_tbl[h]+ "')"
                    cursor.execute(sql)
                db.commit()
                req.redirect(req.href.admin(cat, page))

            elif req.args.get('drop_table'):
                sql = "DROP TABLE holiday"
                cursor.execute(sql)
                db.commit()
                req.redirect(req.href.admin(cat, page))

        #list
        holidays = []
        if tbl_chk:
            sql = "SELECT date,description FROM holiday ORDER BY date"
            cursor.execute(sql)
            for hol_date,hol_desc in cursor:
                holidays.append( { 'date': hol_date, 'description': hol_desc})
        return 'admin_holiday.html',{'_': _, 'holidays': holidays,'tbl_chk':tbl_chk}

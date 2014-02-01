# -*- coding: utf-8 -*-

import locale

from trac.admin import IAdminPanelProvider
from trac.core import Component, implements, TracError
from trac.env import IEnvironmentSetupParticipant

from ganttcalendar.translation import _, add_domain


class HolidayAdminPanel(Component):

    implements(IAdminPanelProvider, IEnvironmentSetupParticipant)

    def __init__(self):
        import pkg_resources
        locale_dir = pkg_resources.resource_filename(__name__, 'locale')
        add_domain(self.env.path, locale_dir)

    # Work around for untranslated messages when first-response
    # IEnvironmentSetupParticipant methods
    def environment_created(self):
        pass

    def environment_needs_upgrade(self, db):
        return False

    def upgrade_environment(self, db):
        pass

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
                cursor.execute("SELECT COUNT(*) FROM holiday WHERE date=%s",
                               (keydate,))
                for cnt, in cursor:
                    dup_chk = cnt
                if dup_chk != 0:
                    raise TracError(_('Holiday %(date)s already exists.',
                                      date=keydate))
                cursor.execute("INSERT INTO holiday VALUES(%s,%s)",
                               (keydate, req.args.get('description')))
                db.commit()
                req.redirect(req.href.admin(cat, page))

            elif req.args.get('remove'):
                sel = req.args.getlist('sel')
                if not sel:
                    raise TracError(_('No holiday selected'))
                cursor.executemany("DELETE FROM holiday WHERE date=%s",
                                   [(val,) for val in sel])
                db.commit()
                req.redirect(req.href.admin(cat, page))

            elif req.args.get('create_table'):
                loc, enc = locale.getdefaultlocale()

                self.log.debug("loc: %r", loc)
                loc = (loc or '').lower()
                if loc.startswith('ko_') or loc.startswith('korean_'):
                   import holiday_ko
                   holidays_tbl = holiday_ko.holidays_tbl
                   self.log.debug("import holiday_ko")
                elif loc.startswith('ja_') or loc.startswith('japanese_'):
                   import holiday_ja
                   holidays_tbl = holiday_ja.holidays_tbl
                   self.log.debug("import holiday_ja")
                else:
                   holidays_tbl = {}
                   self.log.debug('create empty holiday table')

                sql = "CREATE TABLE holiday (date TEXT, description TEXT)"
                cursor.execute(sql)
                coltype = 'date'
                if self.config.get('trac', 'database').startswith('mysql:'):
                    coltype = 'date(10)'
                sql = 'CREATE UNIQUE INDEX idx_holiday ON holiday (%s)' \
                      % coltype
                cursor.execute(sql)
                cursor.executemany('INSERT INTO holiday VALUES(%s,%s)',
                                   list(holidays_tbl.iteritems()))
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

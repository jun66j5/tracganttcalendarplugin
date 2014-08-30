# -*- coding: utf-8 -*-

import locale

from trac.admin import IAdminPanelProvider
from trac.core import Component, implements, TracError
from trac.env import IEnvironmentSetupParticipant
from trac.util.datefmt import format_date, parse_date
try:
    from trac.util.datefmt import user_time
except ImportError:
    def user_time(req, func, *args, **kwargs):
        if 'tzinfo' not in kwargs:
            kwargs['tzinfo'] = getattr(req, 'tz', None)
        if 'locale' not in kwargs:
            kwargs['locale'] = getattr(req, 'locale', None)
        return func(*args, **kwargs)

from ganttcalendar.translation import _, add_domain


class HolidayAdminPanel(Component):

    implements(IAdminPanelProvider, IEnvironmentSetupParticipant)

    def __init__(self):
        from pkg_resources import resource_filename, resource_exists
        if resource_exists(__name__, 'locale'):
            locale_dir = resource_filename(__name__, 'locale')
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
            yield ('ganttcalendar', u'Ganttcalendar',
                   'holiday', _('Holiday Setting'))

    def render_admin_panel(self, req, cat, page, path_info):
        if req.method == 'POST':
            fn = None
            if req.args.get('add'):
                fn = self._process_add
            elif req.args.get('remove'):
                fn = self._process_remove
            elif req.args.get('create_table'):
                fn = self._process_create_table
            elif req.args.get('drop_table'):
                fn = self._process_drop_table
            if fn:
                fn(req, cat, page, path_info)
                req.redirect(req.href.admin(cat, page))

        return self._process_list(req, cat, page, path_info)

    def _process_list(self, req, cat, page, path_info):
        db = self.env.get_read_db()
        cursor = db.cursor()
        tbl_chk = True
        try:
            cursor.execute("SELECT COUNT(*) FROM holiday")
        except:
            holidays = []
            tbl_chk = False
        else:
            cursor.execute("SELECT date,description FROM holiday "
                           "ORDER BY date")
            columns = ('date', 'description')
            holidays = [dict(zip(columns, row)) for row in cursor]
            tbl_chk = True

        data = {'_': _, 'holidays': holidays, 'tbl_chk': tbl_chk}
        return 'ganttcalendar_admin_holiday.html', data

    def _process_add(self, req, cat, page, path_info):
        keydate = req.args.getfirst('date')
        keydate = user_time(req, parse_date, keydate)
        keydate = user_time(req, format_date, keydate, format='iso8601')

        db = self.env.get_read_db()
        cursor = db.cursor()
        cursor.execute("SELECT COUNT(*) FROM holiday WHERE date=%s",
                       (keydate,))
        row = cursor.fetchone()
        if row[0] != 0:
            raise TracError(_('Holiday %(date)s already exists.',
                              date=keydate))

        @self.env.with_transaction()
        def fn(db):
            description = req.args.getfirst('description')
            cursor = db.cursor()
            cursor.execute("INSERT INTO holiday VALUES(%s,%s)",
                           (keydate, description))

    def _process_remove(self, req, cat, page, path_info):
        sel = req.args.getlist('sel')
        if not sel:
            raise TracError(_('No holiday selected'))

        @self.env.with_transaction()
        def fn(db):
            cursor = db.cursor()
            cursor.executemany("DELETE FROM holiday WHERE date=%s",
                               [(val,) for val in sel])

    def _process_create_table(self, req, cat, page, path_info):
        loc, enc = locale.getdefaultlocale()
        loc = (loc or '').lower()

        mod = None
        if loc.startswith('ko_') or loc.startswith('korean_'):
            import holiday_ko as mod
        elif loc.startswith('ja_') or loc.startswith('japanese_'):
            import holiday_ja as mod
        if mod:
            holidays_tbl = mod.holidays_tbl
        else:
            holidays_tbl = {}

        @self.env.with_transaction()
        def fn(db):
            cursor = db.cursor()
            cursor.execute(
                "CREATE TABLE holiday (date TEXT, description TEXT)")
            coltype = 'date'
            if self.config.get('trac', 'database').startswith('mysql:'):
                coltype = 'date(10)'
            cursor.execute("CREATE UNIQUE INDEX idx_holiday ON holiday (%s)"
                           % coltype)
            cursor.executemany("INSERT INTO holiday VALUES(%s,%s)",
                               list(holidays_tbl.iteritems()))

    def _process_drop_table(self, req, cat, page, path_info):
        @self.env.with_transaction()
        def fn(db):
            cursor = db.cursor()
            cursor.execute("DROP TABLE holiday")

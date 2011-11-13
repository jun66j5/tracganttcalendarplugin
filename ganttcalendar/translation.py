# -*- coding: utf-8 -*-

try:
    from trac.util.translation import domain_functions
except ImportError:
    domain_functions = None

if domain_functions:
    # i18n support for plugins, available since Trac r7705
    # use _ and N_ as usual, e.g. _("this is a message text")
    _, N_, add_domain = domain_functions('ganttcalendar', 
        '_', 'N_', 'add_domain')
else:
    from trac.util.translation import _, N_
    def add_domain(path, dir):
        pass

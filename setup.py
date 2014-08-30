#! /usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import find_packages, setup

extra = {}
try:
    from trac.util.dist import get_l10n_cmdclass
    cmdclass = get_l10n_cmdclass()
    if cmdclass:
        extra['cmdclass'] = cmdclass
        extractors = [
            ('**.py',                'python', None),
            ('**/templates/**.html', 'genshi', None),
            ('**/templates/**.txt',  'genshi', {
                'template_class': 'genshi.template:NewTextTemplate',
            }),
        ]
        extra['message_extractors'] = {
            'ganttcalendar': extractors,
        }
except ImportError:
    pass

setup(
    name='TracGanttCalendarPlugin', version='0.6.3',
    packages=find_packages(exclude=['*.tests*']),

    author="Takashi Okamoto",
    author_email='okamototk@user.sourceforge.jp',
    url="http://sourceforge.jp/projects/shibuya-trac/",
    description='Provide calendar and ganttchart.',
    license = "New BSD",

    entry_points = """
        [trac.plugins]
        ganttcalendar.ticketcalendar = ganttcalendar.ticketcalendar
        ganttcalendar.ticketgantt = ganttcalendar.ticketgantt
        ganttcalendar.complete_by_close = ganttcalendar.complete_by_close
        ganttcalendar.admin = ganttcalendar.admin
        ganttcalendar.ticketvalidator = ganttcalendar.ticketvalidator
    """,
    package_data={
        'ganttcalendar': [
            'templates/*.html', 'htdocs/img/*.png', 'htdocs/js/*.js',
            'locale/*/LC_MESSAGES/*.mo',
        ],
    },
    **extra)

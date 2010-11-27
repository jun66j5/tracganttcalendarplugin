from setuptools import find_packages, setup

extra = {} 
from trac.util.dist import get_l10n_cmdclass 

cmdclass = get_l10n_cmdclass() 

if True:
#if cmdclass: # Yay, Babel is there, we've got something to do! 
    extra['cmdclass'] = cmdclass 
    extractors = [ 
       ('**.py',                'python', None), 
       ('**/templates/**.html', 'genshi', None), 
       ('**/templates/**.txt',  'genshi', { 
            'template_class': 'genshi.template:TextTemplate' 
       }), 
    ] 
    extra['message_extractors'] = { 
       'ganttcalendar': extractors, 
    } 


setup(
    name='TracGanttCalendarPlugin', version='0.5',
    packages=find_packages(exclude=['*.tests*']),

    author = "Takashi Okamoto",
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
    package_data={'ganttcalendar': ['templates/*.html','htdocs/img/*','htdocs/js/*', 'locale/*.*','locale/*/LC_MESSAGES/*.*']},
    **extra
)

#        ticketcalendar = ticketcalendar
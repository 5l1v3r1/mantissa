
from axiom import iaxiom, scheduler

from xmantissa import webadmin, offering, stats
from xmantissa.webadmin import (TracebackViewer, LocalUserBrowser,
                                DeveloperApplication, BatchManholePowerup,
                                PortConfiguration)
from xmantissa.signup import SignupConfiguration

adminOffering = offering.Offering(
    name = u'mantissa',
    description = u'Powerups for administrative control of a Mantissa server.',
    siteRequirements = [],
    appPowerups = [scheduler.SubScheduler, stats.StatsService],
    installablePowerups = [("Signup Configuration", "Allows configuration of signup mechanisms", SignupConfiguration),
                           ("Traceback Viewer", "Allows viewing unhandled exceptions which occur on the server", TracebackViewer),
                           ("Port Configuration", "Allows manipulation of network service configuration.", PortConfiguration),
                           ("Local User Browser", "A page listing all users existing in this site's store.", LocalUserBrowser),
                           ("Admin REPL", "An interactive python prompt.", DeveloperApplication),
                           ("Batch Manhole", "Enables ssh login to the batch-process manhole", BatchManholePowerup),
                           ("Offering Configuration", "Allows installation of Offerings on this site", offering.OfferingConfiguration)],
    loginInterfaces=(),
    themes = ())

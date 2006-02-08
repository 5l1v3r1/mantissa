"""
This module is the basis for Mantissa-based web applications.  It provides
several basic pluggable application-level features, most notably Powerup-based
integration of the extensible hierarchical navigation system defined in
xmantissa.webnav
"""

import os

from zope.interface import implements

from epsilon.structlike import record

from axiom.item import Item
from axiom.attributes import text, integer, reference
from axiom.userbase import getAccountNames
from axiom import upgrade

from nevow.rend import Page
from nevow import livepage, athena
from nevow.inevow import IResource, IQ
from nevow import tags as t
from nevow.url import URL

from xmantissa.publicweb import CustomizedPublicPage
from xmantissa.website import PrefixURLMixin, StaticRedirect
from xmantissa.webtheme import getAllThemes
from xmantissa.webnav import getTabs
from xmantissa._webidgen import genkey, storeIDToWebID, webIDToStoreID
from xmantissa.fragmentutils import PatternDictionary, dictFillSlots

from xmantissa.ixmantissa import INavigableFragment, INavigableElement,\
    ISiteRootPlugin, IWebTranslator, ISearchAggregator, IStaticShellContent

from xmantissa.settings import Settings
from xmantissa.webgestalt import AuthenticationApplication
from xmantissa.prefs import PreferenceAggregator, DefaultPreferenceCollection
from xmantissa.search import SearchAggregator

def _reorderForPreference(themeList, preferredThemeName):
    """
    Re-order the input themeList according to the preferred theme.

    Returns None.
    """
    for t in themeList:
        if preferredThemeName == t.themeName:
            themeList.remove(t)
            themeList.insert(0,t)
            return


class NavMixin(object):

    fragmentName = 'main'
    username = None
    searchPattern = None

    def __init__(self, webapp, pageComponents):
        self.webapp = webapp
        self.pageComponents = pageComponents

    def getDocFactory(self, fragmentName, default=None):
        return self.webapp.getDocFactory(fragmentName, default)

    def render_content(self, ctx, data):
        raise NotImplementedError("implement render_context in subclasses")

    def render_navigation(self, ctx, data):
        # this won't work with child tabs who have children
        url = URL.fromContext(ctx)

        patterns = PatternDictionary(self.getDocFactory('navigation'))

        def fillSlots(tab, pattern):
            return dictFillSlots(pattern,
                                 dict(href=tab.linkURL, name=tab.name))
        allTabsStan = []
        selChildStan = []

        def markTabs(tabs):
            for tab in tabs:
                if tab.linkURL is None:
                    tab.linkURL = self.webapp.linkTo(tab.storeID)
                if tab.linkURL[1:] == url.path:
                    tab.selected = True
                else:
                    tab.selected = False

                markTabs(tab.children)

        markTabs(self.pageComponents.navigation)

        for tab in self.pageComponents.navigation:
            if tab.selected or True in (c.selected for c in tab.children):
                tabStan = fillSlots(tab, patterns['selected-tab'])
                for child in tab.children:
                    if child.selected:
                        pname = 'selected-child-selected'
                    else:
                        pname = 'selected-child-unselected'
                    selChildStan.append(fillSlots(child, patterns[pname]))
            else:
                tabStan = fillSlots(tab, patterns['tab'])
                if 0 < len(tab.children):
                    subStan = patterns['subtabs'].fillSlots('subtabs',
                            list(fillSlots(c, patterns['subtab']) for c in tab.children))
                else:
                    subStan = ''
                tabStan = tabStan.fillSlots('subtabs', subStan)

            allTabsStan.append(tabStan)

        return ctx.tag.fillSlots(
                'tabs', allTabsStan).fillSlots(
                        'selected-children', selChildStan)

    def render_title(self, ctx, data):
        return ctx.tag[self.__class__.__name__]

    def render_search(self, ctx, data):
        searchAggregator = self.pageComponents.searchAggregator
        if searchAggregator is None or not searchAggregator.providers():
            return ''

        if self.searchPattern is None:
            self.searchPattern = IQ(self.docFactory).patternGenerator("search")

        action = self.webapp.linkTo(searchAggregator.storeID)
        return ctx.tag[self.searchPattern.fillSlots('form-action', action)]

    def render_username(self, ctx, data):
        if self.username is None:
            for (user, domain) in getAccountNames(self.webapp.installedOn):
                self.username = '%s@%s' % (user, domain)
                break
            else:
                self.username = 'nobody@noplace'
        return ctx.tag[self.username]

    def data_settingsLink(self, ctx, data):
        return self.webapp.linkTo(self.pageComponents.settings.storeID)

    def render_head(self, ctx, data):
        return ctx.tag

    def render_header(self, ctx, data):
        staticShellContent = self.pageComponents.staticShellContent
        if staticShellContent is None:
            return ctx.tag
        header = staticShellContent.getHeader()
        if header is not None:
            return ctx.tag[header]
        else:
            return ctx.tag

    def render_footer(self, ctx, data):
        staticShellContent = self.pageComponents.staticShellContent
        if staticShellContent is None:
            return ctx.tag
        footer = staticShellContent.getFooter()
        if footer is not None:
            return ctx.tag[footer]
        else:
            return ctx.tag

INSPECTROFY = os.environ.get('MANTISSA_DEV')

class FragmentWrapperMixin:
    def __init__(self, fragment):
        self.fragment = fragment
        fragment.page = self

    def beforeRender(self, ctx):
        return getattr(self.fragment, 'beforeRender', lambda x: None)(ctx)

    def render_introspectionWidget(self, ctx, data):
        "Until we have eliminated everything but GenericAthenaLivePage"
        if INSPECTROFY:
            return ctx.tag['No debugging on crap-ass bad pages']
        else:
            return ''

    def render_head(self, ctx, data):
        l = list(getAllThemes())
        _reorderForPreference(l, self.webapp.preferredTheme)
        extras = []
        for theme in l:
            extra = theme.head()
            if extra is not None:
                extras.append(extra)
        extra = self.fragment.head()
        if extra is not None:
            extras.append(extra)
        return ctx.tag[extras]

    def render_title(self, ctx, data):
        return ctx.tag[getattr(self.fragment, 'title', self.fragment.__class__.__name__)]

    def render_content(self, ctx, data):
        return ctx.tag[self.fragment]

class GenericNavigationPage(FragmentWrapperMixin, Page, NavMixin):
    def __init__(self, webapp, fragment, pageComponents):
        Page.__init__(self, docFactory=webapp.getDocFactory('shell'))
        NavMixin.__init__(self, webapp, pageComponents)
        FragmentWrapperMixin.__init__(self, fragment)


class GenericNavigationLivePage(FragmentWrapperMixin, livepage.LivePage, NavMixin):
    def __init__(self, webapp, fragment, pageComponents):
        livepage.LivePage.__init__(self, docFactory=webapp.getDocFactory('shell'))
        NavMixin.__init__(self, webapp, pageComponents)
        FragmentWrapperMixin.__init__(self, fragment)

    # XXX TODO: support live nav, live fragments somehow
    def render_head(self, ctx, data):
        ctx.tag[t.invisible(render=t.directive("liveglue"))]
        return FragmentWrapperMixin.render_head(self, ctx, data)

    def goingLive(self, ctx, client):
        getattr(self.fragment, 'goingLive', lambda x, y: None)(ctx, client)

    def locateHandler(self, ctx, path, name):
        handler = getattr(self.fragment, 'locateHandler', None)

        if handler is None:
            return getattr(self.fragment, 'handle_' + name)
        else:
            return handler(ctx, path, name)

class GenericNavigationAthenaPage(athena.LivePage, FragmentWrapperMixin, NavMixin):
    def __init__(self, webapp, fragment, pageComponents):
        root = URL.fromString('/').child('private').child('jsmodule')
        athena.LivePage.__init__(self, getattr(fragment, 'iface', None), fragment, jsModuleRoot=root, docFactory=webapp.getDocFactory('shell'))
        NavMixin.__init__(self, webapp, pageComponents)
        FragmentWrapperMixin.__init__(self, fragment)

    def render_head(self, ctx, data):
        ctx.tag[t.invisible(render=t.directive("liveglue"))]
        return FragmentWrapperMixin.render_head(self, ctx, data)

    def render_introspectionWidget(self, ctx, data):
        if INSPECTROFY:
            f = athena.IntrospectionFragment()
            f.setFragmentParent(self)
            return ctx.tag[f]
        else:
            return ''

class PrivateRootPage(Page, NavMixin):
    addSlash = True

    def __init__(self, webapp, pageComponents):
        self.webapp = webapp
        Page.__init__(self, docFactory=webapp.getDocFactory('shell'))
        NavMixin.__init__(self, webapp, pageComponents)

    def child_(self, ctx):
        navigation = self.pageComponents.navigation
        if not navigation:
            return self
        # /private/XXXX ->
        click = self.webapp.linkTo(navigation[0].storeID)
        return URL.fromContext(ctx).click(click)

    def render_content(self, ctx, data):
        return """
        You have no default root page set, and no navigation plugins installed.  I
        don't know what to do.
        """

    def render_title(self, ctx, data):
        return ctx.tag['Private Root Page (You Should Not See This)']

    def child_jsmodule(self, ctx):
        return athena.JSModules(athena.jsDeps.mapping)

    def childFactory(self, ctx, name):
        storeID = self.webapp.linkFrom(name)
        if storeID is None:
            return None

        o = self.webapp.store.getItemByID(storeID, None)
        if o is None:
            return None
        res = IResource(o, None)
        if res is not None:
            return res
        fragment = INavigableFragment(o, None)
        if fragment is None:
            return None
        if fragment.fragmentName is not None:
            fragDocFactory = self.webapp.getDocFactory(fragment.fragmentName, None)
            if fragDocFactory is not None:
                fragment.docFactory = fragDocFactory
        if fragment.docFactory is None:
            raise RuntimeError("%r (fragment name %r) has no docFactory" % (fragment, fragment.fragmentName))

        pageClass = {False: GenericNavigationPage,
         True: GenericNavigationLivePage,
         'athena': GenericNavigationAthenaPage}.get(fragment.live)
        return pageClass(self.webapp, fragment, self.pageComponents)


class _PageComponents(record('navigation searchAggregator staticShellContent settings')):
    pass

class PrivateApplication(Item, PrefixURLMixin):
    """
    This is the root of a private, navigable web application.  It is designed
    to be installed on avatar stores after installing WebSite.

    To plug into it, install powerups of the type INavigableElement on the
    user's store.  Their tabs will be retrieved and items that are part of
    those powerups will be linked to; provide adapters for said items to either
    INavigableFragment or IResource.

    Note: IResource adapters should be used sparingly, for example, for
    specialized web resources which are not 'nodes' within the application; for
    example, that need to set a custom content/type or that should not display
    any navigation elements because they will be displayed only within IFRAME
    nodes.  Do _NOT_ use IResource adapters to provide a customized
    look-and-feel; instead use mantissa themes.  (XXX document webtheme.py more
    thoroughly)

    @ivar preferredTheme: A C{unicode} string naming the preferred theme for
    this application.  Templates and suchlike will be looked up for this theme
    first.

    @ivar hitCount: Number of page loads of this application.

    @ivar privateKey: A random integer used to deterministically but
    unpredictably perturb link generation to avoid being the target of XSS
    attacks.

    @ivar privateIndexPage: A reference to the Item whose IResource or
    INavigableFragment adapter will be displayed on login and upon viewing the
    'root' page, /private/.
    """

    implements(ISiteRootPlugin, IWebTranslator)

    typeName = 'private_web_application'
    schemaVersion = 2

    installedOn = reference()

    preferredTheme = text()
    hitCount = integer(default=0)
    privateKey = integer()

    #XXX Nothing ever uses this
    privateIndexPage = reference()

    prefixURL = 'private'

    sessioned = True
    sessionless = False

    def __init__(self, **kw):
        super(PrivateApplication, self).__init__(**kw)
        gk = genkey()
        self.privateKey = gk

    def installOn(self, other):
        super(PrivateApplication, self).installOn(other)
        other.powerUp(self, IWebTranslator)

        def findOrCreate(*a, **k):
            return other.store.findOrCreate(*a, **k)

        findOrCreate(StaticRedirect,
                     sessioned=True,
                     sessionless=False,
                     prefixURL=u'',
                     targetURL=u'/'+self.prefixURL).installOn(other, -1)

        findOrCreate(CustomizedPublicPage).installOn(other)

        findOrCreate(AuthenticationApplication)
        findOrCreate(PreferenceAggregator).installOn(other)
        findOrCreate(DefaultPreferenceCollection).installOn(other)
        findOrCreate(Settings).installOn(other)
        findOrCreate(SearchAggregator).installOn(other)

    def createResource(self):
        navigation = getTabs(self.installedOn.powerupsFor(INavigableElement))
        searchAggregator = ISearchAggregator(self.installedOn, None)
        staticShellContent = IStaticShellContent(self.installedOn, None)

        pageComponents = _PageComponents(navigation,
                                         searchAggregator,
                                         staticShellContent,
                                         self.installedOn.findFirst(Settings))

        return PrivateRootPage(self, pageComponents)

    # ISiteRootPlugin
    def resourceFactory(self, segments):
        return super(PrivateApplication, self).resourceFactory(segments)


    # IWebTranslator
    def linkTo(self, obj):
        # currently obj must be a storeID, but other types might come eventually
        return '/%s/%s' % (self.prefixURL, storeIDToWebID(self.privateKey, obj))

    def linkFrom(self, webid):
        return webIDToStoreID(self.privateKey, webid)

    def getDocFactory(self, fragmentName, default=None):
        l = list(getAllThemes())
        _reorderForPreference(l, self.preferredTheme)
        for t in l:
            fact = t.getDocFactory(fragmentName, None)
            if fact is not None:
                return fact
        return default

def upgradePrivateApplication1To2(oldApp):
    newApp = oldApp.upgradeVersion(
        'private_web_application', 1, 2,
        installedOn=oldApp.installedOn,
        preferredTheme=oldApp.preferredTheme,
        hitCount=oldApp.hitCount,
        privateKey=oldApp.privateKey,
        privateIndexPage=oldApp.privateIndexPage)
    newApp.installedOn.findOrCreate(
        CustomizedPublicPage).installOn(newApp.installedOn)
    return newApp

upgrade.registerUpgrader(upgradePrivateApplication1To2, 'private_web_application', 1, 2)

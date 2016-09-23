# [START imports]
from google.appengine.api import users
from google.appengine.ext import ndb
import os, time, datetime, webapp2, logging, urllib

import jinja2
import webapp2

admin_users = ["arnaudboland@gmail.com", "a.portois@gmail.com "]
currentSeason = "2016-2017"

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)
# [END imports]

DEFAULT_TEAM = 'Shadow Falcons'


# We set a parent key on the 'Greetings' to ensure that they are all
# in the same entity group. Queries across the single entity group
# will be consistent. However, the write rate should be limited to
# ~1/second.
def team_key(team=DEFAULT_TEAM):
    """Constructs a Datastore key for a Guestbook entity.
    We use expensebook_name as the key.
    """
    return ndb.Key('Team', team)

def props(cls):
    """ Returns a list of tuples. Each tuple contains the class attribute name and its value.
    """
    keys = [i for i in cls.__dict__.keys() if i[:1] != '_' and not hasattr(cls.__dict__[i],"__call__")]
    props = []
    for k in keys:
        props.append((k, cls.__dict__[k]))
    return props
    
class RenderModel(ndb.Model):
    """ Class that extends ndb.Model to add it a rendering function. This function converts the entity into a dictionary.
    It's used to print an entity in a readable way.  
    """
    def __init__(self, **kwargs):
        ndb.Model.__init__(self, **kwargs)
    
    def render(self):
        """ Represents the entity in a dictionary. Each key is an attribute name and its value is the attribute value.
        It works recursively. So if an attribute value is another entity, it will be rendered as well.
        """
        attr = {}
        attr["id"] = self.key.urlsafe()              #self.key.id()
        # for each entity attribute, get the attribute name and its value.
        for a in props(self.__class__):
            key = a[0]
            val = a[1]._get_value(self)
            # if atribute is not a list, make it a list. This is just to be able to treat list and non list in the same way.
            isList = True
            if type(val) is not list:
                val = [val]
                isList = False
            elements = []
            for el in val:
                # if attribute value is a string, a float, a date or a time, use it as it is.
                if type(el) == unicode or type(el) == float or type(el) == datetime.date or type(el) == datetime.datetime or type(el) == int or type(el) == bool or type(el) == datetime.time:
                    elements.append(el)
                # else if attribute value is not none, it is a key (a reference to another entity) => get its value from Datastore.
                elif el is not None:
                    elements.append(el.get().render())
                else:
                    elements.append("")
            # if list contains only 1 element, remove it from the list.
            # if len(elements) == 1:
                # attr[key] = elements[0]
            # else:
                # attr[key] = elements
            # If was not a list, remove list. 
            if not isList:
                attr[key] = elements[0]
            else:
                attr[key] = elements
        return attr

class Season(RenderModel):
    _use_cache = False
    _use_memcache = False
    name = ndb.StringProperty(indexed=True)
        
class Person(RenderModel):
    _use_cache = False
    _use_memcache = False
    firstName = ndb.StringProperty(indexed=True)
    lastName = ndb.StringProperty(indexed=True)
    surname = ndb.StringProperty(indexed=True)		
    email = ndb.StringProperty(indexed=True)	# Key Name
    type = ndb.StringProperty(indexed=True, choices=["Player","Public"])

class Event(RenderModel):
    _use_cache = False
    _use_memcache = False
    name = ndb.StringProperty(indexed=True)
    date = ndb.DateProperty(indexed =  True, required = True)
    time = ndb.TimeProperty(indexed=False)
    weather = ndb.StringProperty(indexed=False)
    # place = ndb.GeoPtProperty(indexed=False)
    #voteType = ndb.StringProperty(indexed=False, choices=["Maillons","123"])
    type = ndb.StringProperty(indexed=False, choices=["Match","Entrainement"])
    comment = ndb.StringProperty()
    
class Presence(RenderModel):
    _use_cache = False
    _use_memcache = False
    person = ndb.KeyProperty(kind='Person', indexed = True, required = True)
    comment = ndb.StringProperty()
    
class Vote(RenderModel):
    _use_cache = False
    _use_memcache = False
    fort = ndb.KeyProperty(kind='Person', indexed=False)
    fortComment = ndb.StringProperty(indexed=False)
    fortRoulette = ndb.BooleanProperty()            # True if person voted roulette.
    faible = ndb.KeyProperty(kind='Person', indexed=False)
    faibleRoulette = ndb.BooleanProperty()          # True if person voted roulette.
    faibleComment = ndb.StringProperty(indexed=False)
    boulette = ndb.KeyProperty(kind='Person', indexed = False)
    bouletteComment = ndb.StringProperty(indexed=False)
    announced = ndb.BooleanProperty()               # True if vote has been announced to team.

class Stat(RenderModel):
    _use_cache = False
    _use_memcache = False
    player = ndb.KeyProperty(kind='Person', indexed=False)
    type = ndb.StringProperty(indexed=False, choices=["goalFor","goalAgainst","forcedPCFor", "assist", "pcFor", "pcAgainst", "greenCard","yellowCard","redCard"])
    amount = ndb.IntegerProperty()
    comment = ndb.StringProperty()

class EventsListPage(webapp2.RequestHandler):
    def get(self):
        user = users.get_current_user()
        if not user:
            self.redirect(users.create_login_url(self.request.uri))       
        else:    
            if user.email().lower() in admin_users:
                # Get data.
                team = DEFAULT_TEAM            
                
                # Get events list.
                season = Season(parent=team_key(team)).query(Season.name == "2016-2017").get()
                # self.response.write(seasonKey)
                eventsList = Event.query(ancestor=season.key).order(Event.date)
                eventsRenderedList = [e.render() for e in eventsList]
                template_values = {
                    'team': team,
                    'season':season,
                    'user': user.email().lower(),
                    'events' : eventsRenderedList,
                }
                
                template = JINJA_ENVIRONMENT.get_template('events.html')
                self.response.write(template.render(template_values))
        
            else:
                template = JINJA_ENVIRONMENT.get_template('unauthorized.html')
                self.response.write(template.render(template_values))

class EventPage(webapp2.RequestHandler):
    def get(self,eventID):
        user = users.get_current_user()
        if not user:
            self.redirect(users.create_login_url(self.request.uri))       
        else:    
            if user.email().lower() in admin_users and eventID:
                # Get data.
                team = DEFAULT_TEAM            
                
                # Get events list.
                event = ndb.Key(urlsafe=eventID).get()
                
                template_values = {
                    'team': team,
                    'user': user.email().lower(),
                    'event': event,
                }
                
                template = JINJA_ENVIRONMENT.get_template('event.html')
                self.response.write(template.render(template_values))
        
            else:
                template = JINJA_ENVIRONMENT.get_template('unauthorized.html')
                self.response.write(template.render(template_values))

class FeedPage(webapp2.RequestHandler):
    def get(self):
        # Season(parent=team_key(), name="2016-2017").put()
        # ndb.Key(urlsafe="aghkZXZ-Tm9uZXI9CxIEVGVhbSIOU2hhZG93IEZhbGNvbnMMCxIGU2Vhc29uGICAgICAgJAIDAsSBUV2ZW50GICAgICAgLAIDA").delete()
        # seasonKey = Season(parent=team_key()).query(Season.name == "2016-2017").get().key
        # Event(  parent=seasonKey,
                # name = "Match 2",
                # date = datetime.date(2016, 9, 10),
                # time = datetime.time(11,30),
                # weather = "Sunny 15C",
                # # place = "",
                # type = "Match",
                # comment = "0 blesses.").put()
        self.response.write("Done.")
        pass
app = webapp2.WSGIApplication([
    ('/', EventsListPage),
    ('/event/(.*)', EventPage),
    ('/feed', FeedPage),
    
    
], debug=True)
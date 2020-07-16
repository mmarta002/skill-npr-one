from adapt.intent import IntentBuilder
from mycroft.skills.core import MycroftSkill
from mycroft.skills.common_play_skill import CommonPlaySkill, CPSMatchLevel
from mycroft import intent_handler, intent_file_handler
from mycroft.util import get_cache_directory
from mycroft.audio import wait_while_speaking

# handle api calls
class NPROne():
    def __init__(self, apiKey):
        self.serverError = False
        self.apiKey = apiKey

class NPROneSkill(CommonPlaySkill):
    def __init__(self):
        super(NPROneSkill, self).__init__(name="NPROneSkill")
        self.curl = None
        self.now_playing = None
        self.last_message = None
        self.STREAM = '{}/stream'.format(get_cache_directory('NPROneSkill'))

        # read api key for NPR One from settings and pass to api managing cnstructor
        self.apiKey = self.settings.get('api_key')
        self.nprone = NPROne(self.apiKey)
        
        # change setting if modified on web
        self.settings_change_callback = self.websettings_callback

    def CPS_match_query_phrase(self, phrase):
        """ check if skill can play input phrase
            Returns: tuple (matched phrase(str),
                            match level(CPSMatchLevel),
                            optional data(dict))
                     or None if no match was found.
        """
        matched_feed = { 'key': None, 'conf': 0.0}

        # Remove "the" as it matches too well will "other"
        search_phrase = phrase.lower().replace('the', '')

        # Catch any short explicit phrases eg "play the news"
        npr1_phrases = self.translate_list("PlayNPROne") or []
        if search_phrase.strip() in npr1_phrases:
            station_key = self.settings.get("station", "not_set")
            if station_key == "not_set":
                station_key = self.get_default_station()
            matched_feed = { 'key': station_key, 'conf': 1.0 }

        # could add func here for finding specific shows/sources from pre-defined list

        # if no specific show match but utterance contains npr one, return low-ish confidence
        if matched_feed['conf'] == 0.0 and self.voc_match(search_phrase, "NPR one"):
            matched_feed = {'key': None, 'conf': 0.5 }
            match_level = CPSMatchLevel.CATEGORY
        else:
            match_level = None
            return match_level

        return (None, match_level, None )

    def CPS_start(self, phrase, data):
        """ starts playback of npr one"""
        # use default npr one news feed
        self.handle_latest_news()
        pass

    def websettings_callback(self):
        self.apiKey = self.settings.get('api_key')
        self.log.info('NPR One skill api set to ' + self.apiKey)
        self.nprone.setApiKey(self.apiKey)
    
    def setApiKey(self,key):
        self.apiKey = key

    @intent_file_handler("PlayNPROne.intent")
    def handle_npr_one_alt(self, message):
        """ capture alternatives for request """"
        utt = message.data["utterance"]
        match = self.CPS_match_query_phrase(utt)

        # feed them to skill if valid
        if match and len(match) > 2:
            feed = match[2]["feed"]
        else:
            feed = None

        self.handle_latest_news(message, feed)

    @intent_handler(IntentBuilder("").one_of("Give", "Latest").require("News"))
    def handle_latest_news(self, message=None, feed=None):
        try:
            self.stop()
            
            # speak intro while downloading feed
            self.speak_dialog('npr1', data={})
            
            # TODO: get news feed

            # Show news title if exists
            wait_while_speaking()
            # Begin the news stream
            self.log.info('Feed: {}'.format(feed))
            self.CPS_play(('file://' + self.STREAM, mime))
            self.CPS_send_status(image=image or image_path('generic.png'),
                                 track=self.now_playing)
            self.last_message = (True, message)
            self.enable_intent('restart_playback')

        except Exception as e:
            self.log.error("Error: {0}".format(e))
            self.log.info("Traceback: {}".format(traceback.format_exc()))
            self.speak_dialog("could.not.start.the.news.feed")

    @intent_handler(IntentBuilder('').require('Restart'))
    def restart_playback(self, message):
        self.log.debug('Restarting last message')
        if self.last_message:
            self.handle_latest_news(self.last_message[1])

    def stop(self):
        # Disable restarting when stopped
        if self.last_message:
            self.disable_intent('restart_playback')
            self.last_message = None
            # Stop download process if it's running.
        if self.curl:
            try:
                self.curl.kill()
                self.curl.communicate()
            except Exception as e:
                self.log.error('Could not stop curl: {}'.format(repr(e)))
            finally:
                self.curl = None
            self.CPS_send_status()
            return True

    def CPS_send_status(self, artist='', track='', image=''):
        data = {'skill': self.name,
                'artist': artist,
                'track': track,
                'image': image,
                'status': None  # TODO Add status system
                }
        self.bus.emit(Message('play:status', data))

def create_skill():
    return NPROneSkill()
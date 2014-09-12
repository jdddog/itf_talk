#!/usr/bin/env python

import rospy
import urllib, pycurl
from threading import Thread
from std_msgs.msg import String, Float32, Bool
import subprocess
import math
import pyglet
import threading
from SoundFile import SoundFile

class ITFTalker(Thread):
    NODE_NAME = 'itf_talker'
    pub = rospy.Publisher('itf_next_sentence', String, queue_size=1)
    pub_speech_strength = rospy.Publisher('speech_strength', Float32, queue_size=1)
    pub_speech_active = rospy.Publisher('speech_active', Bool, queue_size=1)
    soundfile = None
    rms_params = {"scale": 1.0/5000, "min": 0.0, "max": 1.0}
    gletplayer = None

    def __init__(self):
        Thread.__init__(self)
        rospy.init_node(ITFTalker.NODE_NAME, log_level=rospy.INFO)
        rospy.Subscriber("itf_talk", String, self.callback)

        pyglet.clock._get_sleep_time = pyglet.clock.get_sleep_time
        pyglet.clock.get_sleep_time = lambda sleep_idle: pyglet.clock._get_sleep_time(False)

        threading.Timer(0.0, pyglet.app.run).start()
        rospy.on_shutdown(pyglet.app.exit)

    def split_text_rec(self, input_text, max_length=45):
            """
            Split a string into substrings which are at most max_length.
            """
            combined_text = []

            if (len(input_text) > max_length):
                while (len(input_text) > max_length):
                    lastSpace = max_length
                    section = ""

                    while (lastSpace > 0):
                        if (input_text[lastSpace] == ' '):
                            section = input_text[:lastSpace]
                            input_text = input_text[lastSpace:]
                            lastSpace = -1
                        lastSpace -= 1

                    combined_text.append(section)

            else:
                combined_text.append(input_text)

            return combined_text

    def downloadFile(self, url, fileName):
        fp = open(fileName, "wb")
        curl = pycurl.Curl()
        curl.setopt(pycurl.URL, url)
        curl.setopt(pycurl.WRITEDATA, fp)
        curl.perform()
        curl.close()
        fp.close()

    def getGoogleSpeechURL(self, phrase):
        googleTranslateURL = "http://translate.google.com/translate_tts?tl=en&"
        parameters = {'q': phrase}
        data = urllib.urlencode(parameters)
        googleTranslateURL = "%s%s" % (googleTranslateURL,data)
        return googleTranslateURL

    def speakSpeechFromText(self, phrase):
        phraseSections = self.split_text_rec(phrase)

        for index, section in enumerate(phraseSections):
            print "At index " + str(index) + " is " + section + "\n"

        for index, section in enumerate(phraseSections):
            googleSpeechURL = self.getGoogleSpeechURL(section)
            print "Downloading " + googleSpeechURL + " to " + "tts" + str(index).zfill(index) + ".mp3\n"
            self.downloadFile(googleSpeechURL,"tts" + str(index).zfill(index) + ".mp3")
            print index, section

        # for index, section in enumerate(phraseSections):
        #     print 'Calling mplayer with parameter ' + 'tts' + str(index).zfill(index) + '.mp3'
        #     subprocess.call(['mplayer', 'tts' + str(index).zfill(index) + '.mp3'])
        #     ITFTalker.pub.publish("Google Voice completed.")

        # for index, section in enumerate(phraseSections):
        #     fileName = 'tts' + str(index).zfill(index) + '.mp3'
        #     gletsource = pyglet.media.load(fileName, streaming=False)
        #     self.gletplayer = pyglet.media.Player()
        #     self.gletplayer.queue(gletsource)
        #     self.gletplayer.play()
        ITFTalker.pub_speech_active.publish(True)

        for index, section in enumerate(phraseSections):
            fileName = 'tts' + str(index).zfill(index) + '.mp3'
            print 'Calling SoundPlayer with parameter ' + fileName

            self.play(fileName)

            while self.soundfile:
                while self.soundfile.is_playing:
                    pass

            ITFTalker.pub.publish("Google Voice completed.")

        self.pub_speech_strength.publish(0)

        ITFTalker.pub_speech_active.publish(False)

        #os.system("mplayer tts " + str(index).zfill(index) + ".mp3 -af extrastereo=0 &")

    def hit(self, rms):
        """
        Publishes the current jaw-modified expression, given rms (root mean squared),
        the volume or the power of a small segment in the file.
        """

        # Map the power number to the jaw coefficient.
        # Note that coefficient can't effectively go below 0 or over 1.
        # It will be cut to this range at the receiving end (pau2motors node)
        p = self.rms_params
        jaw_coeff = min(max(math.sqrt(rms * p["scale"]), p["min"]), p["max"])

        self.pub_speech_strength.publish(jaw_coeff)

        # Copy pau expression message stored during handle_face_in(),
        # modify jaw and publish.
        # cmd = copy.deepcopy(self.facepau)
        # coeffs = list(cmd.m_coeffs)
        # coeffs[ShapekeyStore.getIndex("JawOpen")] = jaw_coeff
        # cmd.m_coeffs = coeffs
        # self.pub.publish(cmd)

    def stop(self):
        if self.soundfile:
          self.soundfile.stop()

    def play(self, filename):
        self.stop()
        self.soundfile = SoundFile(filename)
        self.soundfile.on_playmore = self.hit # Set callback
        self.soundfile.play()

    def callback(self, data):
        rospy.loginfo(rospy.get_caller_id()+"I heard %s",data.data)
        self.speakSpeechFromText(data.data)

if __name__ == '__main__':
    rospy.loginfo("Starting {0}...".format(ITFTalker.NODE_NAME))
    talker = ITFTalker()

    talker.start()
    rospy.loginfo("{0} started, listening for text input on topic itf_talk...".format(ITFTalker.NODE_NAME))

    rospy.spin()

    rospy.loginfo("Stopping {0}...".format(ITFTalker.NODE_NAME))
    talker.join()
    rospy.loginfo("{0} stopped.".format(ITFTalker.NODE_NAME))

from twisted.trial import unittest
from wokkel.test.helpers import XmlStreamStub

from collective.xmpp.core import protocols
from collective.xmpp.core.testing import FactoryWithJID


class VCardProtocolTest(unittest.TestCase):
    """ """

    def setUp(self):
        self.stub = XmlStreamStub()
        self.stub.xmlstream.factory = FactoryWithJID()
        self.protocol = protocols.VCardHandler()
        self.protocol.xmlstream = self.stub.xmlstream
        self.protocol.connectionInitialized()

    def test_vcard(self):
        """<iq type='set' id='H_0'>
                <vCard xmlns='vcard-temp' version='3.0'>
                    <FN>Jeremie Miller</FN>
                    <NICKNAME>jer</NICKNAME>
                    <EMAIL><INTERNET/><PREF/><USERID>jer@jabber.org</USERID></EMAIL>
                    <JABBERID>jer@jabber.org</JABBERID>
                </vCard>
            </iq>
        """
        udict = {
            'fullname': 'Jeremie Miller',
            'nickname': 'jer',
            'email': 'jeremie@jabber.org',
            'userid': 'jer@jabber.org',
            'jabberid': 'jer@jabber.org',
            }
        iq = self.protocol.createVCardIQ(udict)
        self.assertEqual(iq.attributes.get('type'), 'set')
        vcard = iq.children[0]
        self.assertEqual(vcard.name, 'vCard')
        self.assertEqual(vcard.uri, 'vcard-temp')
        self.assertEqual(vcard.attributes.get('version'), '3.0')
        self.assertEqual(vcard.toXml(), "<vCard xmlns='vcard-temp' version='3.0'><FN>Jeremie Miller</FN><NICKNAME>jer</NICKNAME><EMAIL>jeremie@jabber.org<INTERNET/><PREF/><USERID>jer@jabber.org</USERID></EMAIL><JABBERID>jer@jabber.org</JABBERID></vCard>")

    def test_sendVCard(self):
        udict = {
            'fullname': 'Jeremie Miller',
            'nickname': 'jer',
            'email': 'jeremie@jabber.org',
            'userid': 'jer@jabber.org',
            'jabberid': 'jer@jabber.org',
            }
        iq = self.protocol.sendVCard(udict)
        vcard = self.stub.output[-1]
        self.assertEqual(vcard.name, u'iq', vcard.name)


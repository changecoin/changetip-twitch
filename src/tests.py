import unittest2 as unittest # backport for latest python unittest
from chat_worker import TwitchIRCBot

class TestSequenceFunctions(unittest.TestCase):

    def test_pubmsg(self):
        # TODO: test each message path
        # bot = TwitchIRCBot()

        message = "great play!"
        author = "@bob"
        channel = "#alice"

        # bot._parse_pubmsg(message, author, channel)

        self.assertEqual(True, True)

if __name__ == '__main__':
    unittest.main()
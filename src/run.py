from master import TwitchMaster
import sys

if __name__ == "__main__":
    try:
        Twitch = TwitchMaster()
    except KeyboardInterrupt:
        print >> sys.stderr, '\nExiting by user request.\n'
        sys.exit(0)
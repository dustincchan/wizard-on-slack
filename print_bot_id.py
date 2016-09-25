import os
from slackclient import SlackClient

BOT_NAME = 'wizardbot'

#FIXME this token needs to be hidden
slack_client = SlackClient(os.environ.get('SLACK_BOT_TOKEN'))

if __name__ == "__main__":
    api_call = slack_client.api_call("channels.list")
    if api_call.get('ok'):
        #retrieve all users so we can find our bot
        channels = api_call.get('channels')
        for channel in channels:
            if channel.get('name') == "maingame":
                print(channel.get('id'))
    else:
        print("could not find bot user with the name " + BOT_NAME)

import time
import os

import requests
import slackclient


def open(token):
    return StubAPI(token)


def open_slack(token):
    return SlackAPI(token)


class StubAPI:
    def __init__(self, token):
        self.token = token

    def read(self):
        return [
            Message('Que tal?'),
            Message('/teapot test'),
            Message('Just msg'),
            Message('Hi')
        ]

    def write(self, messages):
        print(messages)

    def is_connected(self):
        return True

    def is_server_connected(self):
        return True


class SlackAPI(StubAPI):
    def __init__(self, token):
        super().__init__(token)
        self.sc = slackclient.SlackClient(token)

    def is_connected(self, *args, **kwargs):
        return self.sc.rtm_connect(*args, **kwargs)

    def is_server_connected(self):
        # I didn't know about this! Thanks :)
        return self.sc.server.connected

    def read(self):
        # This method returns not Message objects but raw events from Slack API
        # This means that other functions should know about expected structure
        # and this breaks the idea of Single Responsibility and code isolation
        return self.sc.rtm_read()

    def write(self, messages):
        # This function plays right :)
        self.sc.rtm_send_message(messages.channel, messages.text)


class Message:
    def __init__(self, text, channel, author=None):
        self.text = text
        self.channel = channel
        self.author = author

    def __repr__(self):
        return 'Message with text {} for channel {} written by {}'.format(
            self.text, self.channel, self.author)


def get_slack_user(user_id):
    url_user = 'https://slack.com/api/users.info?token={}&user={}&pretty=1'.format(
                                    os.environ["SLACK_API_TOKEN"], user_id,
                                )
    resp = requests.get(url_user)
    if resp.status_code == 200:
        return resp.json().get('user')
    return None


def is_greeting(lowercased_text):
    """This small function makes a decision. We can test it also ;)

    >>> is_greeting('hello, world')
    True
    >>> is_greeting('hey jude')
    True
    >>> is_greeting('hi there')
    True

    >>> is_greeting('¡hola!')
    False
    >>> is_greeting('chip and dale')
    True
    """
    return any(
       phrase in lowercased_text
       for phrase in ('hi', 'hello', 'hey')
   )


def process(messages):
    responses = []
    for msg in messages:
        if not isinstance(msg, dict):
            # Fast skip. But this `dict` thing is Slack-specific.
            # We should expect a list of Message objects and work with them.
            # So the brain could process messages from different APIs
            continue

        if 'text' in msg:
            text = msg['text']  # we have checked that 'text' key is present

            if is_greeting(text.lower()):  # transform to lowercase only once
                # we could use check msg['type'] == 'text' to get rid of those
                # calls to `dict.get`
                if msg.get('channel'):
                    user = msg.get('user')
                    user = get_slack_user(user) if user else ''
                    resp_text = 'Hi, {}!'.format(
                        user.get('real_name', 'Unknown')
                    )
                    responses.append(
                        Message(resp_text, msg.get('channel')),
                    )

            elif text.startswith('/teapot'):
                responses.append(teapot())
            elif text.startswith('/author'):
                responses.append(teapot())
            else:
                echo(msg)
    return responses


def echo(message):
    return message


def teapot():
    return Message('Standart message')


def author():
    return Message('Pavel Mikhadziuk')


def main():
    incoming_queue = []
    outgoing_queue = []

    custom_api = open_slack(os.environ["SLACK_API_TOKEN"])
    if not custom_api.is_connected():
        print('Connection failed')
        exit(1)

    while custom_api.is_server_connected():
        if len(outgoing_queue):
            # only first message from the outgoing queue was sent to API
            # bacause of `list.pop(0)`
            for outgoing_message in outgoing_queue:
                custom_api.write(outgoing_message)
            outgoing_queue.clear()  # Monopoly access to the queue

        incoming_queue = custom_api.read()
        if incoming_queue:
            outgoing_queue.extend(process(incoming_queue))
        time.sleep(10)


if __name__ == '__main__':
    main()

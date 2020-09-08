# i90bot

i90bot is a Slack app that implements a `/shorten` command to shorten a URL.

## Usage

To deploy i90bot, you'll need to:

1. Fork this repo, and customize `serverless.yml` to match your needs.
2. Deploy with `yarn run sls deploy -s prod`. This will print the URL of your API Gateway endpoint.
3. Configure a [Slack slash command](https://api.slack.com/interactivity/slash-commands) to hit the API Gateway endpoint.


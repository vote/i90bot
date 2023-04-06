# i90bot

i90bot is a Slack app that implements a `/shorten` command to shorten a URL.

It uses the Serverless framework to deploy to AWS API Gateway. The existing `serverless.yml` file includes references 
to several secrets that should be configured in your AWS Parameter Store. 

## Usage

To deploy i90bot, you'll need to:

1. Create a Slack app.
2. Fork this repo, and customize `serverless.yml` to match your needs, including pointing `SLACK_SIGNING_SECRET`
to the signing secret from the app you created in step 1.
3. Deploy with `yarn run sls deploy -s prod`. This will print the URL of your API Gateway endpoint.
(Note: Replace `prod` with a different environment identifier to deploy to a different environment.)
4. Configure a [Slack slash command](https://api.slack.com/interactivity/slash-commands) to hit the API Gateway endpoint.


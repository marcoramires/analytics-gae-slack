from apiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials
import httplib2
from urllib2 import HTTPError
from slackclient import SlackClient
import json


def get_service(api_name, api_version, scope, key_file_location):
    credentials = ServiceAccountCredentials.from_json_keyfile_name(key_file_location, scope)
    http = credentials.authorize(httplib2.Http())
    service = build(api_name, api_version, http=http)

    return service


def get_first_profile_id(service):
    accounts = service.management().accounts().list().execute()

    if accounts.get('items'):
        account = accounts.get('items')[0].get('id')
        properties = service.management().webproperties().list(accountId=account).execute()

        if properties.get('items'):
            property = properties.get('items')[0].get('id')
            profiles = service.management().profiles().list(accountId=account, webPropertyId=property).execute()

        if profiles.get('items'):
            return profiles.get('items')[0].get('id')

    return None


def get_results(service, profile_id, metrics, dimensions, sort):
    try:
        return service.data().realtime().get(
            ids='ga:' + profile_id,
            metrics=metrics,
            dimensions=dimensions,
            sort=sort
        ).execute()

    except TypeError, error:
        # Handle errors in constructing a query.
        print ('There was an error in constructing your query : %s' % error)

    except HTTPError, error:
        # Handle API errors.
        print ('Arg, there was an API error : %s : %s' %
               (error.resp.status, error._get_reason()))


def get_detailed_totals(results):
    output = []

    totals = results.get('totalsForAllResults')
    for metric_name, metric_total in totals.iteritems():
        output.append(metric_total)

    if results.get('rows', []):
        detailed = ''
        for row in results.get('rows')[0:10]:
            if row[0] == '(not set)':
                detail = ''
            else:
                detail = row[0]
            detailed += '*' + row[2] + '* ' + row[1] + detail + '\n'

        output.append(detailed)

    return output


def main():
    response = ''
    scope = ['https://www.googleapis.com/auth/analytics.readonly']
    key_file_location = '_analytics-key.json'

    service = get_service('analytics', 'v3', scope, key_file_location)
    profile = get_first_profile_id(service)

    metrics = 'rt:activeUsers'
    dimensions = 'rt:referralPath,rt:source'
    sort = '-rt:activeUsers'

    detailed = get_detailed_totals(get_results(service, profile, metrics=metrics, dimensions=dimensions, sort=sort))
    total_active = detailed[0]
    details = detailed[1]

    if int(total_active) >= 500 :
        try:
            # e.g. _slack-key.json
            # {"token": "<slack token>"}
            with open('_slack-key.json') as json_file:
                json_data = json.load(json_file)
            token = json_data['token']
            sc = SlackClient(token)
            chan = 'google-analytics'
            message = '\n*Google Analytics Real-Time*\n Active Users:\t*' + total_active + '*\n' + details
            # View this post for GAE requests error
            # https://github.com/kennethreitz/requests/compare/master...agfor:master
            print sc.api_call('chat.postMessage', as_user='true', channel=chan, text=message)
            print ('************ DONE ***************')
            response = 'Posted message to Slack #google-analytics'
        except HTTPError, error:
            response = ('Arg, there was an API error : %s : %s' %
                        (error.resp.status, error._get_reason()))

    return response

if __name__ == '__main__':
    main()


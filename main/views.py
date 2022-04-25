
from user_agents import parse
from p0f import P0f, P0fException

from django.shortcuts import render
from django.views import View
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_protect
from django.middleware.csrf import get_token

import requests
import json

def get_location_data(ip_address):
    location_keys_list = ['ip', 'city', 'country_code', 'country_name', 'languages']
    data = requests.get(f'https://ipapi.co/{ip_address}/json/').json()
    return {key: data.get(key) for key in location_keys_list if key in data}


def get_timezone_info(ip_address):
    keys_list = ['timezone', 'utc_offset']
    data = requests.get(f'https://ipapi.co/{ip_address}/json/').json()
    return {key: data.get(key) for key in keys_list if key in data}


def get_ip_address(data):
    headers_list = ['HTTP_X_REAL_IP', 'HTTP_CLIENT_IP', 'HTTP_X_FORWARDED_FOR', 'HTTP_X_FORWARDED',
                    'HTTP_X_CLUSTER_CLIENT_IP', 'HTTP_FORWARDED_FOR', 'HTTP_FORWARDED', 'REMOTE_ADDR']

    for header in headers_list:
        if header in data:
            return data.get(header)


def get_all_ips(data):
    headers_list = ['HTTP_X_REAL_IP', 'HTTP_CLIENT_IP', 'HTTP_X_FORWARDED_FOR', 'HTTP_X_FORWARDED',
                    'HTTP_X_CLUSTER_CLIENT_IP', 'HTTP_FORWARDED_FOR', 'HTTP_FORWARDED', 'REMOTE_ADDR']

    return {header: data.get(header) for header in headers_list if header in data}


def parse_user_agent(user_agent):
    user_agent_info = parse(user_agent)
    print(user_agent_info)
    return str(user_agent_info)


def get_p0f_info(ip_adress):
    data = None
    p0f = P0f("p0f.sock")
    # point this to socket defined with "-s" argument.
    try:
        data = p0f.get_info(ip_adress)
    except P0fException as e:
        # Invalid query was sent to p0f. Maybe the API has changed?
        print(e)
    except KeyError as e:
        # No data is available for this IP address.
        print(e)
    except ValueError as e:
        # p0f returned invalid constant values. Maybe the API has changed?
        print(e)

    if data:
        print("First seen:", data["first_seen"])
        print("Last seen:", data["last_seen"])


class HomeView(View):
    template_name = 'main/index.html'

    def get(self, request):
        # print(get_token(request))

        params = {key: request.META.get(key) for key in request.META if not key.startswith('wsgi.')}

        ip_address = get_ip_address(request.META)
        location_data = get_location_data(ip_address)

        all_ips = get_all_ips(ip_address)
        user_agent_info = parse_user_agent(request.META.get('HTTP_USER_AGENT'))
        timezone_info = get_timezone_info(ip_address)

        # get_p0f_info(ip_address)


        context = {'params': params,
                   'location_data': location_data,
                   'user_agent_info': user_agent_info,
                   'timezone_info': timezone_info,
                   'all_ips': all_ips }

        # print(request.headers)

        return render(request, self.template_name, context)


# @csrf_protect
def set_secret_data(request):
    json_data = json.loads(request.body)
    # print(get_token(request))
    # print(json_data)
    return HttpResponse(5)

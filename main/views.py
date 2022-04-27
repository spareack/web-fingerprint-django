
from user_agents import parse
from p0f import P0f, P0fException

from django.shortcuts import render
from django.views import View
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_protect
from django.middleware.csrf import get_token
from .models import User

import requests
import json
import math


def get_location_data(ip_address):
    location_keys_list = ['ip', 'city', 'country_code', 'country_name', 'languages', 'timezone', 'utc_offset', 'error']
    data = requests.get(f'https://ipapi.co/{ip_address}/json/').json()
    print(data)

    return {key: data.get(key) for key in location_keys_list if key in data}


def get_ip_address(data):
    headers_list = ['HTTP_X_REAL_IP', 'HTTP_CLIENT_IP', 'HTTP_X_ORIGINAL-FORWARDED-FOR', 'HTTP_X_FORWARDED_FOR',
                    'HTTP_X_FORWARDED', 'HTTP_CF_Connecting_IP', 'HTTP_X_CLUSTER_CLIENT_IP', 'HTTP_FORWARDED_FOR',
                    'HTTP_FORWARDED', 'REMOTE_ADDR']

    for header in headers_list:
        if header in data:
            return data.get(header)


def get_proxy_info(data):
    headers_list = ['HTTP_X_REAL_IP', 'HTTP_CLIENT_IP', 'HTTP_X_ORIGINAL-FORWARDED-FOR', 'HTTP_X_FORWARDED_FOR',
                    'HTTP_X_FORWARDED', 'HTTP_CF_Connecting_IP', 'HTTP_X_CLUSTER_CLIENT_IP', 'HTTP_FORWARDED_FOR',
                    'HTTP_FORWARDED', 'REMOTE_ADDR']
    all_ips = {header: data.get(header) for header in headers_list if header in data}

    proxy_response = ''
    if len(all_ips) > 1:
        proxy_value = False
        keys = list(all_ips.keys())
        for i in range(1, len(all_ips.keys())):
            if all_ips[keys[i-1]] != all_ips[keys[i]]:
                proxy_response += '' if proxy_value else '' + f'{keys[i-1]} != {keys[i]}'
                proxy_value = True

        if proxy_value:
            proxy_response = 'Using Proxy or Redirect connection: ' + proxy_response
        else:
            proxy_response += 'No Proxy or connection redirect'

    return {'all_ips': all_ips, 'proxy_value': proxy_response}


def parse_user_agent(user_agent):
    user_agent_info = parse(user_agent)
    print(user_agent_info.browser.family)
    print(user_agent_info.os.family)
    print(user_agent_info.device.family)
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
        print(get_token(request))
        ip_address = get_ip_address(request.META)
        params = {key: request.META.get(key) for key in request.META if not key.startswith('wsgi.')}


        check_user = User.objects.filter(IP=ip_address)
        if check_user.exists():
            check_user.update(headers=params)
        else:
            User.objects.create(IP=ip_address, headers=params)


        location_data = get_location_data(ip_address)

        proxy_info = get_proxy_info(ip_address)
        user_agent_info = parse_user_agent(request.META.get('HTTP_USER_AGENT'))

        # get_p0f_info(ip_address)

        context = {'params': params,
                   'location_data': location_data,
                   'user_agent_info': user_agent_info,
                   'proxy_info': proxy_info,
                   'local': 'true' if 'error' in location_data and location_data['error'] else 'false'
                   }

        return render(request, self.template_name, context)


class DataJs(View):

    def compare_js_headers(self, current_js_data):
        all_users = User.objects.all()

        compare_results = {}
        for user in all_users:
            hard_compare_str = hard_compare_bool = hard_compare_int = 0
            soft_compare_str = soft_compare_bool = soft_compare_int = 0
            js_data = json.loads(user.js_data)
            for js_header_key in js_data & current_js_data:

                if type(js_data[js_header_key]) == 'str' and type(current_js_data[js_header_key]) == 'str':
                    if js_data[js_header_key] == current_js_data[js_header_key]:
                        hard_compare_str += 1

                    soft_compare_str += js_data[js_header_key] & current_js_data[js_header_key]

                elif type(js_data[js_header_key]) == 'bool' and type(current_js_data[js_header_key]) == 'bool':
                    if js_data[js_header_key] == current_js_data[js_header_key]:
                        hard_compare_bool += 1

                    soft_compare_bool += js_data[js_header_key] & current_js_data[js_header_key]

                elif type(js_data[js_header_key]) == 'int' and type(current_js_data[js_header_key]) == 'int':
                    if js_data[js_header_key] == current_js_data[js_header_key]:
                        hard_compare_int += 1

                    soft_compare_int += math.fabs(js_data[js_header_key] - current_js_data[js_header_key])

            hard_compare_sum = hard_compare_str + hard_compare_bool + hard_compare_int
            soft_compare_sum = soft_compare_str + soft_compare_bool + soft_compare_int

            compare_results.add(
                {
                    'hard_compare_str': hard_compare_str,
                    'hard_compare_bool': hard_compare_bool,
                    'hard_compare_int': hard_compare_int,
                    'soft_compare_str': soft_compare_str,
                    'soft_compare_bool': soft_compare_bool,
                    'soft_compare_int': soft_compare_int,
                    'hard_compare_sum': hard_compare_sum,
                    'soft_compare_sum': soft_compare_sum,
                    'average_compare_sum': hard_compare_sum + soft_compare_sum,
                })

        return compare_results

    def handle_js_data(self, js_data):
        compare_results = self.compare_js_headers(js_data)
        print(compare_results)

    def post(self, request):
        ip_address = get_ip_address(request.META)
        json_data = json.loads(request.body)

        check_user = User.objects.filter(IP=ip_address)
        if check_user.exists():
            check_user.update(js_data=json.dumps(json_data))
        else:
            User.objects.create(IP=ip_address, js_data=json.dumps(json_data))

        return HttpResponse(5)




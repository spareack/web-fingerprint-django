
from user_agents import parse
from p0f import P0f, P0fException

from django.shortcuts import render
from django.views import View
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_protect
from django.middleware.csrf import get_token
from .models import User
from django.core.serializers import serialize
from django.views.decorators.csrf import csrf_exempt

import requests
import json
import math
import datetime


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
            if all_ips[keys[i - 1]] != all_ips[keys[i]]:
                proxy_response += '' if proxy_value else '' + f'{keys[i - 1]} != {keys[i]}'
                proxy_value = True

        if proxy_value:
            proxy_response = 'Using Proxy or Redirect connection: ' + proxy_response
        else:
            proxy_response = 'No Proxy or connection redirect'
    else:
        proxy_response = 'No Proxy or connection redirect'

    return {'all_ips': all_ips, 'proxy_value': proxy_response}


def get_location_data(ip_address):
    location_keys_list = ['ip', 'city', 'country_code', 'country_name', 'languages',
                          'timezone', 'utc_offset', 'error', 'reason']
    data = requests.get(f'https://ipapi.co/{ip_address}/json/').json()

    return {key: data.get(key) for key in location_keys_list if key in data}


def parse_user_agent(user_agent):
    user_agent_info = parse(user_agent)
    response = {'device_info': str(user_agent_info), 'device_os': user_agent_info.device.family}
    response_str = 'User Agent seems valid'
    generic = False
    mobile = user_agent_info.is_mobile or user_agent_info.is_tablet

    if mobile or user_agent_info.device.family == 'Generic Smartphone' or \
            user_agent_info.device.family == 'Generic Feature Phone' or \
            user_agent_info.device.family == 'Generic_Android_Tablet':
        generic = True

        if user_agent_info.browser.family == 'Firefox':
            response_str = 'trying to secure mobile device, Tor browser'
        else:
            response_str = 'trying to secure mobile device, more likely tor browser'

    response['os_check'] = response_str
    response['generic'] = generic
    response['mobile'] = mobile
    response['browser'] = user_agent_info.browser.family

    return response


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
        ip_address = get_ip_address(request.META)
        params = {key: request.META.get(key) for key in request.META if not key.startswith('wsgi.')}

        # check_user = User.objects.filter(IP=ip_address)
        # if check_user.exists():
        #     check_user.update(headers=params)
        # else:
        #     User.objects.create(IP=ip_address, headers=params)

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

@csrf_exempt
class DataJs(View):

    def compare_js_headers(self, current_js_data):
        all_users = User.objects.all()

        compare_results = []
        for user in all_users:
            hard_compare_str = hard_compare_bool = hard_compare_int = 0
            soft_compare_str = soft_compare_bool = soft_compare_int = 0

            if user.js_data != '':

                js_data = json.loads(user.js_data)
                for js_header_key in set(js_data.keys()) & set(current_js_data.keys()):

                    if type(js_data[js_header_key]) == str and type(current_js_data[js_header_key]) == str:
                        if js_data[js_header_key] == current_js_data[js_header_key]:
                            hard_compare_str += 1

                        soft_compare_str += js_data[js_header_key] & current_js_data[js_header_key]

                    elif type(js_data[js_header_key]) == bool and type(current_js_data[js_header_key]) == bool:
                        if js_data[js_header_key] == current_js_data[js_header_key]:
                            hard_compare_bool += 1

                        soft_compare_bool += js_data[js_header_key] & current_js_data[js_header_key]

                    elif type(js_data[js_header_key]) == int and type(current_js_data[js_header_key]) == int:
                        if js_data[js_header_key] == current_js_data[js_header_key]:
                            hard_compare_int += 1

                        soft_compare_int += math.fabs(js_data[js_header_key] - current_js_data[js_header_key])

            hard_compare_sum = hard_compare_str + hard_compare_bool + hard_compare_int
            soft_compare_sum = soft_compare_str + soft_compare_bool + soft_compare_int

            compare_results.append(
                {
                    # 'hard_compare_str': hard_compare_str,
                    # 'hard_compare_bool': hard_compare_bool,
                    # 'hard_compare_int': hard_compare_int,
                    # 'soft_compare_str': soft_compare_str,
                    # 'soft_compare_bool': soft_compare_bool,
                    # 'soft_compare_int': soft_compare_int,
                    'hard_compare_sum': hard_compare_sum,
                    'soft_compare_sum': soft_compare_sum,
                    # 'average_compare_sum': hard_compare_sum + soft_compare_sum,
                })

        return compare_results

    def search_component(self, component):
        all_users = User.objects.all()
        for user in all_users:
            spec_data = json.loads(user.spec_data)

            if user.IP == component:
                return user.datetime.strftime("%Y/%m/%d %H:%M:%S")

            for header in spec_data:
                if spec_data[header] == component:
                    return user.datetime.strftime("%Y/%m/%d %H:%M:%S")
        return None

    def get_main_sum(self, request):

        headers = {key: request.META.get(key) for key in request.META if 'wsgi' not in key.lower() and type(request.META[key]) in [str, int, bool]}
        js_data = json.loads(request.body)
        js_spec_headers = js_data['special_values']
        compare_results = self.compare_js_headers(js_data)

        response = ''
        test_hash = js_data['test_hash']
        test_hash_visit = self.search_component(test_hash)

        if test_hash_visit is not None:
            response += f'<h6 style="display: inline">Canvas Hash Test:&nbsp;</h6> ' \
                f'<span style="margin-right: 200px;">{test_hash}: <span class="badge bg-danger text-white"> Same hash visit at {test_hash_visit}</span></span>'
        else:
            response += f'<br><h6 style="display: inline">Canvas Hash Test:&nbsp;</h6> ' \
                f'<span style="margin-right: 200px;">{test_hash}: <span class="badge bg-success text-white"> First Entry</span></span>'

        # print(js_data)
        fingerprint = js_data['fingerprint_js']
        fingerprint_visit = self.search_component(fingerprint)

        if fingerprint_visit is not None:
            response += f'<br><h6 style="display: inline">Fingerprint Test:&nbsp;</h6> ' \
                f'<span style="margin-right: 200px;">{fingerprint}: <span class="badge bg-danger text-white"> Same fingerprint at {fingerprint_visit}</span></span>'
        else:
            response += f'<br><h6 style="display: inline">Fingerprint Test:&nbsp;</h6> ' \
                f'<span style="margin-right: 200px;">{fingerprint}: <span class="badge bg-success text-white"> First Entry </span></span>'

        ip_address = get_ip_address(request.META)
        ip_address_visit = self.search_component(ip_address)

        if ip_address_visit is not None:
            response += f'<br><h6 style="display: inline">IP address:&nbsp;</h6> ' \
                f'<span style="margin-right: 200px;">{ip_address}: <span class="badge bg-danger text-white"> Same address at {ip_address_visit}</span></span>'
        else:
            response += f'<br><h6 style="display: inline">IP address:&nbsp;</h6> ' \
                f'<span style="margin-right: 200px;">{ip_address}: <span class="badge bg-success text-white"> First Entry </span></span>'

        location_data = get_location_data(ip_address)
        system_language = request.META.get('HTTP_ACCEPT_LANGUAGE')
        system_language_main = js_spec_headers.get('language')

        if 'languages' in location_data:
            if system_language_main.lower() not in location_data['languages'].lower() and \
                    all(lang not in system_language_main.lower() for lang in location_data['languages'].lower()):

                response += f'<br><h6 style="display: inline">System and Server Languages are different:&nbsp;</h6> ' \
                    f'<span style="margin-right: 200px;">{system_language_main} not in {location_data["languages"]}</span>'
            else:
                response += f'<br><h6 style="display: inline">System contain Server Languages:&nbsp;</h6> ' \
                    f'<span style="margin-right: 200px;">{system_language_main} and {location_data["languages"]}</span>'
        else:
            response += f'<br><h6 style="display: inline">System and Server Languages:&nbsp;</h6> ' \
                f'<span style="margin-right: 200px;">IP config error</span>'

        if 'utc_offset' in location_data:
            if js_data['system_timezone'] != location_data['utc_offset']:
                response += f'<br><h6 style="display: inline">System and Server Time are different:&nbsp;</h6> ' \
                    f'<span style="margin-right: 200px;">{js_data["system_timezone"]} different' \
                    f' with {location_data["utc_offset"]} {location_data["timezone"]}</span>'
            else:
                response += f'<br><h6 style="display: inline">System time equals Server time:&nbsp;</h6> ' \
                    f'<span style="margin-right: 200px;">{location_data["utc_offset"]} {location_data["timezone"]}</span>'
        else:
            response += f'<br><h6 style="display: inline">System time and Server time:&nbsp;</h6> ' \
                f'<span style="margin-right: 200px;">IP config error</span>'

        proxy_info = get_proxy_info(headers)

        response += f'<br><h6 style="display: inline">Proxy info:&nbsp;</h6> ' \
            f'<span style="margin-right: 200px;"> {proxy_info.get("proxy_value")}</span>'

        user_agent_info = parse_user_agent(request.META.get('HTTP_USER_AGENT'))
        response += f'<br><h6 style="display: inline">Device info:&nbsp;</h6> ' \
            f'<span style="margin-right: 200px;"> {user_agent_info.get("os_check")}</span>'

        if js_spec_headers.get('screenWidth2') == js_spec_headers.get('availWidth') and \
                js_spec_headers.get('screenHeight2') == js_spec_headers.get('availHeight'):
            if user_agent_info.get("mobile"):
                if user_agent_info.get("generic"):
                    response += f'<br><h6 style="display: inline">Tor browser:&nbsp;</h6> ' \
                        f'<span style="margin-right: 200px;"> Mobile Tor Browser </span>'
                else:
                    response += f'<br><h6 style="display: inline">Tor browser:&nbsp;</h6> ' \
                        f'<span style="margin-right: 200px;"> No </span>'
            elif user_agent_info.get('browser') == 'Mozilla':
                response += f'<br><h6 style="display: inline">Tor browser:&nbsp;</h6> ' \
                    f'<span style="margin-right: 200px;"> Yes (screen test + browser family) </span>'
            else:
                response += f'<br><h6 style="display: inline">Tor browser:&nbsp;</h6> ' \
                    f'<span style="margin-right: 200px;"> Yes (screen test) </span>'
        else:
            response += f'<br><h6 style="display: inline">Tor browser:&nbsp;</h6> ' \
                f'<span style="margin-right: 200px;"> No </span>'

        for result in compare_results:
            response += f'<br><h6 style="display: inline">Compare:&nbsp;</h6> ' \
                f'<span style="margin-right: 200px;"> {result} </span>'

        for i in headers:
            print(i, headers[i])

        if test_hash_visit is None or fingerprint_visit is None or ip_address_visit is None:
            spec_data = {'test_hash': test_hash, 'fingerprint': fingerprint}

            User.objects.create(IP=ip_address, headers=json.dumps(headers),
                                js_data=json.dumps(js_spec_headers), spec_data=json.dumps(spec_data))

        return response

    def post(self, request):

        response = self.get_main_sum(request)


        return HttpResponse(response)




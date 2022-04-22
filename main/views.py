
from user_agents import parse

from django.shortcuts import render
from django.views import View
from django.http import HttpResponse

import requests


def get_location_data(ip_address):
    response = requests.get(f'https://ipapi.co/{ip_address}/json/').json()
    return response


def get_ip_address(data):
    headers_list = ['HTTP_X_REAL_IP', 'HTTP_CLIENT_IP', 'HTTP_X_FORWARDED_FOR', 'HTTP_X_FORWARDED',
                    'HTTP_X_CLUSTER_CLIENT_IP', 'HTTP_FORWARDED_FOR', 'HTTP_FORWARDED', 'REMOTE_ADDR']

    for header in headers_list:
        if header in data:
            return data.get(header)


def parse_user_agent(user_agent):
    user_agent_info = parse(user_agent)
    return str(user_agent_info)


class HomeView(View):
    template_name = 'main/index.html'

    def get(self, request):
        params = {key: request.META.get(key) for key in request.META if not key.startwith('wsgi.')}

        ip_address = get_ip_address(request.META)
        location_data = get_location_data(ip_address)

        location_keys_list = ['ip', 'city', 'country_code', 'country_name', 'timezone', 'languages']

        user_agent_info = parse_user_agent(request.META.get('HTTP_USER_AGENT'))

        context = {'params': params,
                   'location_data': location_data,
                   'ip_timezone': location_data.get('utc_offset'),
                   'user_agent_info': user_agent_info}

        # print(request.headers)

        return render(request, self.template_name, context)

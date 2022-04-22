
from django.shortcuts import render
from django.views import View
from django.http import HttpResponse

import requests


def get_location_data(ip_address):
    response = requests.get(f'https://ipapi.co/{ip_address}/json/').json()
    return response


def get_ip_address(data):
    headers_list = 'HTTP_CLIENT_IP', 'HTTP_X_FORWARDED_FOR', 'HTTP_X_FORWARDED', 'HTTP_X_CLUSTER_CLIENT_IP', \
                   'HTTP_FORWARDED_FOR', 'HTTP_FORWARDED', 'REMOTE_ADDR'

    for header in headers_list:
        if header in data:
            return data.get(header)



class HomeView(View):
    template_name = 'main/index.html'

    def get(self, request):
        params = {key: request.META.get(key) for key in request.META if key != 'wsgi.file_wrapper'}

        ip_address = get_ip_address(params)
        location_data = get_location_data(request.META.get(ip_address))

        context = {'params': params, 'location_data': location_data}

        # print(request.headers)

        return render(request, self.template_name, context)


from django.shortcuts import render
from django.views import View
from django.http import HttpResponse

import requests


def get_location_data(ip_address):
    response = requests.get(f'https://ipapi.co/{ip_address}/json/').json()
    return response

class HomeView(View):
    template_name = 'main/index.html'

    def get(self, request):
        params = {key: request.META.get(key) for key in request.META if key != 'wsgi.file_wrapper'}
        location_data = get_location_data(request.META.get('REMOTE_ADDR'))

        context = {'params': params, 'location_data': location_data}

        # print(request.headers)

        return render(request, self.template_name, context)

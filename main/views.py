
from django.shortcuts import render
from django.views import View
from django.http import HttpResponse


class HomeView(View):
    template_name = 'main/index.html'

    def get(self, request):
        params = {key: request.META.get(key) for key in request.META if key != 'wsgi.file_wrapper'}
        context = {'params': params}

        print(params)

        return render(request, self.template_name, context)

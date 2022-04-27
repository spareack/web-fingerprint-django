from django.db import models
from django.utils import timezone

# Create your models here.


class User(models.Model):
    IP = models.CharField(max_length=15)
    headers = models.TextField()
    js_data = models.TextField()
    datetime = models.DateTimeField(auto_now_add=True)

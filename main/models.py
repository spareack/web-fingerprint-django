from django.db import models

# Create your models here.


class User(models.Model):
    IP = models.CharField(max_length=15)
    headers = models.TextField()
    js_data = models.TextField()

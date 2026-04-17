from django.db import models
from core.models import BasePetReport

class Embedding(models.Model):
    pet = models.ForeignKey(BasePetReport, on_delete=models.CASCADE, related_name='embeddings')
    feature_vector = models.JSONField()

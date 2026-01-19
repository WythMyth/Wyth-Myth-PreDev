from django.db import models

# Create your models here.
class HeroVideo(models.Model):
    title = models.CharField(max_length=200)
    video = models.FileField(upload_to='videos/', blank=True, null=True) 
    video_url = models.URLField(null=True,blank=True) 

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title
    
class ContactUs(models.Model):

    name = models.CharField(max_length=255)
    email = models.EmailField()
    subject = models.CharField(max_length=255, null=True, blank=True)
    message = models.TextField(null=True,blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    def __str__(self):
        return self.name
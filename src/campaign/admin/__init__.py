from django.contrib import admin
from campaign.models import Campaign
from .campaign import CampaignAdmin

admin.site.register(Campaign, CampaignAdmin)

from django.contrib import admin


class CoinDecimalNumberAdmin(admin.ModelAdmin):
    list_display = ('id', 'coin_pair', 'decimal_num')
    list_filter = ('coin_pair',)

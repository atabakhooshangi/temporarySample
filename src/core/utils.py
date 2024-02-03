import os
from types import SimpleNamespace
from typing import Union, Optional

from django.contrib import admin
from django.contrib.admin.views import autocomplete
from django.contrib.admin.widgets import AutocompleteSelect
from django.urls import reverse
from dotenv import load_dotenv
from decimal import Decimal
from signals.exceptions import ValueNumberIsNotValid
from signals.models import CoinDecimalNumber

load_dotenv()


def convertor(
        number,
        quote: str = None,
        base: str = None,
        to: str = Optional[Union["decimal", "int"]]
):
    default_value = 10 ** 8
    if quote and base:
        c_type = quote + '/' + base
        try:
            max_digits = 10 ** CoinDecimalNumber.objects.get(coin_pair=c_type).decimal_num
        except CoinDecimalNumber.DoesNotExist:
            max_digits = default_value
    else:
        max_digits = default_value
    if to == 'decimal':
        return number / max_digits
    if to == 'int':
        if float('0.' + str(number).split('.')[len(str(number).split('.')) - 1]) < (1 / max_digits):
            raise ValueNumberIsNotValid(
                detail='Decimal part of {} can not less than {}'.format(number, (1 / max_digits)))
        return Decimal(f'{number}') * Decimal(f'{max_digits}')


class MyAutocompleteSelectWidget(AutocompleteSelect):
    url_name = 'my_autocomplete'

    def get_url(self):
        return reverse(self.url_name)

    def optgroups(self, name, value, attr=None):
        to_field_name = getattr(self.field.remote_field, 'field_name')
        self.choices = SimpleNamespace(
            field=SimpleNamespace(empty_values=(), label_from_instance=lambda obj: getattr(obj, to_field_name)),
            queryset=SimpleNamespace(using=lambda _: SimpleNamespace(
                filter=lambda **_: [SimpleNamespace(**{to_field_name: v}) for v in value])))
        return super().optgroups(name, value, attr=attr)


class MyAutocompleteModelAdmin(admin.ModelAdmin):
    my_autocomplete_fields = {}

    def __init__(self, model, admin_site):
        super().__init__(model, admin_site)
        # Patch remote_field for AutocompleteJsonView.process_request
        for field_name, deferred_remote_field in self.my_autocomplete_fields.items():
            remote_field = deferred_remote_field.field
            self.model._meta.get_field(field_name).remote_field = SimpleNamespace(field_name=remote_field.attname,
                                                                                  model=remote_field.model)

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if 'widget' not in kwargs:
            if db_field.name in self.my_autocomplete_fields:
                kwargs['widget'] = MyAutocompleteSelectWidget(db_field, self.admin_site)
        return super().formfield_for_dbfield(db_field, request, **kwargs)

    def to_field_allowed(self, request, to_field):
        # Allow search fields that are not referenced by foreign key fields
        if to_field in self.search_fields:
            return True
        return super().to_field_allowed(request, to_field)


class MyAutocompleteJsonView(
    autocomplete.AutocompleteJsonView
):

    def get_queryset(self):
        # Patch get_limit_choices_to for non-foreign key field
        self.source_field.get_limit_choices_to = lambda: {}
        return super().get_queryset()

    def process_request(self, request):
        term, model_admin, source_field, to_field_name = super().process_request(request)
        # Store to_field_name for use in get_context_data
        self.to_field_name = to_field_name
        return term, model_admin, source_field, to_field_name

    def get_context_data(self, *, object_list=None, **kwargs):
        context_data = super().get_context_data(object_list=object_list, **kwargs)
        # Patch __str__ to use to_field_name for `str(obj)` in AutocompleteJsonView.get
        for obj in context_data['object_list']:
            obj_type = type(obj)
            new_obj_type = type(obj_type.__name__, (obj_type,),
                                {'__str__': lambda _self: getattr(_self, self.to_field_name),
                                 '__module__': obj_type.__module__})
            obj.__class__ = new_obj_type
        return context_data


def base36encode(number, alphabet='0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'):
    """Converts an integer to a base36 string."""
    if not isinstance(number, int):
        raise TypeError('number must be an integer')

    base36 = ''
    sign = ''

    if number < 0:
        sign = '-'
        number = -number

    if 0 <= number < len(alphabet):
        return sign + alphabet[number]

    while number != 0:
        number, i = divmod(number, len(alphabet))
        base36 = alphabet[i] + base36

    return sign + base36


class ExtendedActionsMixin:
    # actions that can be executed with no items selected on the admin change list.
    # The filtered queryset displayed to the user will be used instead
    extended_actions = []

    def changelist_view(self, request, extra_context=None):
        # if a extended action is called and there's no checkbox selected, select one with
        # invalid id, to get an empty queryset
        if "action" in request.POST and request.POST["action"] in self.extended_actions:
            if not request.POST.getlist(admin.helpers.ACTION_CHECKBOX_NAME):
                post = request.POST.copy()
                post.update({admin.helpers.ACTION_CHECKBOX_NAME: 0})
                request._set_post(post)  # pylint:disable=protected-access
        return super().changelist_view(request, extra_context)

    def get_changelist_instance(self, request):
        """
        Returns a simple ChangeList view instance of the current ModelView.
        (It's a simple instance since we don't populate the actions and list filter
        as expected since those are not used by this class)
        """
        list_display = self.get_list_display(request)
        list_display_links = self.get_list_display_links(request, list_display)
        list_filter = self.get_list_filter(request)
        search_fields = self.get_search_fields(request)
        list_select_related = self.get_list_select_related(request)

        change_list = self.get_changelist(request)

        return change_list(
            request,
            self.model,
            list_display,
            list_display_links,
            list_filter,
            self.date_hierarchy,
            search_fields,
            list_select_related,
            self.list_per_page,
            self.list_max_show_all,
            self.list_editable,
            self,
            self.sortable_by,
            search_help_text=None,
        )

    def get_filtered_queryset(self, request):
        """
        Returns a queryset filtered by the URLs parameters
        """
        change_list = self.get_changelist_instance(request)
        return change_list.get_queryset(request)
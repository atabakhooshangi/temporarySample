import inspect

from rest_framework.generics import GenericAPIView


class MultiplePaginationViewMixin(GenericAPIView):
    @property
    def paginator(self):
        """
        The paginator instance associated with the view, or `None`.
        """
        if not hasattr(self, '_paginator'):
            if self.pagination_class is None:
                self._paginator = None
            else:
                pagination_args = inspect.getfullargspec(self.pagination_class)
                if 'request' in pagination_args.args:
                    self._paginator = self.pagination_class(self.request)
                else:
                    self._paginator = self.pagination_class()
        return self._paginator
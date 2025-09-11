from django.utils.deprecation import MiddlewareMixin

class UserMiddleware(MiddlewareMixin):
    """
    Middleware for handling user-related request/response processing.
    """
    def process_request(self, request):
        # Add any custom user processing logic here
        return None

    def process_response(self, request, response):
        # Add any response processing here
        return response

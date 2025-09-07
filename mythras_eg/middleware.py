from django.conf import settings
from django.http import HttpResponse

class SimpleCorsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.allowed_origins = getattr(settings, "CORS_ALLOWED_ORIGINS", [])

    def __call__(self, request):
        response = self.get_response(request)

        origin = request.META.get("HTTP_ORIGIN")
        print(origin)
        if origin in self.allowed_origins:
            response["Access-Control-Allow-Origin"] = origin
            response["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            response["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
            response["Access-Control-Allow-Credentials"] = "true"

        if request.method == "OPTIONS":
            return HttpResponse(status=204, headers=response.headers)

        return response

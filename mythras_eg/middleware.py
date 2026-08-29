from django.conf import settings
from django.http import HttpResponse


PUBLIC_CORS_PATHS = (
    "/index_json/",
    "/party_index_json/",
    "/generate_enemies_json/",
    "/generate_party_json/",
)


class SimpleCorsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.allowed_origins = getattr(settings, "CORS_ALLOWED_ORIGINS", [])

    def __call__(self, request):
        if self._is_public_cors_path(request.path) and request.method == "OPTIONS":
            response = HttpResponse(status=204)
            self._add_public_cors_headers(response)
            return response

        response = self.get_response(request)

        if self._is_public_cors_path(request.path):
            self._add_public_cors_headers(response)
        elif request.META.get("HTTP_ORIGIN") in self.allowed_origins:
            origin = request.META.get("HTTP_ORIGIN")
            response["Access-Control-Allow-Origin"] = origin
            response["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            response["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
            response["Access-Control-Allow-Credentials"] = "true"

        if request.method == "OPTIONS":
            return HttpResponse(status=204, headers=response.headers)

        return response

    def _is_public_cors_path(self, path):
        path = path.split("?", 1)[0]
        return any(path.endswith(public_path) for public_path in PUBLIC_CORS_PATHS)

    def _add_public_cors_headers(self, response):
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        response["Access-Control-Allow-Headers"] = "Accept, Content-Type"

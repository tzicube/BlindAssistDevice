from django.http import JsonResponse


def health_check(request):
    return JsonResponse(
        {
            "service": "AiServer",
            "status": "ok",
        }
    )

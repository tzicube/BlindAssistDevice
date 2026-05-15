from django.urls import path

from .views import (
    aidemo_asset,
    aidemo_page,
    available_cameras,
    detectable_objects,
    health_check,
    object_search_config,
    webcam_alignment_stream,
)


urlpatterns = [
    path("", health_check, name="health-check"),
    path("demo/", aidemo_page, name="aidemo-page"),
    path("demo/<str:asset_name>", aidemo_asset, name="aidemo-asset"),
    path("api/cameras/", available_cameras, name="available-cameras"),
    path("api/detectable-objects/", detectable_objects, name="detectable-objects"),
    path("api/object-search/config/", object_search_config, name="object-search-config"),
    path("webcam/alignment-stream/", webcam_alignment_stream, name="webcam-alignment-stream"),
]

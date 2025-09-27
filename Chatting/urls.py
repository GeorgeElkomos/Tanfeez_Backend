from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import ChatParticipantsView, ChatThreadView

app_name = "Chatting"

urlpatterns = [
    # GET /chatting/participants/?transaction_id=123
    path("participants/", ChatParticipantsView.as_view(), name="participants"),
    # GET /chatting/thread/?transaction_id=123&user_id=45
    path("thread/", ChatThreadView.as_view(), name="thread"),
    # PUT, DELETE /chatting/message/<int:message_id>/
    path("message/<int:message_id>/", ChatThreadView.as_view(), name="message-detail"),
]

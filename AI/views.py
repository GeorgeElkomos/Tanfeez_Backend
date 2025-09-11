from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from Chatbot.main import orchestrate

class Chatbot_Request(APIView):
    """
    API view to handle chatbot requests.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Handle POST requests to the chatbot.
        """
        user_input = request.data.get('user_input', '')
        if not user_input:
            return Response({"error": "User input is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Here you would typically call your chatbot logic
        # For example: response = orchestrate(user_input)
        response = orchestrate(user_input, logs=False)

        return Response({"response": response}, status=status.HTTP_200_OK)
from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
# Create your views here.

import os
from openai import OpenAI

from AI.Agents.SQLAgent import analyze_sql_result, generate_sql_query
from AI.Agents.SQLAgent import Execute_Sql_Query




class AnalyzeView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        # Handle POST request for analysis

        User_input = request.data.get("input_data", "")

        if not User_input:
            return Response(
                {
                 "error": "Input data is required.",
                 "Message": "Please provide valid input data."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Here you would add your analysis logic
        ai_response, sql_result = analyze_sql_result(User_input)


        if ai_response:

            print("✅ DeepSeek Response:")
            print(ai_response)
            return Response(
                {
                    "Response": ai_response,
                    "SQL Result": sql_result
                },
                status=status.HTTP_200_OK
            )

        else:
            return Response({"error": "Failed to generate SQL query."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        #     return None

from rest_framework.response import Response
from rest_framework.views import APIView


class ExtendSessionTime(APIView):
    def post(self, request):
        request.session.modified = True
        expire = request.session.get_expiry_date().isoformat()
        return Response({"expire": expire}, status=200)


class GetSessionTime(APIView):
    def get(self, request):
        expire = request.session.get_expiry_date().isoformat()
        return Response({"expire": expire}, status=200)

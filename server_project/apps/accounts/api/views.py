from django.contrib.auth.models import Group
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import GroupProfile


class SessionTimeExtendView(APIView):
    def post(self, request):
        request.session.modified = True
        expire = request.session.get_expiry_date().isoformat()
        return Response({"expire": expire}, status=200)


class SessionTimeView(APIView):
    def get(self, request):
        expire = request.session.get_expiry_date().isoformat()
        return Response({"expire": expire}, status=200)


class PublishersView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not request.user.is_admin() and not request.user.is_publisher():
            return Response(
                {"error": "You don't have permission to view publishers."}, status=403
            )

        publisher_groups = Group.objects.filter(
            profile__type=GroupProfile.Type.PUBLISHER
        )
        publishers_by_group = [
            {
                "id": group.id,
                "name": group.name,
                "users": [
                    {
                        "id": user.id,
                        "username": user.username,
                        "full_name": user.get_korean_name(),
                    }
                    for user in group.user_set.all()
                ],
            }
            for group in publisher_groups
        ]
        return Response(publishers_by_group, status=200)

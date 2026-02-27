from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import IsAdmin, IsSupervisor

from .models import NotificationLog
from .serializers import NotificationLogSerializer, SendNotificationSerializer
from .services import send_zoom_message


class NotificationLogViewSet(viewsets.ReadOnlyModelViewSet):
    """通知ログ閲覧"""

    queryset = NotificationLog.objects.all()
    serializer_class = NotificationLogSerializer
    permission_classes = [IsSupervisor]
    filterset_fields = ["trigger", "is_sent"]
    ordering_fields = ["created_at"]

    @action(detail=False, methods=["post"], permission_classes=[IsAdmin])
    def send(self, request):
        """手動通知送信（管理者専用）"""
        serializer = SendNotificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        log = send_zoom_message(
            to_contact=serializer.validated_data["to_contact"],
            message=serializer.validated_data["message"],
            trigger=serializer.validated_data["trigger"],
        )
        return Response(
            NotificationLogSerializer(log).data,
            status=status.HTTP_201_CREATED,
        )

from rest_framework import serializers

from .models import NotificationLog


class NotificationLogSerializer(serializers.ModelSerializer):
    trigger_display = serializers.CharField(source="get_trigger_display", read_only=True)

    class Meta:
        model = NotificationLog
        fields = [
            "id",
            "trigger",
            "trigger_display",
            "recipient_zoom_account",
            "message",
            "is_sent",
            "error_message",
            "created_at",
        ]
        read_only_fields = "__all__"


class SendNotificationSerializer(serializers.Serializer):
    to_contact = serializers.EmailField()
    message = serializers.CharField(max_length=2000)
    trigger = serializers.ChoiceField(
        choices=NotificationLog.Trigger.choices,
    )

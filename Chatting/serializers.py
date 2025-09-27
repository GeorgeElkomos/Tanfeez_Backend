from rest_framework import serializers
from django.utils import timezone
from .models import Chat


class ChatSerializer(serializers.ModelSerializer):
    # Read-only usernames for convenience in list/detail responses
    user_from_username = serializers.CharField(
        source="user_from.username", read_only=True
    )
    user_to_username = serializers.CharField(source="user_to.username", read_only=True)
    can_edit = serializers.BooleanField(read_only=True)
    edit_history_display = serializers.SerializerMethodField(read_only=True)
    seen_status = serializers.SerializerMethodField(read_only=True)

    def get_edit_history_display(self, obj):
        """Format edit history for display"""
        if not obj.edit_history:
            return []
        return [
            {
                "message": entry["message"],
                "edited_at": entry["timestamp"],
                "edited_by": entry.get("edited_by"),
            }
            for entry in obj.edit_history
        ]

    def get_seen_status(self, obj):
        """Get formatted seen status"""
        return {
            "is_seen": obj.seen,
            "seen_at": obj.seen_at,
            "can_mark_as_seen": not obj.seen
            and obj.user_to == self.context["request"].user,
        }

    def validate_message(self, value):
        """Validate message content"""
        if not value or len(value.strip()) == 0:
            raise serializers.ValidationError(
                "Message cannot be empty or only whitespace"
            )
        if len(value) > 5000:
            raise serializers.ValidationError("Message cannot exceed 5000 characters")
        return value.strip()

    def validate(self, data):
        """Cross-field validation"""
        request = self.context.get("request")
        if not request:
            raise serializers.ValidationError("Request context is required")

        if request.method in ["POST", "PUT"]:
            # Set user_from to current user if not provided
            if "user_from" not in data:
                data["user_from"] = request.user

            # Prevent sending messages to yourself
            user_from = data["user_from"]
            user_to = data.get("user_to")
            if user_from == user_to:
                raise serializers.ValidationError("Cannot send message to yourself")

            # For PUT requests, verify ownership
            if request.method == "PUT" and self.instance:
                if self.instance.user_from != request.user:
                    raise serializers.ValidationError(
                        "You can only edit your own messages"
                    )
                if self.instance.is_deleted:
                    raise serializers.ValidationError("Cannot edit deleted messages")
                if not self.instance.can_edit:
                    raise serializers.ValidationError("Edit window has expired")

            # Validate transaction exists and is accessible to both users
            transaction = data.get("transaction")
            if transaction:
                if not (
                    transaction.from_department.user_set.filter(
                        id=user_from.id
                    ).exists()
                    or transaction.to_department.user_set.filter(
                        id=user_from.id
                    ).exists()
                ):
                    raise serializers.ValidationError(
                        "You don't have access to this transaction"
                    )

        return data

    class Meta:
        model = Chat
        fields = [
            "id",
            "user_from",
            "user_to",
            "user_from_username",
            "user_to_username",
            "transaction_id",
            "message",
            "original_message",
            "is_edited",
            "is_deleted",
            "timestamp",
            "last_modified",
            "can_edit",
            "edit_history_display",
            "seen_status",
        ]
        read_only_fields = [
            "id",
            "timestamp",
            "user_from_username",
            "user_to_username",
            "is_edited",
            "is_deleted",
            "original_message",
            "last_modified",
            "can_edit",
            "edit_history_display",
            "seen_status",
        ]

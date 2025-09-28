# Chatting/views.py
from django.db.models import Q, OuterRef, Subquery
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .models import Chat
from .serializers import ChatSerializer
from budget_management.models import xx_BudgetTransfer
from user_management.models import xx_User
from approvals.pagination import SmallResultsSetPagination
from user_management.models import xx_User


class ChatParticipantsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Returns all users that have previous chats linked with a specific transfer
        where the request.user is a participant (user_from or user_to).

        Query params:
        - transaction_id: required, the budget transfer transaction id
        """
        transaction_id = request.query_params.get("transaction_id")
        if not transaction_id:
            return Response(
                {"detail": "transaction_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            transaction_id = int(transaction_id)
        except (TypeError, ValueError):
            return Response(
                {"detail": "transaction_id must be an integer"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # All chats in this transaction where the current user is a participant
        user_chats_qs = Chat.objects.filter(transaction_id=transaction_id).filter(
            Q(user_from=request.user) | Q(user_to=request.user)
        )

        # Enforce that the requester must be part of a chat for this transaction
        if not user_chats_qs.exists():
            return Response(
                {
                    "detail": "You are not a participant in any chats for this transaction.",
                    "participants": [],
                },
                status=status.HTTP_200_OK,
            )

        # The set of counterpart user IDs the requester chatted with in this transaction
        counterpart_ids = set(
            user_chats_qs.filter(user_from=request.user).values_list(
                "user_to_id", flat=True
            )
        ) | set(
            user_chats_qs.filter(user_to=request.user).values_list(
                "user_from_id", flat=True
            )
        )

        if not counterpart_ids:
            return Response({"participants": []}, status=status.HTTP_200_OK)

        # Subquery for the last chat message between request.user and each counterpart in this transaction
        last_chat_subq = (
            Chat.objects.filter(
                transaction_id=transaction_id,
            )
            .filter(
                (Q(user_from=request.user) & Q(user_to=OuterRef("pk")))
                | (Q(user_to=request.user) & Q(user_from=OuterRef("pk")))
            )
            .order_by("-timestamp")
        )

        participants_qs = (
            xx_User.objects.filter(id__in=list(counterpart_ids))
            .annotate(
                last_message=Subquery(last_chat_subq.values("message")[:1]),
            )
            .annotate(
                last_message_at=Subquery(last_chat_subq.values("timestamp")[:1]),
            )
            .annotate(
                last_message_id=Subquery(last_chat_subq.values("id")[:1]),
            )
            .annotate(
                last_message_from_id=Subquery(
                    last_chat_subq.values("user_from_id")[:1]
                ),
            )
            .annotate(
                last_message_to_id=Subquery(last_chat_subq.values("user_to_id")[:1]),
            )
        )

        # Get unseen message counts for each participant
        unseen_counts = {}
        for user_id in counterpart_ids:
            unseen_count = Chat.objects.filter(
                transaction_id=transaction_id,
                user_from_id=user_id,
                user_to=request.user,
                seen=False,
                is_deleted=False,
            ).count()
            unseen_counts[user_id] = unseen_count

        data = [
            {
                "user_id": u.id,  # Renamed from 'id' to be more explicit
                "id": u.id,  # Keeping 'id' for backward compatibility
                "username": u.username,
                "last_message": u.last_message,
                "last_message_at": u.last_message_at,
                "last_message_id": u.last_message_id,
                "last_message_from_id": u.last_message_from_id,
                "last_message_to_id": u.last_message_to_id,
                "unseen_count": unseen_counts.get(u.id, 0),
            }
            for u in participants_qs
        ]

        return Response({"participants": data}, status=status.HTTP_200_OK)


class ChatThreadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Send a new message in a chat thread.

        Required POST data:
        - transaction_id: int
        - user_id: int (recipient user id)
        - message: str (the message content)
        """
        transaction_id = request.data.get("transaction_id")
        user_id = request.data.get("user_id")
        message = request.data.get("message")

        # Validate required fields
        if not all([transaction_id, user_id, message]):
            return Response(
                {"detail": "transaction_id, user_id, and message are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            transaction_id = int(transaction_id)
            user_id = int(user_id)
        except (TypeError, ValueError):
            return Response(
                {"detail": "transaction_id and user_id must be integers"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Verify recipient user exists
        try:
            recipient = xx_User.objects.get(id=user_id)
        except xx_User.DoesNotExist:
            return Response(
                {"detail": "Recipient user not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # Verify transaction exists
        transaction = xx_BudgetTransfer.objects.filter(
            transaction_id=transaction_id
        ).first()
        if not transaction:
            return Response(
                {"detail": "Transaction not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # Create the new chat message
        chat = Chat.objects.create(
            user_from=request.user,
            user_to=recipient,
            transaction=transaction,
            message=message,
        )

        serializer = ChatSerializer(chat, context={"request": request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def put(self, request, message_id):
        """Edit a message within 15 minutes of creation.

        Required PUT data:
        - message: str (the new message content)
        """
        try:
            chat = Chat.objects.get(id=message_id, user_from=request.user)
        except Chat.DoesNotExist:
            return Response(
                {"detail": "Message not found or you're not the sender"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Check if message is already deleted
        if chat.is_deleted:
            return Response(
                {"detail": "Cannot edit a deleted message"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check if message is within 15-minute edit window
        if not chat.can_edit:
            return Response(
                {
                    "detail": "Message can no longer be edited (15-minute limit exceeded)"
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        new_message = request.data.get("message", "").strip()
        if not new_message:
            return Response(
                {"detail": "New message content is required and cannot be empty"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check if the new message is different from the current one
        if new_message == chat.message:
            return Response(
                {"detail": "New message is identical to the current one"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Store edit history
        if not chat.is_edited:
            chat.original_message = chat.message
            chat.edit_history = []

        chat.edit_history.append(
            {
                "message": chat.message,
                "timestamp": timezone.now().isoformat(),
                "edited_by": request.user.username,
            }
        )

        chat.message = new_message
        chat.is_edited = True
        chat.save(
            update_fields=[
                "message",
                "is_edited",
                "edit_history",
                "original_message",
                "last_modified",
            ]
        )

        serializer = ChatSerializer(chat, context={"request": request})
        return Response(serializer.data)

    def delete(self, request, message_id):
        """Soft delete a message within 15 minutes of creation."""
        try:
            chat = Chat.objects.get(id=message_id, user_from=request.user)
        except Chat.DoesNotExist:
            return Response(
                {"detail": "Message not found or you're not the sender"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Check if message is within 15-minute edit window
        if not chat.can_edit:
            return Response(
                {
                    "detail": "Message can no longer be deleted (15-minute limit exceeded)"
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        chat.is_deleted = True
        chat.save()

        serializer = ChatSerializer(chat, context={"request": request})
        return Response(serializer.data)

    def get(self, request):
        """
        Return paginated chat messages between request.user and another user
        for a given transaction.

        Query params:
        - transaction_id: required, int
        - user_id: required, int (counterpart user id)
        - page, page_size: optional (pagination)
        """
        transaction_id = request.query_params.get("transaction_id")
        user_id = request.query_params.get("user_id")

        if not transaction_id or not user_id:
            return Response(
                {"detail": "transaction_id and user_id are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            transaction_id = int(transaction_id)
            user_id = int(user_id)
        except (TypeError, ValueError):
            return Response(
                {"detail": "transaction_id and user_id must be integers"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Optional: ensure the other user exists (avoid leaking that they don't)
        try:
            xx_User.objects.only("id").get(id=user_id)
        except xx_User.DoesNotExist:
            return Response(
                {"detail": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )

        qs = (
            Chat.objects.select_related("user_from", "user_to")
            .filter(transaction_id=transaction_id)
            .filter(
                (Q(user_from=request.user) & Q(user_to_id=user_id))
                | (Q(user_to=request.user) & Q(user_from_id=user_id))
            )
            .order_by("-timestamp")
        )

        # Modify message content for deleted messages in the queryset
        for chat in qs:
            if chat.is_deleted:
                chat.message = "This message has been deleted"

        # Mark unseen messages as seen
        now = timezone.now()
        unseen_messages = qs.filter(user_to=request.user, seen=False)
        if unseen_messages.exists():
            unseen_messages.update(seen=True, seen_at=now)

        paginator = SmallResultsSetPagination()
        page = paginator.paginate_queryset(qs, request, view=self)
        serializer = ChatSerializer(page, many=True, context={"request": request})
        return paginator.get_paginated_response(serializer.data)

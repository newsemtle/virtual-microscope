import json

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from apps.database.models import Slide


class SlideConsumer(AsyncWebsocketConsumer):
    def __init__(self):
        super().__init__()
        self.group_name = None
        self.user = None
        self.slide = None

    async def connect(self):
        slide_id = int(self.scope["url_route"]["kwargs"]["slide_id"])

        self.user = self.scope["user"]
        self.slide = await sync_to_async(Slide.objects.get)(id=slide_id)

        if not self.user.is_authenticated or not await sync_to_async(
            self.slide.user_can_view
        )(self.user):
            await self.close()
            return

        self.group_name = f"slide_{slide_id}"

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if self.group_name:
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def slide_initialized(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "event": "slide_initialized",
                    "status": event["status"],
                    "slide_id": self.slide.id,
                    "slide_name": self.slide.name,
                }
            )
        )

    async def progress_update(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "event": "progress_update",
                    "status": event["status"],
                    "progress": event["progress"],
                    "slide_id": self.slide.id,
                    "slide_name": self.slide.name,
                }
            )
        )

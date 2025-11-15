import logging
import os
import sys

import httpx
import uvicorn
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import BasePushNotificationSender, InMemoryPushNotificationConfigStore, InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
)
from app.agent import ElliotAgent
from app.agent_executor import ElliotAgentExecutor

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MissingAPIKeyError(Exception):
    """Exception for missing API key."""


def main():
    """Starts Elliot's Agent server."""
    host = "localhost"
    port = 10004
    try:
        if not os.getenv("GOOGLE_API_KEY"):
            raise MissingAPIKeyError("GOOGLE_API_KEY environment variable not set.")

        capabilities = AgentCapabilities(streaming=True, pushNotifications=True)
        skill = AgentSkill(
            id="schedule_pickleball",
            name="Pickleball Scheduling Tool",
            description="Helps with finding Elliot's availability for pickleball",
            tags=["scheduling", "pickleball"],
            examples=["Are you free to play pickleball on Saturday?"],
        )
        agent_card = AgentCard(
            name="Elliot Agent",
            description="Helps with scheduling pickleball games",
            url=f"http://{host}:{port}/",
            version="1.0.0",
            defaultInputModes=ElliotAgent.SUPPORTED_CONTENT_TYPES,
            defaultOutputModes=ElliotAgent.SUPPORTED_CONTENT_TYPES,
            capabilities=capabilities,
            skills=[skill],
        )

        # http request handlerer
        httpx_client = httpx.AsyncClient()
        request_handler = DefaultRequestHandler(
            agent_executor=ElliotAgentExecutor(),
            task_store=InMemoryTaskStore(),
            push_config_store=InMemoryPushNotificationConfigStore(),
            push_sender=BasePushNotificationSender(
                httpx_client, InMemoryPushNotificationConfigStore()
            ),  # for streaming, making it faster
        )

        # run the server
        server = A2AStarletteApplication(
            agent_card=agent_card, http_handler=request_handler
        )

        app = server.build()
        logger.info(f"Registered routes: {[route.path for route in app.routes]}")

        uvicorn.run(app, host=host, port=port)

    except MissingAPIKeyError as e:
        logger.error(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"An error occurred during server startup: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

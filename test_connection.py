import asyncio
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("TestConnection")

try:
    import websockets
except ImportError:
    logger.error("Websockets not installed. Run 'pip install websockets'")
    sys.exit(1)

SERVER_URL = "ws://127.0.0.1:8989"

async def test_connection():
    logger.info(f"Starting connection test to {SERVER_URL}...")
    
    try:
        logger.debug("Calling websockets.connect()...")
        async with websockets.connect(SERVER_URL, ping_timeout=5) as ws:
            logger.info("✅ Connection ESTABLISHED successfully!")
            
            # Wait for initial "registered" message
            logger.debug("Waiting for server messages...")
            try:
                # Expecting at least 3 initial messages: registered, players_update, chat_update
                for i in range(3):
                    msg = await asyncio.wait_for(ws.recv(), timeout=2.0)
                    logger.info(f"📩 Received Message {i+1}: {msg}")
            except asyncio.TimeoutError:
                logger.warning("Timed out waiting for initial server welcome messages.")

            # Send a test update
            test_msg = '{"type": "player_update", "x": 100, "y": 100, "map": "test_map", "direction": "down", "moving": false}'
            logger.info(f"📤 Sending test update: {test_msg}")
            await ws.send(test_msg)
            
            logger.info("Update sent. Waiting 1 second...")
            await asyncio.sleep(1.0)
            
            logger.info("Test finished. Closing connection...")
            
    except ConnectionRefusedError:
        logger.error("❌ Connection REFUSED. Is the server running? Is the port 8989 open?")
    except TimeoutError:
        logger.error("❌ Connection TIMED OUT. Firewall blocking?")
    except Exception as e:
        logger.error(f"❌ Connection FAILED with error: {type(e).__name__}: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(test_connection())
    except KeyboardInterrupt:
        logger.info("Test cancelled.")

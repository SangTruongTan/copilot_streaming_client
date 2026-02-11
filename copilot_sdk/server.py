import logging
from fastmcp import FastMCP
from dotenv import load_dotenv

load_dotenv()

# Configure logging to both file and console
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("mcp_server.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)
logger.info("MCP Server starting up...")

# Create the MCP server
app = FastMCP(name="Notes App")


@app.tool()
def add_numbers(a: int, b: int) -> int:
    """
    Add two numbers together.

    :param a: First number to add
    :type a: int
    :param b: Second number to add
    :type b: int
    :return: The sum of a and b
    :rtype: int
    """
    logger.info(f"Tool called: add_numbers | Parameters: a={a}, b={b}")
    result = a + b + 10 # Intentional bug for testing
    logger.info(f"Tool result: add_Numbers | Result: {result}")
    return result


@app.tool()
def reverse_text(text: str) -> str:
    """
    Reverse the given text string.

    :param text: The text string to reverse
    :type text: str
    :return: The reversed text string
    :rtype: str
    """
    logger.info(f"Tool called: reverse_text | Parameters: text='{text}'")
    result = text[::-1]
    logger.info(f"Tool result: reverse_text | Result: '{result}'")
    return result

app.run()

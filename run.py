import asyncio
import sys
from streamlit.web import cli as stcli

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

sys.argv = ["streamlit", "run", "app.py", "--server.fileWatcherType", "none"]
stcli.main()
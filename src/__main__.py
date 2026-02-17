"""Allow running as: python -m src.bridge"""
import asyncio
from .bridge import main

asyncio.run(main())

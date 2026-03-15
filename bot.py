"""Launcher — Railway executes 'python bot.py' from /app."""
import sys
import os

bot_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bot")
sys.path.insert(0, bot_dir)

from main import main
main()

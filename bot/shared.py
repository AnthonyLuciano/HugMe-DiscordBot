bot_instance = None

def set_bot_instance(bot):
    global bot_instance
    bot_instance = bot

def get_bot_instance():
    return bot_instance
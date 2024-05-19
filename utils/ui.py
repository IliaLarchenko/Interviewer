def add_interviewer_message(message):
    def f(chat, skip=False):
        if not skip:
            chat.append((None, message))
        return chat

    return f


def add_candidate_message(message, chat):
    if message and len(message) > 0:
        chat.append((message, None))
    return chat


def get_status_color(obj):
    if obj.status:
        if obj.streaming:
            return "🟢"
        return "🟡"
    return "🔴"

def add_interviewer_message(message):
    def f(chat, skip=False):
        if not skip:
            chat.append((None, message))
        return chat

    return f


def add_candidate_message(message, chat):
    chat.append((message, None))
    return chat

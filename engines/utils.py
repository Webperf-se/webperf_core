# -*- coding: utf-8 -*-


def use_website(current_index, skip, take):
    if skip > 0 and current_index < skip:
        return False

    if take != -1 and current_index >= (skip + take):
        return False

    return True
